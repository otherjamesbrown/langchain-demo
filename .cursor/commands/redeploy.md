# Redeploy Streamlit App

Reference docs: `docs/INFRASTRUCTURE_QUICK_REFERENCE.md`, `docs/SSH_ACCESS_GUIDE.md`, `docs/GITHUB_AUTH.md`, `docs/STREAMLIT_WORKFLOW.md`.

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
- If SSH still fails, use the Linode Weblish/LISH console (see `docs/SSH_ACCESS_GUIDE.md`).

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
ssh linode-langchain-user "cd ~/langchain-demo && bash scripts/start_streamlit.sh"
```

`scripts/start_streamlit.sh` handles stopping any existing process on port `8501`, reactivating the virtualenv, and starting the dashboard. This mirrors the manual steps documented in `docs/SSH_ACCESS_GUIDE.md` and `docs/INFRASTRUCTURE_QUICK_REFERENCE.md`.

## 4. Monitor logs (optional)

```bash
ssh linode-langchain-user "tail -f /tmp/streamlit.log"
```

If Streamlit fails to start, rerun `ssh linode-langchain-user` and inspect `/tmp/streamlit.log` directly. Use the Linode console if key-based SSH is not yet configured.

