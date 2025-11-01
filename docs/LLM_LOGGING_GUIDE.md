# LLM Call Logging and Monitoring Guide

This guide explains how to log LLM calls, track token usage, and monitor activity through the Streamlit UI.

## System Overview

```
LLM Call
  ↓
Metrics Tracking (src/utils/metrics.py)
  ↓
Logger (src/utils/llm_logger.py)
  ↓
Database (llm_call_logs table)
  ↓
Streamlit UI (src/ui/streamlit_dashboard.py)
```

## Components

### 1. Database Schema (`src/database/schema.py`)

**Table:** `llm_call_logs`

Stores:
- Token usage (prompt, completion, total)
- Generation time and performance metrics
- Prompts and responses
- Model information
- Success/failure status
- Timestamps and metadata

### 2. Metrics Tracking (`src/utils/metrics.py`)

**Classes:**
- `LLMMetrics`: Container for metrics data
- `MetricsTracker`: Aggregates metrics across calls

**Usage:**
```python
from src.utils.metrics import LLMMetrics

metrics = LLMMetrics(
    prompt_tokens=10,
    completion_tokens=25,
    total_tokens=35,
    generation_time=1.5,
    model_name="llama-2-7b",
    model_type="local"
)
```

### 3. LLM Logger (`src/utils/llm_logger.py`)

**Functions:**
- `log_llm_call()`: Log a successful LLM call
- `log_error()`: Log a failed LLM call
- `get_llm_logger()`: Get logger instance

**Usage:**
```python
from src.utils.llm_logger import log_llm_call

log_llm_call(
    metrics=metrics,
    prompt="What is Python?",
    response="Python is a programming language...",
    model_name="llama-2-7b-chat.Q4_K_M.gguf"
)
```

### 4. Streamlit Dashboard (`src/ui/streamlit_dashboard.py`)

Visual interface showing:
- Summary statistics
- Recent call history
- Detailed call information
- Filtering by model type and date range

## Quick Start

### 1. Initialize Database

```bash
python -c "import sys; sys.path.insert(0, '.'); from src.database.schema import create_database; create_database()"
```

Or from the server:
```bash
cd ~/langchain-demo
source venv/bin/activate
python -c "from src.database.schema import create_database; create_database()"
```

### 2. Install Streamlit (if not installed)

```bash
pip install streamlit
```

### 3. Test Logging

```bash
python scripts/test_logging.py
```

This will:
- Make several LLM calls
- Log them to the database
- Display the results

### 4. Launch Dashboard

```bash
streamlit run src/ui/streamlit_dashboard.py
```

Access at: http://localhost:8501

## Integration Example

Here's how to integrate logging into your code:

```python
import time
from llama_cpp import Llama
from src.utils.metrics import LLMMetrics
from src.utils.llm_logger import log_llm_call

# Initialize model
model = Llama(model_path="./models/llama-2-7b-chat.Q4_K_M.gguf")

# Make call with logging
prompt = "Explain AI in one sentence."
start_time = time.time()

result = model(prompt, max_tokens=50)

end_time = time.time()
generation_time = end_time - start_time

# Extract metrics
usage = result.get('usage', {})
metrics = LLMMetrics(
    prompt_tokens=usage.get('prompt_tokens', 0),
    completion_tokens=usage.get('completion_tokens', 0),
    total_tokens=usage.get('total_tokens', 0),
    start_time=start_time,
    end_time=end_time,
    generation_time=generation_time,
    model_name="llama-2-7b-chat.Q4_K_M.gguf",
    model_type="local"
)

# Log to database
log_entry = log_llm_call(
    metrics=metrics,
    prompt=prompt,
    response=result['choices'][0]['text'],
    model_name="llama-2-7b-chat",
    call_type="invoke"
)

if log_entry:
    print(f"Logged call ID: {log_entry.id}")
```

## Dashboard Features

### Summary Statistics
- Total calls made
- Cumulative token usage
- Total generation time
- Average performance metrics
- Success/failure rates

### Call History
- Recent calls with timestamps
- Token breakdown per call
- Generation speed (tokens/second)
- Success status

### Detailed View
- Full prompt text
- Full response text
- Performance metrics
- Error messages (if any)
- Additional metadata

### Filtering
- By model type (local, openai, anthropic, gemini)
- By time range (hour, day, week, month, all time)

## Configuration

### Enable/Disable Logging

Set environment variable:
```bash
LOG_LLM_CALLS=false  # Disable logging
LOG_LLM_CALLS=true   # Enable logging (default)
```

### Database Location

Set in `.env`:
```bash
DATABASE_PATH=./data/research_agent.db
```

## Remote Access

**Current Setup:**
- **Server IP:** 172.234.181.156
- **Port:** 8501
- **Status:** ✅ Accessible remotely
- **URL:** http://172.234.181.156:8501

**Firewall Configuration:**
- Linode Cloud Firewall has **INBOUND** rule for TCP port 8501
- Allows external access to the dashboard

**Alternative: SSH Tunnel (More Secure)**
```bash
# Create SSH tunnel
ssh -L 8501:localhost:8501 linode-langchain-user

# Then access: http://localhost:8501
```

**Security Notes:**
- The dashboard shows full prompts and responses
- For production, consider:
  - SSH tunneling for encrypted access
  - Adding authentication/authorization
  - Restricting firewall to specific IP addresses
  - Using HTTPS with SSL certificate

## Troubleshooting

### No data in dashboard
1. Run test script: `python scripts/test_logging.py`
2. Check database exists: `ls -la data/research_agent.db`
3. Verify table exists: Check with database browser or SQL

### Database errors
1. Ensure database directory exists: `mkdir -p data`
2. Run `create_database()` to create tables
3. Check file permissions

### Streamlit import errors
1. Install: `pip install streamlit pandas`
2. Activate virtual environment
3. Check Python path

## Next Steps

1. **Integrate into Agent**: Add logging to your research agent
2. **Add Alerts**: Set up alerts for high token usage or failures
3. **Export Data**: Add CSV export functionality to dashboard
4. **Visualizations**: Add charts for token usage over time
5. **Cost Tracking**: Add cost estimation for remote APIs

