# SSH Access Guide for Linode Server

## Current Configuration

**Server IP:** 172.234.181.156  
**SSH Users:** 
- `root` (for administrative access)
- `langchain` (application user)  
- `linode-langchain-user` (may exist)

**SSH Key:** `~/.ssh/id_ed25519_langchain` (for key-based auth)

## Quick Reference

**See [SSH_KEY_SETUP.md](SSH_KEY_SETUP.md) for complete setup instructions.**

**Current Public Key:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFEBhaQKqeRrcPzziL3t4c/c1Z4SlIBcZPQsxBCRL+MR langchain-linode-20251101
```

## Authentication Methods

### Option 1: Use Linode Cloud Manager Console (Easiest - No SSH Keys Needed)

If you can't authenticate via SSH, use Linode's built-in console:

1. Go to https://cloud.linode.com
2. Navigate to your Linode instance
3. Click on **"Launch LISH Console"** or **"Weblish"**
4. This gives you direct terminal access without SSH

Then run the restart commands:
```bash
cd ~/langchain-demo
lsof -ti:8501 | xargs kill -9 2>/dev/null
source venv/bin/activate
nohup streamlit run src/ui/streamlit_dashboard.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  > /tmp/streamlit.log 2>&1 &
```

### Option 2: Setup SSH Keys (Recommended for Long-term)

If you want to use SSH, you'll need to set up SSH key authentication:

**On your local machine:**
```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_langchain -C "langchain-server"

# Copy public key (you'll need to add this to the server)
cat ~/.ssh/id_ed25519_langchain.pub
```

**Add key to server (via Linode Console):**
```bash
# On the server, as linode-langchain-user or root:
mkdir -p ~/.ssh
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

**Then SSH from local:**
```bash
ssh -i ~/.ssh/id_ed25519_langchain linode-langchain-user@172.234.181.156
```

### Option 3: Use Root Access (If Available)

If root access is available via Linode console:
```bash
# SSH as root
ssh root@172.234.181.156

# Then switch to application user
su - langchain
cd ~/langchain-demo
# ... restart commands
```

### Option 4: Deploy via Git (If Repository is Set Up)

If the code is in a git repository:
1. Commit and push your changes locally
2. Access server via Linode Console
3. Pull the latest code:
```bash
cd ~/langchain-demo
git pull
# Then restart Streamlit
```

## Current Status

Based on `INFRASTRUCTURE_STATUS.md`:
- ✅ Server is running at 172.234.181.156
- ✅ Streamlit dashboard is accessible at http://172.234.181.156:8501
- ⚠️ SSH key authentication may need to be configured

## Troubleshooting

### "Permission denied (publickey,password)"
- SSH keys not set up: Use Linode Console instead
- Or set up SSH keys following Option 2 above

### "No such identity: /root/.ssh/id_ed25519_langchain"
- The SSH client is looking for a specific key file
- Either create that key, or use a different method (Linode Console)

### Quick Fix: Use Linode Console
1. Go to https://cloud.linode.com
2. Select your instance
3. Click "Launch LISH Console"
4. Run restart commands directly

