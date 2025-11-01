#!/bin/bash
#
# Setup SSH Key Authentication for Linode Server
#
# This script helps set up SSH key access for both root and langchain users
# on the remote Linode server (172.234.181.156)
#
# Usage:
#   1. Run this script locally to generate keys (if needed)
#   2. Copy the public key that's displayed
#   3. Use Linode Console to add the key to both root and langchain users
#   4. Test SSH connection

set -e

REMOTE_HOST="172.234.181.156"
SSH_KEY_PATH="$HOME/.ssh/id_ed25519_langchain"
PUBLIC_KEY_PATH="${SSH_KEY_PATH}.pub"

echo "🔐 Setting up SSH Key Authentication for Linode Server"
echo "======================================================"
echo ""
echo "Server: ${REMOTE_HOST}"
echo "Key Location: ${SSH_KEY_PATH}"
echo ""

# Step 1: Generate SSH key if it doesn't exist
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "📝 Generating new SSH key..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "langchain-server-${USER}"
    echo "✅ SSH key generated"
else
    echo "✅ SSH key already exists at ${SSH_KEY_PATH}"
fi

# Step 2: Display public key
echo ""
echo "📋 Your Public Key (copy this):"
echo "--------------------------------"
cat "$PUBLIC_KEY_PATH"
echo ""
echo "--------------------------------"
echo ""

# Step 3: Instructions
echo "📝 Next Steps:"
echo ""
echo "1. Go to Linode Cloud Manager: https://cloud.linode.com"
echo "2. Select your instance (${REMOTE_HOST})"
echo "3. Click 'Launch LISH Console'"
echo ""
echo "4. Add key to ROOT user:"
echo "   sudo mkdir -p /root/.ssh"
echo "   sudo chmod 700 /root/.ssh"
echo "   sudo nano /root/.ssh/authorized_keys"
echo "   # Paste the public key above, save and exit"
echo "   sudo chmod 600 /root/.ssh/authorized_keys"
echo ""
echo "5. Add key to LANGCHAIN user:"
echo "   sudo mkdir -p /home/langchain/.ssh"
echo "   sudo chown langchain:langchain /home/langchain/.ssh"
echo "   sudo chmod 700 /home/langchain/.ssh"
echo "   sudo -u langchain nano /home/langchain/.ssh/authorized_keys"
echo "   # Paste the public key above, save and exit"
echo "   sudo chmod 600 /home/langchain/.ssh/authorized_keys"
echo ""
echo "6. If linode-langchain-user exists, add key there too:"
echo "   sudo mkdir -p /home/linode-langchain-user/.ssh"
echo "   sudo chown linode-langchain-user:linode-langchain-user /home/linode-langchain-user/.ssh"
echo "   sudo chmod 700 /home/linode-langchain-user/.ssh"
echo "   sudo -u linode-langchain-user nano /home/linode-langchain-user/.ssh/authorized_keys"
echo "   # Paste the public key above, save and exit"
echo "   sudo chmod 600 /home/linode-langchain-user/.ssh/authorized_keys"
echo ""
echo "7. Test connection:"
echo "   ssh -i ${SSH_KEY_PATH} root@${REMOTE_HOST}"
echo "   ssh -i ${SSH_KEY_PATH} langchain@${REMOTE_HOST}"
echo ""

# Step 4: Create SSH config entry
SSH_CONFIG="$HOME/.ssh/config"
if [ ! -f "$SSH_CONFIG" ]; then
    touch "$SSH_CONFIG"
    chmod 600 "$SSH_CONFIG"
fi

if ! grep -q "Host langchain-server" "$SSH_CONFIG"; then
    echo ""
    echo "📝 Adding SSH config entry..."
    cat >> "$SSH_CONFIG" << EOF

# Langchain Server
Host langchain-server
    HostName ${REMOTE_HOST}
    User root
    IdentityFile ${SSH_KEY_PATH}
    IdentitiesOnly yes

Host langchain-server-root
    HostName ${REMOTE_HOST}
    User root
    IdentityFile ${SSH_KEY_PATH}
    IdentitiesOnly yes

Host langchain-server-langchain
    HostName ${REMOTE_HOST}
    User langchain
    IdentityFile ${SSH_KEY_PATH}
    IdentitiesOnly yes
EOF
    echo "✅ SSH config updated"
    echo ""
    echo "You can now connect using:"
    echo "  ssh langchain-server-root"
    echo "  ssh langchain-server-langchain"
else
    echo ""
    echo "✅ SSH config already has langchain-server entries"
fi

echo ""
echo "🎯 Setup complete! Follow the steps above to add keys to the server."

