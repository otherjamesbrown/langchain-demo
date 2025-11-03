# Deployment Verification Guide

This guide explains where errors are logged and how to verify the system is functioning after deployment.

## Error Logging Locations

### 1. Server/Component Startup Errors

**Primary Location**: `/tmp/streamlit.log`

This file contains:
- Streamlit startup errors
- Import errors
- Database connection failures
- Module loading issues
- Port binding errors

**View logs:**
```bash
# From local machine
ssh linode-langchain-user "tail -f /tmp/streamlit.log"

# Or check last 50 lines
ssh linode-langchain-user "tail -50 /tmp/streamlit.log"

# Check for errors specifically
ssh linode-langchain-user "grep -i error /tmp/streamlit.log | tail -20"
```

**Common startup errors:**
- `ModuleNotFoundError`: Missing Python packages or import path issues
- `Port already in use`: Previous Streamlit instance still running
- `Database connection failed`: Database file path or permissions issue
- `ImportError`: Virtual environment not activated or packages not installed

### 2. LLM Error Logging

**Location**: Database table `llm_call_logs`

LLM errors are logged to the database with:
- `success = False`
- `error_message` field containing the error details
- `call_type = "error"` or `"invoke"` (if it was an invocation that failed)

**View via Streamlit UI:**
- Navigate to **"📊 Monitoring"** page
- Filter by `success = False`
- Click on any log entry to see error details

**View via database query:**
```bash
ssh linode-langchain-user
cd ~/langchain-demo
source venv/bin/activate
python -c "
from src.database.schema import get_session, LLMCallLog
from sqlalchemy import desc
session = get_session()
errors = session.query(LLMCallLog).filter(
    LLMCallLog.success == False
).order_by(desc(LLMCallLog.created_at)).limit(10).all()
for log in errors:
    print(f\"{log.created_at}: {log.model_name} - {log.error_message}\")
"
```

**Programmatic access:**
```python
from src.database.schema import get_session, LLMCallLog
from sqlalchemy import desc

session = get_session()
recent_errors = session.query(LLMCallLog).filter(
    LLMCallLog.success == False
).order_by(desc(LLMCallLog.created_at)).limit(10).all()

for error in recent_errors:
    print(f"Error: {error.error_message}")
    print(f"Model: {error.model_name}")
    print(f"Time: {error.created_at}\n")
```

### 3. UI/Streamlit Errors

**Location**: Displayed in Streamlit UI

Errors are shown to users via:
- `st.error()`: Critical errors (red message boxes)
- `st.warning()`: Warnings (yellow message boxes)
- `st.exception()`: Full exception tracebacks

**Common UI errors:**
- Database connection failures
- Model loading failures
- Agent initialization errors
- Validation errors

**Note**: These are also logged to `/tmp/streamlit.log` for debugging.

### 4. Application Logging

**Location**: `logs/research_agent.log` (if configured)

The application uses Python's `logging` module. Logs go to:
- Console (if running interactively)
- File: `logs/research_agent.log` (if `setup_logging()` is called)

**Check if logging is configured:**
```python
from src.utils.logging import get_logger
logger = get_logger()
logger.info("Test message")  # Should appear in logs
```

## Testing Local LLM Functionality

### Quick Test Script

**Script**: `scripts/test_llm_simple.py`

This is the simplest test to verify a local LLM can be invoked:

```bash
# On the server
ssh linode-langchain-user
cd ~/langchain-demo
source venv/bin/activate
python scripts/test_llm_simple.py
```

**What it tests:**
1. ✅ Model file exists at expected path
2. ✅ Model can be loaded (LlamaCpp initialization)
3. ✅ Model can generate a response to a simple prompt

**Expected output:**
```
Testing LLM...
==================================================
Model: ./models/llama-2-7b-chat.Q4_K_M.gguf
Loading model (this may take 10-30 seconds on first load)...

✓ Model loaded successfully!

Prompt: What is Python programming? Answer in 2-3 sentences.

Generating response...

Response:
--------------------------------------------------
[Response text here]
--------------------------------------------------

✅ LLM test successful!
```

### Full Test Suite

**Script**: `tests/test_models.py`

Run comprehensive tests:

```bash
# Run all model tests
pytest tests/test_models.py -v

# Run only local LLM tests (requires model file)
pytest tests/test_models.py::TestLocalLLM -v -m "requires_model"

# Run with output
pytest tests/test_models.py -v -s
```

**What tests cover:**
- Model factory function (`get_llm`, `get_chat_model`)
- Local model loading with various parameters
- Remote model configuration validation
- Model type enum validation

### Via Streamlit UI

**Page**: "🤖 Local LLM"

1. Navigate to the Local LLM page in Streamlit
2. Select a model file
3. Enter a simple prompt (e.g., "Say hello")
4. Click "Generate Response"
5. ✅ Should see response (no errors)

## Post-Deployment Verification Checklist

### 1. Check Streamlit Process Status

```bash
# Check if Streamlit is running on port 8501
ssh linode-langchain-user "lsof -ti:8501"

# Should output a process ID if running
# If empty, Streamlit is not running
```

### 2. Check Streamlit Logs for Errors

```bash
# View recent logs
ssh linode-langchain-user "tail -50 /tmp/streamlit.log"

# Check for specific error patterns
ssh linode-langchain-user "grep -i 'error\|exception\|failed' /tmp/streamlit.log | tail -20"

# Check for successful startup
ssh linode-langchain-user "grep -i 'running\|started\|you can now view' /tmp/streamlit.log | tail -5"
```

**Success indicators:**
- `You can now view your Streamlit app in your browser.`
- `Network URL: http://0.0.0.0:8501`
- No `ERROR` or `CRITICAL` messages

### 3. Verify Dashboard Access

```bash
# Check if port is accessible (from server)
curl -I http://localhost:8501

# Or from local machine (if firewall allows)
curl -I http://172.234.181.156:8501
```

**Expected**: HTTP 200 response

### 4. Test Database Connection

```bash
ssh linode-langchain-user
cd ~/langchain-demo
source venv/bin/activate
python -c "
from src.database.schema import get_session, LLMCallLog
session = get_session()
count = session.query(LLMCallLog).count()
print(f'✅ Database connected. Total logs: {count}')
"
```

### 5. Test Local LLM Invocation

```bash
ssh linode-langchain-user
cd ~/langchain-demo
source venv/bin/activate
python scripts/test_llm_simple.py
```

**Expected**: No errors, model loads and generates response

### 6. Test Model Factory

```bash
ssh linode-langchain-user
cd ~/langchain-demo
source venv/bin/activate
python -c "
from src.models.model_factory import get_chat_model
model = get_chat_model(model_type='local')
print(f'✅ Model loaded: {type(model).__name__}')
# Test invocation
response = model.invoke('Say hello')
print(f'✅ Response received: {response[:50]}...')
"
```

### 7. Test Structured Output Strategy Selection

**This tests the refactored code:**

```bash
ssh linode-langchain-user
cd ~/langchain-demo
source venv/bin/activate
python -c "
from src.models.model_factory import get_chat_model
from src.models.structured_output import select_structured_output_strategy
from src.tools.models import CompanyInfo

# Test local model (should return None)
local_model = get_chat_model(model_type='local')
strategy = select_structured_output_strategy(
    model=local_model,
    model_type='local',
    schema=CompanyInfo
)
print(f'Local model strategy: {strategy}')  # Should be None

# If you have remote models configured, test those too
# strategy = select_structured_output_strategy(...)
print('✅ Strategy selection working')
"
```

### 8. Test Agent Initialization

```bash
ssh linode-langchain-user
cd ~/langchain-demo
source venv/bin/activate
python -c "
from src.agent.research_agent import ResearchAgent
agent = ResearchAgent(model_type='local', max_iterations=3)
print(f'✅ Agent initialized successfully')
print(f'Model type: {agent.model_type}')
print(f'Model display name: {agent._model_display_name}')
"
```

### 9. Check UI Functionality

1. **Access Dashboard**: http://172.234.181.156:8501
2. **Verify Sidebar**: Should show all pages (Home, Local LLM, Monitoring, Agent)
3. **Check Version**: Look at bottom of sidebar - should show current version
4. **Test Navigation**: Click through pages - should load without errors
5. **Test Local LLM Page**: 
   - Select a model
   - Enter a prompt
   - Generate response
   - Verify response appears

## Quick Health Check Script

Create a comprehensive health check:

```bash
#!/bin/bash
# scripts/health_check.sh

echo "🔍 System Health Check"
echo "====================="
echo ""

# Check Streamlit process
if lsof -ti:8501 >/dev/null 2>&1; then
    echo "✅ Streamlit running on port 8501"
else
    echo "❌ Streamlit NOT running on port 8501"
fi

# Check recent errors
ERROR_COUNT=$(grep -i "error\|exception\|failed" /tmp/streamlit.log 2>/dev/null | tail -5 | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✅ No recent errors in logs"
else
    echo "⚠️  Found $ERROR_COUNT recent error(s) in logs"
    grep -i "error\|exception\|failed" /tmp/streamlit.log | tail -3
fi

# Test database
python3 -c "
from src.database.schema import get_session
try:
    session = get_session()
    print('✅ Database connection working')
except Exception as e:
    print(f'❌ Database error: {e}')
" 2>&1

# Test model loading
python3 -c "
from src.models.model_factory import get_chat_model
try:
    model = get_chat_model(model_type='local')
    print('✅ Local model can be loaded')
except Exception as e:
    print(f'⚠️  Model loading issue: {e}')
" 2>&1

echo ""
echo "Check complete!"
```

**Run health check:**
```bash
ssh linode-langchain-user "cd ~/langchain-demo && bash scripts/health_check.sh"
```

## Troubleshooting Common Issues

### Streamlit Won't Start

1. **Check logs**: `tail -50 /tmp/streamlit.log`
2. **Check port**: `lsof -ti:8501` (kill if process exists)
3. **Check virtualenv**: `source venv/bin/activate && which python`
4. **Check dependencies**: `pip list | grep streamlit`

### LLM Errors

1. **Model file missing**: Check `MODEL_PATH` environment variable
2. **GPU/CUDA issues**: Try `n_gpu_layers=0` for CPU-only
3. **Memory issues**: Reduce `n_ctx` context window
4. **Check logs**: Look for specific error messages in database or logs

### Import Errors

1. **Activate venv**: `source venv/bin/activate`
2. **Check PYTHONPATH**: Ensure project root is in path
3. **Reinstall dependencies**: `pip install -r requirements.txt`

### Database Errors

1. **Check path**: Verify `DATABASE_PATH` in `.env`
2. **Check permissions**: `ls -la data/research_agent.db`
3. **Recreate database**: `python -c "from src.database.schema import create_database; create_database()"`

## Summary

**Error Locations:**
- ✅ Server errors: `/tmp/streamlit.log`
- ✅ LLM errors: `llm_call_logs` table in database
- ✅ UI errors: Displayed in Streamlit + logged to `/tmp/streamlit.log`

**Basic LLM Test:**
- ✅ `python scripts/test_llm_simple.py` - quickest test
- ✅ Streamlit UI "🤖 Local LLM" page - interactive test

**Post-Deploy Verification:**
1. Check `/tmp/streamlit.log` for startup errors
2. Verify process running: `lsof -ti:8501`
3. Test dashboard access
4. Run `scripts/test_llm_simple.py`
5. Verify UI functionality

---

**Last Updated**: 2025-01-XX  
**Related Docs**: 
- `docs/STREAMLIT_WORKFLOW.md` - Streamlit deployment
- `docs/LLM_LOGGING_GUIDE.md` - LLM logging details
- `docs/SSH_ACCESS_GUIDE.md` - SSH access methods

