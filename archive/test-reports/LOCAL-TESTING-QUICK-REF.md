# Local Testing - Quick Reference Card

## 🚨 MANDATORY POLICY


---

## ⚡ Quick Commands

### Before EVERY Push (Choose One)

```bash
# OPTION 1: Full CI (RECOMMENDED) - 5-10 minutes
make ci

# OPTION 2: Quick validation (MINIMUM) - 1-2 minutes
make quick

# OPTION 3: Windows PowerShell
.\local-ci.ps1          # Full
.\local-ci.ps1 -Quick   # Quick
```

### Daily Development

```bash
# Format code (before committing)
make format

# Run tests frequently (every 15-30 min)
make quick

# Security scans (before pushing)
make security
```

---

## 📋 Command Reference

| Command | What It Does | When to Use | Time |
|---------|-------------|-------------|------|
| `make quick` | Format + Lint + Unit Tests | Before every commit | 1-2 min |
| `make ci` | Complete CI pipeline | Before every push | 5-10 min |
| `make all` | Everything including integration | Major changes | 10-15 min |
| `make format` | Auto-fix formatting | Anytime | 10 sec |
| `make lint` | Check code quality | During development | 30 sec |
| `make security` | Security scans | Before pushing | 1-2 min |
| `make test` | All tests | After changes | 3-5 min |
| `make coverage` | Coverage report | Check coverage | 3-5 min |

---

## ✅ Pre-Push Checklist

1. [ ] `make format` - Auto-format code
2. [ ] `make ci` - Full CI pipeline passes
3. [ ] Review output - No errors

---

## 🎯 Workflow

```bash
# 1. Make changes
vim src/my_file.py

# 2. Format
make format

# 3. Test frequently
make quick

# 4. Commit

# 5. Before pushing (MANDATORY)
make ci

# 6. Push (only if tests pass!)
```

---

## 🔧 Installation (One-Time Setup)

```bash
# Install tools
make install-dev

# Setup pre-commit hooks (auto-checks)
make pre-commit-setup
```

---

## 💡 Tips

### Save Time
```bash
# Run tests in parallel
pytest -n auto

# Stop on first failure
pytest -x

# Run only failed tests
pytest --lf
```

### Fix Issues
```bash
# Auto-fix formatting
make format

# See detailed failures
pytest -v --tb=short

# Check coverage
make coverage
open htmlcov/index.html
```

### Security
```bash
# Quick security check
make security

# Fix vulnerabilities
pip install --upgrade vulnerable-package
```

---

## ❌ Common Mistakes

**DON'T**:
- ❌ Push without running `make ci`
- ❌ Skip tests for "small changes"
- ❌ Ignore security warnings
- ❌ Commit without formatting

**DO**:
- ✅ Run `make ci` before every push
- ✅ Format code before committing
- ✅ Fix security issues immediately
- ✅ Maintain test coverage

---

## 🆘 Troubleshooting

### "Tests are slow"
```bash
make quick  # Faster subset of tests
```

### "Formatting failed"
```bash
make format  # Auto-fix
```

### "Tests fail locally but not in CI"
```bash
make clean   # Clear cache
pip install -r requirements.txt  # Update deps
```

### "Out of memory"
```bash
pytest -n 2  # Reduce parallel workers
```

---

## 💰 Why This Matters

### Cost Savings
- Full CI run: ~15-20 min
- Multiple Python versions: 3x time
- Multiple OS: 2x time

### Time Savings
- Local: 5-10 minutes
- CI: 20-30 minutes + waiting
- **Save 15-20 minutes per push!**

### Quality
- Catch issues before CI
- Faster feedback loop
- Better code quality

---

## 📚 Full Documentation

- **[DEVELOPMENT-WORKFLOW.md](DEVELOPMENT-WORKFLOW.md)** - Complete workflow guide
- **[PROJECT-STANDARDS.md](PROJECT-STANDARDS.md)** - All project standards
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute
- **[RUN-TESTS-LOCALLY.md](RUN-TESTS-LOCALLY.md)** - Detailed testing guide

---

## 🎓 Remember

1. **ALWAYS** run `make ci` before pushing
2. **NEVER** skip local testing
4. **MAINTAIN** code quality

---

**Questions?** See full documentation or ask the team!

**Print this card** and keep it at your desk! 📌
