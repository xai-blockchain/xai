# CI/CD Setup Checklist

Use this checklist to ensure your CI/CD pipeline is properly configured and operational.

## Pre-Setup (Before Pushing to GitHub)

- [ ] Review all workflow files in `.github/workflows/`
- [ ] Update `USERNAME/REPO` placeholders in badge templates
- [ ] Install pre-commit hooks locally
  ```bash
  pip install pre-commit
  pre-commit install
  ```
- [ ] Test pre-commit hooks
  ```bash
  pre-commit run --all-files
  ```
- [ ] Run local tests to ensure they pass
  ```bash
  pytest tests/aixn_tests/unit/ -v
  ```
- [ ] Verify Docker builds successfully
  ```bash
  docker build -t aixn-blockchain .
  ```

## GitHub Repository Configuration

### Enable GitHub Actions

- [ ] Go to Settings → Actions → General
- [ ] Set "Actions permissions" to "Allow all actions and reusable workflows"
- [ ] Set "Workflow permissions" to "Read and write permissions"
- [ ] Enable "Allow GitHub Actions to create and approve pull requests"

### Create Environments

- [ ] Go to Settings → Environments → New environment

**Staging Environment:**
- [ ] Name: `staging`
- [ ] No protection rules needed
- [ ] Add environment variables (if needed)

**Production Environment:**
- [ ] Name: `production`
- [ ] Enable "Required reviewers"
  - [ ] Add at least one reviewer
- [ ] Enable "Wait timer": 5 minutes
- [ ] Deployment branches: Only protected branches
  - [ ] Add rule: `main`

### Configure Branch Protection (Recommended)

- [ ] Go to Settings → Branches → Add rule
- [ ] Branch name pattern: `main`
- [ ] Enable "Require a pull request before merging"
- [ ] Enable "Require status checks to pass before merging"
  - [ ] Add status checks:
    - [ ] `code-quality`
    - [ ] `python-security`
    - [ ] `unit-tests`
- [ ] Enable "Require branches to be up to date before merging"
- [ ] Enable "Include administrators" (optional)

## Optional Integrations

### Codecov (Code Coverage)

- [ ] Go to [codecov.io](https://codecov.io)
- [ ] Sign in with GitHub
- [ ] Add repository
- [ ] Copy upload token (for private repos)
- [ ] Add to GitHub Secrets:
  - Secret name: `CODECOV_TOKEN`
  - Secret value: [your token]
- [ ] Update badge URL in README with token

### Slack Notifications (Optional)

- [ ] Create Slack incoming webhook
- [ ] Add to GitHub Secrets:
  - Secret name: `SLACK_WEBHOOK`
  - Secret value: [webhook URL]
- [ ] Uncomment notification steps in workflows

### Discord Notifications (Optional)

- [ ] Create Discord webhook
- [ ] Add to GitHub Secrets:
  - Secret name: `DISCORD_WEBHOOK`
  - Secret value: [webhook URL]
- [ ] Uncomment notification steps in workflows

### Docker Hub (Optional - if not using GHCR)

- [ ] Add to GitHub Secrets:
  - Secret name: `DOCKER_USERNAME`
  - Secret value: [your Docker Hub username]
- [ ] Add to GitHub Secrets:
  - Secret name: `DOCKER_PASSWORD`
  - Secret value: [your Docker Hub password/token]

## Initial Deployment

### Commit and Push Workflows

- [ ] Create commit with CI/CD files
  ```bash
  git add .github/ .pylintrc mypy.ini .pre-commit-config.yaml .yamllint.yml
  git commit -m "ci: Add comprehensive CI/CD pipelines"
  ```
- [ ] Push to GitHub
  ```bash
  git push origin main
  ```
- [ ] Monitor initial workflow runs in Actions tab

### Verify Workflow Execution

**Quality Workflow:**
- [ ] Navigate to Actions → Quality → Latest run
- [ ] Verify all jobs completed successfully
- [ ] Review any warnings or errors
- [ ] Download and review artifacts (if any)

**Security Workflow:**
- [ ] Navigate to Actions → Security → Latest run
- [ ] Verify all security scans completed
- [ ] Review Bandit report
- [ ] Review Safety report
- [ ] Review Semgrep report
- [ ] Check for any critical vulnerabilities

**Tests Workflow:**
- [ ] Navigate to Actions → Tests → Latest run
- [ ] Verify tests passed on all Python versions
- [ ] Verify tests passed on all operating systems
- [ ] Check code coverage percentage
- [ ] Review coverage report artifact

**Deploy Workflow:**
- [ ] Navigate to Actions → Deploy → Latest run
- [ ] Verify build completed successfully
- [ ] Check Docker image was created
- [ ] Verify artifacts were uploaded

## Status Badges

### Update README.md

- [ ] Copy badge template from `.github/README_BADGES_TEMPLATE.md`
- [ ] Replace `USERNAME` with your GitHub username
- [ ] Replace `REPO` with your repository name
- [ ] Add badges to top of README.md
- [ ] Commit and push changes
  ```bash
  git add README.md
  git commit -m "docs: Add CI/CD status badges"
  git push
  ```
- [ ] Verify badges display correctly in README

### Example Badge Section

```markdown
[![Code Quality](https://github.com/USERNAME/REPO/actions/workflows/quality.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/quality.yml)
[![Security](https://github.com/USERNAME/REPO/actions/workflows/security.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/security.yml)
[![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/tests.yml)
[![Deploy](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/deploy.yml)
[![codecov](https://codecov.io/gh/USERNAME/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/REPO)
```

## Testing & Validation

### Local Testing

- [ ] Run pre-commit hooks on all files
  ```bash
  pre-commit run --all-files
  ```
- [ ] Fix any issues found
- [ ] Run tests locally
  ```bash
  pytest tests/aixn_tests/unit/ -v --cov=src/aixn/core
  pytest tests/aixn_tests/integration/ -v
  ```
- [ ] Run security scans locally
  ```bash
  bandit -r src/
  safety check
  ```
- [ ] Run code quality checks
  ```bash
  black --check src/ tests/ scripts/
  pylint src/aixn/core/
  mypy src/aixn/core/
  ```

### Create Test Pull Request

- [ ] Create a new branch
  ```bash
  git checkout -b test/ci-cd-verification
  ```
- [ ] Make a small change
  ```bash
  echo "# CI/CD Test" >> docs/CI_CD_TEST.md
  git add docs/CI_CD_TEST.md
  git commit -m "test: Verify CI/CD pipeline"
  ```
- [ ] Push branch
  ```bash
  git push origin test/ci-cd-verification
  ```
- [ ] Create Pull Request on GitHub
- [ ] Verify all checks run and pass
- [ ] Review check details
- [ ] Merge PR if all checks pass
- [ ] Delete test branch

## Production Deployment Test

### Create Test Release

- [ ] Tag a test release
  ```bash
  git tag -a v0.1.0-test -m "Test release for CI/CD validation"
  git push origin v0.1.0-test
  ```
- [ ] Navigate to Actions → Deploy
- [ ] Verify deployment workflow triggered
- [ ] Check build artifacts were created
- [ ] Verify Docker image was pushed
- [ ] Check GitHub release was created
- [ ] Review release notes
- [ ] Delete test tag if needed
  ```bash
  git tag -d v0.1.0-test
  git push origin :refs/tags/v0.1.0-test
  ```

## Ongoing Maintenance

### Weekly Tasks

- [ ] Review workflow runs for failures
- [ ] Check security scan results
- [ ] Update pre-commit hooks
  ```bash
  pre-commit autoupdate
  ```
- [ ] Review dependency updates
  ```bash
  pip list --outdated
  ```

### Monthly Tasks

- [ ] Update GitHub Actions versions in workflows
- [ ] Review and update Python dependencies
- [ ] Check code coverage trends
- [ ] Review and optimize workflow performance
- [ ] Update documentation

### Quarterly Tasks

- [ ] Perform comprehensive security audit
- [ ] Review and update CI/CD strategy
- [ ] Evaluate new tools and integrations
- [ ] Update team documentation
- [ ] Review and optimize costs (if using paid features)

## Troubleshooting Checklist

### Workflow Not Running

- [ ] Check if GitHub Actions is enabled
- [ ] Verify workflow file syntax (use YAML linter)
- [ ] Check branch name matches triggers
- [ ] Review workflow logs for errors
- [ ] Verify repository permissions

### Tests Failing

- [ ] Run tests locally to reproduce
- [ ] Check Python version compatibility
- [ ] Verify all dependencies are listed in requirements.txt
- [ ] Review test logs for specific errors
- [ ] Check for environment-specific issues
- [ ] Verify test data and fixtures

### Security Scan Issues

- [ ] Review security report artifacts
- [ ] Check for false positives
- [ ] Update .bandit config if needed
- [ ] Update vulnerable dependencies
- [ ] Verify secrets are not exposed

### Deployment Issues

- [ ] Check environment configuration
- [ ] Verify secrets are set correctly
- [ ] Review deployment logs
- [ ] Test Docker build locally
- [ ] Verify deployment scripts

### Badge Not Updating

- [ ] Check badge URL format
- [ ] Verify workflow name matches
- [ ] Clear browser cache
- [ ] Wait a few minutes for update
- [ ] Check if workflow actually ran

## Documentation Checklist

- [ ] Review `.github/workflows/README.md`
- [ ] Read `.github/CICD_SETUP_GUIDE.md`
- [ ] Check `.github/CI_CD_IMPLEMENTATION_SUMMARY.md`
- [ ] Review badge templates in `.github/README_BADGES_TEMPLATE.md`
- [ ] Update project README with:
  - [ ] Status badges
  - [ ] CI/CD information
  - [ ] Contribution guidelines
  - [ ] Testing instructions

## Team Onboarding Checklist

- [ ] Share CI/CD documentation with team
- [ ] Explain workflow purposes and triggers
- [ ] Demonstrate how to read workflow logs
- [ ] Show how to run checks locally
- [ ] Explain branch protection rules
- [ ] Train on pre-commit hooks usage
- [ ] Document common troubleshooting steps
- [ ] Set up notification channels

## Quality Metrics Tracking

### Code Quality

- [ ] Set target: Code quality score > 8.0/10
- [ ] Monitor Pylint scores
- [ ] Track MyPy error count
- [ ] Review complexity metrics

### Test Coverage

- [ ] Set target: Overall coverage > 80%
- [ ] Unit test coverage > 90%
- [ ] Integration test coverage > 70%
- [ ] Monitor coverage trends

### Security

- [ ] Set target: 0 high/critical vulnerabilities
- [ ] Review security scan results weekly
- [ ] Track dependency vulnerabilities
- [ ] Monitor secret scanning alerts

### Performance

- [ ] Set target: Workflow runtime < 10 minutes
- [ ] Monitor workflow execution times
- [ ] Optimize slow jobs
- [ ] Track artifact sizes

## Success Criteria

Your CI/CD pipeline is successfully set up when:

- [x] All workflow files are created
- [ ] All workflows run successfully
- [ ] Code coverage is being tracked
- [ ] Security scans are passing
- [ ] Status badges are displayed
- [ ] Pre-commit hooks are working
- [ ] Team is onboarded
- [ ] Documentation is complete

## Final Verification

- [ ] All workflows show green checkmarks
- [ ] Status badges display correctly
- [ ] Code coverage report is generated
- [ ] Security scans show no critical issues
- [ ] Docker images are being built
- [ ] Deployment works for staging
- [ ] Team can run checks locally
- [ ] Documentation is accessible

## Completion

Congratulations! Your CI/CD pipeline is now fully operational.

**Date Completed:** _________________

**Completed By:** _________________

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

## Quick Reference Commands

### Local Development
```bash
# Run pre-commit hooks
pre-commit run --all-files

# Run tests
pytest tests/aixn_tests/unit/ -v

# Check code quality
black --check src/
pylint src/aixn/core/
mypy src/aixn/core/

# Security scan
bandit -r src/
safety check
```

### Git Operations
```bash
# Create feature branch
git checkout -b feature/my-feature

# Commit with conventional commit
git commit -m "feat: Add new feature"

# Push and create PR
git push origin feature/my-feature
gh pr create  # if using GitHub CLI
```

### Docker
```bash
# Build image
docker build -t aixn-blockchain .

# Run container
docker run -p 8333:8333 -p 8080:8080 aixn-blockchain

# Check logs
docker logs <container-id>
```

### Monitoring
```bash
# List workflow runs (requires GitHub CLI)
gh run list

# View workflow run details
gh run view <run-id>

# Watch workflow
gh run watch
```

---

**Need Help?**
- Review `.github/CICD_SETUP_GUIDE.md`
- Check `.github/workflows/README.md`
- Consult troubleshooting section above
- Open an issue in the repository
