# LangSmith Tracing Toggle Guide

## Overview

LangSmith tracing can now be controlled via the database, allowing you to enable/disable tracing at runtime without changing environment variables or restarting the application.

## How It Works

The tracing setting is stored in the `app_settings` table with the key `LANGCHAIN_TRACING_V2`. The system checks the database first, then falls back to the environment variable if not set in the database.

**Priority Order:**
1. Database setting (`app_settings` table)
2. Environment variable (`LANGCHAIN_TRACING_V2`)
3. Default: `false` (disabled)

## Usage

### Command Line Script

Use the provided script to toggle tracing:

```bash
# Enable tracing
python scripts/toggle_langsmith_tracing.py --enable

# Disable tracing
python scripts/toggle_langsmith_tracing.py --disable

# Check current status
python scripts/toggle_langsmith_tracing.py --status
```

### Python API

You can also control tracing programmatically:

```python
from src.utils.monitoring import (
    get_langsmith_tracing_enabled,
    set_langsmith_tracing_enabled
)

# Check if tracing is enabled
enabled = get_langsmith_tracing_enabled()
print(f"Tracing enabled: {enabled}")

# Enable tracing
set_langsmith_tracing_enabled(True)

# Disable tracing
set_langsmith_tracing_enabled(False)
```

### Database Direct Access

You can also query/update the database directly:

```python
from src.database.operations import get_app_setting, set_app_setting

# Get current setting
value = get_app_setting("LANGCHAIN_TRACING_V2", default="false")
print(f"Tracing: {value}")

# Set to enabled
set_app_setting("LANGCHAIN_TRACING_V2", "true")

# Set to disabled
set_app_setting("LANGCHAIN_TRACING_V2", "false")
```

## Important Notes

1. **Immediate Effect**: Changes take effect immediately for new LLM calls. You don't need to restart the application.

2. **Environment Variable Override**: If you set `LANGCHAIN_TRACING_V2` in your `.env` file, it will be used as a fallback if the database setting is not found.

3. **API Key Required**: Tracing requires `LANGCHAIN_API_KEY` to be set in your environment. The toggle only controls whether tracing is active, not whether it's configured.

4. **LLM Calls Only**: This setting affects LangChain LLM calls. Non-LangChain code tracing is controlled separately.

## Verification

After toggling, verify the setting:

```bash
# Check status
python scripts/toggle_langsmith_tracing.py --status

# Or in Python
from src.utils.monitoring import get_langsmith_tracing_enabled
print(get_langsmith_tracing_enabled())
```

## Integration with Existing Code

The `configure_langsmith_tracing()` function automatically checks the database setting:

```python
from src.utils.monitoring import configure_langsmith_tracing

# This will check the database and set LANGCHAIN_TRACING_V2 accordingly
configure_langsmith_tracing(project_name="my-project")
```

All existing code that uses `configure_langsmith_tracing()` will automatically respect the database setting.

## Troubleshooting

**Tracing not working?**
1. Check if API key is set: `echo $LANGCHAIN_API_KEY`
2. Check database setting: `python scripts/toggle_langsmith_tracing.py --status`
3. Verify setting in database: Query `app_settings` table for key `LANGCHAIN_TRACING_V2`

**Setting not persisting?**
- Make sure the database is writable
- Check that `set_app_setting()` is being called successfully
- Verify the database connection is working

