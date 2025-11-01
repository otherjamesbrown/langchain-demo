# Streamlit Dashboard Workflow

## Consistent Startup Process

This document describes the standard workflow for starting the Streamlit dashboard after making code changes.

## Version Numbering

The dashboard includes a version number (`DASHBOARD_VERSION`) in `src/ui/streamlit_dashboard.py`. 

**Important:** When making UI changes:
1. Increment the version number (e.g., `1.2.0` → `1.2.1`)
2. This allows validation that the new code is running
3. Version is displayed at the bottom of the sidebar

**Current Version:** v1.2.0

## Quick Start

Use the provided start script (recommended):

```bash
cd ~/langchain-demo
bash scripts/start_streamlit.sh
```

This script automatically:
1. ✅ Checks if port 8501 is in use
2. ✅ Kills any existing Streamlit process on port 8501
3. ✅ Starts the dashboard on port 8501

## Standard Workflow After Code Changes

When you make changes to `src/ui/streamlit_dashboard.py` or related UI code, follow this process:

### Step 1: Check for Running Instance

```bash
lsof -ti:8501
```

If this returns a PID, the dashboard is running.

### Step 2: Kill Existing Process

```bash
lsof -ti:8501 | xargs kill -9 2>/dev/null || echo "Port 8501 is free"
```

This safely kills any process on port 8501, or does nothing if the port is free.

### Step 3: Start New Version

```bash
cd ~/langchain-demo
source venv/bin/activate  # If using virtual environment
streamlit run src/ui/streamlit_dashboard.py --server.port 8501
```

## One-Line Command

For quick restarts:

```bash
lsof -ti:8501 | xargs kill -9 2>/dev/null; cd ~/langchain-demo && streamlit run src/ui/streamlit_dashboard.py --server.port 8501
```

Or use the script:

```bash
bash scripts/start_streamlit.sh
```

## Why Port 8501?

Using a consistent port (8501) ensures:
- ✅ Predictable access URL: http://localhost:8501
- ✅ No port confusion when accessing the dashboard
- ✅ Easier firewall configuration
- ✅ Consistent documentation and scripts

## Start Script Details

The `scripts/start_streamlit.sh` script performs these checks:

1. **Port Check**: Uses `lsof -ti:8501` to find any process using port 8501
2. **Clean Kill**: Kills the process with `kill -9` if found
3. **Verification**: Waits and verifies the port is free
4. **Start**: Launches Streamlit on port 8501

## Troubleshooting

### Port Still in Use After Kill

If the port appears to still be in use:

```bash
# Check what's using the port
lsof -i:8501

# Force kill all Streamlit processes
pkill -9 -f streamlit

# Verify port is free
lsof -ti:8501 || echo "Port is free"
```

### Permission Denied

If you get permission errors:

```bash
# Check file permissions
chmod +x scripts/start_streamlit.sh

# Or run manually
bash scripts/start_streamlit.sh
```

### Different Port Error

If Streamlit tries to use a different port, check:
- Environment variables that might override the port
- Previous Streamlit config in `~/.streamlit/config.toml`
- Explicitly pass `--server.port 8501` flag

## Background Execution (Server)

For server deployment where you want the process to run in the background:

```bash
# Kill existing
lsof -ti:8501 | xargs kill -9 2>/dev/null

# Start in background
cd ~/langchain-demo
source venv/bin/activate
nohup streamlit run src/ui/streamlit_dashboard.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  > /tmp/streamlit.log 2>&1 &
```

Check logs:
```bash
tail -f /tmp/streamlit.log
```

## Best Practices

1. **Always use port 8501** - Don't change ports between runs
2. **Kill before start** - Always check and kill existing instances
3. **Use the script** - The start script handles edge cases
4. **Check after changes** - Verify the dashboard loads correctly after code changes
5. **Document exceptions** - If you need a different port, document why

## Integration with Development Workflow

When developing UI features:

1. Make code changes to `src/ui/streamlit_dashboard.py`
2. Save file
3. Run: `bash scripts/start_streamlit.sh`
4. Test changes in browser at http://localhost:8501
5. Repeat as needed

The script ensures you're always running the latest code without port conflicts.

