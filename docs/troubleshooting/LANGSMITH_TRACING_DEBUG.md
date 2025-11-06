# LangSmith Tracing Debug Guide

## Where Traces Are Created

### 1. **LLM Calls (Automatic Tracing)**

LangChain LLM calls are **automatically traced** when:
- `LANGCHAIN_TRACING_V2=true` is set in environment
- `LANGCHAIN_API_KEY` is set
- You use LangChain LLM components (ChatOpenAI, ChatAnthropic, etc.)

**Location in code:**
- `src/research/llm_processor.py:103` - `llm.invoke(prompt, config={"callbacks": [callback]})`
- This should automatically create a trace in LangSmith

**To verify:**
```python
import os
print("LANGCHAIN_TRACING_V2:", os.getenv("LANGCHAIN_TRACING_V2"))
print("LANGCHAIN_API_KEY:", "SET" if os.getenv("LANGCHAIN_API_KEY") else "NOT SET")
```

### 2. **Context Managers (Manual Tracing)**

The context managers (`langsmith_trace`, `langsmith_phase_trace`) are meant to wrap non-LangChain code:

**Locations:**
- `src/research/query_generator.py` - Query generation (Phase 1)
- `src/research/search_executor.py` - Search execution (Phase 1)
- `src/research/prompt_builder.py` - Prompt building (Phase 2)
- `src/research/workflows.py` - Workflow orchestration

**Current Issue:**
The context managers currently only set environment variables and collect metadata. They don't create actual LangSmith traces for non-LangChain code.

### 3. **Callback Handler**

`EnhancedLangSmithCallback` tracks metrics but doesn't create traces - it's for monitoring within a trace.

**Location:**
- `src/research/llm_processor.py:82-92` - Creates callback for token/cost tracking

## Why You're Not Seeing Traces

### Most Likely Causes:

1. **`LANGCHAIN_TRACING_V2` not set**
   - Check: `os.getenv("LANGCHAIN_TRACING_V2")` should be `"true"`
   - Fix: Ensure `configure_langsmith_tracing()` is called before LLM calls

2. **LLM calls not using LangChain components**
   - If using raw API calls (not LangChain), they won't auto-trace
   - Fix: Use LangChain LLM wrappers (ChatOpenAI, etc.)

3. **Context managers not creating traces**
   - Current implementation only sets env vars
   - Fix: Need to use `@traceable` decorator or LangSmith Client API

4. **API key not set or invalid**
   - Check: `os.getenv("LANGCHAIN_API_KEY")` should be set
   - Fix: Add to `.env` file

## How to Fix

### For LLM Calls (Should Work Automatically):

1. Ensure `LANGCHAIN_TRACING_V2=true` is set:
```python
from src.utils.monitoring import configure_langsmith_tracing
configure_langsmith_tracing(project_name="research-agent")
```

2. Verify LLM is LangChain component:
```python
from langchain_openai import ChatOpenAI  # ✅ This traces automatically
# NOT: from openai import OpenAI  # ❌ This doesn't trace
```

3. Check trace appears in LangSmith dashboard

### For Non-LangChain Code:

Currently, the context managers don't create actual traces. To fix:

**Option 1: Use `@traceable` decorator on functions**
```python
from langsmith import traceable

@traceable(name="generate_queries", tags=["phase:search-collection"])
def generate_queries(company_name: str):
    # Your code
    pass
```

**Option 2: Use LangSmith Client API**
```python
from langsmith import Client

client = Client()
run = client.create_run(
    name="generate_queries",
    run_type="chain",
    tags=["phase:search-collection"]
)
```

## Verification Steps

1. **Check environment variables:**
```python
import os
print("LANGCHAIN_TRACING_V2:", os.getenv("LANGCHAIN_TRACING_V2"))
print("LANGCHAIN_API_KEY:", "SET" if os.getenv("LANGCHAIN_API_KEY") else "NOT SET")
print("LANGCHAIN_PROJECT:", os.getenv("LANGCHAIN_PROJECT"))
```

2. **Run a simple LLM test:**
```python
from langchain_openai import ChatOpenAI
from src.utils.monitoring import configure_langsmith_tracing

configure_langsmith_tracing(project_name="test")
llm = ChatOpenAI(model="gpt-3.5-turbo")
response = llm.invoke("Hello")
# Check LangSmith dashboard - should see a trace
```

3. **Check LangSmith dashboard:**
- Go to https://smith.langchain.com
- Look for project: "research-agent" or "test"
- Should see traces for LLM calls

## Current Implementation Status

✅ **LLM Calls**: Should trace automatically if `LANGCHAIN_TRACING_V2=true`  
⚠️ **Context Managers**: Currently only set env vars, don't create traces  
✅ **Callback Handler**: Tracks metrics within traces  

## Next Steps

1. Verify `LANGCHAIN_TRACING_V2=true` is set before LLM calls
2. Test with a simple LLM call to confirm traces appear
3. Update context managers to use `@traceable` decorator or Client API for non-LangChain code

