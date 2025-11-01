# Server Setup Guide

This guide covers the installation and configuration of the LangChain Research Agent on a remote Linode GPU instance.

## Prerequisites

- Linode GPU instance (8GB+ VRAM recommended)
- Ubuntu 22.04 LTS
- Root or sudo access via SSH
- Public IP address with SSH access

## Step 1: System Updates

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

## Step 2: Install Python 3.10+

```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev
python3 --version  # Should be 3.10 or higher
```

## Step 3: Install CUDA (GPU Support)

For GPU support with local LLMs, you need CUDA installed:

### Option A: Linode GPU Instances

Linode GPU instances typically come with CUDA pre-installed. Verify:

```bash
nvcc --version
nvidia-smi
```

If CUDA is not installed:

```bash
# Install NVIDIA CUDA toolkit
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get -y install cuda

# Reboot to load NVIDIA drivers
sudo reboot
```

### Option B: CPU-Only Setup

If you're not using a GPU instance, you can still run smaller quantized models on CPU:

```bash
# Install build tools for compiling llama-cpp-python
sudo apt install -y build-essential cmake
```

## Step 4: Install System Dependencies

```bash
# Essential build tools
sudo apt install -y build-essential git curl wget

# Additional libraries
sudo apt install -y libssl-dev libffi-dev

# For llama-cpp-python GPU support
sudo apt install -y nvidia-cuda-toolkit
```

## Step 5: Create Application User (Recommended)

```bash
# Create dedicated user for the application
sudo adduser langchain
sudo usermod -aG sudo langchain

# Switch to the new user
su - langchain
```

## Step 6: Clone Repository

```bash
cd ~
git clone <your-repository-url> langchain-demo
cd langchain-demo
```

## Step 7: Setup Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

## Step 8: Install Python Dependencies

### For GPU Support (Recommended)

```bash
# Install llama-cpp-python with CUDA support
# Note: Use GGML_CUDA (LLAMA_CUBLAS is deprecated)
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python

# Install remaining dependencies
pip install -r requirements.txt
```

### For CPU-Only

```bash
# Install without GPU support
pip install llama-cpp-python --no-cache-dir
pip install -r requirements.txt
```

**Note:** Remove development dependencies for production:

```bash
pip install -r requirements.txt --no-deps
pip install langchain langchain-community llama-cpp-python openai anthropic sqlalchemy requests python-dotenv pyyaml langsmith
```

## Step 9: Download Llama Model (Optional)

If using local LLM:

```bash
# Create models directory
mkdir -p models
cd models

# Download a quantized Llama model
# Example: Llama 2 8B Q4_K_M (recommended for 8GB VRAM)
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf

cd ..
```

**Model Recommendations:**
- **8GB VRAM**: Llama 2 7B Q4_K_M or Q4_0
- **16GB VRAM**: Llama 2 13B Q4_K_M or Llama 2 70B Q2_K
- **CPU**: Smaller models like Phi-2, Orca Mini

## Step 10: Configure Environment

```bash
# Copy environment template
cp config/env.example .env

# Edit configuration
nano .env
```

Key settings to configure:

```bash
# Model Configuration
MODEL_TYPE=local  # or 'openai', 'anthropic'
MODEL_PATH=./models/llama-2-7b-chat.Q4_K_M.gguf

# API Keys (if using remote models or search)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here

# Database
DATABASE_PATH=./data/research_agent.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/agent_execution.log
```

## Step 11: Create Required Directories

```bash
mkdir -p logs data models
```

## Step 12: Verify Installation

```bash
# Test Python installation
python --version

# Test CUDA (if applicable)
nvidia-smi

# Test llama-cpp-python
python -c "from llama_cpp import Llama; print('Llama-cpp-python installed successfully')"

# Run basic tests
pytest tests/ -v
```

## Step 13: Setup Systemd Service (Optional)

For running the agent as a service:

```bash
sudo nano /etc/systemd/system/langchain-agent.service
```

Add:

```ini
[Unit]
Description=LangChain Research Agent
After=network.target

[Service]
Type=simple
User=langchain
WorkingDirectory=/home/langchain/langchain-demo
Environment="PATH=/home/langchain/langchain-demo/venv/bin"
ExecStart=/home/langchain/langchain-demo/venv/bin/python src/agent/research_agent.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable langchain-agent
sudo systemctl start langchain-agent
sudo systemctl status langchain-agent
```

## Troubleshooting

### CUDA Issues

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA installation
nvcc --version

# Reinstall NVIDIA drivers if needed
sudo ubuntu-drivers autoinstall
```

### Memory Issues

```bash
# Monitor memory usage
watch -n 1 free -m
watch -n 1 nvidia-smi

# Use smaller quantized models
# Q2_K or Q3_K_S for lower memory
```

### Python Import Errors

```bash
# Verify virtual environment is activated
which python

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Model Loading Issues

```bash
# Verify model file exists
ls -lh models/

# Test model loading
python -c "from llama_cpp import Llama; model = Llama(model_path='./models/llama-2-7b-chat.Q4_K_M.gguf', n_ctx=2048, n_gpu_layers=-1)"
```

## Security Considerations

1. **Firewall Setup**:
```bash
sudo ufw allow 22/tcp
sudo ufw enable
```

2. **SSH Key Authentication**: Disable password auth
3. **Environment Variables**: Store API keys securely
4. **File Permissions**: Restrict access to sensitive files
```bash
chmod 600 .env
chown -R langchain:langchain ~/langchain-demo
```

## Performance Optimization

### For GPU Instances

```bash
# Set GPU memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
```

### For CPU Instances

```bash
# Set number of threads
export OMP_NUM_THREADS=8
```

## Next Steps

1. Test the agent with sample data
2. Configure monitoring and logging
3. Setup regular backups
4. Implement job scheduling if needed
5. Review logs for errors

## Additional Resources

- [Linode GPU Documentation](https://www.linode.com/docs/products/compute/gpu/)
- [CUDA Installation Guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [Llama-cpp-python Docs](https://llama-cpp-python.readthedocs.io/)

