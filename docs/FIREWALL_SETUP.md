# Linode Cloud Firewall Setup for Streamlit

## Understanding Firewall Rules

- **Outbound Rules:** Allow your server to make connections TO external services
- **Inbound Rules:** Allow external connections TO reach your server

For Streamlit dashboard access, you need an **INBOUND** rule.

## Step-by-Step: Adding Inbound Rule

1. **Go to Linode Cloud Manager**
   - https://cloud.linode.com
   - Navigate to **Firewalls** (in left sidebar)

2. **Select Your Firewall**
   - Find the firewall attached to your Linode instance
   - Or create a new firewall and attach it to your instance

3. **Add Inbound Rule**
   - Click **"Add an Inbound Rule"** or edit existing rules
   - Configure:
     ```
     Label: Allow Streamlit Dashboard (optional)
     Type: Custom
     Protocol: TCP
     Ports: 8501
     Sources: 
       - Option 1 (Public): 0.0.0.0/0 (allows anyone)
       - Option 2 (Secure): YOUR_IP_ADDRESS/32 (only your IP)
     Action: Accept
     ```
   - Click **Save**

4. **Apply Firewall**
   - Ensure the firewall is attached to your Linode instance
   - Go to your Linode → **Firewalls** tab
   - Verify firewall is listed and active

5. **Test Connection**
   ```bash
   curl -I http://172.234.181.156:8501
   ```
   Should return HTTP 200 or 302 (redirect)

## Visual Guide

```
Linode Cloud Manager
  → Firewalls (left sidebar)
    → [Your Firewall Name]
      → Rules tab
        → INBOUND RULES section
          → Add an Inbound Rule
            → Fill in:
              Protocol: TCP
              Ports: 8501
              Sources: 0.0.0.0/0 (or your IP)
              Action: Accept
```

## Security Recommendations

### Option 1: Allow All IPs (Quick Setup)
- **Sources:** `0.0.0.0/0`
- **Pros:** Easy, works immediately
- **Cons:** Less secure, anyone can access

### Option 2: Allow Only Your IP (Recommended)
- **Sources:** `YOUR_PUBLIC_IP/32`
- Find your IP: `curl ifconfig.me` or visit https://whatismyip.com
- **Pros:** More secure
- **Cons:** If your IP changes, you'll need to update

### Option 3: Use SSH Tunnel (Most Secure)
```bash
ssh -L 8501:localhost:8501 linode-langchain-user
# Then access: http://localhost:8501
```
- **Pros:** Most secure, encrypted
- **Cons:** Requires SSH connection

## Troubleshooting

### Rule Added But Still Not Working?

1. **Verify it's INBOUND, not OUTBOUND**
   - Check the rule direction in Linode dashboard

2. **Check Firewall is Applied**
   - Linode instance → Firewalls tab
   - Should show firewall name

3. **Wait a Few Seconds**
   - Firewall rules may take 10-30 seconds to propagate

4. **Check Server Firewall**
   ```bash
   ssh linode-langchain-user
   sudo ufw status
   # If active, may need: sudo ufw allow 8501/tcp
   ```

5. **Verify Streamlit is Running**
   ```bash
   ssh linode-langchain-user
   ps aux | grep streamlit
   ss -tlnp | grep 8501
   ```

### Testing Connection

```bash
# Test from external machine
curl -I http://172.234.181.156:8501

# Should return HTTP headers, not timeout
# Expected: HTTP/1.1 200 OK or HTTP/1.1 302 Found
```

## Current Status

After adding the inbound rule, you should see:
- ✅ HTTP connection succeeds (not timeout)
- ✅ Browser can access http://172.234.181.156:8501
- ✅ Dashboard loads and displays LLM call logs

If still not working after 30 seconds, double-check:
- Rule is INBOUND (not outbound)
- Port is 8501 (not 8500 or other)
- Protocol is TCP
- Firewall is applied to your Linode

