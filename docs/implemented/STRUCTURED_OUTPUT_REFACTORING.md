# Structured Output Strategy Refactoring

## Summary

Refactored structured output strategy selection from hardcoded logic in `research_agent.py` to a centralized, extensible module in `src/models/structured_output.py`. This improves maintainability, testability, and makes it easier to add support for new models.

## Changes Made

### 1. New Module: `src/models/structured_output.py`

Created a centralized `StructuredOutputSelector` class that:

- **Encapsulates strategy selection logic**: Determines which strategy (ProviderStrategy, ToolStrategy, or None) to use based on model capabilities
- **Handles model-specific detection**: Automatically detects model names and maps them to supported strategies
- **Provides educational documentation**: Includes extensive comments explaining why each strategy is chosen
- **Supports extensibility**: Easy to add new models or capabilities

**Key Features:**
- Model capability registry (PROVIDER_STRATEGY_MODELS, TOOL_STRATEGY_MODELS)
- Automatic model name extraction from LangChain model instances
- Fallback logic for unknown models
- Debugging utility (`get_strategy_info()`) for understanding strategy selection

### 2. Updated `src/agent/research_agent.py`

**Before:**
```python
if self.model_type == "local":
    response_format = None
else:
    response_format = ProviderStrategy(CompanyInfo)
```

**After:**
```python
model_name = None
if isinstance(self.model_kwargs, dict):
    model_name = self.model_kwargs.get("model_name")

# Try database configuration if not in kwargs
if not model_name and self.model_type != "local":
    try:
        from src.database.operations import get_default_model_configuration
        db_model = get_default_model_configuration()
        if db_model and db_model.provider == self.model_type:
            model_name = db_model.api_identifier
    except Exception:
        pass

response_format = select_structured_output_strategy(
    model=chat_model,
    model_type=self.model_type,
    schema=CompanyInfo,
    model_name=model_name,
)
```

**Benefits:**
- Removed hardcoded strategy logic
- Better model name extraction (checks kwargs, database, and model introspection)
- More maintainable and testable

### 3. Updated `src/models/__init__.py`

Exported new functions for easy importing:
- `StructuredOutputSelector` class
- `select_structured_output_strategy()` convenience function

## Strategy Selection Logic

The refactored code follows this decision tree:

```
1. Is model_type == "local"?
   → Return None (ChatLlamaCpp doesn't support structured output)

2. Does model_name match PROVIDER_STRATEGY_MODELS?
   → Return ProviderStrategy (native structured output)

3. Does model_name match TOOL_STRATEGY_MODELS?
   → Return ToolStrategy (artificial tool calling)

4. Is model_type in ["openai", "anthropic", "gemini"]?
   → Return ProviderStrategy (let LangChain auto-select/fallback)

5. Otherwise:
   → Return None (unknown provider)
```

## Model Support Matrix

### ProviderStrategy (Native Structured Output)
- ✅ GPT-4o, GPT-4 Turbo, GPT-4
- ✅ Claude 3 Opus, Sonnet, Haiku
- ✅ Gemini Pro, Flash

### ToolStrategy (Artificial Tool Calling)
- ✅ GPT-4o-mini
- ✅ GPT-3.5 Turbo (16k)
- ✅ Other models with tool calling but no native structured output

### None (No Structured Output)
- ✅ ChatLlamaCpp (local models)
- ✅ Unknown/unsupported providers

## Benefits of This Refactoring

1. **Single Source of Truth**: All strategy selection logic is in one place
2. **Easier Testing**: Can test strategy selection independently of agent creation
3. **Better Extensibility**: Adding new models only requires updating the registry
4. **Improved Maintainability**: Changes to strategy logic don't require modifying agent code
5. **Educational Value**: Clear documentation of why each strategy is chosen
6. **Better Model Detection**: More robust model name extraction from multiple sources

## Future Improvements

1. **Dynamic Capability Detection**: Could query LangChain or provider APIs to detect capabilities at runtime
2. **Configuration-Based**: Allow users to override strategy selection via configuration
3. **Metrics/Logging**: Track which strategies are selected for which models
4. **Validation**: Warn if selected strategy might not work with the model

## Testing Recommendations

When testing, verify:
1. Local models return `None`
2. GPT-4o returns `ProviderStrategy`
3. GPT-4o-mini returns `ToolStrategy`
4. Unknown models fall back appropriately
5. Model name extraction works from various sources (kwargs, database, introspection)

## Related Documentation

- `docs/reference/STRUCTURED_OUTPUT_STRATEGIES.md` - Detailed explanation of ProviderStrategy vs ToolStrategy
- `docs/troubleshooting/REACT_ITERATION_DIFFERENCE.md` - Why structured output affects agent behavior

---

**Date**: 2025-01-XX  
**Files Changed**:
- `src/models/structured_output.py` (new)
- `src/agent/research_agent.py` (updated)
- `src/models/__init__.py` (updated)

