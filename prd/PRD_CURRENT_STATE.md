# Product Requirements Document: LangChain Research Agent - Current State

**Document Status:** Current as of 2025-01-02  
**Version:** 1.0  
**Purpose:** Comprehensive documentation of what has been built

---

## Executive Summary

This project implements a production-ready LangChain-based research agent system for automated company profiling. The system features a **two-phase architecture** that separates search collection from LLM processing, enabling cost-efficient model testing, prompt engineering, and full audit trails.

### Key Capabilities

✅ **Two-Phase Research Architecture** - Search once, process many times  
✅ **Multi-Model Support** - Local (Llama) and remote (OpenAI, Anthropic, Gemini) models  
✅ **Comprehensive Database** - Full audit trail with search history, processing runs, and validation  
✅ **Streamlit UI Dashboard** - Interactive monitoring and LLM interaction interface  
✅ **Production Infrastructure** - Deployed on Linode and GCP with GPU support  
✅ **Educational Focus** - Well-documented codebase for learning LangChain patterns  

---

## Architecture Overview

### Two-Phase Design

The system uses a two-phase architecture that separates expensive search operations from LLM processing:

**Phase 1: Search Collection**
- Generate structured queries from company data
- Execute web searches via API providers (Tavily, Serper)
- Store raw search results in database with full metadata

**Phase 2: LLM Processing**
- Retrieve stored search results
- Build prompts from instructions + search results
- Process through LLM with full metadata tracking
- Store processing runs for comparison and validation

### Benefits

- **Cost Efficiency**: Search once (~$0.10), process many times (no API cost for testing)
- **Reproducibility**: Same inputs → Same outputs
- **Model Comparison**: Test multiple LLMs on identical data
- **Prompt Engineering**: Iterate on prompts without re-searching
- **Full Audit Trail**: Know exactly what each model saw

---

## Component Documentation

### 1. Two-Phase Research System (`src/research/`)

#### 1.1 Query Generator (`query_generator.py`)
**Status:** ✅ Complete

**Purpose:** Generate structured search queries from company names using templates.

**Capabilities:**
- Template-based query generation
- Multiple query types per company (company size, revenue, industry, etc.)
- Customizable query templates
- Company-specific query generation

**Key Functions:**
- `generate_queries_for_companies()` - Generate queries for multiple companies
- Stores queries in `research_queries` table with status tracking

#### 1.2 Search Executor (`search_executor.py`)
**Status:** ✅ Complete

**Purpose:** Execute search queries and store raw results in database.

**Capabilities:**
- Multi-provider support (Tavily, Serper)
- Automatic provider detection
- Raw JSON result storage
- Idempotent execution (can re-run failed queries)
- Execution metadata tracking

**Key Functions:**
- `execute_all_pending_queries()` - Execute all pending queries
- `get_search_results_for_company()` - Retrieve results for a company
- Stores results in `search_history` table with `raw_results` JSON field

#### 1.3 Prompt Builder (`prompt_builder.py`)
**Status:** ✅ Complete

**Purpose:** Combine instruction files with search results into prompts.

**Capabilities:**
- Load markdown instruction files
- Format search results for LLM consumption
- Prompt versioning (hash-based)
- Template-based prompt construction

**Key Functions:**
- `build_prompt_from_files()` - Build complete prompt from instructions and results

#### 1.4 LLM Processor (`llm_processor.py`)
**Status:** ✅ Complete

**Purpose:** Process prompts through LLMs with full metadata tracking.

**Capabilities:**
- Multi-model support (local and remote)
- Full execution metadata capture
- Structured output parsing (CompanyInfo Pydantic model)
- Processing run storage with all inputs/outputs
- Error handling and validation

**Key Functions:**
- `process_with_llm()` - Process single company with single model
- `process_company_with_multiple_models()` - Compare multiple models on same data

#### 1.5 Validation Tools (`validation.py`)
**Status:** ✅ Complete

**Purpose:** Validate and compare processing runs.

**Capabilities:**
- Completeness validation (required fields check)
- Multi-model comparison
- Consensus detection (agreement across models)
- Quality metrics calculation

**Key Functions:**
- `validate_processing_run()` - Validate a single processing run
- `compare_processing_runs()` - Compare multiple runs
- `detect_consensus()` - Find agreement across models

#### 1.6 Workflows (`workflows.py`)
**Status:** ✅ Complete

**Purpose:** High-level workflow functions that combine Phase 1 and Phase 2.

**Capabilities:**
- Phase 1 workflow (`phase1_collect_searches`)
- Phase 2 single model workflow (`phase2_process_with_llm`)
- Phase 2 multi-model workflow (`phase2_process_multiple_models`)
- Full pipeline workflow (`full_research_pipeline`)

**Usage Example:**
```python
# Phase 1: Collect searches
phase1_collect_searches(csv_path="companies.csv", provider="serper")

# Phase 2: Process with single model
phase2_process_with_llm(
    company_name="Acme Corp",
    instructions_path="instructions.md",
    llm_provider="openai",
    llm_model="gpt-4"
)

# Phase 2: Compare multiple models
phase2_process_multiple_models(
    company_name="Acme Corp",
    instructions_path="instructions.md",
    models=[
        {"provider": "openai", "model": "gpt-4"},
        {"provider": "anthropic", "model": "claude-3-opus"}
    ]
)
```

---

### 2. Model Abstraction Layer (`src/models/`)

#### 2.1 Model Factory (`model_factory.py`)
**Status:** ✅ Complete

**Purpose:** Unified interface for creating LLM instances across providers.

**Supported Providers:**
- **Local**: LlamaCpp (quantized models, .gguf format)
- **OpenAI**: GPT-3.5, GPT-4, GPT-4 Turbo
- **Anthropic**: Claude 3 Opus, Sonnet, Haiku
- **Google Gemini**: Gemini Pro, Gemini Pro Vision

**Key Functions:**
- `get_llm()` - Create LangChain LLM instance
- `get_chat_model()` - Create LangChain ChatModel instance (for agents)
- `list_available_providers()` - List installed providers

**Configuration:**
- Environment variable based (`MODEL_TYPE`, `MODEL_PATH`, API keys)
- Automatic provider detection
- Error handling for missing providers/keys

#### 2.2 Local Model Registry (`local_registry.py`)
**Status:** ✅ Complete

**Purpose:** Manage and discover local Llama models.

**Capabilities:**
- Model path resolution
- Model key/name mapping
- Default model selection
- Model configuration storage

---

### 3. Tools (`src/tools/`)

#### 3.1 Web Search Tool (`web_search.py`)
**Status:** ✅ Complete

**Purpose:** LangChain tool for web search operations.

**Supported APIs:**
- **Tavily** (primary) - AI-optimized search
- **Serper** (alternative) - Google search API

**Features:**
- Automatic provider selection
- Structured result formatting
- Rate limiting and error handling
- Result relevance scoring
- Tool schema for agent integration

**Integration:**
- Exposed as LangChain tool (`TOOLS` list)
- Can be used in agent workflows
- Returns structured `SearchResult` objects

#### 3.2 Data Loaders (`data_loaders.py`)
**Status:** ✅ Complete

**Purpose:** Load CSV and markdown files for agent processing.

**Capabilities:**
- CSV loading with company data
- Markdown instruction loading
- Company name extraction
- LangChain tool wrappers

#### 3.3 Data Models (`models.py`)
**Status:** ✅ Complete

**Purpose:** Pydantic models for structured data.

**Models:**
- `CompanyInfo` - Structured company profiling data
- `SearchResult` - Web search result structure
- `AgentResult` - Agent execution result wrapper

---

### 4. Database Layer (`src/database/`)

#### 4.1 Database Schema (`schema.py`)
**Status:** ✅ Complete

**Tables:**

1. **`companies`** - Company profiling data
   - Basic info (name, website, industry, size, headquarters, founded)
   - GTM classifications (growth stage, industry vertical, financial health, etc.)
   - Products, competitors, key personas (JSON fields)
   - Timestamps (created_at, updated_at)

2. **`search_history`** - Web search operations
   - Query text, company name, provider
   - Results summary and count
   - **`raw_results`** JSON field (full API response)
   - Execution metadata (time, success, errors)

3. **`research_queries`** - Structured query tracking
   - Company name, query text, query type
   - Status tracking (pending, completed, failed)
   - Timestamps

4. **`processing_runs`** - LLM processing runs
   - Company name, prompt version, instructions source
   - LLM configuration (model, provider, temperature)
   - Input/output (search result IDs, context, output)
   - Execution metadata (time, success, errors)

5. **`validation_results`** - Validation scores
   - Processing run reference
   - Validation type, score, details (JSON)
   - Validator information

6. **`llm_call_logs`** - Individual LLM API calls
   - Model type/name, call type
   - Token metrics (prompt, completion, total)
   - Performance metrics (generation time, tokens/second)
   - Full prompt/response (truncated if >5000 chars)
   - Success/error tracking
   - Additional metadata (JSON)

**Relationships:**
- `validation_results.processing_run_id` → `processing_runs.id`
- All tables have proper indexes for performance

#### 4.2 Database Operations (`operations.py`)
**Status:** ✅ Complete

**Capabilities:**
- Database initialization (`init_database()`, `create_database()`)
- Company CRUD operations
- Search history storage and retrieval
- Processing run management
- Session management utilities

**Key Functions:**
- `save_company_info()` - Save CompanyInfo to database
- `get_company()` - Retrieve company by name
- `init_database()` - Initialize database schema

---

### 5. Utilities (`src/utils/`)

#### 5.1 Logging (`logging.py`)
**Status:** ✅ Complete

**Purpose:** Centralized logging configuration.

**Features:**
- File and console handlers
- Log rotation (RotatingFileHandler)
- Configurable log levels (via environment)
- Timestamp formatting
- Structured logging to `logs/` directory

#### 5.2 Monitoring (`monitoring.py`)
**Status:** ✅ Complete

**Purpose:** LangChain callback handlers and performance monitoring.

**Features:**
- LangSmith integration (optional)
- Custom callback handlers
- Performance metrics collection
- Token usage tracking
- Execution step logging

#### 5.3 LLM Logger (`llm_logger.py`)
**Status:** ✅ Complete

**Purpose:** Log individual LLM calls to database.

**Features:**
- Log LLM invocations to `llm_call_logs` table
- Token metrics tracking
- Performance metrics (generation time, tokens/sec)
- Full prompt/response storage (with truncation)
- Error logging

#### 5.4 Metrics (`metrics.py`)
**Status:** ✅ Complete

**Purpose:** Metrics tracking and calculation.

**Features:**
- `LLMMetrics` dataclass
- `MetricsTracker` class
- Token usage calculation
- Performance calculation (tokens/second)

---

### 6. User Interface (`src/ui/`)

#### 6.1 Streamlit Dashboard (`streamlit_dashboard.py`)
**Status:** ✅ Complete

**Purpose:** Multi-page dashboard for LLM interaction and monitoring.

**Pages:**

1. **🤖 Local LLM** (`pages/1_🤖_Local_LLM.py`)
   - Interactive LLM calling interface
   - Custom prompt input
   - Real-time response display
   - Model configuration (path, temperature, max tokens)
   - Metrics display (tokens, time, tokens/sec)
   - Response history
   - Automatic database logging (toggleable)
   - Model caching for performance

2. **📊 Monitoring** (`pages/2_📊_Monitoring.py`)
   - Historical LLM call logs
   - Summary statistics (total calls, tokens, time, call rate)
   - Filters (model type, time range)
   - Detailed call information (prompt, response, metrics)
   - Auto-refresh capability (30-second intervals)

3. **🔬 Agent** (`pages/3_🔬_Agent.py`)
   - Research agent execution interface
   - Company research workflow
   - Agent step visualization
   - Execution results display

**Features:**
- Sidebar navigation (radio buttons)
- Version display for code verification
- Consistent port usage (8501)
- Background deployment support
- SSH tunnel access support

**Deployment:**
- **URL:** http://172.234.181.156:8501 (Linode instance)
- **Status:** ✅ Live and accessible
- **Start Script:** `scripts/start_streamlit.sh`

---

### 7. Research Agent (`src/agent/`)

#### 7.1 Research Agent (`research_agent.py`)
**Status:** ✅ Complete (Educational/Legacy Component)

**Purpose:** Educational implementation of LangChain agent using modern runtime.

**Features:**
- Modern `create_agent()` factory (LangChain 0.3+)
- ReAct (Reasoning-Acting) pattern
- Step tracking middleware
- Model call and tool call limits
- Intermediate step visualization
- Structured output (CompanyInfo)
- Error handling and validation

**Integration:**
- Uses `get_chat_model()` for LLM creation
- Uses web search tools from `src/tools/web_search.py`
- Can be used in Streamlit UI agent page

**Note:** This is a legacy/educational component. The two-phase architecture (`src/research/`) is the primary production workflow.

---

### 8. Infrastructure

#### 8.1 Linode Instance
**Status:** ✅ Complete

**Details:**
- **IP:** 172.234.181.156
- **OS:** Ubuntu 22.04 LTS
- **Python:** 3.12.3
- **User:** `langchain` (sudo access)
- **Model:** Llama 2 7B Q4_K_M (3.9GB)
- **Status:** CPU-only (GPU drivers not configured)
- **Streamlit:** Running on port 8501

**Setup:**
- All dependencies installed
- Repository cloned to `/home/langchain/langchain-demo`
- Virtual environment configured
- Environment file created (API keys needed)
- SSH access configured

#### 8.2 GCP Instance
**Status:** ✅ Complete

**Details:**
- **IP:** 34.34.27.155
- **Zone:** europe-west4-b
- **GPU:** NVIDIA Tesla P4 (7680MiB VRAM)
- **CUDA:** 12.4
- **NVIDIA Drivers:** 550.54.15
- **Python:** 3.10.12
- **Model:** Llama 2 7B Q4_K_M (GPU-accelerated)
- **Status:** GPU detected and working

**Setup:**
- All dependencies installed (including CUDA support)
- Repository cloned to `/home/langchain/langchain-demo`
- Virtual environment configured
- Environment file needs to be created
- SSH access via gcloud CLI configured

#### 8.3 Documentation
**Status:** ✅ Complete

**Available Docs:**
- `README.md` - Main project documentation
- `PROJECT_STRUCTURE.md` - Directory layout
- `docs/SERVER_SETUP.md` - Linode setup guide
- `docs/SERVER_SETUP_GCP.md` - GCP setup guide
- `docs/TWO_PHASE_ARCHITECTURE.md` - Architecture details
- `docs/UI_MONITORING.md` - Streamlit dashboard guide
- `docs/LLM_LOGGING_GUIDE.md` - LLM logging system
- `docs/SSH_ACCESS_GUIDE.md` - SSH access instructions
- And more...

---

## Configuration

### Environment Variables

Required/optional variables (see `config/env.example`):

**Model Configuration:**
- `MODEL_TYPE` - `local`, `openai`, `anthropic`, `gemini`
- `MODEL_PATH` - Path to local model file

**API Keys:**
- `OPENAI_API_KEY` - For OpenAI models
- `ANTHROPIC_API_KEY` - For Anthropic models
- `GOOGLE_API_KEY` - For Gemini models
- `TAVILY_API_KEY` - For Tavily search (or `SERPER_API_KEY`)

**Optional:**
- `LANGCHAIN_API_KEY` - For LangSmith monitoring
- `DATABASE_PATH` - Database file path (default: `./data/research_agent.db`)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

---

## Usage Workflows

### Workflow 1: Two-Phase Research (Recommended)

```python
from src.research.workflows import phase1_collect_searches, phase2_process_with_llm

# Phase 1: Collect searches (one time)
phase1_collect_searches(
    csv_path="examples/companies/sample_companies.csv",
    provider="serper"
)

# Phase 2: Process with LLM (can run multiple times)
company_info = phase2_process_with_llm(
    company_name="BitMovin",
    instructions_path="examples/instructions/research_instructions.md",
    llm_provider="openai",
    llm_model="gpt-4"
)
```

### Workflow 2: Model Comparison

```python
from src.research.workflows import phase2_process_multiple_models

# Process same company with multiple models
results = phase2_process_multiple_models(
    company_name="BitMovin",
    instructions_path="examples/instructions/research_instructions.md",
    models=[
        {"provider": "openai", "model": "gpt-4"},
        {"provider": "anthropic", "model": "claude-3-opus"},
        {"provider": "local", "model": "llama-2-7b"}
    ]
)
```

### Workflow 3: Full Pipeline

```python
from src.research.workflows import full_research_pipeline

# Complete workflow: Phase 1 + Phase 2 for all companies
summary = full_research_pipeline(
    csv_path="examples/companies/sample_companies.csv",
    instructions_path="examples/instructions/research_instructions.md",
    llm_provider="openai",
    llm_model="gpt-4"
)
```

### Workflow 4: Streamlit Dashboard

```bash
# Start dashboard
bash scripts/start_streamlit.sh

# Access at http://localhost:8501 or http://172.234.181.156:8501
```

---

## Data Flow

### Phase 1 Flow

```
CSV File → Load Companies → Generate Queries → Execute Searches → Store Raw Results
                                                                         ↓
                                                              search_history table
                                                              (with raw_results JSON)
```

### Phase 2 Flow

```
Instructions + Search Results → Build Prompt → LLM Processing → Parse Output
                                        ↓                          ↓
                              prompt_version                processing_runs table
                                                              (full metadata)
                                        ↓
                              Validation & Comparison
```

### Database Relationships

```
companies (1) ←→ (many) search_history
companies (1) ←→ (many) processing_runs
processing_runs (1) ←→ (many) validation_results
processing_runs (many) ←→ (many) search_history (via JSON IDs)
```

---

## Testing & Scripts

### Test Scripts

**Location:** `scripts/`

1. **`test_two_phase.py`** - Two-phase architecture testing
   - Phase 1 testing
   - Phase 2 single model testing
   - Phase 2 multi-model testing
   - Full pipeline testing

2. **`test_llm_simple.py`** - Simple LLM loading test
3. **`test_llm.py`** - Comprehensive LLM testing
4. **`test_logging.py`** - LLM call logging test
5. **`test_metrics.py`** - Metrics calculation test

### Test Suite

**Location:** `tests/`

**Status:** ❌ Not yet implemented (Next priority)

**Planned Tests:**
- Unit tests for each component
- Integration tests for workflows
- Database operation tests
- Model factory tests

---

## Known Limitations & Future Enhancements

### Current Limitations

1. **Testing:** No automated test suite yet (manual testing only)
2. **Error Recovery:** Limited retry logic for failed operations
3. **Batch Processing:** No batch optimization for large company lists
4. **Authentication:** No auth for Streamlit dashboard (production concern)
5. **Caching:** Search results not cached (may re-execute same queries)

### Future Enhancements (Out of Scope)

- Comprehensive test suite
- Advanced error recovery and retry logic
- Batch processing optimizations
- Authentication for UI
- Vector database for semantic search
- Advanced RAG patterns
- Streaming responses
- Multi-agent systems
- Docker containerization
- Kubernetes deployment

---

## Success Criteria

### ✅ Completed

1. **Functionality:** Two-phase architecture working end-to-end
2. **Multi-Model Support:** Local and remote models operational
3. **Database:** Complete schema with audit trails
4. **UI:** Streamlit dashboard functional and accessible
5. **Documentation:** Comprehensive setup and usage guides
6. **Infrastructure:** Deployed on Linode and GCP
7. **Code Quality:** Well-structured, documented code

### 🔄 In Progress

1. **Testing:** Automated test suite (next priority)

### 📋 Future

1. **Production Hardening:** Error recovery, retry logic
2. **Performance:** Batch optimizations, caching
3. **Security:** Authentication, access control
4. **Monitoring:** Advanced metrics and alerting

---

## Maintenance & Updates

### PRD Update Process

When making changes to the system:

1. **Create PRD Update** - Document changes in [`PRD_UPDATES.md`](PRD_UPDATES.md) (see separate document)
2. **Update This PRD** - Keep this document in sync with implementation
3. **Version Control** - Track changes in git commits
4. **Review Regularly** - Monthly review to ensure accuracy

See [`PRD_UPDATE_PROCESS.md`](PRD_UPDATE_PROCESS.md) for detailed update procedures.

---

## Appendix

### Technology Stack

- **Python:** 3.10+
- **LangChain:** Latest (with modern agent runtime)
- **LLMs:** LlamaCpp (local), OpenAI, Anthropic, Google Gemini
- **Database:** SQLite (SQLAlchemy ORM)
- **UI:** Streamlit
- **Search APIs:** Tavily, Serper
- **Infrastructure:** Linode, GCP
- **Monitoring:** LangSmith (optional)

### File Structure

```
langchain-demo/
├── src/
│   ├── research/          # Two-phase architecture
│   ├── models/            # Model abstraction
│   ├── tools/             # Web search, data loaders
│   ├── database/          # Schema and operations
│   ├── utils/             # Logging, monitoring, metrics
│   ├── ui/                # Streamlit dashboard
│   └── agent/             # Research agent (legacy)
├── examples/              # Sample data and instructions
├── docs/                  # Documentation
├── scripts/               # Test scripts
├── tests/                 # Test suite (to be implemented)
└── config/                # Configuration templates
```

---

**Document Last Updated:** 2025-01-02  
**Next Review:** 2025-02-02  
**Maintainer:** Project Team

