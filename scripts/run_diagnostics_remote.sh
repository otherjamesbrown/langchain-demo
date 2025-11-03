#!/bin/bash
# Run Llama diagnostics on remote Linode server

set -e

SERVER="langchain-server-langchain"
REMOTE_DIR="/home/langchain/langchain-demo"
COMPANY="${1:-BitMovin}"
MAX_ITER="${2:-2}"

echo "=================================================="
echo "🔍 Running Llama Diagnostics on Remote Server"
echo "=================================================="
echo "Server: $SERVER (172.234.181.156)"
echo "Company: $COMPANY"
echo "Max Iterations: $MAX_ITER"
echo "=================================================="
echo ""

# Step 1: Push latest code to server
echo "📤 Step 1: Syncing code to server..."
rsync -avz --exclude='venv/' --exclude='__pycache__/' --exclude='*.pyc' \
    --exclude='.git/' --exclude='data/' --exclude='logs/' \
    /Users/jabrown/Documents/GitHub/Linode/langchain-demo/ \
    ${SERVER}:${REMOTE_DIR}/

echo "✅ Code synced successfully"
echo ""

# Step 2: Run diagnostic test
echo "🚀 Step 2: Running diagnostic test..."
echo "=================================================="
echo ""

ssh ${SERVER} "cd ${REMOTE_DIR} && source venv/bin/activate && python scripts/test_llama_diagnostics.py '${COMPANY}' --max-iterations ${MAX_ITER}"

echo ""
echo "=================================================="
echo "✅ Diagnostic test completed"
echo "=================================================="

