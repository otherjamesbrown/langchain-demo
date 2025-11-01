# LangChain Research Agent Architecture

## Overview

This document describes the architecture of the LangChain Research Agent, which gathers structured company information using web search and LLM-based extraction.

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
from src.agent.research_agent import ResearchAgent
from src.models.model_factory import get_llm

# Create agent
llm = get_llm(model_type="local")
agent = ResearchAgent(llm=llm, verbose=True)

# Research a company
result = agent.research_company("BitMovin")
```

**Agent Workflow**:
1. Receive research task
2. Search for general company information
3. Search for specific data points
4. Synthesize findings
5. Extract structured data
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

**CompanyInfo Fields**:
```python
class CompanyInfo(BaseModel):
    company_name: str
    industry: str
    company_size: str
    revenue: Optional[str]
    founded: Optional[int]
    headquarters: str
    products: List[str]
    funding_stage: Optional[str]
    competitors: List[str]
    description: Optional[str]
    website: Optional[str]
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
from src.agent.research_agent import ResearchAgent
from src.models.model_factory import get_llm

# Initialize
llm = get_llm(model_type="local")
agent = ResearchAgent(llm=llm, verbose=True)

# Research
result = agent.research_company("BitMovin")
print(result.final_answer.model_dump_json(indent=2))
```

### Batch Research

```python
companies = ["BitMovin", "OpenAI", "Anthropic"]
results = agent.batch_research(companies)
```

### Command Line

```bash
# Research single company
python src/agent/research_agent.py BitMovin

# With specific model
python src/agent/research_agent.py BitMovin --model-type openai

# Without database
python src/agent/research_agent.py BitMovin --no-db
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
class ResearchAgent:
    # Override system prompt
    SYSTEM_PROMPT = """
    Your custom prompt here...
    """
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

See `docs/SERVER_SETUP.md` for detailed instructions.

## Future Enhancements

- [ ] Vector database for semantic search
- [ ] Multi-agent collaboration
- [ ] Streaming responses
- [ ] Web UI dashboard
- [ ] Advanced RAG patterns
- [ ] Real-time monitoring
- [ ] API endpoints for external access
- [ ] Docker containerization

