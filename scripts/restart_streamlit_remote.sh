#!/bin/bash
#
# Restart Streamlit Dashboard on Remote Server
#
# This script:
# 1. Pushes code changes to git (if needed)
# 2. SSH into remote server
# 3. Pulls latest code
# 4. Kills existing Streamlit process
# 5. Restarts Streamlit with new code
#
# Usage:
#   ./scripts/restart_streamlit_remote.sh
#   # Or:
#   bash scripts/restart_streamlit_remote.sh

set -e

REMOTE_USER="linode-langchain-user"
REMOTE_HOST="172.234.181.156"
REMOTE_DIR="~/langchain-demo"
PORT=8501

echo "🚀 Restarting Streamlit Dashboard on Remote Server"
echo "=================================================="
echo ""

# Step 1: Check if there are uncommitted changes
if ! git diff --quiet src/ui/streamlit_dashboard.py 2>/dev/null; then
    echo "⚠️  Uncommitted changes detected in src/ui/streamlit_dashboard.py"
    read -p "Do you want to commit and push these changes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add src/ui/streamlit_dashboard.py
        git commit -m "Update Streamlit dashboard: Add navigation and version number"
        git push
        echo "✅ Changes committed and pushed"
    else
        echo "⚠️  Proceeding without commit. Make sure remote has latest code."
    fi
fi

# Step 2: SSH and restart Streamlit
echo ""
echo "📍 Connecting to ${REMOTE_USER}@${REMOTE_HOST}..."
echo ""

ssh ${REMOTE_USER}@${REMOTE_HOST} << 'ENDSSH'
    cd ~/langchain-demo
    
    # Pull latest code if using git
    if [ -d .git ]; then
        echo "📥 Pulling latest code..."
        git pull
    fi
    
    # Kill existing Streamlit process
    echo "🛑 Stopping existing Streamlit process..."
    lsof -ti:8501 | xargs kill -9 2>/dev/null || echo "   No existing process found"
    sleep 2
    
    # Activate virtual environment and restart
    echo "🚀 Starting Streamlit with updated code..."
    source venv/bin/activate
    
    nohup streamlit run src/ui/streamlit_dashboard.py \
        --server.address 0.0.0.0 \
        --server.port 8501 \
        --server.headless true \
        > /tmp/streamlit.log 2>&1 &
    
    # Wait a moment for it to start
    sleep 3
    
    # Check if it's running
    if lsof -ti:8501 >/dev/null 2>&1; then
        echo "✅ Streamlit is running on port 8501"
        echo "   Dashboard available at: http://172.234.181.156:8501"
        echo "   Check logs: tail -f /tmp/streamlit.log"
    else
        echo "❌ Streamlit failed to start. Check logs:"
        tail -20 /tmp/streamlit.log
    fi
ENDSSH

echo ""
echo "✅ Remote restart complete!"
echo "   Dashboard: http://172.234.181.156:8501"
echo "   Validate by checking for version number in sidebar"

