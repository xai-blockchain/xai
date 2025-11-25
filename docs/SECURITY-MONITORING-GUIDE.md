# Security Monitoring Guide

## Overview

The XAI Blockchain project implements comprehensive automated security monitoring using industry-standard tools and practices. This guide covers setup, configuration, and operation of the security monitoring system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Components](#components)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Monitoring Tools](#monitoring-tools)
7. [Alerts and Notifications](#alerts-and-notifications)
8. [Dashboard](#dashboard)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Quick Start

### Local Security Scan

```bash
# Install security tools
pip install bandit safety pip-audit semgrep

# Run quick scan (Bandit only)
python scripts/security_monitor.py --mode quick

# Run standard scan
python scripts/security_monitor.py --mode standard

# Run comprehensive scan
python scripts/security_monitor.py --mode comprehensive
```

### Pre-commit Hooks

```bash
# Install pre-commit framework
pip install pre-commit

# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Run hooks on all files
pre-commit run --all-files
```

## Components

### 1. Security Monitor Script

**File**: `scripts/security_monitor.py`

Orchestrates all security scanning operations:
- Bandit (Python security)
- Safety (dependency scanning)
- pip-audit (package auditing)
- Semgrep (static analysis)
- Trivy (filesystem/container scanning)

**Usage**:
```bash
python scripts/security_monitor.py [--mode MODE] [--output OUTPUT] [--config CONFIG]
```

**Modes**:
- `quick`: Fast scan (Bandit only)
- `standard`: Full scan (Bandit, Safety, pip-audit)
- `comprehensive`: Complete analysis (all tools)

### 2. Alert System

**File**: `scripts/security_alerts.py`

Processes security reports and sends alerts:
- Email notifications
- Slack messages
- GitHub issues
- Severity-based routing

**Usage**:
```bash
python scripts/security_alerts.py --config .security/config.yml --report <report_path>
```

### 3. GitHub Actions Workflow

**File**: `.github/workflows/security-monitoring.yml`

Automated CI/CD security scanning:
- Runs on every push to main/develop
- Runs on every pull request
- Daily scheduled comprehensive scan
- Weekly deep scan with Trivy/OWASP

### 4. Pre-commit Hooks

**File**: `.pre-commit-config.yaml`

Local pre-commit security checks:
- Secret detection (detect-secrets)
- Security linting (Bandit)
- Dependency auditing (pip-audit)
- Code formatting and linting

### 5. Security Dashboard

**File**: `SECURITY-DASHBOARD.md`

Auto-generated dashboard showing:
- Current security score
- Active vulnerabilities
- Scan history
- Trend analysis
- Action items

## Installation

### Prerequisites

- Python 3.11+
- Git
- pip or poetry

### Setup

```bash
# Clone repository
git clone https://github.com/decri/Crypto.git
cd Crypto

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install security tools
pip install bandit safety pip-audit semgrep detect-secrets

# Setup pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg
```

### Optional Tools

```bash
# Install Trivy (container scanning)
# Ubuntu/Debian
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Install OWASP Dependency-Check
# Download from https://dependencycheck.org

# Install SonarQube scanner (optional)
pip install sonarscan
```

## Configuration

### Security Config File

**File**: `.security/config.yml`

Main configuration for security monitoring:

```yaml
scan_targets:
  source: 'src/'
  tests: 'tests/'
  scripts: 'scripts/'

severity_thresholds:
  critical: 0      # Zero tolerance
  high: 5
  medium: 20
  low: 100

tools:
  bandit:
    enabled: true
    level: '-ll'
  safety:
    enabled: true
  pip_audit:
    enabled: true
  semgrep:
    enabled: true

alerts:
  email:
    enabled: false
  slack:
    enabled: false
  github:
    enabled: true
```

### Environment Variables

For alerts and integrations:

```bash
# Email alerts
export ALERT_EMAIL_FROM="your-email@domain.com"
export ALERT_EMAIL_PASSWORD="your-password"
export ALERT_EMAIL_TO="recipient@domain.com"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"

# Slack notifications
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# GitHub integration
export GITHUB_TOKEN="ghp_..."
export GITHUB_REPOSITORY="decri/Crypto"

# SonarQube (optional)
export SONARQUBE_TOKEN="squ_..."
export SONARQUBE_HOST="https://sonarqube.example.com"
```

## Usage

### Local Scanning

#### Quick Scan (5 minutes)
```bash
python scripts/security_monitor.py --mode quick
```

#### Standard Scan (10 minutes)
```bash
python scripts/security_monitor.py --mode standard
```

#### Comprehensive Scan (20+ minutes)
```bash
python scripts/security_monitor.py --mode comprehensive
```

### Pre-commit Checks

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run bandit --all-files

# Skip pre-commit (not recommended)
git commit --no-verify
```

### Manual Alert Processing

```bash
python scripts/security_alerts.py \
  --config .security/config.yml \
  --report security_reports/security_report_20231118_120000.json
```

## Monitoring Tools

### 1. Bandit

Python security linter for common vulnerabilities.

**Configuration**: `.bandit`

```ini
[bandit]
exclude_dirs = ['/test/', '/venv/']
skips = B101,B601
```

**Command**:
```bash
bandit -r src/ -f json -o bandit-report.json
```

### 2. Safety

Checks dependencies against known security vulnerabilities.

**Command**:
```bash
safety check --json --file requirements.txt
```

### 3. pip-audit

Scans Python packages for known vulnerabilities.

**Command**:
```bash
pip-audit --format json --output pip-audit-report.json
```

### 4. Semgrep

Static analysis tool for finding bugs, security issues, and anti-patterns.

**Configuration**: Custom rules in `.semgrep.yml`

**Command**:
```bash
semgrep --config auto --json --output semgrep-report.json src/
```

### 5. Trivy

Container and filesystem vulnerability scanner.

**Command**:
```bash
trivy fs --format json --output trivy-report.json .
```

### 6. CodeQL

Advanced code analysis by GitHub.

Runs automatically in CI/CD. No local setup required.

## Alerts and Notifications

### GitHub Issues

Critical and high-severity issues automatically create GitHub issues with:
- Detailed vulnerability description
- Affected files and line numbers
- Remediation suggestions
- Links to documentation

### Slack Notifications

Configure Slack webhook for real-time alerts:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

### Email Alerts

Configure SMTP for email notifications:

```bash
export ALERT_EMAIL_FROM="security@xai.crypto"
export ALERT_EMAIL_PASSWORD="app-password"
export ALERT_EMAIL_TO="team@xai.crypto"
```

### Dashboard Updates

The `SECURITY-DASHBOARD.md` file auto-updates with:
- Current security score
- Recent scan results
- Vulnerability trends
- Remediation status

## Dashboard

### Viewing the Dashboard

Open [SECURITY-DASHBOARD.md](../SECURITY-DASHBOARD.md) in your browser or text editor.

### Security Score

Calculated as: `100 - (vulnerabilities * 2)`

- **90-100**: Excellent
- **70-89**: Good
- **50-69**: Fair
- **Below 50**: Critical

### Trend Analysis

30-day rolling trend shows:
- Weekly vulnerability counts
- Score progression
- Tool-specific trends
- Remediation rate

## Troubleshooting

### Bandit Issues

**Missing dependencies**:
```bash
pip install bandit[toml]
```

**False positives**:
Edit `.bandit` to skip specific tests:
```ini
[bandit]
skips = B101,B601
```

### Safety Issues

**Database outdated**:
```bash
pip install --upgrade safety
safety update
```

**SSL certificate errors**:
```bash
safety check --insecure
```

### Semgrep Issues

**Rules not found**:
```bash
semgrep --config p/security-audit --config p/owasp-top-ten src/
```

**Performance issues**:
```bash
semgrep --config auto --jobs 1 src/
```

### pre-commit Issues

**Hooks failing**:
```bash
pre-commit install --install-hooks
pre-commit run --all-files
```

**Performance issues**:
```yaml
# Add to .pre-commit-config.yaml
default:
  stages: [commit]
  exclude: '^(venv/|\.venv/|build/|dist/)'
```

## Best Practices

### 1. Security Awareness

- Review security findings regularly
- Understand CVE severity ratings
- Keep dependencies updated

### 2. Remediation Process

1. **Assess**: Evaluate vulnerability impact
2. **Plan**: Determine remediation approach
3. **Implement**: Apply fix or workaround
4. **Test**: Verify fix with re-scan
5. **Document**: Record resolution method

### 3. CI/CD Integration

- Enable security checks on every push
- Require security approval for PRs
- Block merges with critical issues
- Archive reports for compliance

### 4. Dependency Management

```bash
# Regular updates
pip list --outdated
pip install --upgrade <package>

# Security updates
pip-audit --fix

# Test after updates
pytest
```

### 5. Code Review

- Review security findings in PRs
- Ask questions about unusual patterns
- Suggest secure alternatives
- Document exceptions

### 6. Secrets Management

```bash
# Scan for exposed secrets
detect-secrets scan

# Rotate compromised secrets immediately
# Update environment variables
# Force password/token resets
```

## Integration with Development Workflow

### Before Committing

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Fix any issues
# Add changes
git add .

# Commit (hooks run automatically)
git commit -m "feat: add new feature"
```

### Before Pushing

```bash
# Run local security scan
python scripts/security_monitor.py --mode quick

# Review any findings
# Fix security issues
git add .
git commit -m "fix: security issue"
git push
```

### Pull Request

GitHub Actions automatically:
1. Runs security scans
2. Comments on PR with findings
3. Blocks merge if critical issues found
4. Creates security issues if needed

## Maintenance

### Monthly Tasks

- [ ] Review security findings
- [ ] Update security tools
- [ ] Check for new CVEs
- [ ] Update dependency versions

### Quarterly Tasks

- [ ] Comprehensive security audit
- [ ] Review and update security policies
- [ ] Analyze vulnerability trends
- [ ] Plan remediation efforts

### Annual Tasks

- [ ] Full security assessment
- [ ] Penetration testing
- [ ] Architecture review
- [ ] Compliance audit

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://safety.readthedocs.io/)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)

## Contact

For security concerns or questions:
1. Review [SECURITY.md](../SECURITY.md)
2. Check existing issues
3. Create a confidential security issue
4. Email: security@xai.crypto

---

**Last Updated**: 2025-11-18
**Version**: 1.0.0
**Maintainer**: Security Team
