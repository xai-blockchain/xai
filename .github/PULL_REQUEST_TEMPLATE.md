## ⚠️ MANDATORY: Local Testing Confirmation

**CRITICAL**: All testing MUST be done locally before pushing to GitHub to save CI minutes.

- [ ] **I ran `make ci` or `.\local-ci.ps1` locally** - ALL tests passed
- [ ] **I ran `make quick` at minimum** - All checks passed
- [ ] **I reviewed local test output** - No errors or warnings

**If you did NOT run local tests:**
```bash
# Windows
.\local-ci.ps1

# Linux/Mac
./local-ci.sh

# Using Make
make ci
```

**Paste local test results below:**
```bash
# Paste output from your local CI run here

```

---

## Description
Please include a summary of the changes and related context. Explain the "why" behind these changes.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Security patch
- [ ] Dependency update

## Related Issues
Closes #(issue number)

## Testing Checklist
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass locally
- [ ] Tested on testnet (if applicable)

## Code Quality Checklist
- [ ] Code follows project style guidelines
- [ ] Code is self-documenting with clear variable/function names
- [ ] Comments added for complex logic
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] No debug code or print statements left
- [ ] Test coverage maintained or improved
- [ ] No new warnings introduced

## Security Checklist (if applicable)
- [ ] No sensitive data (keys, secrets) committed
- [ ] Input validation implemented
- [ ] Dependencies checked for vulnerabilities
- [ ] Security implications considered

## Screenshots/Demo (if applicable)
Add screenshots, gifs, or descriptions of changes visible to users.

## Breaking Changes
Describe any breaking changes and migration path for users.

## Additional Notes
Any additional information reviewers should know.

---

## 💰 Cost Savings Reminder

By running tests locally before pushing, you help save GitHub Actions minutes (which cost money!).

**Thank you for testing locally first!** 🎉

See [DEVELOPMENT-WORKFLOW.md](../DEVELOPMENT-WORKFLOW.md) for complete local testing guide.
