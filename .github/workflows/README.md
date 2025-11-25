# GitHub Actions CI/CD Workflows

This directory contains comprehensive CI/CD pipelines for the XAI Blockchain project.

## Workflow Files

### 1. `quality.yml` - Code Quality Checks

**Triggers:** Push and Pull Requests to `main` and `develop` branches

**Jobs:**
- **code-quality**: Runs Black formatter, Pylint linter, MyPy type checker, and code complexity analysis
- **documentation-quality**: Validates Markdown files and checks for broken links
- **commit-quality**: Validates commit message format (PR only)

**Status Badge:**
```markdown
![Code Quality](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/quality.yml/badge.svg)
```

### 2. `security.yml` - Security Scanning

**Triggers:**
- Push and Pull Requests to `main` and `develop` branches
- Daily scheduled scan at 2 AM UTC
- Manual workflow dispatch

**Jobs:**
- **python-security**: Runs Bandit, Safety, and Semgrep scans
- **dependency-review**: Reviews dependencies for vulnerabilities (PR only)
- **secret-scanning**: Scans for exposed secrets using TruffleHog
- **codeql-analysis**: Advanced code analysis using GitHub CodeQL
- **security-summary**: Generates comprehensive security report

**Status Badge:**
```markdown
![Security Scan](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/security.yml/badge.svg)
```

### 3. `tests.yml` - Automated Testing

**Triggers:** Push and Pull Requests to `main` and `develop` branches

**Jobs:**
- **unit-tests**: Runs on multiple Python versions (3.10, 3.11, 3.12) and OS (Ubuntu, Windows)
- **integration-tests**: Tests inter-component communication
- **performance-tests**: Benchmarks with pytest-benchmark
- **security-tests**: Validates security controls
- **test-summary**: Generates comprehensive test report

**Features:**
- Code coverage reporting to Codecov
- Parallel test execution with pytest-xdist
- Matrix testing across Python versions and operating systems
- HTML coverage reports as artifacts

**Status Badge:**
```markdown
![Tests](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/tests.yml/badge.svg)
```

### 4. `deploy.yml` - Build and Deployment

**Triggers:**
- Push to `main` and `develop` branches
- Version tags (v*.*.*)
- Manual workflow dispatch with environment selection

**Jobs:**
- **build**: Builds Python package and creates distribution archive
- **docker-build**: Builds and pushes Docker images to GitHub Container Registry
- **deploy-staging**: Deploys to staging environment (develop branch)
- **deploy-production**: Deploys to production (version tags)
- **create-release**: Creates GitHub releases with artifacts
- **notify**: Sends deployment notifications
- **cleanup**: Removes old artifacts (7+ days)

**Features:**
- Multi-architecture Docker builds (amd64, arm64)
- Automated changelog generation
- Build artifact retention
- Environment-specific deployments
- Release notes automation

**Status Badge:**
```markdown
![Build & Deploy](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/deploy.yml/badge.svg)
```

## Configuration Files

### `.pylintrc`
Configures Pylint code analysis with project-specific rules:
- Maximum line length: 100 characters
- Disabled checks for common blockchain patterns
- Multi-process execution for speed

### `mypy.ini`
Configures MyPy type checking:
- Python 3.11 target
- Relaxed settings for blockchain development
- Per-module override options
- Ignores test files

### `pytest.ini`
Already configured in project root with:
- Markers for slow tests
- Directory exclusions

## Required Secrets

Configure these in GitHub Settings → Secrets and Variables → Actions:

### Optional Secrets
- `CODECOV_TOKEN`: For Codecov integration (optional, works without for public repos)
- `SLACK_WEBHOOK`: For Slack notifications
- `DISCORD_WEBHOOK`: For Discord notifications

### GitHub Permissions

The workflows require these permissions (configured in each workflow):
- `contents: read/write` - For reading code and creating releases
- `packages: write` - For pushing Docker images to GHCR
- `security-events: write` - For CodeQL and security scanning

## Status Badges

Add these to your main README.md:

```markdown
# XAI Blockchain

![Code Quality](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/quality.yml/badge.svg)
![Security Scan](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/security.yml/badge.svg)
![Tests](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/tests.yml/badge.svg)
![Build & Deploy](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/deploy.yml/badge.svg)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/YOUR_REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/YOUR_REPO)
```

## Usage Examples

### Running Workflows Manually

1. Go to Actions tab in GitHub
2. Select the workflow you want to run
3. Click "Run workflow" button
4. Select branch and parameters (if applicable)
5. Click "Run workflow" to start

### Testing Locally

Before pushing, you can test locally using:

```bash
# Code quality
black --check src/ tests/ scripts/
pylint src/xai/core/
mypy src/xai/core/

# Security
bandit -r src/
safety check
semgrep --config=auto src/

# Tests
pytest tests/xai_tests/unit/ -v --cov=src/xai/core
pytest tests/xai_tests/integration/ -v
pytest tests/xai_tests/performance/ --benchmark-only
pytest tests/xai_tests/security/ -v
```

### Pre-commit Hooks

Install pre-commit hooks to run checks automatically:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/pylint
    rev: v3.0.3
    hooks:
      - id: pylint
        args: ['--rcfile=.pylintrc']

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ['-r', 'src/']
```

## Troubleshooting

### Common Issues

1. **Pylint/MyPy failures**: Update configuration files to ignore specific warnings
2. **Security scan false positives**: Add exclusions in Bandit/Semgrep configs
3. **Test timeouts**: Increase timeout values or mark tests as slow
4. **Docker build failures**: Check Dockerfile and build context
5. **Permission errors**: Verify GitHub Actions permissions in workflow files

### Debugging Workflows

Enable debug logging:
1. Go to repository Settings → Secrets → Actions
2. Add secret: `ACTIONS_RUNNER_DEBUG` = `true`
3. Add secret: `ACTIONS_STEP_DEBUG` = `true`

### Performance Optimization

- Use caching for pip dependencies (already configured)
- Run tests in parallel with pytest-xdist (already configured)
- Use matrix strategy for multi-version testing (already configured)
- Skip slow tests in CI: `pytest -m "not slow"`

## Maintenance

### Updating Dependencies

Update GitHub Actions regularly:

```bash
# Check for updates
gh extension install mheap/gh-actions-auto-update
gh actions-auto-update

# Or manually update in workflow files
# uses: actions/checkout@v4 → @v5
```

### Monitoring

Monitor workflow runs:
- GitHub Actions dashboard
- Email notifications for failures
- Status badges in README
- Codecov dashboard for coverage trends

## Contributing

When adding new workflows:
1. Follow the existing structure
2. Add proper documentation
3. Test locally first
4. Use meaningful job and step names
5. Add appropriate status badges
6. Update this README

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Security Hardening Guide](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Best Practices](https://docs.github.com/en/actions/learn-github-actions/best-practices-for-workflows)
