# Redeploy Streamlit App

Reference docs: `docs/INFRASTRUCTURE_QUICK_REFERENCE.md`, `docs/SERVER_SETUP.md`,
`docs/STREAMLIT_WORKFLOW.md`.

## 1. Commit and push local changes

```bash
cd /Users/jabrown/Documents/GitHub/Linode/langchain-demo
git status
# Optional: run tests before deploying
pytest tests -v
git add -A
git commit -m "<describe your change>"
git push origin <branch>
```

## 2. SSH to the remote server and pull latest code

```bash
ssh linode-langchain-user@172.234.181.156

cd /home/linode-langchain-user/langchain-demo
git fetch origin
git checkout <branch>
git pull origin <branch>
```

Replace `<branch>` with the branch you just pushed. Exit the SSH session once the pull completes.

## 3. Restart Streamlit on the remote host (same port)

```bash
ssh "linode-langchain-user@172.234.181.156" <<EOF
set -e

cd "/home/linode-langchain-user/langchain-demo"

STREAMLIT_PORT="8501"

if lsof -ti:${STREAMLIT_PORT} >/dev/null 2>&1; then
  echo "Stopping existing process on port ${STREAMLIT_PORT}"
  lsof -ti:${STREAMLIT_PORT} | xargs kill -9 2>/dev/null || true
else
  echo "No existing process found on port ${STREAMLIT_PORT}"
fi

source venv/bin/activate

nohup streamlit run src/ui/streamlit_dashboard.py \
  --server.address 0.0.0.0 \
  --server.port ${STREAMLIT_PORT} \
  --server.headless true \
  > /tmp/streamlit.log 2>&1 &

sleep 3

if lsof -ti:${STREAMLIT_PORT} >/dev/null 2>&1; then
  echo "Streamlit is running on port ${STREAMLIT_PORT}"
  echo "Dashboard: http://172.234.181.156:${STREAMLIT_PORT}"
else
  echo "Streamlit failed to start. Showing recent logs:"
  tail -20 /tmp/streamlit.log
fi
EOF
```

## 4. Monitor logs (optional)

```bash
ssh "linode-langchain-user@172.234.181.156" "tail -f /tmp/streamlit.log"
```

