#!/bin/bash
#
# Add SSH Public Key to Server Users
# 
# Run this script on the Linode server (via Console) to add the SSH key
# to root and langchain users for key-based authentication.
#
# Usage:
#   1. Copy the PUBLIC KEY from setup_ssh_keys.sh output
#   2. SSH into server or use Linode Console
#   3. Run: bash <(curl -s <script-url>) <PUBLIC_KEY>
#   4. Or paste this script and run it with the public key as argument

set -e

PUBLIC_KEY="$1"

if [ -z "$PUBLIC_KEY" ]; then
    echo "❌ Error: No public key provided"
    echo ""
    echo "Usage: $0 'ssh-ed25519 AAAAC...'"
    echo ""
    echo "Or manually add key:"
    echo "  echo 'PUBLIC_KEY' | sudo tee -a /root/.ssh/authorized_keys"
    exit 1
fi

echo "🔐 Adding SSH Public Key to Server Users"
echo "=========================================="
echo ""
echo "Public Key: ${PUBLIC_KEY:0:50}..."
echo ""

# Function to add key to a user
add_key_to_user() {
    local USERNAME=$1
    local HOME_DIR=$2
    local SSH_DIR="${HOME_DIR}/.ssh"
    local AUTH_KEYS="${SSH_DIR}/authorized_keys"
    
    echo "📝 Adding key to ${USERNAME} user..."
    
    # Create .ssh directory if it doesn't exist
    if [ ! -d "$SSH_DIR" ]; then
        if [ "$USERNAME" = "root" ]; then
            mkdir -p "$SSH_DIR"
            chmod 700 "$SSH_DIR"
        else
            mkdir -p "$SSH_DIR"
            chown "${USERNAME}:${USERNAME}" "$SSH_DIR"
            chmod 700 "$SSH_DIR"
        fi
        echo "   ✅ Created ${SSH_DIR}"
    fi
    
    # Create authorized_keys if it doesn't exist
    if [ ! -f "$AUTH_KEYS" ]; then
        touch "$AUTH_KEYS"
        if [ "$USERNAME" != "root" ]; then
            chown "${USERNAME}:${USERNAME}" "$AUTH_KEYS"
        fi
        chmod 600 "$AUTH_KEYS"
        echo "   ✅ Created ${AUTH_KEYS}"
    fi
    
    # Check if key already exists
    if grep -q "$PUBLIC_KEY" "$AUTH_KEYS" 2>/dev/null; then
        echo "   ⚠️  Key already exists in ${AUTH_KEYS}"
    else
        # Add key
        echo "$PUBLIC_KEY" >> "$AUTH_KEYS"
        if [ "$USERNAME" != "root" ]; then
            chown "${USERNAME}:${USERNAME}" "$AUTH_KEYS"
        fi
        chmod 600 "$AUTH_KEYS"
        echo "   ✅ Key added to ${AUTH_KEYS}"
    fi
    
    echo ""
}

# Add key to root
if [ "$EUID" -eq 0 ]; then
    add_key_to_user "root" "/root"
else
    echo "📝 Adding key to root user (requires sudo)..."
    sudo bash -c "
        mkdir -p /root/.ssh
        chmod 700 /root/.ssh
        if ! grep -q '$PUBLIC_KEY' /root/.ssh/authorized_keys 2>/dev/null; then
            echo '$PUBLIC_KEY' >> /root/.ssh/authorized_keys
            chmod 600 /root/.ssh/authorized_keys
            echo '   ✅ Key added to /root/.ssh/authorized_keys'
        else
            echo '   ⚠️  Key already exists in /root/.ssh/authorized_keys'
        fi
    "
    echo ""
fi

# Add key to langchain user
if id "langchain" &>/dev/null; then
    add_key_to_user "langchain" "/home/langchain"
else
    echo "⚠️  langchain user does not exist, skipping..."
    echo ""
fi

# Add key to linode-langchain-user if it exists
if id "linode-langchain-user" &>/dev/null; then
    add_key_to_user "linode-langchain-user" "/home/linode-langchain-user"
else
    echo "⚠️  linode-langchain-user does not exist, skipping..."
    echo ""
fi

echo "✅ SSH key setup complete!"
echo ""
echo "🧪 Test connections:"
echo "   ssh -i ~/.ssh/id_ed25519_langchain root@172.234.181.156"
echo "   ssh -i ~/.ssh/id_ed25519_langchain langchain@172.234.181.156"

