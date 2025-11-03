# LangChain Research Agent on Linode

A production-ready LangChain agent for automated company research that runs on Linode GPU instances using local LLMs.

## Overview

This project implements a two-phase research architecture that:
- **Phase 1:** Generates and executes comprehensive web searches for company information
- **Phase 2:** Processes search results through LLMs to extract structured data
- Supports multiple model providers (local Llama 8B, OpenAI, Anthropic, Google Gemini)
- Stores results in a SQLite database with full audit trails
- Enables model comparison and testing without re-searching
- Includes comprehensive monitoring and logging

## Features

- **Two-Phase Architecture**: Separate search collection from LLM processing
- **Cost-Efficient**: Search once, process with multiple models
- **Model Comparison**: Test different models/prompts on identical data
- **Local LLM Support**: Run Llama 8B quantized models locally on GPU
- **Remote Model Support**: Use OpenAI, Anthropic, or Google Gemini APIs
- **Web Search Integration**: Multiple search API providers (Tavily, Serper, etc.)
- **Database Storage**: SQLite database with full metadata and validation
- **Monitoring**: LangSmith integration and comprehensive logging
- **Flexible Configuration**: Environment-based configuration

## Requirements

- Python 3.10+
- Linode GPU instance (8GB+ VRAM recommended) or local machine with GPU
- Ubuntu 22.04 LTS (recommended)
- CUDA for GPU support (optional but recommended)

## Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd langchain-demo
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp config/env.example .env
# Edit .env with your API keys and settings
```

5. **Download Llama model** (optional, for local LLM)
```bash
# Download from HuggingFace or your preferred source
# Place in models/ directory
```

6. **Run the two-phase research workflow**
```bash
python scripts/test_two_phase.py
```

## Configuration

Key environment variables (see `config/env.example`):

- `MODEL_TYPE`: `local`, `openai`, `anthropic`, or `gemini`
- `MODEL_PATH`: Path to local Llama model
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)
- `GOOGLE_API_KEY`: Google Gemini API key (optional)
- `TAVILY_API_KEY`: Tavily search API key
- `LANGCHAIN_API_KEY`: LangSmith API key (optional)
- `DATABASE_PATH`: SQLite database file path
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed directory layout.

## Usage

### Phase 1: Collect Search Results

```python
from src.research.workflows import phase1_collect_searches

# Generate queries and execute searches
search_ids = phase1_collect_searches(
    company_name="Acme Corporation",
    instructions_path="./examples/instructions/research_instructions.md"
)
print(f"Collected {len(search_ids)} search results")
```

### Phase 2: Process with LLM

```python
from src.research.workflows import phase2_process_with_llm
from src.models.model_factory import get_llm

# Process searches with a single model
llm = get_llm(model_type="local", model_path="./models/llama.gguf")
company_info, processing_run = phase2_process_with_llm(
    company_name="Acme Corporation",
    llm=llm,
    instructions_path="./examples/instructions/research_instructions.md"
)
print(f"Extracted: {company_info.company_name}")
```

### Full Pipeline

```python
from src.research.workflows import full_research_pipeline

# Run both phases in sequence
company_info, search_ids, processing_run = full_research_pipeline(
    company_name="Acme Corporation",
    llm_model_type="local",
    instructions_path="./examples/instructions/research_instructions.md"
)
```

### Compare Multiple Models

```python
from src.research.workflows import phase2_process_multiple_models

# Test different models on the same search results
results = phase2_process_multiple_models(
    company_name="Acme Corporation",
    model_configs=[
        {"model_type": "local", "model_path": "./models/llama.gguf"},
        {"model_type": "openai", "model_name": "gpt-4"},
        {"model_type": "anthropic", "model_name": "claude-3-opus-20240229"}
    ],
    instructions_path="./examples/instructions/research_instructions.md"
)

# Compare results
for result in results:
    print(f"{result['model']}: {result['company_info'].company_name}")
```

## Testing

Run the test suite:
```bash
pytest tests/
```

Run specific test module:
```bash
pytest tests/test_agent.py -v
```

## Documentation

### Setup Guides
- [docs/SERVER_SETUP.md](docs/SERVER_SETUP.md) - Linode server setup guide
- [docs/SERVER_SETUP_GCP.md](docs/SERVER_SETUP_GCP.md) - GCP server setup guide
- `config/env.example` - Configuration template

### Architecture & Status
- [prd/PRD_CURRENT_STATE.md](prd/PRD_CURRENT_STATE.md) - **Current System State** (What's Been Built)
- [prd/PRD.md](prd/PRD.md) - Original Product Requirements Document (Forward-Looking)
- [prd/PRD_UPDATE_PROCESS.md](prd/PRD_UPDATE_PROCESS.md) - Process for Keeping PRDs in Sync
- [prd/PRD_UPDATES.md](prd/PRD_UPDATES.md) - Changelog of PRD Updates
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Project structure
- [INFRASTRUCTURE_STATUS.md](INFRASTRUCTURE_STATUS.md) - Infrastructure setup status
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) - Application development progress

### Monitoring & UI
- [docs/UI_MONITORING.md](docs/UI_MONITORING.md) - Streamlit dashboard for LLM monitoring
- [docs/LLM_LOGGING_GUIDE.md](docs/LLM_LOGGING_GUIDE.md) - LLM call logging system
- [docs/STREAMLIT_ACCESS.md](docs/STREAMLIT_ACCESS.md) - Dashboard access guide
- **Dashboard URL:** http://172.234.181.156:8501 ✅

### Technical Documentation
- [docs/LLM_COMPONENTS.md](docs/LLM_COMPONENTS.md) - LLM component architecture
- [docs/UI_OPTIONS.md](docs/UI_OPTIONS.md) - UI framework options

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

[Specify license]

## Support

For issues and questions:
- Check the troubleshooting section in documentation
- Review logs in `logs/` directory
- Open an issue on GitHub
