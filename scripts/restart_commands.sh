#!/bin/bash
# Commands to run after SSH connection is established
# Copy and paste these into your SSH session

cd ~/langchain-demo

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

# Wait for it to start
sleep 3

# Check if it's running
if lsof -ti:8501 >/dev/null 2>&1; then
    echo "✅ Streamlit is running on port 8501"
    echo "   Dashboard available at: http://172.234.181.156:8501"
    echo "   Check logs: tail -f /tmp/streamlit.log"
    echo ""
    echo "📋 To verify the new version:"
    echo "   Look for 'Dashboard v1.2.0' at the bottom of the sidebar"
else
    echo "❌ Streamlit failed to start. Check logs:"
    tail -20 /tmp/streamlit.log
fi

