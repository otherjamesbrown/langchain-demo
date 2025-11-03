# Structured Output Strategies: ToolStrategy vs ProviderStrategy

## Overview

LangChain v1 provides two strategies for generating structured output from LLM agents:
- **ToolStrategy**: Uses artificial tool calling to generate structured output
- **ProviderStrategy**: Uses the model provider's native structured output generation

Both strategies ensure the agent returns data matching a specific schema (Pydantic model, JSON schema, etc.), but they work differently under the hood.

---

## ToolStrategy

### How It Works
1. LangChain creates an **artificial tool** based on your schema (e.g., `CompanyInfo`)
2. The model is instructed to call this tool with the structured data as parameters
3. LangChain intercepts the tool call and extracts the structured data
4. The data is validated against the schema

### Advantages
- ✅ **Universal Compatibility**: Works with any model that supports tool calling
- ✅ **No Provider Dependency**: Doesn't require special provider features
- ✅ **Flexible**: Can be used with local models (if they support tool calling)

### Disadvantages
- ⚠️ **Extra LLM Call**: Requires the model to generate a tool call, which uses tokens
- ⚠️ **Slightly More Complex**: The agent sees an extra "tool" in its tool list
- ⚠️ **Potential for Errors**: Model might call the tool incorrectly or multiple times

### Model Support
Works with **any model that supports tool calling**, including:
- OpenAI (GPT-3.5, GPT-4, GPT-4 Turbo, etc.)
- Anthropic (Claude 3 Opus, Sonnet, Haiku)
- Google Gemini (Gemini Pro, Gemini Flash)
- Local models with tool calling support (e.g., some Llama models via ChatLlamaCpp)
- Any model with `tool_choice` parameter support

### Example
```python
from langchain.agents.structured_output import ToolStrategy
from langchain.agents import create_agent
from pydantic import BaseModel

class CompanyInfo(BaseModel):
    company_name: str
    industry: str
    company_size: str

agent = create_agent(
    model="gpt-4o-mini",
    tools=[web_search_tool],
    response_format=ToolStrategy(CompanyInfo)
)
```

---

## ProviderStrategy

### How It Works
1. LangChain uses the **provider's native structured output API**
2. The provider enforces the schema directly in the model's response generation
3. The structured data is returned directly from the provider's API
4. LangChain validates the response

### Advantages
- ✅ **More Efficient**: No artificial tool call needed, uses fewer tokens
- ✅ **More Reliable**: Provider handles schema enforcement directly
- ✅ **Better Performance**: Often faster since it's a native feature
- ✅ **Cleaner Output**: No tool call artifacts in the response

### Disadvantages
- ❌ **Limited Provider Support**: Only works with providers that have native structured output
- ❌ **Vendor Lock-in**: Tied to specific provider implementations
- ❌ **Version Dependent**: Requires specific model versions that support the feature

### Model Support
Only works with providers that have **native structured output generation**:

**✅ Supported:**
- **OpenAI**: GPT-4o, GPT-4 Turbo, GPT-4, GPT-3.5 Turbo (structured output mode)
- **Anthropic**: Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku
- **Google Gemini**: Gemini Pro, Gemini Flash (via native structured output)
- **Grok**: xAI's Grok models

**❌ NOT Supported:**
- Local models (Llama, Mistral, etc.)
- Models without native structured output APIs
- Older model versions without the feature

### Example
```python
from langchain.agents.structured_output import ProviderStrategy
from langchain.agents import create_agent
from pydantic import BaseModel

class CompanyInfo(BaseModel):
    company_name: str
    industry: str
    company_size: str

agent = create_agent(
    model="gpt-4o",
    tools=[web_search_tool],
    response_format=ProviderStrategy(CompanyInfo)
)
```

---

## Quick Comparison Table

| Feature | ToolStrategy | ProviderStrategy |
|---------|-------------|------------------|
| **Compatibility** | Any model with tool calling | Only providers with native support |
| **Token Efficiency** | Less efficient (uses tool call) | More efficient (direct generation) |
| **Reliability** | Good (but can have tool call issues) | Excellent (native enforcement) |
| **Performance** | Slightly slower | Faster |
| **Local Models** | ✅ Supported (if tool calling works) | ❌ Not supported |
| **Provider Lock-in** | No | Yes |
| **Complexity** | Medium | Low (for user) |

---

## How LangChain Auto-Selects Strategy

If you pass a schema directly (without wrapping in ToolStrategy/ProviderStrategy), LangChain automatically chooses:

```python
# Auto-selection based on model capabilities
agent = create_agent(
    model="gpt-4o",
    tools=[...],
    response_format=CompanyInfo  # LangChain picks ProviderStrategy for GPT-4o
)

agent = create_agent(
    model="gpt-4o-mini",
    tools=[...],
    response_format=CompanyInfo  # LangChain picks ToolStrategy for GPT-4o-mini
)
```

**Selection logic:**
- If model supports **native structured output** → Uses `ProviderStrategy`
- Otherwise → Uses `ToolStrategy`

---

## Known Issues & Limitations

### ChatLlamaCpp Limitation

**Issue**: Local models using `ChatLlamaCpp` cannot use structured output strategies because:

1. **ToolStrategy fails**: Requires `tool_choice` parameter, which ChatLlamaCpp doesn't support
   - Error: `tool_choice='any' was specified, but the only provided tools were...`

2. **ProviderStrategy fails**: ChatLlamaCpp doesn't have native structured output support

**Solution**: Must rely on:
- Prompt engineering to encourage structured responses
- Manual parsing of raw text output
- Fallback extraction logic

**Code Reference**: See `docs/troubleshooting/REACT_ITERATION_DIFFERENCE.md` for full details.

---

## Recommendation Matrix

### Use ProviderStrategy when:
- ✅ Using OpenAI GPT-4o, GPT-4 Turbo, or GPT-4
- ✅ Using Anthropic Claude 3 models
- ✅ Using Google Gemini (Gemini Pro/Flash)
- ✅ You want maximum reliability and efficiency
- ✅ You're okay with vendor lock-in

### Use ToolStrategy when:
- ✅ Using models without native structured output (e.g., GPT-4o-mini)
- ✅ Need maximum compatibility across different models
- ✅ Working with models that support tool calling but not native structured output
- ✅ You want a fallback that works everywhere

### Use neither (manual parsing) when:
- ❌ Using local models without tool calling support (e.g., ChatLlamaCpp)
- ❌ ProviderStrategy not available and ToolStrategy causes errors
- ✅ You need maximum flexibility and are okay with less reliable extraction

---

## Implementation in This Project

**Current Strategy** (`src/agent/research_agent.py`):

```python
if self.model_type == "local":
    # Local models: No structured output (ChatLlamaCpp limitations)
    response_format = None
else:
    # Remote models: Use ProviderStrategy (native structured output)
    response_format = ProviderStrategy(CompanyInfo)
```

**Why this choice:**
- Remote models (OpenAI, Anthropic, Gemini) all support ProviderStrategy
- ProviderStrategy is more reliable and efficient for these models
- Local models cannot use either strategy due to ChatLlamaCpp limitations

---

## References

- LangChain Structured Output Docs: https://docs.langchain.com/oss/python/langchain/structured-output
- ProviderStrategy Docs: https://docs.langchain.com/oss/python/langchain/agents
- ToolStrategy Docs: https://docs.langchain.com/oss/python/langchain/agents

---

**Last Updated**: 2025-01-XX  
**Related Docs**: `docs/troubleshooting/REACT_ITERATION_DIFFERENCE.md`

