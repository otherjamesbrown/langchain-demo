# Accessing Streamlit Dashboard

## Current Status

✅ **Streamlit is running** on the server at port 8501  
✅ **Listening on all interfaces** (0.0.0.0:8501)  
✅ **External access working** - Firewall configured correctly  
✅ **Dashboard accessible** at http://172.234.181.156:8501
✅ **Dashboard Version:** v1.2.0 (check sidebar)
✅ **Features:**
  - Multi-page navigation (Call Local LLM, Monitor Calls)
  - Interactive LLM calling interface
  - Real-time metrics display
  - Historical call monitoring

## Solution 1: SSH Tunnel (Recommended - Works Immediately)

Create an SSH tunnel to access the dashboard securely:

```bash
# From your local machine
ssh -L 8501:localhost:8501 linode-langchain-user

# Then open in browser:
# http://localhost:8501
```

**Or in a separate terminal (keeps tunnel open):**

```bash
# Terminal 1: Create tunnel
ssh -N -L 8501:localhost:8501 linode-langchain-user

# Terminal 2: Open browser
# Navigate to http://localhost:8501
```

## Solution 2: Open Port in Linode Cloud Firewall

**Important:** You need an **INBOUND** rule (not outbound). Outbound allows server to connect out, inbound allows external connections in.

1. Log into Linode Cloud Manager: https://cloud.linode.com
2. Go to **Firewalls** (left sidebar) or your Linode instance → **Firewalls** tab
3. Create or edit the firewall attached to your Linode
4. Add **INBOUND** rule:
   - **Label:** Allow Streamlit (optional)
   - **Type:** Custom
   - **Protocol:** TCP
   - **Ports:** 8501
   - **Sources:** 
     - For public access: `0.0.0.0/0` (all IPs)
     - For your IP only: Your IP address (more secure)
   - **Action:** Accept
5. **Save** the firewall rules
6. Ensure the firewall is **applied** to your Linode instance

**Note:** Make sure you're adding an INBOUND rule, not outbound!

After opening the port, access at:
- http://172.234.181.156:8501

## Solution 3: Check Server Firewall

If you have direct root access:

```bash
# Check if UFW is active
sudo ufw status

# If active, allow port 8501
sudo ufw allow 8501/tcp

# Check iptables (if UFW not used)
sudo iptables -L -n | grep 8501
```

## Verifying Dashboard is Running

On the server:

```bash
# Check if Streamlit process is running
ps aux | grep streamlit

# Check if port is listening
ss -tlnp | grep 8501

# Test locally on server
curl http://localhost:8501
```

## Starting/Restarting Streamlit Dashboard

### Recommended: Use the Start Script

The easiest way to start the dashboard is using the provided script, which automatically handles port cleanup:

```bash
# From project root
cd ~/langchain-demo
bash scripts/start_streamlit.sh
```

This script:
1. ✅ Checks if port 8501 is in use
2. ✅ Kills any existing Streamlit process on port 8501
3. ✅ Starts the dashboard on port 8501

### Manual Start Process

If you prefer to start manually, follow this consistent process:

```bash
# 1. Check and kill existing process on port 8501
lsof -ti:8501 | xargs kill -9 2>/dev/null || echo "Port 8501 is free"

# 2. Start Streamlit
cd ~/langchain-demo
source venv/bin/activate
streamlit run src/ui/streamlit_dashboard.py --server.port 8501
```

### Background Process (Server Deployment)

For server deployment with background execution:

```bash
# 1. Kill existing process
lsof -ti:8501 | xargs kill -9 2>/dev/null

# 2. Start in background
cd ~/langchain-demo
source venv/bin/activate
nohup streamlit run src/ui/streamlit_dashboard.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  > /tmp/streamlit.log 2>&1 &
```

**Important:** Always use port 8501 consistently. After code changes:
1. Check if app is running: `lsof -ti:8501`
2. Kill it if running: `lsof -ti:8501 | xargs kill -9`
3. Start new version: `streamlit run src/ui/streamlit_dashboard.py --server.port 8501`

## Current Server Status

- **Process:** Running (PID visible in `ps aux | grep streamlit`)
- **Port:** Listening on 0.0.0.0:8501
- **Local Access:** ✅ Working (`curl localhost:8501` works)
- **External Access:** ✅ **Working!** (Firewall configured correctly)

