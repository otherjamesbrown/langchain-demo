# SSH Key Setup Guide

## Overview

This guide sets up SSH key authentication for accessing the Linode server (172.234.181.156) as both `root` and `langchain` users.

## Quick Setup

### Step 1: Generate/Get Your Public Key (Local Machine)

Run the setup script:
```bash
bash scripts/setup_ssh_keys.sh
```

This will:
- Generate an SSH key if it doesn't exist (stored at `~/.ssh/id_ed25519_langchain`)
- Display your public key
- Add convenient SSH config entries

**Copy the public key** that's displayed - you'll need it for Step 2.

### Step 2: Add Key to Server

**Option A: Via Linode Console (Easiest)**

1. Go to https://cloud.linode.com
2. Select your instance (172.234.181.156)
3. Click **"Launch LISH Console"**
4. Run the commands below (paste your public key where indicated)

**Option B: If you have temporary root access**

SSH in using password/temporary method, then run the commands.

### Step 3: Add Key to ROOT User

```bash
# Create .ssh directory
sudo mkdir -p /root/.ssh
sudo chmod 700 /root/.ssh

# Add public key (paste your key here)
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFEBhaQKqeRrcPzziL3t4c/c1Z4SlIBcZPQsxBCRL+MR langchain-linode-20251101" | sudo tee -a /root/.ssh/authorized_keys

# Set correct permissions
sudo chmod 600 /root/.ssh/authorized_keys
```

### Step 4: Add Key to LANGCHAIN User

```bash
# Create .ssh directory
sudo mkdir -p /home/langchain/.ssh
sudo chown langchain:langchain /home/langchain/.ssh
sudo chmod 700 /home/langchain/.ssh

# Add public key (paste your key here)
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFEBhaQKqeRrcPzziL3t4c/c1Z4SlIBcZPQsxBCRL+MR langchain-linode-20251101" | sudo tee -a /home/langchain/.ssh/authorized_keys

# Set correct permissions
sudo chown langchain:langchain /home/langchain/.ssh/authorized_keys
sudo chmod 600 /home/langchain/.ssh/authorized_keys
```

### Step 5: Add Key to LINODE-LANGCHAIN-USER (If Exists)

```bash
# Check if user exists
id linode-langchain-user 2>/dev/null && {
    sudo mkdir -p /home/linode-langchain-user/.ssh
    sudo chown linode-langchain-user:linode-langchain-user /home/linode-langchain-user/.ssh
    sudo chmod 700 /home/linode-langchain-user/.ssh
    echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFEBhaQKqeRrcPzziL3t4c/c1Z4SlIBcZPQsxBCRL+MR langchain-linode-20251101" | sudo tee -a /home/linode-langchain-user/.ssh/authorized_keys
    sudo chown linode-langchain-user:linode-langchain-user /home/linode-langchain-user/.ssh/authorized_keys
    sudo chmod 600 /home/linode-langchain-user/.ssh/authorized_keys
}
```

## Testing Connection

After adding keys, test from your local machine:

```bash
# Test root access
ssh -i ~/.ssh/id_ed25519_langchain root@172.234.181.156

# Test langchain user access
ssh -i ~/.ssh/id_ed25519_langchain langchain@172.234.181.156
```

Or use the convenient aliases (if SSH config was updated):

```bash
ssh langchain-server-root
ssh langchain-server-langchain
```

## Current Public Key

**Your current public key is:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFEBhaQKqeRrcPzziL3t4c/c1Z4SlIBcZPQsxBCRL+MR langchain-linode-20251101
```

**Location:** `~/.ssh/id_ed25519_langchain.pub`

## Troubleshooting

### Permission Denied Still
- Verify key was added correctly: `cat ~/.ssh/authorized_keys` (on server)
- Check file permissions: `ls -la ~/.ssh/`
- Ensure authorized_keys is 600: `chmod 600 ~/.ssh/authorized_keys`
- Check SSH server allows key auth: `sudo grep PubkeyAuthentication /etc/ssh/sshd_config`

### Wrong Key File Error
- Use `-i` flag: `ssh -i ~/.ssh/id_ed25519_langchain user@host`
- Or update SSH config as shown in setup script

### Key Already Exists Warning
- That's fine! The key is already set up for that user.

## Using the Keys

Once set up, you can:

1. **Restart Streamlit remotely:**
   ```bash
   ssh langchain-server-root "cd /home/langchain/langchain-demo && lsof -ti:8501 | xargs kill -9; su - langchain -c 'cd ~/langchain-demo && source venv/bin/activate && nohup streamlit run src/ui/streamlit_dashboard.py --server.address 0.0.0.0 --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &'"
   ```

2. **Run commands as langchain user:**
   ```bash
   ssh langchain-server-langchain "cd ~/langchain-demo && python scripts/test_llm.py"
   ```

3. **Copy files:**
   ```bash
   scp -i ~/.ssh/id_ed25519_langchain file.txt langchain@172.234.181.156:~/langchain-demo/
   ```

## Security Notes

- **Private key** (`~/.ssh/id_ed25519_langchain`) should never be shared
- **Public key** can be safely shared and added to authorized_keys
- Keep your private key file permissions as 600
- Consider using SSH agent: `ssh-add ~/.ssh/id_ed25519_langchain`

