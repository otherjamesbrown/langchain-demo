#!/bin/bash

# LangChain Research Agent Installation Script
# This script installs all required components on Ubuntu 22.04

set -e  # Exit on error

echo "=========================================="
echo "LangChain Research Agent Installation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run with sudo${NC}"
    exit 1
fi

# Detect CPU vs GPU
if command -v nvidia-smi &> /dev/null; then
    HAS_GPU=true
    echo -e "${GREEN}GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader)${NC}"
else
    HAS_GPU=false
    echo -e "${YELLOW}No GPU detected - will install CPU-only version${NC}"
fi

# Update system
echo ""
echo "Step 1: Updating system packages..."
apt update && apt upgrade -y

# Install system dependencies
echo ""
echo "Step 2: Installing system dependencies..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    git \
    curl \
    wget \
    cmake \
    libssl-dev \
    libffi-dev

# Install CUDA if GPU is present
if [ "$HAS_GPU" = true ]; then
    echo ""
    echo "Step 3: Setting up GPU support..."
    
    if ! command -v nvcc &> /dev/null; then
        echo "Installing CUDA toolkit..."
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
        dpkg -i cuda-keyring_1.1-1_all.deb
        apt-get update
        apt-get install -y cuda
        echo -e "${GREEN}CUDA installed. System reboot required.${NC}"
    else
        echo -e "${GREEN}CUDA already installed${NC}"
    fi
else
    echo ""
    echo "Step 3: Skipping GPU setup (CPU-only mode)"
fi

# Create application user
echo ""
echo "Step 4: Creating application user..."
if ! id -u langchain &>/dev/null; then
    useradd -m -s /bin/bash langchain
    echo -e "${GREEN}User 'langchain' created${NC}"
else
    echo -e "${YELLOW}User 'langchain' already exists${NC}"
fi

# Clone repository if in the repository directory
if [ -f "requirements.txt" ]; then
    REPO_DIR=$(pwd)
    echo ""
    echo "Step 5: Using existing repository at $REPO_DIR"
else
    echo ""
    echo "Step 5: Please clone the repository manually"
    echo "   git clone <repository-url> ~/langchain-demo"
    echo "   cd ~/langchain-demo"
fi

# Setup Python environment
echo ""
echo "Step 6: Setting up Python environment..."
if [ -f "requirements.txt" ]; then
    # Create venv in current directory
    sudo -u langchain python3 -m venv venv
    
    # Activate and upgrade pip
    sudo -u langchain bash -c "source venv/bin/activate && pip install --upgrade pip"
    
    echo -e "${GREEN}Virtual environment created${NC}"
else
    echo -e "${YELLOW}Skipping venv setup - run this script from repository directory${NC}"
fi

# Install Python packages
echo ""
echo "Step 7: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    if [ "$HAS_GPU" = true ]; then
        echo "Installing with GPU support..."
        # Note: Use GGML_CUDA (LLAMA_CUBLAS is deprecated)
        sudo -u langchain bash -c "source venv/bin/activate && CMAKE_ARGS=\"-DGGML_CUDA=on\" pip install llama-cpp-python"
        sudo -u langchain bash -c "source venv/bin/activate && pip install -r requirements.txt"
    else
        echo "Installing CPU-only version..."
        sudo -u langchain bash -c "source venv/bin/activate && pip install llama-cpp-python --no-cache-dir"
        sudo -u langchain bash -c "source venv/bin/activate && pip install -r requirements.txt"
    fi
    echo -e "${GREEN}Python dependencies installed${NC}"
else
    echo -e "${YELLOW}Skipping Python package installation${NC}"
fi

# Create directories
echo ""
echo "Step 8: Creating required directories..."
if [ -d "langchain-demo" ]; then
    sudo -u langchain mkdir -p langchain-demo/{logs,data,models,examples/companies,examples/instructions}
    echo -e "${GREEN}Directories created${NC}"
elif [ -f "requirements.txt" ]; then
    sudo -u langchain mkdir -p logs data models examples/companies examples/instructions
    chown -R langchain:langchain logs data models examples
    echo -e "${GREEN}Directories created${NC}"
fi

# Setup firewall
echo ""
echo "Step 9: Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp
    ufw --force enable
    echo -e "${GREEN}Firewall configured${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Switch to the langchain user: sudo su - langchain"
echo "2. Navigate to repository: cd langchain-demo"
echo "3. Activate venv: source venv/bin/activate"
echo "4. Configure environment: cp config/env.example .env && nano .env"
echo "5. Download model (optional): See docs/SERVER_SETUP.md"
echo "6. Test installation: pytest tests/ -v"
echo ""

if [ "$HAS_GPU" = true ] && ! command -v nvcc &> /dev/null; then
    echo -e "${YELLOW}IMPORTANT: System reboot required to complete CUDA installation${NC}"
    echo -e "${YELLOW}Run: sudo reboot${NC}"
    echo ""
fi

echo "For detailed setup instructions, see: docs/SERVER_SETUP.md"

