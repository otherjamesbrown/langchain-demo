# LangChain Research Agent Architecture

## Overview

This document describes the architecture of the LangChain Research Agent, which gathers structured company information using web search and LLM-based extraction.

**📋 Important**: For architectural principles and conventions that guide development decisions, see **[ARCHITECTURAL_PRINCIPLES.md](./ARCHITECTURAL_PRINCIPLES.md)**. This includes principles like "database as source of truth" and other key conventions.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │         Research Agent (ReAct Pattern)           │    │
│  │  - Orchestrates workflow                          │    │
│  │  - Manages tools and decisions                    │    │
│  │  - Extracts structured data                       │    │
│  └───────────────────────────────────────────────────┘    │
│                         │                                   │
│          ┌──────────────┴──────────────┐                  │
│          ▼                             ▼                   │
│  ┌─────────────────┐         ┌─────────────────┐         │
│  │  Web Search     │         │  LLM (Local/    │         │
│  │     Tool        │         │   Remote)       │         │
│  │  (Tavily/       │         │  - OpenAI       │         │
│  │   Serper)       │         │  - Anthropic    │         │
│  └─────────────────┘         │  - Llama 8B     │         │
│          │                   └─────────────────┘         │
│          ▼                            │                   │
│  ┌──────────────────────────────────────────┐           │
│  │      Structured Data Extractor          │           │
│  │      (Pydantic Models)                  │           │
│  └──────────────────────────────────────────┘           │
│                         │                                  │
│          ┌──────────────┴──────────────┐                 │
│          ▼                             ▼                  │
│  ┌─────────────────┐         ┌─────────────────┐        │
│  │   Database      │         │  Monitoring &   │        │
│  │   (SQLite)      │         │   Logging       │        │
│  │  - Companies    │         │  - LangSmith    │        │
│  │  - Search       │         │  - Performance  │        │
│  │  - Executions   │         │  - Callbacks    │        │
│  └─────────────────┘         └─────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Research Agent (`src/agent/research_agent.py`)

**Purpose**: Main orchestration component that coordinates the research workflow.

**Key Features**:
- ReAct (Reasoning-Acting) pattern implementation
- Iterative web search and information gathering
- Structured output extraction
- Database integration
- Error handling and recovery

**Usage**:
```python
from src.research.workflows import full_research_pipeline

# Run complete two-phase workflow
company_info, search_ids, processing_run = full_research_pipeline(
    company_name="BitMovin",
    llm_model_type="local",
    instructions_path="./examples/instructions/research_instructions.md"
)
```

**Research Workflow**:
1. **Phase 1**: Generate and execute search queries
2. Store raw search results with metadata
3. **Phase 2**: Build prompt from instructions + search results
4. Process through LLM to extract structured data
5. Validate and store results with full audit trail
6. Save to database

### 2. Model Factory (`src/models/model_factory.py`)

**Purpose**: Abstraction layer for multiple LLM providers.

**Supported Providers**:
- Local: LlamaCpp (quantized models)
- Remote: OpenAI GPT-4, Anthropic Claude

**Key Functions**:
- `get_llm()`: Factory function to create LLM instances
- `list_available_providers()`: List installed providers

**Usage**:
```python
from src.models.model_factory import get_llm

# Local model
llm = get_llm(model_type="local", model_path="./models/llama.gguf")

# Remote models
llm = get_llm(model_type="openai")
llm = get_llm(model_type="anthropic")
```

### 3. Web Search Tool (`src/tools/web_search.py`)

**Purpose**: LangChain tool for web search operations.

**Supported APIs**:
- Tavily Search API (primary)
- Serper API (alternative)

**Features**:
- Structured search results
- Result formatting for agents
- Rate limiting and error handling
- Relevance scoring

**Usage**:
```python
from src.tools.web_search import web_search_tool

# Agent automatically uses this tool
# Tool query: "BitMovin company information"
results = web_search_tool("BitMovin industry employees")
```

### 4. Data Models (`src/tools/models.py`)

**Purpose**: Pydantic models for structured data validation.

**Key Models**:
- `CompanyInfo`: Complete company information
- `SearchResult`: Search API responses
- `AgentResult`: Agent execution results

**CompanyInfo Fields (core + GTM profiling)**:
```python
class CompanyInfo(BaseModel):
    # Core firmographics
    company_name: str
    industry: str
    company_size: str
    company_size_reason: Optional[str]
    headquarters: str
    founded: Optional[int]
    description: Optional[str]
    website: Optional[str]
    products: List[str]
    competitors: List[str]
    revenue: Optional[str]
    funding_stage: Optional[str]

    # GTM classifications with evidence
    growth_stage: Optional[str]
    growth_stage_reason: Optional[str]
    industry_vertical: Optional[str]
    industry_vertical_reason: Optional[str]
    sub_industry_vertical: Optional[str]
    sub_industry_vertical_reason: Optional[str]
    financial_health: Optional[str]
    financial_health_reason: Optional[str]
    business_and_technology_adoption: Optional[str]
    business_and_technology_adoption_reason: Optional[str]
    primary_workload_philosophy: Optional[str]
    primary_workload_philosophy_reason: Optional[str]
    buyer_journey: Optional[str]
    buyer_journey_reason: Optional[str]
    budget_maturity: Optional[str]
    budget_maturity_reason: Optional[str]
    cloud_spend_capacity: Optional[str]
    cloud_spend_capacity_reason: Optional[str]
    procurement_process: Optional[str]
    procurement_process_reason: Optional[str]
    key_personas: List[str]
    key_personas_reason: Optional[str]
```

### 5. Database Layer (`src/database/`)

**Purpose**: Persistent storage for company data and execution history.

**Components**:
- `schema.py`: SQLAlchemy models and database setup
- `operations.py`: CRUD operations for data access

**Tables**:
- `companies`: Company information
- `search_history`: Web search operations
- `agent_executions`: Agent run records

**Usage**:
```python
from src.database.operations import save_company_info, get_company

# Save company data
company_info = CompanyInfo(...)
save_company_info(company_info)

# Retrieve company
company = get_company("BitMovin")
```

### 6. Monitoring & Logging (`src/utils/`)

**Purpose**: Observability and debugging utilities.

**Components**:
- `logging.py`: Centralized logging configuration
- `monitoring.py`: Callbacks and performance tracking

**Features**:
- Structured logging with rotation
- LangSmith integration
- Performance metrics
- Agent step tracking

## Data Flow

### Example: Researching BitMovin

```
1. Input
   └─ Company Name: "BitMovin"
   
2. Agent Initialization
   └─ Load LLM (local/remote)
   └─ Setup tools and prompts
   
3. Agent Execution (ReAct Loop)
   ├─ Thought: "Need company overview"
   ├─ Action: web_search("BitMovin company overview")
   ├─ Observation: "BitMovin is a video streaming tech company..."
   │
   ├─ Thought: "Need employee count"
   ├─ Action: web_search("BitMovin employee count")
   ├─ Observation: "200-500 employees..."
   │
   ├─ Thought: "Need competitors"
   ├─ Action: web_search("BitMovin competitors")
   ├─ Observation: "Brightcove, JW Player, Mux..."
   │
   └─ Final Answer: Structured CompanyInfo
   
4. Data Storage
   ├─ Save to companies table
   ├─ Save execution record
   └─ Log to file
   
5. Result
   └─ CompanyInfo with all fields populated
```

## Configuration

### Environment Variables

```bash
# Model Configuration
MODEL_TYPE=local  # or openai, anthropic
MODEL_PATH=./models/llama-8b-q4.gguf

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
SERPER_API_KEY=...

# Database
DATABASE_PATH=./data/research_agent.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/agent_execution.log

# Monitoring
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=research-agent

# Agent Settings
TEMPERATURE=0.7
MAX_ITERATIONS=10
```

### Configuration Files

- `config/env.example`: Environment variable template
- `config/model_config.yaml`: Model-specific settings (future)
- `config/agent_config.yaml`: Agent behavior settings (future)

## Usage Examples

### Basic Usage

```python
from src.research.workflows import full_research_pipeline

# Research a company
company_info, search_ids, processing_run = full_research_pipeline(
    company_name="BitMovin",
    llm_model_type="local",
    instructions_path="./examples/instructions/research_instructions.md"
)
print(company_info.model_dump_json(indent=2))
```

### Multi-Model Comparison

```python
from src.research.workflows import phase2_process_multiple_models

# Compare results across different models
results = phase2_process_multiple_models(
    company_name="BitMovin",
    model_configs=[
        {"model_type": "local", "model_path": "./models/llama.gguf"},
        {"model_type": "openai", "model_name": "gpt-4"},
        {"model_type": "anthropic", "model_name": "claude-3-opus-20240229"}
    ],
    instructions_path="./examples/instructions/research_instructions.md"
)
```

### Command Line

```bash
# Run two-phase research workflow
python scripts/test_two_phase.py

# Phase 1 only (collect searches)
python scripts/test_two_phase.py --phase 1

# Phase 2 with specific model
python scripts/test_two_phase.py --phase 2 --company BitMovin
```

## Performance Considerations

### Optimization Strategies

1. **Model Selection**
   - Use local Llama for cost efficiency
   - Use remote models for better accuracy
   - Consider model size vs. quality tradeoffs

2. **Search Optimization**
   - Limit search results (default: 5)
   - Use specific queries
   - Cache repeated searches

3. **Database Performance**
   - SQLite suitable for single-server deployment
   - Index on company_name for fast lookups
   - Consider PostgreSQL for scale

4. **Monitoring**
   - Track execution times
   - Monitor tool usage
   - Analyze agent reasoning

## Extensibility

### Adding New Tools

```python
from langchain.tools import tool

@tool
def custom_tool(input: str) -> str:
    """Tool description for agent."""
    # Implementation
    return result
```

### Adding New Models

```python
# In model_factory.py
def _create_custom_model(**kwargs):
    # Implementation
    return CustomLLM(**kwargs)
```

### Custom Prompt Engineering

```python
# Customize LLM prompts via instructions file
instructions = """
Your custom research instructions here...
Focus on: industry, products, competitors, funding
"""

company_info, search_ids, processing_run = full_research_pipeline(
    company_name="BitMovin",
    llm_model_type="local",
    instructions=instructions  # Pass custom instructions
)
```

## Security

### Best Practices

1. **API Keys**: Store in environment variables, never in code
2. **Database**: Use connection pooling, validate inputs
3. **Logging**: Don't log sensitive data
4. **Rate Limiting**: Implement for API calls
5. **Input Validation**: Sanitize user inputs

## Testing

### Unit Tests

```bash
pytest tests/test_tools.py
pytest tests/test_agent.py
pytest tests/test_database.py
```

### Integration Tests

```bash
pytest tests/test_integration.py
```

## Deployment

### Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp config/env.example .env
# Edit .env

# Run
python src/agent/research_agent.py BitMovin
```

### Server Deployment

See `docs/infrastructure/SERVER_SETUP.md` for detailed instructions.

## Future Enhancements

- [ ] Vector database for semantic search
- [ ] Multi-agent collaboration
- [ ] Streaming responses
- [ ] Web UI dashboard
- [ ] Advanced RAG patterns
- [ ] Real-time monitoring
- [ ] API endpoints for external access
- [ ] Docker containerization


