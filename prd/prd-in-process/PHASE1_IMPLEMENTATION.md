# Phase 1 Implementation: Core Infrastructure

**Status**: ✅ Complete  
**Date Completed**: 2025-11-06  
**Related PRD**: `PRD_LANGSMITH_OBSERVABILITY.md`

---

## Overview

Phase 1 establishes the core infrastructure for comprehensive LangSmith observability. This includes enhanced callback handlers, configuration utilities, and context managers for easy tracing integration.

## What Was Implemented

### 1. EnhancedLangSmithCallback Class

**File**: `src/utils/monitoring.py`

**Purpose**: Comprehensive callback handler that tracks all LangChain events with detailed metrics.

**Features**:
- ✅ LLM event tracking (start, end, error)
- ✅ Chat model event tracking
- ✅ Tool event tracking (start, end, error)
- ✅ Agent event tracking (actions, finish)
- ✅ Chain event tracking (start, end, error)
- ✅ Token usage tracking (prompt, completion, total)
- ✅ **Cost calculation** for API-based models (OpenAI, Anthropic, Gemini)
- ✅ Latency tracking for all operations
- ✅ Custom metadata support (company, phase, model, etc.)
- ✅ Error capture with full context
- ✅ Summary statistics and reporting

**Usage Example**:
```python
from src.utils.monitoring import EnhancedLangSmithCallback

# Create callback with metadata
callback = EnhancedLangSmithCallback(
    metadata={
        "company": "BitMovin",
        "phase": "llm-processing",
        "model": "gpt-4"
    },
    track_costs=True,
    verbose=True
)

# Use with LLM
response = llm.invoke(prompt, config={"callbacks": [callback]})

# Print summary
callback.print_summary()
```

**Cost Tracking**:
The callback automatically calculates costs for:
- **OpenAI**: GPT-4, GPT-3.5-turbo, GPT-4-turbo
- **Anthropic**: Claude 3 Opus, Sonnet, Haiku
- **Google Gemini**: Gemini Pro, 1.5 Pro, 1.5 Flash

Costs are based on current pricing (as of 2025) per 1M tokens.

### 2. configure_langsmith_tracing() Function

**File**: `src/utils/monitoring.py`

**Purpose**: Enhanced configuration function with support for custom projects, tags, and metadata.

**Features**:
- ✅ Automatic API key detection
- ✅ Custom project name configuration
- ✅ Global tags for all traces
- ✅ Global metadata for all traces
- ✅ Graceful degradation when LangSmith unavailable
- ✅ Verbose logging of configuration

**Usage Example**:
```python
from src.utils.monitoring import configure_langsmith_tracing

# Configure with custom settings
configure_langsmith_tracing(
    project_name="research-agent-phase2",
    tags=["phase:llm-processing", "production"],
    metadata={"version": "1.0", "environment": "production"},
    verbose=True
)
```

**Environment Variables**:
```bash
# Required
LANGCHAIN_API_KEY=ls__your_api_key_here

# Optional (set by function)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=research-agent
```

### 3. Context Managers for Tracing

**File**: `src/utils/monitoring.py`

**Purpose**: Simplify tracing setup with context managers that automatically handle configuration and error capture.

#### 3.1 langsmith_trace()

General-purpose context manager for tracing any code block.

**Usage Example**:
```python
from src.utils.monitoring import langsmith_trace

with langsmith_trace(
    name="process_company_data",
    tags=["data-processing", "company:bitmovin"],
    metadata={"model": "gpt-4", "temperature": 0.7}
) as trace:
    # Your code here
    result = process_company(company_data)
    
# After context, trace includes:
# - trace['duration']: Execution time
# - trace['success']: True/False
# - trace['error']: Error message if failed
```

#### 3.2 langsmith_phase_trace()

Specialized context manager for two-phase research workflow.

**Usage Example**:
```python
from src.utils.monitoring import langsmith_phase_trace

# Phase 1: Search Collection
with langsmith_phase_trace(
    phase="phase1",
    company_name="BitMovin"
) as trace:
    search_results = execute_searches(company)

# Phase 2: LLM Processing
with langsmith_phase_trace(
    phase="phase2",
    company_name="BitMovin",
    model_name="gpt-4"
) as trace:
    result = process_with_llm(company, search_results)
```

**Automatic Tagging**:
- `phase:search-collection` or `phase:llm-processing`
- `company:<company_name>`
- `model:<model_name>` (Phase 2 only)

**Automatic Metadata**:
- `phase`: Normalized phase name
- `company`: Company name
- `model`: Model name (Phase 2 only)
- `timestamp`: ISO format timestamp

### 4. Backward Compatibility

**Feature**: Legacy function and class names maintained.

- `configure_langsmith()` → calls `configure_langsmith_tracing()`
- `LangSmithCallback` → alias for `EnhancedLangSmithCallback`

This ensures existing code continues to work without modifications.

---

## Testing

### Test Script

**File**: `scripts/test_langsmith_basic.py`

**Purpose**: Comprehensive test suite for Phase 1 implementation.

**Tests Included**:
1. ✅ Configuration test (API key, environment setup)
2. ✅ OpenAI callback test (token usage, cost tracking)
3. ✅ Local LLM callback test (Llama support)
4. ✅ Context manager test (basic tracing)
5. ✅ Phase context manager test (Phase 1 & Phase 2)
6. ✅ Error handling test (error capture)

**Running the Tests**:
```bash
# Ensure environment variables are set
cd /Users/jabrown/Documents/GitHub/Linode/langchain-demo
source venv/bin/activate

# Run test script
python scripts/test_langsmith_basic.py

# Expected output:
# - Configuration status
# - Test LLM calls
# - Token usage and costs
# - Trace summaries
# - All tests passing
```

**Viewing Traces**:
1. Visit https://smith.langchain.com
2. Navigate to Projects
3. Open `langsmith-test-basic` project
4. Explore traces with tags, metadata, and metrics

---

## File Changes

### Modified Files

1. **`src/utils/monitoring.py`**
   - Added comprehensive module docstring
   - Enhanced imports (contextmanager, datetime, etc.)
   - Replaced basic `LangSmithCallback` with `EnhancedLangSmithCallback` (500+ lines)
   - Enhanced `configure_langsmith_tracing()` function
   - Added `langsmith_trace()` context manager
   - Added `langsmith_phase_trace()` context manager
   - Maintained backward compatibility

### New Files

2. **`scripts/test_langsmith_basic.py`**
   - Comprehensive test suite (400+ lines)
   - 6 test functions covering all features
   - Detailed output and instructions
   - Examples of usage patterns

3. **`prd/prd-in-process/PHASE1_IMPLEMENTATION.md`**
   - This file (implementation documentation)

### Configuration Files

4. **`config/env.example`** (already had LangSmith config)
   - ✅ LANGCHAIN_API_KEY
   - ✅ LANGCHAIN_TRACING_V2
   - ✅ LANGCHAIN_PROJECT

---

## Usage Guide

### Quick Start

1. **Set up LangSmith**:
```bash
# Get API key from https://smith.langchain.com
# Add to .env file:
echo "LANGCHAIN_API_KEY=ls__your_api_key_here" >> .env
```

2. **Basic usage**:
```python
from src.utils.monitoring import EnhancedLangSmithCallback

callback = EnhancedLangSmithCallback(
    metadata={"task": "my_task"},
    track_costs=True,
    verbose=True
)

response = llm.invoke(prompt, config={"callbacks": [callback]})
callback.print_summary()
```

3. **With context manager**:
```python
from src.utils.monitoring import langsmith_trace

with langsmith_trace(
    name="my_operation",
    tags=["production"],
    metadata={"user": "john"}
):
    # Your code here
    result = do_work()
```

### Integration Patterns

#### Pattern 1: Individual Function Tracing

```python
from src.utils.monitoring import langsmith_trace, EnhancedLangSmithCallback

def process_company(company_name: str):
    with langsmith_trace(
        name=f"process_{company_name}",
        tags=["processing", f"company:{company_name}"]
    ):
        callback = EnhancedLangSmithCallback(
            metadata={"company": company_name}
        )
        
        # Your LLM calls
        result = llm.invoke(prompt, config={"callbacks": [callback]})
        
        return result
```

#### Pattern 2: Workflow Tracing

```python
from src.utils.monitoring import langsmith_phase_trace

def phase1_workflow(company_name: str):
    with langsmith_phase_trace("phase1", company_name):
        # Search collection logic
        queries = generate_queries(company_name)
        results = execute_searches(queries)
        return results

def phase2_workflow(company_name: str, search_results):
    with langsmith_phase_trace("phase2", company_name, "gpt-4"):
        # LLM processing logic
        result = process_with_llm(search_results)
        return result
```

#### Pattern 3: Multiple Models Comparison

```python
from src.utils.monitoring import EnhancedLangSmithCallback

def compare_models(prompt: str):
    models = ["gpt-4", "claude-3-opus", "gemini-1.5-pro"]
    results = {}
    
    for model_name in models:
        callback = EnhancedLangSmithCallback(
            metadata={"model": model_name, "comparison": True},
            track_costs=True
        )
        
        llm = get_llm(model_name)
        response = llm.invoke(prompt, config={"callbacks": [callback]})
        
        summary = callback.get_summary()
        results[model_name] = {
            "response": response,
            "tokens": summary["total_tokens"],
            "cost": summary["total_cost"],
            "duration": summary["total_duration"]
        }
    
    return results
```

---

## Cost Calculation Details

### Pricing Table (Per 1M Tokens)

| Model | Prompt Cost | Completion Cost | Total (1K tokens) |
|-------|-------------|-----------------|-------------------|
| **OpenAI** |
| GPT-4 | $30.00 | $60.00 | $0.09 |
| GPT-4 Turbo | $10.00 | $30.00 | $0.04 |
| GPT-3.5 Turbo | $0.50 | $1.50 | $0.002 |
| **Anthropic** |
| Claude 3 Opus | $15.00 | $75.00 | $0.09 |
| Claude 3 Sonnet | $3.00 | $15.00 | $0.018 |
| Claude 3 Haiku | $0.25 | $1.25 | $0.0015 |
| **Google Gemini** |
| Gemini Pro | $0.50 | $1.50 | $0.002 |
| Gemini 1.5 Pro | $3.50 | $10.50 | $0.014 |
| Gemini 1.5 Flash | $0.075 | $0.30 | $0.000375 |

### Example Cost Calculation

```python
# Example: GPT-4 with 1,500 prompt tokens and 500 completion tokens

prompt_cost = (1500 / 1_000_000) * $30.00 = $0.045
completion_cost = (500 / 1_000_000) * $60.00 = $0.030
total_cost = $0.075
```

The callback automatically performs this calculation and stores it in the trace metadata.

---

## Known Limitations

1. **Local Models**: Cost tracking not applicable (returns $0.00)
2. **Custom Models**: Unknown models return $0.00 cost
3. **Streaming**: Callback handlers work but may show partial tokens
4. **Rate Limits**: No automatic retry logic for LangSmith API

---

## Next Steps (Phase 2)

With Phase 1 complete, the next phase will integrate this infrastructure into the research workflows:

1. Add tracing to `src/research/query_generator.py`
2. Add tracing to `src/research/search_executor.py`
3. Add tracing to `src/research/llm_processor.py`
4. Add tracing to `src/research/prompt_builder.py`
5. Add tracing to `src/research/workflows.py`
6. Create test script `scripts/test_langsmith_two_phase.py`

See `PRD_LANGSMITH_OBSERVABILITY.md` for full Phase 2 details.

---

## Troubleshooting

### Issue: "LangSmith not configured (no API key)"

**Solution**:
1. Get API key from https://smith.langchain.com
2. Add to `.env`: `LANGCHAIN_API_KEY=ls__your_api_key_here`
3. Restart your script/application

### Issue: Traces not appearing in LangSmith UI

**Possible causes**:
1. API key incorrect → Check key starts with `ls__`
2. Project name mismatch → Check `LANGCHAIN_PROJECT` environment variable
3. Tracing not enabled → Check `LANGCHAIN_TRACING_V2=true`
4. Network issues → Check internet connection

**Debug steps**:
```python
import os
print("API Key:", os.getenv("LANGCHAIN_API_KEY")[:10])
print("Tracing:", os.getenv("LANGCHAIN_TRACING_V2"))
print("Project:", os.getenv("LANGCHAIN_PROJECT"))
```

### Issue: Cost showing as $0.00

**Possible causes**:
1. Using local model (expected)
2. Unknown model name
3. Token usage not reported by model

**Solution**: Check `model_name` in callback summary matches pricing table.

---

## References

- **PRD**: `prd/prd-in-process/PRD_LANGSMITH_OBSERVABILITY.md`
- **LangSmith Docs**: https://docs.smith.langchain.com
- **LangSmith Platform**: https://smith.langchain.com
- **LangChain Callbacks**: https://python.langchain.com/docs/modules/callbacks

---

**Phase 1 Status**: ✅ Complete  
**Tested**: ✅ Yes (`scripts/test_langsmith_basic.py`)  
**Ready for Phase 2**: ✅ Yes

