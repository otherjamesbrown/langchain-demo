# Llama 3.1 Output Truncation Issue

## Problem Summary

The Llama 3.1 8B Instruct model (`meta-llama-3.1-8b-instruct-q4_k_m`) is producing truncated output when used with the research agent. Unlike Gemini, which performs 3-4 iterations with multiple web search tool calls, Llama 3.1 stops after a single iteration with truncated text.

## Observed Behavior

### Expected (Gemini)
- Multiple iterations (3-4)
- Multiple `web_search_tool` calls
- Complete, comprehensive output

### Actual (Llama 3.1)
- Single iteration
- Output truncated mid-sentence
- Example truncated output:
  ```
  Model Iteration 1:
  Based on the web search tool, here's what I found about BitMovin:
  Company Name: Bitmovin Industry: Digital Media and Entertainment...
  [truncated at] ...Bitmovin offers a range of products,
  ```

## Configuration Details

### Model Metadata
- **Model**: `meta-llama-3.1-8b-instruct-q4_k_m`
- **Context Window**: 8192 tokens (from `local_registry.py`)
- **Max Output Tokens**: 4096 (calculated as `context_window // 2`)
- **Model Path**: `/home/langchain/langchain-demo/models/meta-llama-3.1-8b-instruct.Q4_K_M.gguf`
- **Chat Format**: `llama-3`

### Current Configuration Flow

1. **UI Layer** (`src/ui/pages/3_🔬_Agent.py`):
   - Retrieves `context_window: 8192` from database
   - Calculates `max_output_tokens = max(8192 // 2, 512) = 4096`
   - Sets `model_kwargs["max_tokens"] = 4096`

2. **Agent Layer** (`src/agent/research_agent.py`):
   - Passes `model_kwargs` to `get_chat_model()`

3. **Model Factory** (`src/models/model_factory.py`):
   - Receives `kwargs["max_tokens"] = 4096`
   - Passes both `max_tokens=4096` and `n_predict=4096` to `ChatLlamaCpp` constructor

## Attempted Fixes

### Fix 1: Pass `max_tokens` to Constructor
**Status**: ❌ Not effective
- Added `max_tokens` parameter to `ChatLlamaCpp` constructor
- Result: Still truncated

### Fix 2: Use `.bind()` Method
**Status**: ❌ Not effective
- Used LangChain's `.bind()` method to set invocation-time parameters
- Set both `max_tokens` and `n_predict` via `.bind()`
- Result: Still truncated

### Fix 3: Pass Both `max_tokens` and `n_predict` Directly
**Status**: ❌ Not effective
- Updated `_create_local_chat_model()` to pass both parameters to constructor
- Set `llama_params["max_tokens"] = 4096` and `llama_params["n_predict"] = 4096`
- Result: Still truncated (current state)

### Fix 4: UI `max_output_tokens` Calculation
**Status**: ✅ Applied but issue persists
- Changed hardcoded fallback from `1024` to `max(context_window // 2, 512)`
- Ensures correct value (4096) is calculated for Llama 3.1
- Verified in logs: `"model_kwargs": {"max_tokens": 4096}`

## Technical Investigation

### Verified Parameters
- ✅ `max_tokens: 4096` is correctly passed to model factory
- ✅ `n_predict: 4096` is set in ChatLlamaCpp constructor
- ✅ `max_tokens: 4096` is set in ChatLlamaCpp constructor
- ✅ Context window (`n_ctx`) is set to 8192

### Possible Root Causes

1. **ChatLlamaCpp Parameter Acceptance**
   - `ChatLlamaCpp` may not accept `max_tokens` or `n_predict` in constructor
   - May require different parameter names
   - May need invocation-time parameter passing (via `.invoke()` kwargs)

2. **Stop Sequences**
   - Model may be hitting implicit stop tokens
   - Llama 3.1 format may have built-in stop sequences
   - Agent framework may be adding stop sequences

3. **Context Window Exhaustion**
   - Input prompt may be consuming most of the context
   - Combined input + output may exceed `n_ctx: 8192`
   - Need to verify actual prompt token count

4. **Agent Framework Truncation**
   - LangChain agent executor may be truncating output
   - Middleware (ModelCallLimitMiddleware, ToolCallLimitMiddleware) may be interfering
   - Agent may be interpreting truncated output as complete

5. **llama-cpp-python Version Issues**
   - Version mismatch between `llama-cpp-python` and `langchain-community`
   - Parameter names may have changed in different versions
   - Default behavior may differ

## Code References

### Key Files Modified
- `src/models/model_factory.py` (lines 354-381)
- `src/ui/pages/3_🔬_Agent.py` (lines 151-164)

### Current Implementation
```python
# src/models/model_factory.py
llama_params = {
    "model_path": str(resolved_path),
    "temperature": temperature,
    "n_ctx": kwargs.get("n_ctx", suggested_ctx or 4096),
    "n_gpu_layers": kwargs.get("n_gpu_layers", -1),
    "verbose": kwargs.get("verbose", False),
    "n_batch": kwargs.get("n_batch", 512),
}

# Set max generation tokens - ChatLlamaCpp may accept either max_tokens or n_predict
if "max_tokens" in kwargs:
    max_gen_tokens = kwargs["max_tokens"]
    llama_params["max_tokens"] = max_gen_tokens
    llama_params["n_predict"] = max_gen_tokens
elif suggested_ctx:
    max_gen_tokens = max(suggested_ctx // 2, 512)
    llama_params["max_tokens"] = max_gen_tokens
    llama_params["n_predict"] = max_gen_tokens

return ChatLlamaCpp(**llama_params)
```

## Next Steps / Potential Solutions

### 1. Verify ChatLlamaCpp Parameters
- Check actual `ChatLlamaCpp.__init__()` signature
- Inspect what parameters it accepts
- Verify parameter names match our expectations

### 2. Check Prompt Token Count
- Log actual prompt size in tokens
- Verify `n_ctx: 8192` is sufficient for input + output
- Calculate: `input_tokens + max_output_tokens <= n_ctx`

### 3. Try Invocation-Time Parameters
- Pass `max_tokens`/`n_predict` via `.invoke()` kwargs instead of constructor
- May require custom wrapper or monkey-patching

### 4. Check Stop Sequences
- Inspect if agent framework adds stop sequences
- Check if Llama 3.1 format has implicit stops
- Disable or modify stop sequences

### 5. Direct llama-cpp-python Test
- Test model directly with `llama-cpp-python` (bypassing LangChain)
- Verify `n_predict` works correctly at that level
- Isolate whether issue is LangChain wrapper or underlying library

### 6. Version Compatibility
- Check `llama-cpp-python` version on server
- Check `langchain-community` version
- Verify compatibility between versions

### 7. Alternative: Increase Context Window
- Try increasing `n_ctx` beyond 8192 (if supported)
- Verify model actually supports larger context
- May reveal if truncation is due to context limits

### 8. Debug Logging
- Add verbose logging to see actual parameters passed
- Log token counts (input/output)
- Log when truncation occurs (model level vs agent level)

## Related Issues / References

- User reported truncation despite `max_tokens: 4096` in logs
- Gemini works correctly with same agent framework
- Issue is specific to local Llama 3.1 model
- No errors in logs, just truncated output

## Environment

- **Server**: Linode GPU instance
- **Model**: Meta Llama 3.1 8B Instruct Q4_K_M
- **Framework**: LangChain with ChatLlamaCpp
- **Agent**: ReAct agent with web search tool

---

**Status**: ❌ **OPEN** - Issue persists after multiple fix attempts

**Last Updated**: 2025-01-27

