# Model Availability Utilities

**Status**: ✅ **Implemented**  
**Location**: `src/utils/model_availability.py`  
**Related Docs**: 
- `MODEL_CONFIGURATION_STORAGE.md` - Database storage for models
- `TESTING_FRAMEWORK_PLAN.md` - Testing framework that uses these utilities

## Overview

The `model_availability` module provides centralized utilities for validating and retrieving available models from the database. This eliminates code duplication across CLI tools, UI pages, and test scripts.

**Educational Focus:**
- Demonstrates DRY (Don't Repeat Yourself) principle
- Shows how to create reusable validation utilities
- Centralizes business logic for easier maintenance

## Problem Solved

Previously, model availability validation logic was duplicated in multiple places:
- `scripts/run_test_framework.py` - ~130 lines of duplicate code
- `scripts/test_bitmovin_research.py` - ~70 lines of duplicate code  
- `src/ui/pages/4_🧪_Test_BitMovin.py` - ~90 lines of duplicate code
- `src/ui/pages/3_🔬_Agent.py` - Inline validation logic

**Total**: ~290 lines of duplicate code with slight variations, making maintenance difficult.

## Solution

Created `src/utils/model_availability.py` as a single source of truth for:
- Checking if provider packages are installed
- Validating API keys (filtering out placeholders)
- Checking if local model files exist
- Getting filtered lists of available models

## API Reference

### Core Functions

#### `get_available_models()`

Main function to retrieve all available models from the database.

```python
from src.utils.model_availability import get_available_models

# Get all available models
models = get_available_models()

# Filter by provider
gemini_models = get_available_models(provider_filter=["gemini"])

# Use existing session (for UI pages)
models = get_available_models(session=my_session)

# Get skip reasons for debugging
models, reasons = get_available_models(include_reasons=True)
```

**Returns**: List of model configuration dicts with keys:
- `name`: Model display name
- `provider`: Provider type ("local", "openai", "anthropic", "gemini")
- `config_id`: Database ID
- `model_path`: Path for local models (if applicable)
- `model_key`: Model key for local models (if applicable)
- `api_identifier`: API model identifier for remote models (if applicable)

#### `check_provider_packages_installed()`

Check if required packages are installed for a provider.

```python
from src.utils.model_availability import check_provider_packages_installed

if check_provider_packages_installed("gemini"):
    print("Gemini packages available")
```

#### `is_placeholder_api_key()`

Check if an API key is a placeholder value (should be filtered out).

```python
from src.utils.model_availability import is_placeholder_api_key

if is_placeholder_api_key("your_anthropic_key_here"):
    print("This is a placeholder")
```

#### `is_local_model_usable()`

Check if a local model file exists and is usable.

```python
from src.utils.model_availability import is_local_model_usable

if is_local_model_usable("~/models/llama.gguf"):
    print("Model file exists")
```

#### `is_remote_model_usable()`

Check if a remote model has a valid (non-placeholder) API key.

```python
from src.utils.model_availability import is_remote_model_usable

if is_remote_model_usable("gemini", session=session):
    print("Gemini has valid API key")
```

## Usage Examples

### CLI Scripts

```python
from src.utils.model_availability import get_available_models

# In scripts/run_test_framework.py
models = get_available_models(provider_filter=["gemini", "openai"])
for model in models:
    print(f"Testing {model['name']}")
```

### UI Pages

```python
from src.utils.model_availability import get_available_models

# In Streamlit UI pages
session = get_session()
models = get_available_models(session=session)
for model in models:
    st.checkbox(model["name"])
```

### Test Scripts

```python
from src.utils.model_availability import get_available_models

# In test scripts
models = get_available_models()
assert len(models) > 0, "No models available for testing"
```

## Validation Logic

### Package Installation Check

For each provider, checks if required LangChain integration packages are installed:
- **local**: `llama_cpp` or `llama_cpp_python`
- **openai**: `langchain_openai` or `openai`
- **anthropic**: `langchain_anthropic` or `anthropic`
- **gemini**: `langchain_google_genai` or `google.generativeai`

### Local Model Validation

1. Check if `model_path` is configured
2. Try direct path: `os.path.exists(model_path)`
3. Try expanded path: `os.path.exists(os.path.expanduser(model_path))`

### Remote Model Validation

1. Check if API key exists in database
2. Check if API key is not empty/whitespace
3. Check if API key is not a placeholder:
   - Empty string
   - `"your_{provider}_api_key_here"`
   - `"sk-your_{provider}_key_here"`
   - `"your_anthropic_key_here"`
   - `"sk-ant-your_anthropic_key_here"`
   - Any key containing "placeholder"
   - Keys starting with `"sk-ant-your_"`

## Benefits

### Code Reduction
- **Eliminated**: ~290 lines of duplicate code
- **Created**: 315 lines of well-documented, reusable utilities
- **Net**: Better maintainability with comprehensive documentation

### Consistency
- Same validation logic everywhere
- Same placeholder detection
- Same error handling

### Maintainability
- Fix bugs in one place
- Update validation logic once
- Add new validation rules centrally

### Testability
- Utilities can be unit tested independently
- No need to test duplicate code in multiple places
- Clear interfaces for mocking

## Migration Guide

### Old Pattern (Before)

```python
# Duplicated in multiple files
def check_provider_packages_installed(provider: str) -> bool:
    # ... 40 lines of code ...
    
def get_available_models_from_database():
    # ... 90 lines of code ...
```

### New Pattern (After)

```python
# Single import
from src.utils.model_availability import get_available_models

# Use directly
models = get_available_models()
```

## Files Using This Module

All these files now use the shared utilities:

1. **`scripts/run_test_framework.py`**
   - Removed duplicate functions
   - Imports `get_available_models` and `check_provider_packages_installed`

2. **`scripts/test_bitmovin_research.py`**
   - Removed duplicate functions
   - Wrapper function for backward compatibility

3. **`src/ui/pages/4_🧪_Test_BitMovin.py`**
   - Removed duplicate validation logic
   - Uses shared utilities with session parameter

4. **`src/ui/pages/3_🔬_Agent.py`**
   - Could be refactored to use utilities (future enhancement)

## Related Components

- **Database**: `src/database/operations.py` - Model configuration storage
- **Model Factory**: `src/models/model_factory.py` - Model initialization
- **Testing Framework**: `src/testing/test_runner.py` - Uses these utilities

## Future Enhancements

- [ ] Add caching for package installation checks
- [ ] Add async support for batch validation
- [ ] Add metrics/telemetry for model availability
- [ ] Refactor Agent page to use shared utilities

---

**Last Updated**: 2025-01-XX  
**Implemented By**: Testing framework refactoring  
**Status**: ✅ Complete

