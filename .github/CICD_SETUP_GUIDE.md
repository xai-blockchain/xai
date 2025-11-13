# CI/CD Setup Guide for AIXN Blockchain

This guide will help you set up and configure the complete CI/CD pipeline for the AIXN Blockchain project.

## Quick Start

### 1. Prerequisites

- GitHub repository with admin access
- GitHub Actions enabled (free for public repos)
- Docker Hub or GitHub Container Registry account (optional)

### 2. Initial Setup (5 minutes)

```bash
# 1. Install pre-commit hooks locally
pip install pre-commit
pre-commit install

# 2. Install development dependencies
pip install -r src/aixn/requirements.txt
pip install -r tests/aixn_tests/requirements_test.txt
pip install black pylint mypy bandit safety semgrep

# 3. Test pre-commit hooks
pre-commit run --all-files

# 4. Verify workflows are valid
# Push to GitHub and check Actions tab
git add .github/workflows/
git commit -m "Add CI/CD workflows"
git push
```

### 3. Configure GitHub Repository

#### Enable GitHub Actions

1. Go to repository Settings → Actions → General
2. Set "Workflow permissions" to "Read and write permissions"
3. Enable "Allow GitHub Actions to create and approve pull requests"

#### Configure Environments

1. Go to Settings → Environments
2. Create two environments:
   - **staging**
     - No protection rules needed
     - Add environment variables if needed
   - **production**
     - Enable "Required reviewers" (recommended)
     - Add protection rules:
       - Wait timer: 5 minutes
       - Restrict to specific branches: `main`

#### Set Up Secrets (Optional)

Go to Settings → Secrets and variables → Actions → New repository secret

**Optional Secrets:**
- `CODECOV_TOKEN`: For private repo coverage (get from codecov.io)
- `SLACK_WEBHOOK`: For Slack notifications
- `DISCORD_WEBHOOK`: For Discord notifications
- `DOCKER_USERNAME`: For Docker Hub (if not using GHCR)
- `DOCKER_PASSWORD`: For Docker Hub (if not using GHCR)

### 4. First Workflow Run

```bash
# Create a test commit to trigger workflows
echo "# Test" >> test.txt
git add test.txt
git commit -m "test: Trigger CI/CD workflows"
git push

# Check workflow status
gh run list  # if gh CLI is installed
# Or visit: https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

## Workflow Details

### Quality Workflow (`quality.yml`)

**Runs on every push and PR**

**What it does:**
- Formats code with Black
- Checks code quality with Pylint
- Performs type checking with MyPy
- Analyzes code complexity with Radon
- Validates Markdown files
- Checks commit messages (PR only)

**Expected first-run issues:**
- Formatting violations (run `black src/ tests/ scripts/` to fix)
- Pylint warnings (configure `.pylintrc` to suppress false positives)
- MyPy errors (configure `mypy.ini` to ignore missing stubs)

**How to fix:**
```bash
# Auto-fix formatting
black src/ tests/ scripts/

# Check what Pylint complains about
pylint src/aixn/core/ --rcfile=.pylintrc

# Adjust .pylintrc to disable specific warnings:
# disable=C0103,C0111,W0212

# Check MyPy errors
mypy src/aixn/core/ --ignore-missing-imports
```

### Security Workflow (`security.yml`)

**Runs on:**
- Every push and PR
- Daily at 2 AM UTC
- Manual trigger

**What it does:**
- Scans code with Bandit for security issues
- Checks dependencies with Safety
- Performs SAST with Semgrep
- Scans for secrets with TruffleHog
- Runs CodeQL analysis

**Expected first-run issues:**
- Bandit warnings (B101, B110, B603, etc.)
- Safety vulnerabilities in dependencies
- False positive secret detections

**How to fix:**
```bash
# Check Bandit issues
bandit -r src/

# Create .bandit config to skip false positives
cat > .bandit <<EOF
[bandit]
exclude_dirs = /tests/,/temp_/
skips = B101,B601
EOF

# Update vulnerable dependencies
pip list --outdated
pip install --upgrade <package_name>

# Verify no real secrets
git log -p | grep -E "(password|secret|key|token)" -i
```

### Tests Workflow (`tests.yml`)

**Runs on every push and PR**

**What it does:**
- Runs unit tests on Python 3.10, 3.11, 3.12
- Tests on Ubuntu and Windows
- Runs integration tests
- Executes performance benchmarks
- Performs security testing
- Uploads coverage to Codecov

**Expected first-run issues:**
- Test failures due to missing dependencies
- Import errors from path issues
- Timeout errors on slow tests

**How to fix:**
```bash
# Run tests locally first
pytest tests/aixn_tests/unit/ -v

# Check for import errors
python -c "import sys; sys.path.insert(0, 'src'); from aixn.core.blockchain import Blockchain"

# Mark slow tests
# Add to test function:
# @pytest.mark.slow

# Run without slow tests
pytest -m "not slow"

# Increase timeout for specific tests
# @pytest.mark.timeout(60)
```

### Deploy Workflow (`deploy.yml`)

**Runs on:**
- Push to main/develop
- Version tags (v*.*.*)
- Manual trigger

**What it does:**
- Builds Python package
- Creates Docker images (multi-arch)
- Deploys to staging (develop branch)
- Deploys to production (version tags)
- Creates GitHub releases
- Cleans up old artifacts

**Expected first-run issues:**
- Docker build failures
- Missing deployment scripts
- Environment configuration errors

**How to fix:**
```bash
# Test Docker build locally
docker build -t aixn-blockchain .

# If build fails, check Dockerfile
docker build -t aixn-blockchain . --progress=plain

# Test deployment scripts
bash scripts/deploy/deploy.sh staging

# Create deployment placeholders
mkdir -p scripts/deploy
cat > scripts/deploy/deploy.sh <<EOF
#!/bin/bash
echo "Deploying to \$1 environment..."
# Add your deployment logic here
EOF
chmod +x scripts/deploy/deploy.sh
```

## Codecov Integration

### Setup (Free for public repos)

1. Go to [codecov.io](https://codecov.io)
2. Sign in with GitHub
3. Add your repository
4. Copy the upload token (for private repos)
5. Add token to GitHub Secrets as `CODECOV_TOKEN`

### Badge

Add to README.md:
```markdown
[![codecov](https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/USERNAME/REPO)
```

### View Coverage

- Go to `https://codecov.io/gh/USERNAME/REPO`
- View coverage trends over time
- See file-by-file coverage
- Review uncovered lines

## Status Badges

Add these to the top of your README.md:

```markdown
# AIXN Blockchain

[![Code Quality](https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/quality.yml)
[![Security Scan](https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/security.yml)
[![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/tests.yml)
[![Build & Deploy](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml)
[![codecov](https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/REPO)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```

Replace `USERNAME/REPO` with your actual GitHub username and repository name.

## Customization

### Adjust Workflow Triggers

Edit `.github/workflows/*.yml`:

```yaml
# Run only on specific branches
on:
  push:
    branches: [ main, develop, feature/* ]

# Run on schedule
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

# Run manually
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'
```

### Modify Test Matrix

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python-version: ['3.10', '3.11', '3.12']
    # Exclude specific combinations
    exclude:
      - os: macos-latest
        python-version: '3.10'
```

### Add Notifications

Add to end of workflow:

```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"Build failed: ${{ github.repository }}"}' \
      ${{ secrets.SLACK_WEBHOOK }}
```

## Troubleshooting

### Workflow Not Running

**Problem:** Pushed code but workflow doesn't start

**Solutions:**
1. Check Actions tab for disabled workflows
2. Verify branch name matches trigger condition
3. Check if Actions are enabled in Settings
4. Look for workflow syntax errors

### Permission Denied Errors

**Problem:** `Error: Resource not accessible by integration`

**Solutions:**
1. Go to Settings → Actions → General
2. Set workflow permissions to "Read and write permissions"
3. Enable "Allow GitHub Actions to create and approve pull requests"

### Docker Build Fails

**Problem:** Docker build timeout or failure

**Solutions:**
```yaml
# Increase timeout
- name: Build Docker
  timeout-minutes: 30

# Enable BuildKit
env:
  DOCKER_BUILDKIT: 1

# Use cache
- name: Build
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Tests Fail in CI but Pass Locally

**Problem:** Tests pass on local machine but fail in GitHub Actions

**Solutions:**
1. Check Python version matches
2. Verify all dependencies are in requirements.txt
3. Check for hardcoded paths
4. Look for timezone/locale issues
5. Enable debug logging:
   ```yaml
   - name: Run tests
     run: pytest -vv --log-cli-level=DEBUG
   ```

### Coverage Not Uploading

**Problem:** Codecov upload fails

**Solutions:**
1. Verify `CODECOV_TOKEN` is set (for private repos)
2. Check coverage.xml is generated
3. Use Codecov action v4:
   ```yaml
   - uses: codecov/codecov-action@v4
     with:
       token: ${{ secrets.CODECOV_TOKEN }}
       fail_ci_if_error: false
   ```

## Maintenance

### Weekly Tasks

- Review workflow runs for patterns
- Update failing workflows
- Check dependency updates
- Review security scan results

### Monthly Tasks

- Update GitHub Actions versions
- Update Python dependencies
- Review and adjust test coverage goals
- Optimize workflow performance

### Update Dependencies

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Update GitHub Actions
# Edit .github/workflows/*.yml and bump versions:
# actions/checkout@v4 → @v5

# Update Python packages
pip list --outdated
pip install --upgrade <package>
```

## Best Practices

### Commit Messages

Follow conventional commits:
```
feat: Add new feature
fix: Bug fix
docs: Documentation changes
style: Code style changes
refactor: Code refactoring
test: Test changes
chore: Build/tooling changes
```

### Pull Requests

- All checks must pass before merge
- Require at least one approval
- Keep PRs small and focused
- Link to relevant issues

### Security

- Never commit secrets
- Use GitHub Secrets for sensitive data
- Regularly update dependencies
- Review security scan results
- Enable Dependabot alerts

## Support

### Getting Help

- Check [GitHub Actions Documentation](https://docs.github.com/en/actions)
- Review workflow logs in Actions tab
- Search [GitHub Community Forum](https://github.community/)
- Open issue in this repository

### Debugging

Enable debug mode:
```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

View detailed logs:
1. Go to failed workflow run
2. Click on failed job
3. Click on failed step
4. Review error messages and logs

## Next Steps

1. **Test all workflows** - Push changes and verify all workflows pass
2. **Set up Codecov** - Get coverage reporting working
3. **Configure notifications** - Add Slack/Discord webhooks
4. **Create first release** - Tag version and test deployment
5. **Document deployment** - Add deployment documentation
6. **Monitor regularly** - Set up dashboard to track workflow health

## Checklist

- [ ] Pre-commit hooks installed and working
- [ ] All four workflows created and valid
- [ ] GitHub Actions enabled with correct permissions
- [ ] Staging and production environments configured
- [ ] Codecov integration set up (optional)
- [ ] Status badges added to README
- [ ] First successful workflow run completed
- [ ] Docker build tested and working
- [ ] Security scans reviewed and false positives addressed
- [ ] Test coverage above 80%
- [ ] Documentation updated

Congratulations! Your CI/CD pipeline is now fully configured.
