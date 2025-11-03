# Gemini Failing in Test_BitMovin but Working in Agent Escalation

## Issue Summary

Gemini model works successfully in the **Agent Escalation** page (`3_🔬_Agent.py`) but fails with "❌ Failed - No company info returned" in the **Test_BitMovin** page (`4_🧪_Test_BitMovin.py`).

## Key Differences Between Pages

### 1. Model Configuration Retrieval

**Agent Escalation Page:**
- Filters models from `get_model_configurations()` (line 70)
- Validates each model (checks API keys, model paths) (lines 73-97)
- Uses `selected_model.api_identifier` directly (line 137)

**Test_BitMovin Page:**
- Gets models from `get_available_models_from_database()` (line 256)
- Uses `model_config.get("api_identifier")` from the config dict (line 313)

**Potential Issue**: The model configuration might be slightly different, or the `api_identifier` might not be set correctly in the Test_BitMovin path.

### 2. Model Initialization

**Agent Escalation Page:**
```python
model_kwargs = {}
model_kwargs["model_name"] = selected_model.api_identifier  # Line 137

agent = ResearchAgent(
    model_type=model_type,
    model_kwargs=model_kwargs,  # Line 266
    ...
)
```

**Test_BitMovin Page:**
```python
agent_kwargs = {
    "model_type": model_type,
    ...
}

if model_config.get("api_identifier"):
    agent_kwargs["model_kwargs"] = {
        "model_name": model_config["api_identifier"]  # Line 314-316
    }

agent = ResearchAgent(**agent_kwargs)  # Line 319
```

**Analysis**: Both should work the same way, but there's a subtle difference:
- Agent Escalation creates `model_kwargs` as a top-level dict
- Test_BitMovin nests it inside `agent_kwargs["model_kwargs"]`

Both should work, but let's verify they're equivalent.

### 3. Error Handling

**Agent Escalation Page:**
- Shows full result information
- Displays company_info if available (lines 431-517)
- Shows warning if no company_info (line 345)

**Test_BitMovin Page (BEFORE fix):**
- Only checked `if result.company_info:` (line 323)
- If None, immediately showed error without details
- Didn't show `result.raw_output` or `result.success` status

**Test_BitMovin Page (AFTER fix):**
- Now shows detailed error information:
  - `result.success` status
  - `result.iterations`
  - `result.raw_output` (first 500 chars)
  - Intermediate steps for debugging

## Potential Root Causes

### 1. Model Identifier Difference

**Hypothesis**: The Gemini model identifier might be different between the two pages.

**Check**:
- What Gemini model is configured in Agent Escalation? (Check `selected_model.api_identifier`)
- What Gemini model is configured in Test_BitMovin? (Check `model_config["api_identifier"]`)
- Do both use the same model? (e.g., `gemini-flash-latest` vs `gemini-pro-latest`)

Some Gemini models might not support ProviderStrategy properly:
- ✅ `gemini-flash-latest` - Should support ProviderStrategy
- ✅ `gemini-pro-latest` - Should support ProviderStrategy  
- ❓ `gemini-2.0-flash-exp` - Experimental, might have issues
- ❓ Older model versions might not support ProviderStrategy

### 2. ProviderStrategy Validation Failure

**Hypothesis**: Gemini's ProviderStrategy is generating structured output, but it fails Pydantic validation against the `CompanyInfo` schema.

**Evidence**:
- Agent executes successfully (no exception)
- `result.success` might be True or False
- `result.company_info` is None
- `result.raw_output` contains the actual response

**Check**: Look at `result.raw_output` - it might contain valid JSON that just doesn't match the schema exactly.

### 3. Missing Required Fields

**Hypothesis**: Gemini is generating structured output but missing required fields (`company_name`, `industry`, `company_size`, `headquarters`), causing validation to fail silently.

**Check**: The enhanced error logging will show:
- What's in `result.raw_output`
- Whether there's JSON that can be parsed
- What validation errors occur

### 4. Exception Being Swallowed

**Hypothesis**: An exception occurs but is caught and not properly displayed.

**Check**: The exception handler in Test_BitMovin (lines 452-465) should catch and display any exceptions.

## Debugging Steps

### Step 1: Compare Model Identifiers

1. Run Agent Escalation with Gemini
2. Note which Gemini model is selected (check sidebar or logs)
3. Run Test_BitMovin with Gemini  
4. Check which Gemini model is used (should be shown in test output)
5. Verify they're the same

### Step 2: Check Raw Output

With the enhanced error display:
1. Run Test_BitMovin with Gemini
2. When it fails, check the "Error Details" section
3. Look at "Raw Output" - this will show what Gemini actually returned
4. Check if it's valid JSON or structured data

### Step 3: Check Success Status

1. Look at `result.success` in the error details
2. If `result.success = True` but `company_info = None`:
   - ProviderStrategy might have returned data that failed validation
   - Check the raw_output for the actual response
3. If `result.success = False`:
   - Check if there's an exception message in raw_output
   - Check intermediate steps for clues

### Step 4: Check Logs

With the enhanced logging in `research_agent.py`:
1. Check application logs for warnings/errors
2. Look for: "Structured response is None for gemini model"
3. Look for: "CompanyInfo validation failed for gemini"

## Quick Fixes to Try

### Fix 1: Use ToolStrategy for Gemini (Temporary)

If ProviderStrategy is the issue, we can force ToolStrategy:

```python
# In src/agent/research_agent.py, around line 417
if self.model_type == "local":
    response_format = None
elif self.model_type == "gemini":
    # Gemini sometimes has issues with ProviderStrategy
    # Fall back to ToolStrategy as workaround
    response_format = ToolStrategy(CompanyInfo)
else:
    response_format = ProviderStrategy(CompanyInfo)
```

### Fix 2: Ensure Model Identifier is Set

Verify that `model_kwargs` is being passed correctly in Test_BitMovin:

```python
# Make sure model_kwargs is always a dict
agent_kwargs = {
    "model_type": model_type,
    "verbose": False,
    "max_iterations": 10,
    "model_kwargs": {},  # Initialize empty dict
}

if model_type != "local":
    if model_config.get("api_identifier"):
        agent_kwargs["model_kwargs"]["model_name"] = model_config["api_identifier"]
```

### Fix 3: Add Fallback Parsing

If ProviderStrategy fails, try to parse from raw_output:

```python
# After line 334 in research_agent.py
company_info = self._parse_company_info(structured_response, raw_output, company_name)

# If still None and we have raw_output, try harder
if company_info is None and raw_output and self.model_type != "local":
    # Log the raw output for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to parse company_info for {self.model_type}. Raw output: {raw_output[:500]}")
```

## Next Steps

1. **Run Test_BitMovin again** with the enhanced error display
2. **Compare the raw_output** between Agent Escalation (if you can capture it) and Test_BitMovin
3. **Check application logs** for the new warning/error messages
4. **Compare model identifiers** to ensure they're the same
5. **Consider the ToolStrategy fallback** if ProviderStrategy continues to fail

---

**Last Updated**: 2025-01-XX  
**Related Docs**: 
- `docs/STRUCTURED_OUTPUT_STRATEGIES.md`
- `docs/REACT_ITERATION_DIFFERENCE.md`

