#!/bin/bash
#
# Start Streamlit Dashboard Script
#
# This script ensures consistent startup of the Streamlit dashboard:
# 1. Checks if Streamlit is already running on port 8501
# 2. Kills any existing process on that port
# 3. Starts the dashboard on port 8501
#
# Usage:
#   ./scripts/start_streamlit.sh
#   # Or from project root:
#   bash scripts/start_streamlit.sh

set -e  # Exit on error

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Port to use (always 8501 for consistency)
PORT=8501

echo "🚀 Starting Streamlit Dashboard"
echo "=================================="
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check if port 8501 is in use
PID=$(lsof -ti:$PORT 2>/dev/null || echo "")

if [ -n "$PID" ]; then
    echo "⚠️  Found existing process on port $PORT (PID: $PID)"
    echo "   Killing existing process..."
    kill -9 "$PID" 2>/dev/null || true
    sleep 2
    
    # Verify port is free
    if lsof -ti:$PORT >/dev/null 2>&1; then
        echo "❌ Failed to free port $PORT"
        echo "   Please manually kill the process using: lsof -ti:$PORT | xargs kill -9"
        exit 1
    else
        echo "✅ Port $PORT is now free"
    fi
else
    echo "✅ Port $PORT is available"
fi

echo ""
echo "📍 Starting Streamlit on port $PORT..."
echo "   Dashboard will be available at: http://localhost:$PORT"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "   Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start Streamlit
streamlit run src/ui/streamlit_dashboard.py \
    --server.port $PORT

