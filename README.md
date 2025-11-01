# LangChain Research Agent on Linode

A production-ready LangChain agent for automated company research that runs on Linode GPU instances using local LLMs.

## Overview

This project implements a research agent that:
- Loads company data from CSV files
- Performs web searches for company information
- Summarizes findings using local or remote LLMs
- Stores results in a SQLite database
- Supports multiple model providers (local Llama 8B, OpenAI, Anthropic, Google Gemini)
- Includes comprehensive monitoring and logging

## Features

- **Local LLM Support**: Run Llama 8B quantized models locally on GPU
- **Remote Model Support**: Use OpenAI, Anthropic, or Google Gemini APIs as alternatives
- **Web Search Integration**: Multiple search API providers (Tavily, Serper, etc.)
- **Database Storage**: SQLite database for research results
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

6. **Run the agent**
```bash
python src/agent/research_agent.py
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

### Basic Usage

```python
from src.agent.research_agent import ResearchAgent
from src.models.model_factory import get_llm

# Initialize LLM
llm = get_llm(model_type="local", model_path="./models/llama.gguf")

# Create agent
agent = ResearchAgent(llm=llm)

# Run research on CSV file
results = agent.research_companies(
    csv_path="./examples/companies/sample_companies.csv",
    instructions_path="./examples/instructions/research_instructions.md"
)

# Access results
for company, summary in results.items():
    print(f"{company}: {summary}")
```

### Advanced Configuration

```python
from src.agent.research_agent import ResearchAgent
from src.utils.monitoring import LangSmithCallback

# Configure monitoring
callbacks = [LangSmithCallback()]

# Create agent with custom configuration
agent = ResearchAgent(
    llm=llm,
    max_iterations=10,
    verbose=True,
    callbacks=callbacks
)
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

- [PRD.md](PRD.md) - Product Requirements Document
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Project structure
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Overall project status
- [INFRASTRUCTURE_STATUS.md](INFRASTRUCTURE_STATUS.md) - Infrastructure setup status (Linode & GCP)
- [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) - Application development progress
- `config/env.example` - Configuration template

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

[Specify license]

## Support

For issues and questions:
- Check the troubleshooting section in documentation
- Review logs in `logs/` directory
- Open an issue on GitHub
