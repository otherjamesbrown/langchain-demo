# Redeploy Streamlit App

Reference docs: `docs/infrastructure/INFRASTRUCTURE_QUICK_REFERENCE.md`, `docs/infrastructure/SSH_ACCESS_GUIDE.md`, `docs/infrastructure/GITHUB_AUTH.md`, `docs/implemented/STREAMLIT_WORKFLOW.md`.

## 0. Prerequisites (run locally)

- Confirm GitHub auth is configured (token stored via credential helper):
  ```bash
  git config --global credential.helper  # should output "store"
  git config --global user.name
  git config --global user.email
  ```
- Verify the Linode SSH key is present (`~/.ssh/id_ed25519_langchain`) and loaded:
  ```bash
  ls -l ~/.ssh/id_ed25519_langchain
  ssh-add -l || ssh-add ~/.ssh/id_ed25519_langchain
  ```
- If SSH still fails, use the Linode Weblish/LISH console (see `docs/infrastructure/SSH_ACCESS_GUIDE.md`).

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

Replace `<branch>` with the branch you are deploying (e.g., `main`).

## 2. SSH to the remote server and pull latest code

```bash
# Either use the SSH config alias (recommended)
ssh linode-langchain-user

# Or specify the key and user explicitly
ssh -i ~/.ssh/id_ed25519_langchain langchain@172.234.181.156

# Once connected
cd ~/langchain-demo
git fetch origin
git checkout <branch>
git pull --ff-only origin <branch>
exit
```

If SSH is unavailable, launch the Linode console and run the same git commands there.

## 3. Restart Streamlit on the remote host

```bash
ssh -n linode-langchain-user "cd ~/langchain-demo && (nohup bash scripts/start_streamlit.sh > /tmp/streamlit.log 2>&1 &); exit"
```

The `-n` flag prevents SSH from reading from stdin (which prevents hanging). The command runs the Streamlit restart in a subshell with `nohup ... &` and immediately exits the SSH session. The script stops any existing process on port `8501`, reactivates the virtualenv, and launches the dashboard—mirroring the manual steps in `docs/infrastructure/SSH_ACCESS_GUIDE.md` and `docs/infrastructure/INFRASTRUCTURE_QUICK_REFERENCE.md`.

**Alternative if using explicit key:**
```bash
ssh -n -i ~/.ssh/id_ed25519_langchain langchain@172.234.181.156 "cd ~/langchain-demo && (nohup bash scripts/start_streamlit.sh > /tmp/streamlit.log 2>&1 &); exit"
```

## 4. Verify deployment

Run these checks to ensure the system is functioning after deployment:

### 4a. Check Streamlit process status

```bash
# Verify Streamlit is running on port 8501
ssh linode-langchain-user "lsof -ti:8501"
# Should output a process ID if running
```

### 4b. Check logs for errors

```bash
# View recent logs
ssh linode-langchain-user "tail -50 /tmp/streamlit.log"

# Check for specific errors
ssh linode-langchain-user "grep -i 'error\|exception\|failed' /tmp/streamlit.log | tail -20"

# Check for successful startup
ssh linode-langchain-user "grep -i 'running\|started\|you can now view' /tmp/streamlit.log | tail -5"
```

**Success indicators:**
- `You can now view your Streamlit app in your browser.`
- `Network URL: http://0.0.0.0:8501`
- No `ERROR` or `CRITICAL` messages

### 4c. Test local LLM functionality

```bash
# Quick test to verify local LLM can be invoked
ssh linode-langchain-user "cd ~/langchain-demo && source venv/bin/activate && python scripts/test_llm_simple.py"
```

**Expected**: Model loads and generates a response without errors.

### 4d. Verify dashboard access

Open in browser: http://172.234.181.156:8501

Or test via curl:
```bash
curl -I http://172.234.181.156:8501
# Should return HTTP 200
```

### 4e. Test database connection (optional)

```bash
ssh linode-langchain-user "cd ~/langchain-demo && source venv/bin/activate && python -c 'from src.database.schema import get_session, LLMCallLog; session = get_session(); count = session.query(LLMCallLog).count(); print(f\"✅ Database connected. Total logs: {count}\")'"
```

### 4f. Test structured output strategy (optional, if code changed)

```bash
ssh linode-langchain-user "cd ~/langchain-demo && source venv/bin/activate && python -c 'from src.models.model_factory import get_chat_model; from src.models.structured_output import select_structured_output_strategy; from src.tools.models import CompanyInfo; model = get_chat_model(model_type=\"local\"); strategy = select_structured_output_strategy(model=model, model_type=\"local\", schema=CompanyInfo); print(f\"✅ Strategy selection working: {strategy}\")'"
```

**Note**: For detailed verification guide, see `docs/reference/DEPLOYMENT_VERIFICATION.md`.

## 5. Monitor logs (optional)

```bash
ssh linode-langchain-user "tail -f /tmp/streamlit.log"
```

If Streamlit fails to start, rerun `ssh linode-langchain-user` and inspect `/tmp/streamlit.log` directly. Use the Linode console if key-based SSH is not yet configured.

