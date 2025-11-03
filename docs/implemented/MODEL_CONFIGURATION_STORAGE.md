# Model Configuration Storage Architecture

This document explains where model configuration information is stored and how it flows through the application.

## Storage Locations (Multiple Sources)

Model configuration information is **NOT** stored in a single consolidated location. Instead, it's distributed across multiple sources that work together:

### 1. **Environment Variables (`.env` file)** - Primary Configuration Source

**Location:** `.env` in project root (server: `~/langchain-demo/.env`)

**Contains:**
- `MODEL_TYPE` - Which provider to use (`local`, `openai`, `anthropic`, `gemini`)
- `MODEL_PATH` - Path to local model file (for local models)
- `LOCAL_MODEL_NAME` - Registry key for local model
- `OPENAI_MODEL` - OpenAI model identifier (e.g., `gpt-4-turbo-preview`)
- `ANTHROPIC_MODEL` - Anthropic model identifier
- `GEMINI_MODEL` - Gemini model identifier (e.g., `gemini-flash-latest`)
- `TEMPERATURE` - Default sampling temperature
- **API Keys:**
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `GOOGLE_API_KEY` (for Gemini)
  - `TAVILY_API_KEY`, `SERPER_API_KEY` (for web search)

**Used By:**
- `src/models/model_factory.py` - Reads these to create LLM instances
- Direct fallback when database doesn't have configuration

**Status:** Currently active on server:
- `MODEL_TYPE=local`
- `MODEL_PATH=./models/llama-2-7b-chat.Q4_K_M.gguf`
- `GOOGLE_API_KEY=your_google_gemini_api_key_here` (placeholder)

---

### 2. **Python Code Registry** - Hardcoded Local Model Definitions

**Location:** `src/models/local_registry.py`

**Contains:**
- Static registry of local models with metadata
- Model definitions:
  - `llama-2-7b-chat-q4_k_m`
  - `meta-llama-3.1-8b-instruct-q4_k_m`
- Each entry includes:
  - `key` - Registry identifier
  - `display_name` - Human-readable name
  - `filename` - Model file name
  - `description` - Educational description
  - `recommended_vram_gb` - Memory requirements
  - `context_window` - Token context size
  - `chat_format` - Format specification

**Used By:**
- `src/models/model_factory.py` - To resolve local model paths
- `src/database/operations.py` - To seed database with local model configs

**Purpose:** Provides the "source of truth" for what local models are available in the codebase.

---

### 3. **SQLite Database** - Runtime Configuration Storage

**Location:** `data/research_agent.db` (server: `~/langchain-demo/data/research_agent.db`)

**Tables:**

#### `model_configurations` Table
Stores model configurations (both local and remote):
- `id` - Primary key
- `name` - Display name (e.g., "Llama 2 7B Chat (Q4_K_M)")
- `provider` - Provider type (`local`, `openai`, `anthropic`, `gemini`)
- `model_key` - Registry key (for local models) or null
- `model_path` - File path (for local models)
- `api_identifier` - API model ID (for remote models, e.g., `gpt-4-turbo-preview`)
- `is_active` - Whether model is enabled
- `extra_metadata` - JSON blob with:
  - `description`
  - `recommended_vram_gb`
  - `context_window`
  - `max_output_tokens`
  - `chat_format` (if applicable)

#### `api_credentials` Table
Stores API keys for remote providers:
- `id` - Primary key
- `provider` - Provider name (`openai`, `anthropic`, `gemini`)
- `api_key` - Encrypted/stored API key
- `created_at`, `updated_at` - Timestamps

#### `app_settings` Table
Stores application-level settings:
- `last_used_model_id` - Foreign key to `model_configurations`

**Used By:**
- All Streamlit UI pages - Primary source for displaying available models
- `src/database/operations.py` - Functions to query/update configurations
- `src/models/model_factory.py` - Falls back to database for API keys

**Populated By:**
- `ensure_default_configuration()` function - Syncs from:
  - `local_registry.py` → `model_configurations` (for local models)
  - `.env` API keys → `api_credentials` (when keys are present)
  - Creates default remote model configs when API keys are available

---

### 4. **File System** - Actual Model Files

**Location:** `models/` directory (server: `~/langchain-demo/models/`)

**Contains:**
- Physical `.gguf` model files:
  - `llama-2-7b-chat.Q4_K_M.gguf` (3.9 GB)
  - `meta-llama-3.1-8b-instruct.Q4_K_M.gguf` (4.6 GB)

**Used By:**
- `LlamaCpp` / `ChatLlamaCpp` - Actually loads the model into memory

---

## Configuration Flow

### Startup Sequence:

1. **Application starts** (e.g., Streamlit dashboard)
2. **Database initialization:**
   - `create_database()` - Creates tables if needed
   - `ensure_default_configuration()` runs:
     - Reads `local_registry.py` → syncs local models to database
     - Reads `.env` API keys → syncs to `api_credentials` table
     - Creates default remote model configs if API keys exist
3. **UI loads:**
   - `get_model_configurations()` - Queries database for available models
   - `get_api_key()` - Retrieves API keys from database (falls back to `.env`)
   - Displays models in dropdowns/selectboxes

### Model Resolution (when creating LLM):

1. **Function call:** `get_llm(model_type="local")` or similar
2. **Type resolution:**
   - Parameter provided? Use it
   - Otherwise: Read `MODEL_TYPE` from `.env`
3. **Local model path resolution:**
   - Parameter provided? Use it
   - Otherwise: Read `MODEL_PATH` from `.env`
   - Or: Read `LOCAL_MODEL_NAME` → lookup in `local_registry.py`
4. **API key resolution:**
   - First: Check database (`get_api_key()`)
   - Fallback: Read from `.env` (e.g., `GOOGLE_API_KEY`)
5. **Create LLM instance** with resolved configuration

---

## Consolidated View Locations

While configuration is distributed, there are places where it's **displayed together**:

### 1. **Streamlit Home Page** (`src/ui/Home.py`)

Shows consolidated view:
- **Configured Models table** - All models from database with metadata
- **API Credential Status** - Shows which API keys are configured
- **Active Model selector** - Dropdown to choose default model

### 2. **Database Query Functions**

`src/database/operations.py` provides:
- `get_model_configurations()` - Returns all models
- `get_api_key(provider)` - Returns API key for provider
- `get_last_used_model()` - Returns currently active model

### 3. **Model Factory** (`src/models/model_factory.py`)

Unified factory that:
- Reads from `.env` or parameters
- Falls back to database for API keys
- Resolves local models via registry
- Creates appropriate LLM instances

---

## Current Server State Summary

Based on remote server inspection:

### Active Configuration:
- **Model Type:** `local` (from `.env`)
- **Model Path:** `./models/llama-2-7b-chat.Q4_K_M.gguf` (from `.env`)
- **Available Models (on disk):**
  - `llama-2-7b-chat.Q4_K_M.gguf` (3.9 GB) ✅
  - `meta-llama-3.1-8b-instruct.Q4_K_M.gguf` (4.6 GB) ✅

### Database Status:
- Local models should be synced from registry
- Last used model tracked in `app_settings`
- API keys may be stored if previously set via UI

### API Keys:
- `GOOGLE_API_KEY` in `.env` = placeholder (`your_google_gemini_api_key_here`)
- Database may have API keys if set via Streamlit UI

---

## Recommendations

### For Viewing All Configuration:
1. **Streamlit Dashboard Home Page** - Best consolidated view
   - Shows all models from database
   - Shows API key status
   - Allows switching active model

2. **Query Database Directly:**
```python
from src.database.operations import (
    get_model_configurations,
    get_api_key,
    get_last_used_model
)

models = get_model_configurations()
keys = {p: get_api_key(p) for p in ["openai", "anthropic", "gemini"]}
last_used = get_last_used_model()
```

3. **Check `.env` file:**
```bash
cat .env | grep -E "MODEL|API_KEY"
```

### For Modifying Configuration:

**Option 1: Streamlit UI (Recommended)**
- Use Home page → "Manage API Credentials" expander
- Select models from dropdown (automatically updates `last_used_model`)

**Option 2: Edit `.env` file directly**
- Manually edit environment variables
- Requires restart of application to take effect

**Option 3: Database Operations**
- Use `src/database/operations.py` functions
- `upsert_api_key()` - Update API keys
- `set_last_used_model()` - Change active model

---

## Architecture Notes

### Why Multiple Sources?

1. **`.env` file** - Traditional configuration, works without database
2. **Database** - Persistent storage, UI-manageable, shared across instances
3. **Code registry** - Hardcoded model definitions, version-controlled
4. **File system** - Actual model binaries

### Priority Order:

When resolving configuration:
1. **Function parameters** (highest priority)
2. **Environment variables** (`.env` file)
3. **Database** (for API keys and model metadata)
4. **Code defaults** (registry defaults)

This allows:
- Override at call time (parameters)
- Per-instance configuration (`.env`)
- Persistent UI-managed config (database)
- Sensible defaults (code)

---

## Related Files

- `config/env.example` - Template for `.env` configuration
- `src/models/model_factory.py` - Factory that reads all sources
- `src/models/local_registry.py` - Hardcoded local model definitions
- `src/database/operations.py` - Database query/update functions
- `src/database/schema.py` - Database table definitions
- `src/ui/Home.py` - Consolidated view in Streamlit UI

