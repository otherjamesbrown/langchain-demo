# LLM Dashboard UI

This document describes the Streamlit dashboard for interacting with and monitoring LLM calls, token usage, and performance metrics.

## Overview

The Streamlit dashboard provides a multi-page interface with:

### Page 1: Call Local LLM 🤖
Interactive interface for:
- Calling your local LLM with custom prompts
- Viewing responses in real-time
- Seeing token usage metrics (prompt, completion, total tokens)
- Monitoring generation time and tokens/second
- Logging calls to the database
- Response history

### Page 2: Monitor Calls 📊
Monitoring interface for:
- Viewing historical LLM call logs
- Token usage statistics (prompt, completion, total)
- Generation time and performance metrics
- Call history with detailed logs
- Filtering by model type, date range, etc.
- Success/failure tracking

### Navigation
- **Sidebar Navigation**: Radio buttons to switch between pages
- **Version Number**: Displayed at bottom of sidebar (e.g., "Dashboard v1.2.0")
- Use the sidebar to switch between "Call Local LLM" and "Monitor Calls"

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

#### Recommended: Use Start Script

```bash
# From project root
cd ~/langchain-demo
bash scripts/start_streamlit.sh
```

This script automatically:
- Checks if port 8501 is in use
- Kills any existing Streamlit process
- Starts the dashboard on port 8501

#### Manual Start (After Code Changes)

**Consistent Process:**
1. Check if app is running on port 8501
2. Kill it if running
3. Start the new version

```bash
# Step 1: Check and kill existing process
lsof -ti:8501 | xargs kill -9 2>/dev/null || echo "Port 8501 is free"

# Step 2: Start Streamlit
cd ~/langchain-demo
source venv/bin/activate
streamlit run src/ui/streamlit_dashboard.py --server.port 8501
```

#### Server Deployment (Background)

For background execution on a server:

```bash
# Kill existing and start in background
lsof -ti:8501 | xargs kill -9 2>/dev/null
cd ~/langchain-demo
source venv/bin/activate
nohup streamlit run src/ui/streamlit_dashboard.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  > /tmp/streamlit.log 2>&1 &
```

**Access the dashboard:**
- **Local:** http://localhost:8501
- **Remote:** http://172.234.181.156:8501 (if firewall configured)
- **Via SSH tunnel:** http://localhost:8501 (after `ssh -L 8501:localhost:8501 user@server`)

**Note:** Always use port 8501 consistently. The dashboard will automatically detect and kill any existing instance before starting.

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

### Page Navigation

The dashboard has a sidebar navigation with two pages:
1. **🤖 Call Local LLM** - Interactive LLM calling interface
2. **📊 Monitor Calls** - Historical call logs and statistics

The version number is displayed at the bottom of the sidebar for validation that the latest code is running.

### Call Local LLM Page

**Features:**
- Text area for entering prompts/questions
- Generate Response button
- Real-time response display
- Model configuration (path, temperature, max tokens)
- Metrics display:
  - Prompt tokens
  - Completion tokens
  - Total tokens
  - Generation time
  - Tokens per second
- Response history
- Automatic logging to database (toggleable)

**Model Loading:**
- Models are cached after first load for faster subsequent calls
- Supports local LLM models (.gguf files)
- Model path configurable via sidebar

### Monitor Calls Page

**Summary Statistics:**
- **Total Calls**: Number of LLM calls made
- **Total Tokens**: Cumulative token usage
- **Total Time**: Cumulative generation time
- **Call Rate**: Calls per minute

**Filters:**
- **Model Type**: Filter by model type (local, openai, anthropic, gemini)
- **Time Range**: Filter by time period (last hour, 24h, 7 days, 30 days, all time)

**Call Details:**
- View individual call details:
  - Full prompt and response
  - Token breakdown
  - Performance metrics
  - Error messages (if any)
  - Additional metadata

**Auto-Refresh:**
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
- **Version:** v1.2.0 (check sidebar to verify)
- **Pages:** 
  - ✅ Call Local LLM - Interactive LLM interface
  - ✅ Monitor Calls - Historical call logs
- **Database:** Connected and logging calls
- **Firewall:** Configured correctly (INBOUND rule for port 8501)
- **Navigation:** Sidebar navigation working with radio buttons

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

