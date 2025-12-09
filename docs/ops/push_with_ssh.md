# Pushing to GitHub via SSH

Use the configured SSH key (`~/.ssh/id_ed25519_github`) and remote `git@github.com:decristofaroj/xai.git`.

## One-Time Setup
- Ensure your public key is added to your GitHub account.
- Verify remote:
  ```bash
  git remote -v
  # should show git@github.com:decristofaroj/xai.git
  ```

## Push Steps
1. Stage changes:
   ```bash
   git add .
   ```
2. Commit:
   ```bash
   git commit -m "your message"
   ```
3. Push over SSH:
   ```bash
   git push
   ```

If you see SSH auth errors, run:
```bash
ssh -T git@github.com
```
to debug key/agent issues. Do not commit private keys or secrets.***
