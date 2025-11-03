#!/bin/bash
"""
Run BitMovin research test on remote server.

This script:
1. SSHs to the remote server
2. Activates the virtual environment
3. Runs the BitMovin research test against all available models
4. Outputs results with formatting
"""

set -euo pipefail

# Configuration
REMOTE_HOST="${REMOTE_HOST:-172.234.181.156}"
REMOTE_USER="${REMOTE_USER:-langchain}"
SSH_KEY_PATH="${LANGCHAIN_SSH_KEY:-$HOME/.ssh/id_ed25519_langchain}"
REMOTE_DIR="~/langchain-demo"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running BitMovin Research Test on Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check SSH key exists
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found at $SSH_KEY_PATH${NC}"
    echo "Set LANGCHAIN_SSH_KEY environment variable to override."
    exit 1
fi

# Check if SSH connection works
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ! ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
    "${REMOTE_USER}@${REMOTE_HOST}" "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${RED}Error: Cannot connect to ${REMOTE_USER}@${REMOTE_HOST}${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Run the test remotely
echo -e "${YELLOW}Running test on remote server...${NC}"
echo -e "${BLUE}This may take several minutes depending on models...${NC}"
echo ""

ssh -i "$SSH_KEY_PATH" \
    -o StrictHostKeyChecking=no \
    "${REMOTE_USER}@${REMOTE_HOST}" << 'ENDSSH'
    set -euo pipefail
    
    cd ~/langchain-demo || exit 1
    
    # Activate virtual environment
    if [ ! -d "venv" ]; then
        echo "Error: Virtual environment not found. Run setup first."
        exit 1
    fi
    
    source venv/bin/activate
    
    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        echo "Installing pytest and dependencies..."
        pip install -q pytest pytest-cov pytest-asyncio pytest-mock
    fi
    
    # Run the specific test
    echo ""
    echo "========================================"
    echo "Running: pytest tests/test_bitmovin_research.py -v"
    echo "========================================"
    echo ""
    
    pytest tests/test_bitmovin_research.py -v -s
    
    echo ""
    echo "========================================"
    echo "Test execution complete"
    echo "========================================"
ENDSSH

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Test completed successfully${NC}"
else
    echo -e "${RED}❌ Test failed with exit code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE

