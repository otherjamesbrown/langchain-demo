# Architectural Principles

This document defines the core architectural principles and conventions that guide development in this codebase. These principles ensure consistency, maintainability, and correct behavior across all components.

**Important**: When making changes to the codebase, these principles should be followed. If you need to deviate from a principle, document the reason in code comments and update this document if the principle changes.

---

## 1. Database as Source of Truth

### Principle
**All configuration and state data must be stored in the database as the primary source of truth.**

### Application

#### Model Configuration
- ✅ **DO**: Store model paths, names, and metadata in `model_configurations` table
- ✅ **DO**: Use `get_default_model_configuration()` to retrieve active models
- ✅ **DO**: Fall back to environment variables only if database has no configuration
- ✅ **DO**: Use `get_available_models()` from `src.utils.model_availability` to check which models are usable
- ❌ **DON'T**: Hardcode model paths or rely solely on environment variables
- ❌ **DON'T**: Read model configuration from `.env` files as primary source
- ❌ **DON'T**: Duplicate model availability validation logic (package checks, API key validation, file existence)

**Priority Order** (implemented in `src/models/model_factory.py`):
1. Database (`get_default_model_configuration()`)
2. Environment variables (`MODEL_PATH`, `LOCAL_MODEL_NAME`)
3. Code registry defaults

**Example**:
```python
# ✅ CORRECT: Database-first approach
from src.database.operations import get_default_model_configuration

db_model = get_default_model_configuration()
if db_model and db_model.provider == "local":
    model_path = db_model.model_path

# ❌ WRONG: Environment variable only
model_path = os.getenv("MODEL_PATH")  # Only as fallback!
```

#### API Keys and Credentials
- ✅ **DO**: Store API keys in `api_credentials` table
- ✅ **DO**: Use `get_api_key(provider)` which checks database first
- ✅ **DO**: Allow `.env` as fallback for local development
- ❌ **DON'T**: Hardcode API keys in code
- ❌ **DON'T**: Read API keys directly from environment variables without database check

**Priority Order**:
1. Database (`get_api_key()`)
2. Environment variables (`.env` file)

**Reference**: `src/models/model_factory.py::_fetch_api_key()`

#### Application Settings
- ✅ **DO**: Store app-level settings in `app_settings` table
- ✅ **DO**: Use `get_app_setting(key)` which checks database first
- ✅ **DO**: Support environment variables as fallback
- ❌ **DON'T**: Read settings directly from environment without database check

**Settings stored in database**:
- `MODEL_TYPE` - Active model provider (local, openai, anthropic, gemini)
- `TEMPERATURE` - Default LLM temperature
- `MAX_ITERATIONS` - Agent iteration limits
- Other application-wide configuration

**Reference**: `src/database/operations.py::get_app_setting()`

---

## 2. Consistent Model Resolution Pattern

### Principle
**All code that needs model configuration must follow the same resolution priority.**

### Application

The `model_factory.py` implements this pattern - other code should use it rather than duplicating logic:

**For Local Models** (`_select_local_model()`):
1. Function parameters (`model_path` or `local_model_name`)
2. Database (`get_default_model_configuration()` - last used local model)
3. Environment variables (`MODEL_PATH` or `LOCAL_MODEL_NAME`)
4. Code registry default

**For Remote Models**:
1. Function parameters (`model_name`)
2. Database (`get_default_model_configuration()` - last used remote model)
3. Environment variables (`OPENAI_MODEL`, `ANTHROPIC_MODEL`, etc.)
4. Provider-specific defaults

**✅ CORRECT**: Use factory functions
```python
from src.models.model_factory import get_chat_model

# This automatically follows the priority order
model = get_chat_model(model_type="local")
```

**❌ WRONG**: Duplicate resolution logic
```python
# Don't reimplement model selection - use the factory!
model_path = os.getenv("MODEL_PATH")  # Skips database!
```

**Reference**: 
- `src/models/model_factory.py`
- `docs/implemented/DATABASE_CONSOLIDATION.md`

---

## 3. Structured Output Strategy Selection

### Principle
**Structured output strategy selection must be centralized and based on model capabilities.**

### Application

- ✅ **DO**: Use `select_structured_output_strategy()` from `src/models/structured_output.py`
- ✅ **DO**: Let the selector determine ProviderStrategy vs ToolStrategy vs None
- ✅ **DON'T**: Hardcode strategy selection based on model type
- ✅ **DON'T**: Duplicate strategy selection logic in multiple places

**Strategy Selection Rules**:
1. **Local models (ChatLlamaCpp)**: `None` (doesn't support tool_choice parameter)
2. **Models with native support** (GPT-4o, Claude 3, Gemini): `ProviderStrategy`
3. **Models without native support but with tool calling** (GPT-4o-mini): `ToolStrategy`

**Reference**: 
- `src/models/structured_output.py`
- `docs/reference/STRUCTURED_OUTPUT_STRATEGIES.md`

---

## 4. Error Handling and Logging

### Principle
**Errors must be logged to appropriate locations and not silently ignored.**

### Application

#### Error Logging Locations
1. **Server/Component Errors**: `/tmp/streamlit.log` (for Streamlit startup failures)
2. **LLM Errors**: Database `llm_call_logs` table with `success=False` and `error_message`
3. **UI Errors**: Display via `st.error()` / `st.warning()` in Streamlit
4. **Application Logs**: `logs/research_agent.log` (if logging configured)

#### Error Handling Best Practices
- ✅ **DO**: Log errors with context (model name, prompt snippet, error type)
- ✅ **DO**: Use appropriate logging levels (ERROR, WARNING, INFO)
- ✅ **DO**: Include stack traces for unexpected errors
- ❌ **DON'T**: Swallow exceptions without logging
- ❌ **DON'T**: Log sensitive data (API keys, full prompts in production)

**Reference**: 
- `docs/reference/DEPLOYMENT_VERIFICATION.md` - Error logging locations
- `src/utils/logging.py` - Logging configuration

---

## 5. Database Schema Consistency

### Principle
**Database schema changes must be backward compatible when possible, and migrations should be documented.**

### Application

- ✅ **DO**: Use `create_database()` to initialize schema
- ✅ **DO**: Add new columns as nullable when possible
- ✅ **DO**: Document schema changes in migration notes
- ❌ **DON'T**: Break existing queries with schema changes
- ❌ **DON'T**: Remove columns without deprecation period

**Reference**: 
- `src/database/schema.py`
- `docs/DATABASE_CONSOLIDATION.md`

---

## 6. Code Organization and File Structure

### Principle
**Code organization must follow established patterns and be easy to discover.**

### Application

#### Directory Structure
- `src/` - All source code
  - `agent/` - Agent implementations
  - `models/` - Model abstractions and factories
  - `database/` - Database schema and operations
  - `tools/` - LangChain tools
  - `utils/` - Shared utilities
  - `ui/` - Streamlit UI components

#### Import Patterns
- ✅ **DO**: Use absolute imports from `src.*`
- ✅ **DO**: Add project root to `sys.path` when needed
- ✅ **DO**: Keep imports organized (stdlib, third-party, local)
- ❌ **DON'T**: Use relative imports across packages
- ❌ **DON'T**: Duplicate code across modules

#### Shared Utilities
- ✅ **DO**: Use shared utilities from `src/utils/` for common operations
  - `model_availability.py` - Model validation and availability checking
  - `model_factory.py` - Model creation and initialization
  - `logging.py` - Centralized logging configuration
- ✅ **DO**: Check `src/utils/` before implementing new validation logic
- ❌ **DON'T**: Duplicate validation logic (package checks, API key validation, file existence)
- ❌ **DON'T**: Create new utility functions without checking if similar functionality exists

**Example - Model Availability**:
```python
# ✅ CORRECT: Use shared utility
from src.utils.model_availability import get_available_models

models = get_available_models(provider_filter=["gemini"])

# ❌ WRONG: Duplicate validation logic
def check_provider_packages_installed(provider: str) -> bool:
    # ... 40 lines of duplicate code ...
```

**Reference**: 
- `src/utils/model_availability.py` - Shared model availability utilities
- `docs/implemented/MODEL_AVAILABILITY_UTILITIES.md` - Utilities documentation
- `.cursorrules` - File organization guidelines
- `PROJECT_STRUCTURE.md` - Directory layout

---

## 7. Testing and Verification

### Principle
**All deployments must be verified to ensure system functionality.**

### Application

#### Post-Deployment Verification
1. Check Streamlit process is running
2. Verify logs for errors
3. Test local LLM functionality
4. Verify dashboard access
5. Test database connection
6. Verify critical functionality (e.g., structured output strategy)

**Reference**: 
- `.cursor/commands/redeploy.md` - Deployment verification steps
- `docs/reference/DEPLOYMENT_VERIFICATION.md` - Detailed verification guide

---

## 8. Configuration Management

### Principle
**Configuration must be manageable through database UI when possible, with environment variables as fallback.**

### Application

- ✅ **DO**: Provide UI (Streamlit) for configuring models and API keys
- ✅ **DO**: Store user selections in database
- ✅ **DO**: Support `.env` file for initial setup
- ✅ **DO**: Sync `.env` to database on startup (via `ensure_default_configuration()`)
- ❌ **DON'T**: Require manual `.env` editing for all configuration
- ❌ **DON'T**: Hardcode configuration values

**Reference**: 
- `docs/implemented/DATABASE_CONSOLIDATION.md`
- `src/database/operations.py::ensure_default_configuration()`

---

## 9. Educational Focus

### Principle
**All code should be educational and well-documented, especially for LangChain concepts.**

### Application

- ✅ **DO**: Include docstrings explaining LangChain patterns
- ✅ **DO**: Add comments explaining "why" not just "what"
- ✅ **DO**: Show best practices in examples
- ✅ **DO**: Document architectural decisions in code comments
- ❌ **DON'T**: Write cryptic or overly clever code
- ❌ **DON'T**: Skip documentation for complex logic

**Reference**: 
- `.cursorrules` - Educational focus guidelines

---

## 10. Model Capability Detection

### Principle
**Model capabilities must be detected dynamically when possible, not hardcoded.**

### Application

- ✅ **DO**: Use `StructuredOutputSelector` to detect model capabilities
- ✅ **DO**: Allow model introspection to determine features
- ✅ **DO**: Fall back to capability registry for known models
- ❌ **DON'T**: Hardcode capability checks per model name
- ❌ **DON'T**: Assume all models of a type have same capabilities

**Reference**: 
- `src/models/structured_output.py::_extract_model_name()`

---

## Adding New Principles

When establishing a new architectural principle:

1. **Document it here** with:
   - Clear statement of the principle
   - Rationale (why it's important)
   - Application guidelines (DO/DON'T examples)
   - Code references

2. **Update affected code** to follow the principle

3. **Add verification** to ensure principle is followed (tests, linters, code reviews)

4. **Reference from relevant docs** (architecture docs, contributing guide, etc.)

---

## Related Documentation

- `docs/ARCHITECTURE.md` - System architecture overview
- `docs/implemented/DATABASE_CONSOLIDATION.md` - Database-first approach details
- `docs/implemented/MODEL_CONFIGURATION_STORAGE.md` - Model configuration storage
- `docs/implemented/MODEL_AVAILABILITY_UTILITIES.md` - Shared model availability utilities
- `.cursorrules` - Code style and conventions
- `PROJECT_STRUCTURE.md` - Directory organization

---

**Last Updated**: 2025-01-XX  
**Maintained By**: Project maintainers  
**Review Frequency**: When architectural changes are made

