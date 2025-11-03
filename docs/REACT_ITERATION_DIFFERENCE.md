# ReAct Agent Iteration Count Difference: Gemini vs Llama

## Problem Statement

When running the research agent:
- **Gemini**: Performs 4-5 ReAct iterations with multiple web searches
- **Llama**: Performs only 1 iteration with minimal research

This document explains why this happens and how to fix it.

---

## Root Cause: Structured Output Configuration

The difference in iteration behavior is caused by **structured output enforcement**:

### Code Location

`src/agent/research_agent.py`, lines 383-391:

```python
response_format = CompanyInfo if self.model_type != "local" else None

return create_agent(
    model=chat_model,
    tools=TOOLS,
    system_prompt=self._system_prompt,
    middleware=middleware,
    response_format=response_format,
)
```

### How Structured Output Affects Iterations

#### With Structured Output (Gemini, OpenAI, Anthropic)

1. **Agent starts** with task: "Research company X"
2. **Iteration 1**: Agent realizes it needs data, calls `web_search_tool`
3. **Agent evaluates**: "Do I have enough data to satisfy the CompanyInfo schema?"
   - Missing: revenue, competitors, funding_stage, etc.
   - **Decision**: Continue researching
4. **Iteration 2**: Agent makes another web search for missing data
5. **Iteration 3-4**: More targeted searches for specific fields
6. **Final iteration**: Agent has sufficient data, returns structured JSON

**Key point**: The agent MUST gather enough data to populate the required fields in the `CompanyInfo` schema.

#### Without Structured Output (Llama)

1. **Agent starts** with task: "Research company X"
2. **Iteration 1**: Agent calls `web_search_tool`, gets some basic info
3. **Agent evaluates**: "I have some information about the company"
   - No schema enforcement requiring specific fields
   - **Decision**: This is sufficient, generate response
4. **Agent returns**: Whatever text it considers complete

**Key point**: Without schema enforcement, the agent stops as soon as it has *any* reasonable answer.

---

## Why Structured Output is Disabled for Local Models

Local models (Llama) have structured output disabled because:

### 1. **Technical Limitations**
- `ChatLlamaCpp` doesn't fully support LangChain's structured output API
- Requires special JSON mode or grammar-based constraints
- May not consistently produce valid JSON for complex schemas

### 2. **Performance Concerns**
- Structured output requires more sophisticated prompting
- Local models may generate invalid JSON that fails parsing
- Retry logic could slow down execution significantly

### 3. **Context Window Constraints**
- Embedding the full schema in the prompt uses tokens
- Local models (8K context) have less room than remote models (128K+)
- Complex schemas like `CompanyInfo` (20+ fields) add prompt overhead

---

## Solutions

### ✅ Solution 1: Use ToolStrategy for Llama (Correct Implementation)

**Status**: Implemented correctly using LangChain v1 structured output strategies.

**Previous Issue**:
```
Tool choice tool_choice='any' was specified, but the only provided tools were 
['web_search_tool', 'CompanyInfo'].
```

**Root Cause Identified**: We were passing `response_format=CompanyInfo` directly, but **LangChain v1 requires explicit strategy selection**:
- `ToolStrategy`: Uses "artificial tool calling" for structured output (works with ANY model that supports tool calling)
- `ProviderStrategy`: Uses provider-native structured output (only for OpenAI, Anthropic, Gemini)

**The Fix** (from LangChain docs):
```python
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy

# For local models (ChatLlamaCpp)
response_format = ToolStrategy(CompanyInfo)

# For remote models (Gemini, OpenAI, Anthropic)
response_format = ProviderStrategy(CompanyInfo)
```

**How ToolStrategy Works**:
- Treats the `CompanyInfo` schema as a special "tool"
- Model must "call" this tool to finish (enforces structured output)
- Works with ChatLlamaCpp since it supports tool calling ✅
- This naturally enforces multiple iterations (model can't finish without calling the schema "tool")

**Testing**:
```bash
# Test with diagnostic mode enabled
python -c "
from src.agent.research_agent import ResearchAgent
agent = ResearchAgent(model_type='local', verbose=True, enable_diagnostics=True)
result = agent.research_company('BitMovin')
print(f'Iterations: {result.iterations}')
"
```

---

### ✅ Solution 2: Improve Prompt to Encourage Multiple Iterations (Applied)

**Status**: Code has been updated to enhance the system prompt with explicit iteration guidance.

Even without structured output, we modified the prompts to encourage more thorough research.

#### Current System Prompt Weakness

Current prompt says:
```
"You are a focused company research analyst following the ReAct pattern. 
Think step-by-step, decide whether a web search is required, and only 
produce answers grounded in retrieved evidence."
```

**Problem**: Doesn't explicitly tell the model to:
- Make multiple searches
- Verify it has all required information
- Continue until comprehensive

#### Proposed Enhanced System Prompt

Add to `_build_system_prompt()` in `src/agent/research_agent.py`:

```python
"You are a focused company research analyst following the ReAct pattern. "
"Think step-by-step, decide whether a web search is required, and only "
"produce answers grounded in retrieved evidence.\n\n"
"IMPORTANT RESEARCH PROCESS:\n"
"1. Start with a general company overview search\n"
"2. Make additional searches for missing information\n"
"3. Search for specific data points: size, revenue, competitors, funding\n"
"4. Verify you have comprehensive information before finishing\n"
"5. Make AT LEAST 3-4 web searches to ensure thorough research\n\n"
"DO NOT provide a final answer until you have:\n"
"- Company basics (name, website, location, founded)\n"
"- Business details (products, services, description)\n"
"- Size/scale data (employees, revenue if available)\n"
"- Market context (competitors, industry position)\n\n"
```

---

### ⚠️ Solution 3: Add Minimum Iteration Middleware (Attempted - Limited Success)

**Status**: Code has been implemented but doesn't work as expected due to LangChain architecture limitations.

**Issue**: LangChain's agent system makes finish/continue decisions internally and middleware cannot override them. Returning modified state from `after_model` doesn't prevent the agent from finishing when it decides to.

Created middleware that attempts to ensure a minimum number of iterations before allowing completion, but the agent ignores the continuation requests.

**New file**: `src/agent/min_iteration_middleware.py`

```python
from langchain.agents.middleware.types import AgentMiddleware, AgentState
from typing import Any, Optional, Dict

class MinimumIterationMiddleware(AgentMiddleware[AgentState, None]):
    """Middleware that prevents agent from finishing too early."""
    
    def __init__(self, min_iterations: int = 3):
        super().__init__()
        self.min_iterations = min_iterations
        self._iteration_count = 0
    
    def before_agent(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Track iterations."""
        self._iteration_count += 1
        return None
    
    def after_agent(self, state: AgentState, runtime: Any) -> Optional[Dict[str, Any]]:
        """Force continuation if below minimum iterations."""
        if self._iteration_count < self.min_iterations:
            # Check if agent is trying to finish
            messages = state.get("messages", [])
            if messages and not hasattr(messages[-1], "tool_calls"):
                # Agent generated a final answer - reject it
                return {
                    "messages": messages[:-1],  # Remove final answer
                    "continue": True,  # Force another iteration
                }
        return None
```

**Usage** in `research_agent.py`:

```python
from src.agent.min_iteration_middleware import MinimumIterationMiddleware

middleware = [
    self._step_tracker,
    MinimumIterationMiddleware(min_iterations=3),  # NEW
    ModelCallLimitMiddleware(run_limit=self.max_iterations, exit_behavior="end"),
    ToolCallLimitMiddleware(run_limit=self.max_iterations, exit_behavior="end"),
]
```

---

### 📊 Solution 4: Post-Process and Auto-Retry

Detect when Llama provides insufficient information and automatically retry with more specific prompts.

**Implementation**: Add to `ResearchAgent.research_company()`:

```python
def research_company(self, company_name: str) -> ResearchAgentResult:
    """Research company with auto-retry for insufficient results."""
    
    result = self._execute_research(company_name)
    
    # Check if result is insufficient (only works for local models)
    if self.model_type == "local" and result.iterations < 3:
        missing_fields = self._check_missing_critical_fields(result.company_info)
        
        if missing_fields:
            # Retry with more specific prompt
            enhanced_prompt = (
                f"Continue researching {company_name}. "
                f"Previous search was incomplete. Focus on finding: "
                f"{', '.join(missing_fields)}"
            )
            result = self._execute_research(company_name, enhanced_prompt=enhanced_prompt)
    
    return result

def _check_missing_critical_fields(self, company_info: Optional[CompanyInfo]) -> List[str]:
    """Check which critical fields are missing."""
    if not company_info:
        return ["all fields"]
    
    missing = []
    critical_fields = ["company_size", "revenue", "competitors", "products"]
    
    for field in critical_fields:
        value = getattr(company_info, field, None)
        if not value or (isinstance(value, list) and len(value) == 0):
            missing.append(field)
    
    return missing
```

---

## Recommendations

### For Production Use

**UPDATED Solution**: Use **ToolStrategy** for local models (Solution 1 properly implemented)

1. ✅ **Solution 1 FIXED**: Use `ToolStrategy(CompanyInfo)` for ChatLlamaCpp (enforces structured output via artificial tool calling)
2. ✅ **Solution 2 Implemented**: Enhanced system prompt encourages thorough research  
3. ✅ **Solution 3 Implemented**: Minimum iteration middleware with `jump_to="model"` as backup
4. 🧪 **Testing Required**: Verify Llama performs 3+ iterations with ToolStrategy

**Expected Result**: With `ToolStrategy`, ChatLlamaCpp should match Gemini's 3-5 iterations since the model must "call" the CompanyInfo schema to finish, enforcing comprehensive research.

### For Development/Testing

Use **Solution 3** (minimum iteration middleware) as a safeguard to ensure comprehensive research during development.

### Quick Fix (Already Done)

The code has been updated to enable structured output for all models. Test this first before adding additional complexity.

---

## Testing & Validation

### Test Script

```bash
# Test Llama with diagnostics
python scripts/test_llama_diagnostics.py BitMovin --max-iterations 10

# Expected output:
# - 3-5 iterations (not just 1)
# - Multiple web_search_tool calls
# - Complete CompanyInfo JSON at the end
```

### Success Criteria

- ✅ Llama performs **3+ iterations** (not just 1)
- ✅ Multiple web searches executed (4-5 tool calls)
- ✅ Comprehensive data gathered (all critical fields populated)
- ✅ Valid JSON output matching CompanyInfo schema

---

## Related Files

- `src/agent/research_agent.py` - Main agent logic (MODIFIED)
- `src/tools/models.py` - CompanyInfo schema definition
- `prompts/research-agent-prompt.md` - Research instructions
- `src/models/model_factory.py` - Model initialization
- `docs/TRUNCATION_ISSUE_RESOLVED.md` - Related GPU/performance issue

---

## Additional Notes

### Why This Matters

**For Linode Blog/Tutorial**: This is an important lesson about LLM behavior differences:
- Remote models (Gemini, GPT-4) have built-in structured output support
- Local models require explicit prompting and constraints
- Agent iteration count is not just about "intelligence" but about configuration

**Educational Value**: Shows learners how to:
- Debug unexpected agent behavior
- Configure agents differently for local vs remote models
- Use middleware to control agent execution flow

---

**Status**: ✅ **SOLUTION FOUND - ToolStrategy for Local Models**  
**Last Updated**: 2025-11-03  
**Changes Applied**:
- ✅ Solution 1: Use `ToolStrategy(CompanyInfo)` for local models, `ProviderStrategy(CompanyInfo)` for remote
- ✅ Solution 2: Enhanced system prompt with explicit iteration requirements
- ✅ Solution 3: Minimum iteration middleware with `@hook_config(can_jump_to=["model"])` and `jump_to="model"`

**Key Discovery**: LangChain v1 documentation revealed that:
- **ChatLlamaCpp DOES support structured output via `ToolStrategy`** ✅
- Must explicitly wrap schema: `ToolStrategy(CompanyInfo)` not just `CompanyInfo`
- `ToolStrategy` treats schema as an "artificial tool" the model must call to finish
- This naturally enforces multiple iterations (model can't finish without comprehensive data)

**Expected Result**:
- Llama should now perform **3-5 iterations** matching Gemini
- Structured output enforcement works the same way (tool calling mechanism)
- Middleware provides backup enforcement via `jump_to="model"`

**Next Steps**: Deploy and test to verify Llama matches Gemini's iteration count

