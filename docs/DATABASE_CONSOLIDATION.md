# Database Consolidation - Model Configuration

This document describes the consolidation of all model configuration into the database as the primary source of truth.

## Overview

All model configuration information has been consolidated into the SQLite database, making it the **single source of truth** for the application. The database now stores:

1. **Model Configurations** - All local and remote model definitions
2. **API Credentials** - API keys for remote providers
3. **Application Settings** - Global settings like MODEL_TYPE, TEMPERATURE, etc.
4. **Last Used Model** - Which model is currently active

## Architecture Changes

### Previous Architecture (Distributed)
- Configuration spread across: `.env` file, code registry, database, file system
- Priority: Function parameters → `.env` → Database → Code defaults

### New Architecture (Database-Centric)
- Configuration primarily in: **Database**
- Priority: Function parameters → **Database** → `.env` (fallback) → Code defaults

## Database Schema

### `app_settings` Table
Stores global application settings:
- `key` (PRIMARY KEY) - Setting name (e.g., "MODEL_TYPE", "TEMPERATURE")
- `value` (TEXT) - Setting value
- `created_at`, `updated_at` - Timestamps

**Stored Settings:**
- `MODEL_TYPE` - Default model provider (`local`, `openai`, `anthropic`, `gemini`)
- `TEMPERATURE` - Default sampling temperature (0.0-2.0)
- `MAX_ITERATIONS` - Default max iterations for agents
- `last_used_model_id` - Foreign key to active model (moved from separate tracking)

### `model_configurations` Table
(Unchanged - already stored model metadata)

### `api_credentials` Table
(Unchanged - already stored API keys)

## New Functions

### `src/database/operations.py`

#### `get_app_setting(key, default=None, session=None)`
Retrieve an application setting from the database with optional fallback.

```python
from src.database.operations import get_app_setting

model_type = get_app_setting("MODEL_TYPE", default="local")
temperature = float(get_app_setting("TEMPERATURE", default="0.7"))
```

#### `set_app_setting(key, value, session=None)`
Store or update an application setting in the database.

```python
from src.database.operations import set_app_setting

set_app_setting("MODEL_TYPE", "gemini")
set_app_setting("TEMPERATURE", "0.8")
```

#### `get_default_model_configuration(session=None)`
Get the default/active model configuration from database.
Returns the last used model, or first available model if none set.

```python
from src.database.operations import get_default_model_configuration

default_model = get_default_model_configuration()
if default_model:
    print(f"Active model: {default_model.name} ({default_model.provider})")
```

## Updated Functions

### `ensure_default_configuration()`
Now syncs app-level settings from `.env` to database on startup:
- Reads `MODEL_TYPE`, `TEMPERATURE`, `MAX_ITERATIONS` from `.env`
- Stores them in database if not already present (database takes precedence)
- Syncs API keys from `.env` (excluding placeholders)
- Creates remote model configs when API keys are available

### `src/models/model_factory.py`

All factory functions now read primarily from database:

#### `_fetch_api_key(provider)`
Priority: Database → Environment variables

#### `_fetch_app_setting(key, default)`
Priority: Database → Environment variables

#### `get_llm()` / `get_chat_model()`
**Model Type Resolution:**
1. Function parameter
2. Database (`get_app_setting("MODEL_TYPE")`)
3. Environment variable (`MODEL_TYPE`)
4. Default (`"local"`)

**Temperature Resolution:**
1. Function parameter
2. Database (`get_app_setting("TEMPERATURE")`)
3. Environment variable (`TEMPERATURE`)
4. Default (`0.7`)

#### `_select_local_model()`
**Local Model Resolution:**
1. Function parameters (`model_path` or `local_model_name`)
2. Database (`get_default_model_configuration()` - last used local model)
3. Environment variables (`MODEL_PATH` or `LOCAL_MODEL_NAME`)
4. Code registry default

#### `_create_openai_llm()` / `_create_anthropic_llm()` / `_create_gemini_llm()`
**Remote Model Resolution:**
1. Function parameter (`model_name`)
2. Database (`get_default_model_configuration()` - active model's `api_identifier`)
3. Environment variable (e.g., `OPENAI_MODEL`)
4. Code default

## Migration Path

### Automatic Migration
On first run after update:
1. `ensure_default_configuration()` runs automatically
2. Reads existing `.env` values
3. Syncs them to database (if database is empty)
4. Future changes made in database take precedence

### Manual Migration
To explicitly sync current `.env` to database:

```python
from src.database.operations import ensure_default_configuration
from src.database.schema import get_session

session = get_session()
ensure_default_configuration(session=session)
session.close()
```

## Benefits

### 1. Single Source of Truth
- All configuration in one place (database)
- Easy to query and modify
- Consistent across application instances

### 2. UI-Manageable
- Streamlit UI can directly modify database settings
- No need to edit `.env` files
- Changes persist across restarts

### 3. Multi-User Friendly
- Database can store per-user settings (future)
- Settings shared across processes
- Better for distributed deployments

### 4. Backward Compatible
- Still falls back to `.env` if database is empty
- Gradual migration path
- No breaking changes

## Usage Examples

### Setting Default Model Type
```python
from src.database.operations import set_app_setting

# Set default model type to Gemini
set_app_setting("MODEL_TYPE", "gemini")
```

### Getting Current Configuration
```python
from src.database.operations import (
    get_app_setting,
    get_default_model_configuration
)

# Get active model
active_model = get_default_model_configuration()
print(f"Active: {active_model.name}")

# Get settings
model_type = get_app_setting("MODEL_TYPE", "local")
temperature = get_app_setting("TEMPERATURE", "0.7")
```

### Creating LLM with Database Config
```python
from src.models.model_factory import get_llm

# Automatically uses database settings
llm = get_llm()  # Uses MODEL_TYPE from database

# Or override for this call
llm = get_llm(model_type="openai", temperature=0.9)
```

## UI Integration

The Streamlit dashboard already uses database configurations:
- Home page shows all models from database
- Model selector updates `last_used_model_id` in database
- API key management stores keys in database
- Settings can be managed via UI (future enhancement)

## Environment Variables

`.env` file is now **optional** and serves as:
- **Initial seed values** - Synced to database on first run
- **Fallback** - Used if database doesn't have a setting
- **Development convenience** - Quick local overrides

Priority order ensures database always wins once initialized.

## Future Enhancements

1. **Settings UI Page** - Add Streamlit page to manage app settings
2. **Per-User Settings** - Support user-specific configurations
3. **Settings Export/Import** - Backup and restore configurations
4. **Settings Validation** - Validate values before storing
5. **Settings History** - Track changes over time

## Related Documentation

- [MODEL_CONFIGURATION_STORAGE.md](MODEL_CONFIGURATION_STORAGE.md) - Original distributed architecture (for reference)
- [DATABASE_OPERATIONS.md](../src/database/operations.py) - Full API documentation
- [MODEL_FACTORY.md](../src/models/model_factory.py) - Model creation functions

