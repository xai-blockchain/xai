# Security Tools Quick Start Guide

This guide covers the Python security tools installed for the AIXN blockchain project.

## Installed Tools

- **bandit** - Security linter for Python code
- **pip-audit** - Dependency vulnerability scanner
- **semgrep** - Static analysis tool
- **pylint** - Code quality checker
- **mypy** - Static type checker
- **black** - Code formatter
- **flake8** - Style guide enforcement

## Quick Start

### 1. Install Development Tools

```bash
pip install -r requirements-dev.txt
```

### 2. Run Security Scans

#### Scan for Dependency Vulnerabilities
```bash
# Scan requirements file
pip-audit -r src/aixn/requirements.txt

# Scan with fixes suggested
pip-audit -r src/aixn/requirements.txt --fix

# Output to JSON
pip-audit -r src/aixn/requirements.txt --format json -o pip-audit-report.json
```

#### Run Static Security Analysis (Semgrep)
```bash
# Auto-detect security issues
semgrep --config auto src/

# Use security-focused rulesets
semgrep --config p/security-audit src/
semgrep --config p/owasp-top-ten src/
semgrep --config p/secrets src/

# Scan and output to JSON
semgrep --config auto src/ --json -o semgrep-report.json

# Scan with severity filters
semgrep --config auto src/ --severity ERROR
```

#### Run Bandit Security Linter
```bash
# Basic scan
bandit -r src/

# Use configuration file
bandit -r src/ -c .bandit

# Output to JSON
bandit -r src/ -c .bandit -f json -o bandit-report.json

# Only show high severity issues
bandit -r src/ -ll

# Scan specific file
bandit src/aixn/core/wallet.py
```

### 3. Code Quality Checks

#### Run Pylint
```bash
# Check all code
pylint src/aixn

# Check specific module
pylint src/aixn/core/blockchain.py

# With custom rcfile
pylint --rcfile=.pylintrc src/aixn

# JSON output
pylint src/aixn --output-format=json
```

#### Run MyPy (Type Checking)
```bash
# Type check entire project
mypy src/aixn

# Ignore missing imports
mypy src/aixn --ignore-missing-imports

# Strict mode
mypy src/aixn --strict

# Check specific file
mypy src/aixn/core/wallet.py
```

#### Format Code with Black
```bash
# Check what would be formatted
black --check src/

# Format all files
black src/

# Format specific file
black src/aixn/core/blockchain.py

# Show diff
black --diff src/
```

#### Run Flake8 (Style Guide)
```bash
# Check all code
flake8 src/

# With specific config
flake8 --config=.flake8 src/

# Check specific file
flake8 src/aixn/core/wallet.py
```

## Configuration Files

### .bandit
Location: `C:\Users\decri\GitClones\Crypto\.bandit`
- Excludes test directories and build artifacts
- Configured for comprehensive security scanning

### .semgrepignore
Location: `C:\Users\decri\GitClones\Crypto\.semgrepignore`
- Excludes version control and build artifacts
- Protects sensitive files from scanning

## Common Workflows

### Pre-Commit Checks
```bash
# Run all checks before committing
black --check src/
flake8 src/
mypy src/aixn --ignore-missing-imports
bandit -r src/ -ll
```

### Full Security Audit
```bash
# Complete security scan
pip-audit -r src/aixn/requirements.txt
semgrep --config auto src/
bandit -r src/ -c .bandit
```

### CI/CD Integration
See `.github/workflows/security-scan.yml` for automated scanning setup.

## Tool-Specific Tips

### Bandit

**Common Issues:**
- Python 3.14 compatibility: Use Python 3.11/3.12 for scanning
- False positives: Use `# nosec` comment to suppress specific warnings

**Example suppression:**
```python
# This is safe because we validate input
password = input("Enter password: ")  # nosec B322
```

### Semgrep

**Best Practices:**
- Start with `--config auto` for automatic rule selection
- Use multiple configs for comprehensive coverage
- Review and tune rules for your project

**Custom rules:**
Create `.semgrep.yml` for project-specific rules

### Pip-audit

**Best Practices:**
- Run regularly (weekly recommended)
- Use `--fix` flag to see upgrade suggestions
- Monitor for new CVEs in dependencies

**Exclude packages:**
```bash
pip-audit --ignore-vuln GHSA-xxxx-xxxx-xxxx
```

## Integration with Git Hooks

### Setup Pre-commit Hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash

echo "Running security checks..."

# Quick security scan
bandit -r src/ -ll -q
if [ $? -ne 0 ]; then
    echo "Bandit found security issues!"
    exit 1
fi

# Code quality
black --check src/ -q
if [ $? -ne 0 ]; then
    echo "Code needs formatting with black!"
    exit 1
fi

echo "Security checks passed!"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Interpreting Results

### Severity Levels

- **HIGH**: Critical security vulnerabilities - fix immediately
- **MEDIUM**: Significant issues - fix within 1 week
- **LOW**: Minor issues or potential problems - review and fix as needed

### Common Findings

1. **Hardcoded credentials** - Never commit API keys, passwords
2. **SQL injection** - Use parameterized queries
3. **Command injection** - Validate and sanitize user input
4. **Insecure crypto** - Use strong algorithms and key sizes
5. **Path traversal** - Validate file paths and use safe functions

## Continuous Monitoring

### Recommended Schedule

- **Daily**: Run black and flake8 during development
- **Weekly**: Full pip-audit scan for vulnerabilities
- **Per commit**: Bandit security scan
- **Per PR**: Complete semgrep analysis
- **Monthly**: Manual security review and tool updates

## Getting Help

### Tool Documentation

- Bandit: https://bandit.readthedocs.io/
- Semgrep: https://semgrep.dev/docs/
- pip-audit: https://github.com/pypa/pip-audit
- Pylint: https://pylint.pycqa.org/
- MyPy: https://mypy.readthedocs.io/
- Black: https://black.readthedocs.io/
- Flake8: https://flake8.pycqa.org/

### Common Issues

**Q: Tool not found**
```bash
# Reinstall development tools
pip install -r requirements-dev.txt
```

**Q: Too many false positives**
- Review and configure exclude patterns
- Use inline suppressions with documentation
- Tune severity thresholds

**Q: Scans taking too long**
- Use `.bandit` and `.semgrepignore` to exclude unnecessary directories
- Run incremental scans on changed files only
- Use parallel processing options where available

## Updating Tools

```bash
# Update all development tools
pip install -U -r requirements-dev.txt

# Update specific tool
pip install -U bandit
```

## Report Location

Security scan reports are generated in the project root:
- `pip-audit-report.json` - Dependency vulnerabilities
- `bandit-report.json` - Code security issues
- `semgrep-report.json` - Static analysis results
- `SECURITY_AUDIT_REPORT.md` - Comprehensive security report

---

**Last Updated:** 2025-11-12
**Maintained by:** AIXN Security Team
