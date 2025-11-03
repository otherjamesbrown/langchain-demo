# Project Structure

This document outlines the folder structure of the LangChain Research Agent project.

## Directory Overview

```
langchain-demo/
├── README.md                 # Main project documentation
├── prd/                      # Product Requirements Documents
│   ├── PRD.md                # Original Product Requirements Document
│   ├── PRD_CURRENT_STATE.md  # Current System State
│   ├── PRD_UPDATE_PROCESS.md # PRD Update Process
│   └── PRD_UPDATES.md        # PRD Update Changelog
├── PROJECT_STRUCTURE.md      # This file
├── .gitignore                # Git ignore rules
│
├── src/                      # Source code
│   ├── agent/                # Research agent implementation
│   │   ├── __init__.py
│   │   └── research_agent.py
│   │
│   ├── tools/                # Agent tools
│   │   ├── __init__.py
│   │   ├── web_search.py
│   │   └── data_loaders.py
│   │
│   ├── models/               # Model abstraction layer
│   │   ├── __init__.py
│   │   └── model_factory.py
│   │
│   ├── database/             # Database operations
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   └── operations.py
│   │
│   └── utils/                # Shared utilities
│       ├── __init__.py
│       ├── monitoring.py
│       └── logging.py
│
├── examples/                 # Example files and data
│   ├── companies/            # Sample CSV files
│   │   └── sample_companies.csv
│   │
│   └── instructions/         # Sample markdown instructions
│       └── research_instructions.md
│
├── config/                   # Configuration files
│   ├── model_config.yaml     # Model-specific settings
│   ├── agent_config.yaml     # Agent behavior settings
│   └── env.example           # Environment variable template
│
├── logs/                     # Log files (gitignored)
│   └── agent_execution.log
│
├── tests/                    # Unit and integration tests
│   ├── test_tools.py
│   ├── test_agent.py
│   └── test_database.py
│
└── requirements.txt          # Python dependencies
```

## Key Directories

### `src/`
Contains all source code organized by functionality:
- `agent/`: Main research agent implementation
- `tools/`: LangChain tools for web search and data loading
- `models/`: Model abstraction layer supporting local and remote LLMs
- `database/`: Database schema and operations for storing research results
- `utils/`: Shared utilities for monitoring and logging

### `examples/`
Contains sample data files for testing:
- CSV files with company data
- Markdown files with research instructions

### `config/`
Configuration files for models, agents, and other settings. Can be YAML, JSON, or Python files.

### `logs/`
Runtime log files are stored here. This directory is gitignored.

### `tests/`
Unit tests and integration tests for the codebase.

## File Naming Conventions

- **Python files**: `snake_case.py`
- **Directory names**: `snake_case/`
- **Config files**: `snake_case.yaml` or `snake_case.json`
- **Test files**: `test_something.py`

## Component Overview

### Research Agent
The main agent (`src/agent/research_agent.py`) orchestrates the research workflow:
1. Loads CSV data with company information
2. Reads markdown instructions for research tasks
3. Uses tools to gather information (web search)
4. Processes and summarizes findings
5. Stores results in database

### Tools
LangChain tools that the agent can use:
- **Web Search**: Searches the web for information about companies
- **Data Loaders**: Loads CSV and markdown files

### Models
Abstraction layer for LLM providers:
- Local models (Llama 8B via LlamaCpp)
- Remote APIs (OpenAI, Anthropic)

### Database
SQLite database for storing:
- Research results
- Company information
- Search history
- Execution metadata
