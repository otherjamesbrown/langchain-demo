# LLM Call Monitoring UI

This document describes the Streamlit dashboard for monitoring LLM calls, token usage, and performance metrics.

## Overview

The Streamlit dashboard provides a real-time interface to view and analyze LLM API calls, including:
- Token usage statistics (prompt, completion, total)
- Generation time and performance metrics
- Call history with detailed logs
- Filtering by model type, date range, etc.
- Success/failure tracking

## Database Schema

LLM calls are stored in the `llm_call_logs` table with the following structure:

```sql
CREATE TABLE llm_call_logs (
    id INTEGER PRIMARY KEY,
    model_type VARCHAR(100),        -- local, openai, anthropic, gemini
    model_name VARCHAR(255),        -- Actual model identifier
    call_type VARCHAR(100),         -- invoke, stream, batch, etc.
    agent_execution_id INTEGER,      -- Link to agent execution if applicable
    
    -- Token metrics
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    
    -- Performance metrics
    generation_time_seconds FLOAT,
    tokens_per_second FLOAT,
    
    -- Input/Output
    prompt TEXT,                    -- Full prompt (truncated if >5000 chars)
    prompt_length INTEGER,
    response TEXT,                  -- Full response (truncated if >5000 chars)
    response_length INTEGER,
    
    -- Status
    success BOOLEAN,
    error_message TEXT,
    
    -- Metadata (stored as extra_metadata to avoid SQLAlchemy reserved word conflict)
    extra_metadata JSON,
    
    -- Timestamp
    created_at DATETIME
);
```

## Installation

1. **Install Streamlit** (if not already installed):
   ```bash
   pip install streamlit pandas
   ```

2. **Ensure database is initialized**:
   ```python
   from src.database.schema import create_database
   create_database()
   ```

**Note:** The `create_database()` function is in `src/database/schema.py`, not `operations.py`.

## Usage

### Running the Dashboard

```bash
# From project root
cd ~/langchain-demo
source venv/bin/activate

# Run with remote access enabled
streamlit run src/ui/streamlit_dashboard.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true
```

**Current Server Setup:**
- Running on: http://172.234.181.156:8501
- Process: Running in background (check with `ps aux | grep streamlit`)
- Logs: `/tmp/streamlit.log`

The dashboard is accessible at:
- **Remote:** http://172.234.181.156:8501 ✅
- **Local (via SSH tunnel):** http://localhost:8501

### Logging LLM Calls

To automatically log LLM calls, use the `log_llm_call()` function:

```python
from src.utils.metrics import LLMMetrics
from src.utils.llm_logger import log_llm_call
from llama_cpp import Llama
import time

model = Llama(model_path="./models/llama-2-7b-chat.Q4_K_M.gguf")

prompt = "What is Python?"
start_time = time.time()
result = model(prompt, max_tokens=50)
end_time = time.time()

# Extract metrics
usage = result.get('usage', {})
metrics = LLMMetrics(
    prompt_tokens=usage.get('prompt_tokens', 0),
    completion_tokens=usage.get('completion_tokens', 0),
    total_tokens=usage.get('total_tokens', 0),
    start_time=start_time,
    end_time=end_time,
    generation_time=end_time - start_time,
    model_name="llama-2-7b-chat",
    model_type="local"
)

# Log to database
log_llm_call(
    metrics=metrics,
    prompt=prompt,
    response=result['choices'][0]['text'],
    model_name="llama-2-7b-chat.Q4_K_M.gguf"
)
```

### Testing the Logging

Run the test script to generate sample logs:

```bash
python scripts/test_logging.py
```

This will:
1. Make several LLM calls
2. Log them to the database
3. Display the logged entries

## Dashboard Features

### Summary Statistics

- **Total Calls**: Number of LLM calls made
- **Total Tokens**: Cumulative token usage
- **Total Time**: Cumulative generation time
- **Call Rate**: Calls per minute

### Filters

- **Model Type**: Filter by model type (local, openai, anthropic, gemini)
- **Time Range**: Filter by time period (last hour, 24h, 7 days, 30 days, all time)

### Call Details

- View individual call details:
  - Full prompt and response
  - Token breakdown
  - Performance metrics
  - Error messages (if any)
  - Additional metadata

### Auto-Refresh

Enable auto-refresh to see new calls in real-time (updates every 30 seconds).

## Integration with Agent

To automatically log all agent LLM calls, integrate the logger into your agent code:

```python
from src.utils.metrics import MetricsTracker
from src.utils.llm_logger import log_llm_call

# In your agent's LLM call method
tracker = MetricsTracker()
start_time = time.time()

# Make LLM call
response = llm.invoke(prompt)

end_time = time.time()

# Extract metrics (if using llama-cpp-python directly)
# or use LangChain callbacks for remote models

# Log to database
metrics = LLMMetrics(...)
log_llm_call(metrics, prompt=prompt, response=response)
```

## Security Notes

- The dashboard shows full prompts and responses - ensure proper access control in production
- Consider adding authentication for production deployments
- For remote access, use SSH tunneling or configure firewall rules appropriately

## Current Status

✅ **Dashboard is Live and Working**
- **URL:** http://172.234.181.156:8501
- **Status:** Accessible and functional
- **Database:** Connected and logging calls
- **Firewall:** Configured correctly (INBOUND rule for port 8501)

## Troubleshooting

### No data showing
- Ensure calls are being logged: `python scripts/test_logging.py`
- Check database path in `.env`: `DATABASE_PATH=./data/research_agent.db`
- Verify database exists and has the `llm_call_logs` table
- Run `create_database()` to ensure tables exist

### Database errors
- **Common Issue:** `metadata` is reserved in SQLAlchemy - fixed by using `extra_metadata`
- Run `create_database()` to ensure tables exist
- Check database file permissions: `ls -la data/research_agent.db`
- Verify SQLAlchemy version compatibility
- Clear Python cache: `find src -name '*.pyc' -delete`

### Import errors (ModuleNotFoundError)
- Ensure you're in project root: `cd ~/langchain-demo`
- Activate virtual environment: `source venv/bin/activate`
- Check Python path: The dashboard adds project root to `sys.path` automatically

### Streamlit not found
- Install: `pip install streamlit pandas`
- Ensure virtual environment is activated
- Verify installation: `streamlit --version`

### Connection timeout
- Verify firewall has **INBOUND** rule (not outbound) for port 8501
- Check Streamlit is listening: `ss -tlnp | grep 8501`
- Test locally first: `curl http://localhost:8501`

