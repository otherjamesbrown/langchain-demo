# Infrastructure Quick Reference

This file contains quick reference information for accessing and managing the LangChain demo infrastructure.

## Remote Server Connection (Linode)

**IP Address:** 172.234.181.156

### SSH Connection Commands

**As root user:**
```bash
ssh linode-langchain
# or
ssh -i ~/.ssh/id_ed25519_langchain root@172.234.181.156
```

**As langchain user (Recommended for app work):**
```bash
ssh linode-langchain-user
# or
ssh -i ~/.ssh/id_ed25519_langchain langchain@172.234.181.156
```

### SSH Configuration

- **SSH Key Path:** `~/.ssh/id_ed25519_langchain`
- **Port:** 22 (default)
- **SSH Config Hosts:**
  - `linode-langchain` → root@172.234.181.156
  - `linode-langchain-user` → langchain@172.234.181.156

### Application User (langchain)

- **Username:** langchain
- **Status:** ✅ Already exists and configured
- **Home Directory:** `/home/langchain`
- **Has sudo access:** ✅ Yes (member of sudo group)
- **User ID:** 1000
- **Groups:** langchain, sudo, users
- **Password:** No password set (account locked - password auth disabled)
- **SSH Key Access:** ✅ Configured and working
- **Access method:** `ssh linode-langchain-user` (recommended) or `su - langchain` from root

## Git Repository

- **GitHub URL:** https://github.com/otherjamesbrown/langchain-demo
- **Status:** ✅ Repository created and code pushed
- **Local git:** ✅ Initialized, committed, and pushed to main branch
- **Server clone:** ✅ Successfully cloned to `/home/langchain/langchain-demo`

## Python Environment (Linode Server)

- **Python version:** 3.12.3
- **Virtual environment:** ✅ Created at `/home/langchain/langchain-demo/venv`
- **pip:** ✅ Upgraded to 25.3
- **Dependencies:** ✅ All installed (llama-cpp-python with CUDA support, LangChain, OpenAI, Anthropic, Google Gemini, etc.)
- **Installation note:** Using `GGML_CUDA` flag (replaced deprecated `LLAMA_CUBLAS`)
- **Remote LLM APIs:** OpenAI, Anthropic, Google Gemini (via langchain-google-genai)

## Streamlit Dashboard

- **URL:** http://172.234.181.156:8501
- **Status:** ✅ Running (when started)
- **Current Version:** Check sidebar for version number
- **Restart Command:**
  ```bash
  ssh linode-langchain-user "cd ~/langchain-demo && lsof -ti:8501 | xargs kill -9 2>/dev/null; source venv/bin/activate && nohup streamlit run src/ui/streamlit_dashboard.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &"
  ```

## Google Cloud Platform (GCP) Project

- **Project ID:** langchain-demo-476911
- **Project Name:** langchain-demo
- **Project Number:** 794834705883
- **Status:** ✅ Connected and configured
- **Active Account:** james@brown.chat
- **gcloud Config:** ✅ Project set as default

### GCP Setup Status

- **Billing:** ✅ Enabled
- **Compute Engine API:** ✅ Enabled
- **GPU Quota:** ⚠️ Partially approved
  - **Regional Quotas:** ✅ Approved
    - **NVIDIA T4 GPUs:** 1 (in us-central1 region)
    - **NVIDIA L4 GPUs:** 1 (in us-central1 region)
  - **Global Quota:** ⚠️ **GPUS_ALL_REGIONS = 0** (needs increase for some operations)
- **Available GPU Types:** nvidia-tesla-t4, nvidia-tesla-v100, nvidia-l4, nvidia-a100-80gb, nvidia-h100-80gb (us-central1-a)
- **Recommended Zone:** us-central1-a (has multiple GPU types available)
- **Recommended GPU:** nvidia-tesla-t4 (cost-effective, 16GB VRAM, good for Llama 2 7B-13B models)
- **Alternative - CHEAPER:** nvidia-tesla-p4 (~$0.30-0.35/hour, 8GB VRAM, good for Llama 2 7B quantized models)

### GCP Instance

- **Instance Name:** langchain-gpu-instance
- **Zone:** europe-west4-b
- **IP Address:** 34.34.27.155
- **Status:** RUNNING
- **GPU:** NVIDIA Tesla P4 (7680MiB VRAM)
- **SSH:** `gcloud compute ssh langchain-gpu-instance --zone=europe-west4-b`

### gcloud Commands Reference

```bash
# Set project (if needed)
gcloud config set project langchain-demo-476911

# Verify connection
gcloud projects describe langchain-demo-476911

# Check GPU quota
gcloud compute project-info describe --format="get(quotas[metric=GPUS_ALL_REGIONS])"

# List available GPU types in zone
gcloud compute accelerator-types list --filter="zone:us-central1-a"

# List available zones
gcloud compute zones list --filter="status:UP"

# SSH into GCP instance
gcloud compute ssh langchain-gpu-instance --zone=europe-west4-b
```

## Quick Commands

### Restart Streamlit Dashboard
```bash
ssh linode-langchain-user "cd ~/langchain-demo && bash scripts/start_streamlit.sh"
```

### Check Streamlit Status
```bash
ssh linode-langchain-user "lsof -ti:8501 && echo 'Running' || echo 'Not running'"
```

### View Streamlit Logs
```bash
ssh linode-langchain-user "tail -f /tmp/streamlit.log"
```

### Pull Latest Code on Server
```bash
ssh linode-langchain-user "cd ~/langchain-demo && git pull"
```

## Related Documentation

- **Server Setup:** `docs/SERVER_SETUP.md` (Linode)
- **GCP Setup:** `docs/SERVER_SETUP_GCP.md`
- **SSH Access:** `docs/SSH_ACCESS_GUIDE.md`
- **Infrastructure Status:** `INFRASTRUCTURE_STATUS.md` (root directory)

