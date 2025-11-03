# GitHub Authentication Setup

## Personal Access Token

✅ **GitHub Personal Access Token is configured and stored securely.**

### Storage Location

The token is stored in the git credential helper:
- **File:** `~/.git-credentials`
- **Method:** Git credential store
- **Permissions:** 600 (read/write for owner only)
- **Format:** `https://username:token@github.com`

### Configuration

Git is configured to use the credential store:
```bash
git config --global credential.helper store
```

This means git will automatically use the stored token for all GitHub operations (push, pull, fetch).

### Security

- ✅ Token is **never committed to git**
- ✅ File has restricted permissions (600)
- ✅ Stored in user home directory (not in project)
- ✅ `.git-credentials` is excluded from git

### Token Scope

The token has `repo` scope, allowing:
- ✅ Push to repository
- ✅ Pull from repository
- ✅ Clone repository
- ✅ Create/delete branches

### Updating the Token

If you need to update the token:

1. Generate a new token at: https://github.com/settings/tokens/new
2. Update the stored credential:
   ```bash
   # Edit the file directly
   nano ~/.git-credentials
   # Or remove old and add new
   grep -v github.com ~/.git-credentials > ~/.git-credentials.tmp
   mv ~/.git-credentials.tmp ~/.git-credentials
   echo "https://otherjamesbrown:NEW_TOKEN@github.com" >> ~/.git-credentials
   chmod 600 ~/.git-credentials
   ```

### Testing Authentication

Test that the token works:
```bash
git push origin main
```

If it works without prompting, the token is configured correctly.

### Related Documentation

- **Infrastructure Reference:** `docs/INFRASTRUCTURE_QUICK_REFERENCE.md`
- **SSH Access:** `docs/SSH_ACCESS_GUIDE.md`

