# Server Setup Guide - Google Cloud Platform

This guide covers the installation and configuration of the LangChain Research Agent on a Google Cloud Platform (GCP) Compute Engine GPU instance.

## Prerequisites

- Google Cloud Platform account with billing enabled
- GCP project with Compute Engine API enabled
- `gcloud` CLI installed on your local machine (optional, can use Cloud Shell)
- GPU quota enabled for your project (request via GCP Console)
- Ubuntu 22.04 LTS with GPU support

## Step 0: Create GPU Instance (if needed)

If you don't have a GPU instance yet, create one:

```bash
# Set your project ID and zone
export PROJECT_ID=your-project-id
export ZONE=us-central1-a  # or your preferred zone with GPU availability
export INSTANCE_NAME=langchain-gpu-instance

# Create GPU instance with CUDA pre-installed image
gcloud compute instances create $INSTANCE_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --scopes=https://www.googleapis.com/auth/cloud-platform

# Wait for instance to be ready
gcloud compute instances wait-until-running $INSTANCE_NAME --zone=$ZONE

# SSH into the instance
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE
```

**Note:** For GPU instances, you'll need to install NVIDIA drivers separately. GCP provides an easy script (Note: this script shows a deprecation warning but still works):

```bash
# On the instance, install NVIDIA drivers
curl -fsSL https://raw.githubusercontent.com/GoogleCloudPlatform/compute-gpu-installation/main/linux/install_gpu_driver.py | sudo python3

# Reboot after installation
sudo reboot
```

**Important:** After installing drivers, you'll also need to install the CUDA toolkit separately for compiling llama-cpp-python (see Step 3).

**Alternative:** Use GCP's Deep Learning VM images which come with CUDA pre-installed:

```bash
gcloud compute instances create $INSTANCE_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --maintenance-policy=TERMINATE \
  --image-family=tf2-ent-2-13-cu113 \
  --image-project=deeplearning-platform-release \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd
```

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

### Option A: GCP GPU Instances with Standard Ubuntu

If you used a standard Ubuntu image, verify CUDA:

```bash
nvcc --version
nvidia-smi
```

If CUDA is not installed (nvcc not found), you'll need to install the CUDA toolkit separately. The GPU driver installation script only installs drivers, not the CUDA toolkit:

```bash
# Install NVIDIA CUDA toolkit (needed for compiling llama-cpp-python with CUDA support)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# Install CUDA toolkit 12.4 (matches driver version, adjust if needed)
sudo apt-get -y install cuda-toolkit-12-4

# Add CUDA to PATH permanently (add to ~/.bashrc)
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Verify installation
nvcc --version
nvidia-smi
```

**Note:** You may need to fix g++ symlinks if they're missing:
```bash
# Fix g++ symlink if needed (required for CUDA compilation)
sudo ln -sf /usr/bin/g++-11 /usr/bin/g++
sudo ln -sf /usr/bin/gcc-11 /usr/bin/gcc
```

### Option B: Deep Learning VM Images

GCP Deep Learning VM images come with CUDA pre-installed. Verify:

```bash
nvcc --version
nvidia-smi
```

The CUDA installation is typically at `/usr/local/cuda`. You may need to add it to your PATH:

```bash
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### Option C: CPU-Only Setup

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

# Note: nvidia-cuda-toolkit from Ubuntu repos may be outdated
# Better to install CUDA toolkit directly from NVIDIA (see Step 3 Option A)
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
# Ensure CUDA is in PATH (if not already in ~/.bashrc)
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

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

**Alternative:** Use Google Cloud Storage for model storage:

```bash
# Upload model to GCS bucket (from local machine)
gsutil cp ./models/llama-2-7b-chat.Q4_K_M.gguf gs://your-bucket-name/models/

# Download from GCS on instance
gsutil cp gs://your-bucket-name/models/llama-2-7b-chat.Q4_K_M.gguf ./models/
```

**Model Recommendations:**
- **8GB VRAM (P4, T4)**: Llama 2 7B Q4_K_M or Q4_0 (recommended for P4/T4)
- **16GB VRAM (V100, T4 in some configs)**: Llama 2 13B Q4_K_M or Llama 2 70B Q2_K
- **24GB VRAM (L4)**: Llama 2 70B Q3_K_M or Q4_K_M
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

**GCP-specific:** You can also use Google Cloud Secret Manager for API keys:

```bash
# Store secrets in Secret Manager (from local machine or Cloud Shell)
gcloud secrets create openai-api-key --data-file=- <<< "your-key-here"
gcloud secrets create anthropic-api-key --data-file=- <<< "your-key-here"

# Grant the instance service account access
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Then access in your code:

```python
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
openai_key = client.access_secret_version(
    name="projects/PROJECT_ID/secrets/openai-api-key/versions/latest"
).payload.data.decode("UTF-8")
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

# Check if GPU is visible to the instance
lspci | grep -i nvidia

# Reinstall NVIDIA drivers if needed (for standard Ubuntu images)
sudo apt-get purge nvidia* cuda*
curl -fsSL https://raw.githubusercontent.com/GoogleCloudPlatform/compute-gpu-installation/main/linux/install_gpu_driver.py | sudo python3

# Then reinstall CUDA toolkit (drivers don't include CUDA toolkit)
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-4

# Fix compiler symlinks if needed
sudo ln -sf /usr/bin/g++-11 /usr/bin/g++
sudo ln -sf /usr/bin/gcc-11 /usr/bin/gcc

sudo reboot
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

### GCP-Specific Issues

```bash
# Check instance quotas
gcloud compute project-info describe --project=PROJECT_ID

# Check if GPU is attached
gcloud compute instances describe INSTANCE_NAME --zone=ZONE --format="get(guestAccelerators)"

# Verify service account permissions
gcloud compute instances describe INSTANCE_NAME --zone=ZONE --format="get(serviceAccounts)"
```

## Security Considerations

1. **Firewall Rules**: GCP uses firewall rules instead of ufw
```bash
# From local machine or Cloud Shell
gcloud compute firewall-rules create allow-ssh \
  --allow tcp:22 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow SSH access"

# More restrictive: allow only your IP
gcloud compute firewall-rules create allow-ssh-restricted \
  --allow tcp:22 \
  --source-ranges YOUR_IP_ADDRESS/32 \
  --description "Allow SSH from specific IP"
```

2. **SSH Key Authentication**: GCP manages SSH keys automatically via metadata or OS Login
3. **Environment Variables**: Store API keys securely in Secret Manager (see Step 10)
4. **File Permissions**: Restrict access to sensitive files
```bash
chmod 600 .env
chown -R langchain:langchain ~/langchain-demo
```

5. **Service Account**: Use minimal permissions for the instance service account

## Performance Optimization

### For GPU Instances

```bash
# Set GPU memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# For persistent storage, consider using local SSDs for models
# Create instance with local SSD (faster but ephemeral)
gcloud compute instances create $INSTANCE_NAME \
  --local-ssd=interface=NVME \
  --local-ssd=interface=NVME
```

### For CPU Instances

```bash
# Set number of threads
export OMP_NUM_THREADS=8
```

### GCP-Specific Optimizations

1. **Use Persistent Disks**: For model storage, use persistent SSDs
```bash
# Create persistent disk
gcloud compute disks create model-disk \
  --size=200GB \
  --type=pd-ssd \
  --zone=$ZONE

# Attach to instance
gcloud compute instances attach-disk $INSTANCE_NAME \
  --disk=model-disk \
  --zone=$ZONE

# Mount on instance
sudo mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/sdb
sudo mkdir -p /mnt/models
sudo mount -o discard,defaults /dev/sdb /mnt/models
```

2. **Use Preemptible Instances**: For cost savings (with auto-restart)
```bash
gcloud compute instances create $INSTANCE_NAME \
  --preemptible \
  --maintenance-policy=TERMINATE
```

3. **Enable GPU Time Sharing**: Share GPUs across multiple workloads
```bash
gcloud compute instances create $INSTANCE_NAME \
  --guest-accelerator=type=nvidia-tesla-t4,count=1 \
  --metadata="install-nvidia-driver=True,gpu-sharing-strategy=time-sharing,max-shared-clients-per-gpu=4"
```

## Next Steps

1. Test the agent with sample data
2. Configure monitoring and logging (consider Cloud Logging)
3. Setup regular backups using Cloud Storage
4. Implement job scheduling if needed (Cloud Scheduler + Pub/Sub)
5. Review logs for errors (Cloud Logging)
6. Set up Cloud Monitoring alerts for GPU usage
7. Consider using Cloud Run Jobs for batch processing

## Additional Resources

- [GCP GPU Documentation](https://cloud.google.com/compute/docs/gpus)
- [CUDA Installation on GCP](https://cloud.google.com/compute/docs/gpus/install-drivers-gpu)
- [Deep Learning VM Documentation](https://cloud.google.com/deep-learning-vm/docs)
- [GCP Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Llama-cpp-python Docs](https://llama-cpp-python.readthedocs.io/)
- [Compute Engine Best Practices](https://cloud.google.com/compute/docs/best-practices)

