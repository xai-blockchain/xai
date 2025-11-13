# Quick Start Guide

Get your CI/CD pipeline running in 5 minutes!

## Step 1: Install Pre-commit Hooks (1 minute)

```bash
pip install pre-commit
pre-commit install
```

## Step 2: Test Locally (2 minutes)

```bash
# Test hooks
pre-commit run --all-files

# Run tests
pytest tests/aixn_tests/unit/ -v
```

## Step 3: Push to GitHub (1 minute)

```bash
git add .github/ .pylintrc mypy.ini .pre-commit-config.yaml .yamllint.yml
git commit -m "ci: Add comprehensive CI/CD pipelines"
git push origin main
```

## Step 4: Configure GitHub (1 minute)

1. Go to **Settings → Actions → General**
2. Set **Workflow permissions** to "Read and write permissions"
3. Enable "Allow GitHub Actions to create and approve pull requests"

## Step 5: Monitor Workflows

Visit: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`

## What's Running?

- ✅ **quality.yml** - Code formatting, linting, type checking
- ✅ **security.yml** - Security scans (Bandit, Safety, Semgrep, CodeQL)
- ✅ **tests.yml** - Unit, integration, performance, security tests
- ✅ **deploy.yml** - Build, Docker image, deployment

## Add Status Badges

Copy to your README.md:

```markdown
[![Code Quality](https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/quality.yml)
[![Security](https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/security.yml)
[![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/tests.yml)
[![Deploy](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml)
```

Replace `USERNAME/REPO` with your values!

## Next Steps

- 📖 Read [CICD_SETUP_GUIDE.md](CICD_SETUP_GUIDE.md) for detailed setup
- ✅ Follow [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) for complete configuration
- 🎯 Review [CI_CD_IMPLEMENTATION_SUMMARY.md](CI_CD_IMPLEMENTATION_SUMMARY.md) for overview

## Need Help?

Check the troubleshooting section in [CICD_SETUP_GUIDE.md](CICD_SETUP_GUIDE.md)

---

**That's it! Your CI/CD pipeline is now running! 🎉**
