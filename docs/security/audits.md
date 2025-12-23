# Security Audits and Automated Scanning

This document describes the comprehensive security testing infrastructure for the XAI blockchain. XAI employs multiple layers of automated security scanning through CI/CD pipelines, plus manual security review processes.

## Table of Contents

- [Continuous Security Scanning](#continuous-security-scanning)
- [Security Tools Overview](#security-tools-overview)
- [Running Scans Locally](#running-scans-locally)
- [Interpreting Results](#interpreting-results)
- [Security Workflow](#security-workflow)
- [Known Issues and Remediation](#known-issues-and-remediation)

## Continuous Security Scanning

XAI's CI/CD pipeline runs comprehensive security scans on every commit to `main` branch, pull requests, and weekly scheduled runs.

### Automated Scanning Schedule

- **On Push to Main**: Full security suite runs on every merge
- **On Pull Requests**: Comprehensive scans before code review
- **Weekly Scheduled**: Sunday 00:00 UTC full security audit
- **Dependency Review**: Automatic on all PRs (blocks merge if high/critical vulnerabilities)

### Security Pipeline Architecture

```
┌─────────────────┐
│   Code Commit   │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Parallel │
    │ Security │
    │ Scanning │
    └────┬─────┘
         │
    ┌────▼──────────────────────────────────┐
    │  1. Bandit (Python SAST)              │
    │  2. Semgrep (Multi-language SAST)     │
    │  3. CodeQL (Deep semantic analysis)   │
    │  4. pip-audit (Dependency vulns)      │
    │  5. Safety (Known CVEs)               │
    │  6. Gitleaks (Secret scanning)        │
    │  7. TruffleHog (Credential detection) │
    └────┬──────────────────────────────────┘
         │
    ┌────▼────────────┐
    │ Security Summary │
    │ Report Generated │
    └─────────────────┘
```

## Security Tools Overview

### 1. Bandit - Python Security Scanner

**Purpose**: Detects common security issues in Python code

**Configuration**: `.bandit`

**Scans for**:
- Hardcoded passwords and secrets
- SQL injection vulnerabilities
- Command injection risks
- Insecure cryptographic functions
- Unsafe YAML/pickle usage
- Assert statements in production code

**Example Issues Detected**:
```python
# B105: Hardcoded password
password = "admin123"  # FLAGGED

# B608: SQL injection
query = f"SELECT * FROM users WHERE id = {user_input}"  # FLAGGED

# B324: Insecure hash function
hashlib.md5(data)  # FLAGGED - use SHA-256 or better
```

**Severity Levels**:
- **HIGH**: Immediate security risk (SQL injection, command injection)
- **MEDIUM**: Potential vulnerability (weak crypto, insecure deserialization)
- **LOW**: Best practice violations (assert usage, weak randomness)

### 2. Semgrep - Static Application Security Testing

**Purpose**: Pattern-based code analysis for security vulnerabilities

**Rulesets Used**:
- `p/security-audit` - General security patterns
- `p/python` - Python-specific vulnerabilities
- `p/secrets` - Credential and secret detection
- `p/owasp-top-ten` - OWASP Top 10 vulnerabilities

**Advanced Detection**:
- Taint tracking (input → output flow analysis)
- Control flow analysis
- Cross-file analysis
- Custom XAI-specific rules

**Example Patterns**:
```python
# Detects unsafe deserialization
pickle.loads(untrusted_data)  # VULNERABLE

# Detects path traversal
open(user_input)  # VULNERABLE - needs validation

# Detects SSRF
requests.get(user_provided_url)  # VULNERABLE - needs allowlist
```

### 3. CodeQL - Deep Semantic Analysis

**Purpose**: GitHub's advanced code analysis engine

**Analysis Type**: Dataflow and control-flow analysis

**Queries**: `security-and-quality` query suite

**Detects**:
- Complex injection vulnerabilities
- Race conditions
- Resource leaks
- Null pointer dereferences
- Logic errors leading to security issues

**Unique Capabilities**:
- Multi-file analysis (traces data across modules)
- Inter-procedural analysis (follows function calls)
- Framework-aware (understands Flask, Django patterns)

**Example Analysis**:
```python
# CodeQL tracks taint flow:
user_input = request.args.get('file')  # Source
path = os.path.join('/data', user_input)  # Dataflow
with open(path) as f:  # Sink - VULNERABLE
    return f.read()
```

### 4. pip-audit - Dependency Vulnerability Scanner

**Purpose**: Checks Python dependencies for known CVEs

**Database**: PyPI Advisory Database + OSV

**Scans**:
- `requirements.txt`
- `pyproject.toml` dependencies
- Installed packages in virtual environment

**Output Example**:
```
Found 2 vulnerabilities in 1 package:
cryptography (38.0.1)
├── CVE-2023-23931: GHSA-w7pp-m8wf-vj6r
│   Fixed in: 39.0.1
│   Severity: HIGH
└── CVE-2023-0286: GHSA-x4qr-2fvf-3mr5
    Fixed in: 39.0.1
    Severity: HIGH
```

### 5. Safety - Known Vulnerability Database

**Purpose**: Cross-references dependencies with safety-db

**Database**: https://github.com/pyupio/safety-db

**Checks**:
- Known security vulnerabilities
- Malicious packages
- License compliance (flags GPL/AGPL)

**Complementary to pip-audit**: Uses different databases for comprehensive coverage

### 6. Gitleaks - Secret Detection

**Purpose**: Scans git history for accidentally committed secrets

**Detection Methods**:
- Regex patterns for common secrets (API keys, tokens)
- Entropy analysis (high entropy = potential secret)
- Custom rules for XAI-specific secrets

**Detects**:
- Private keys (RSA, ECDSA, ED25519)
- API keys (AWS, Google Cloud, GitHub)
- Database credentials
- Authentication tokens
- Encryption keys

**Example Detection**:
```bash
# Gitleaks finds:
Finding: github_personal_access_token
Secret: ghp_1234567890abcdefghijklmnopqrstuvwxyz
File: config/production.yml
Line: 15
Commit: abc123def456
```

### 7. TruffleHog - Credential Scanner

**Purpose**: Deep credential scanning with verification

**Features**:
- **Verification**: Attempts to use found credentials (checks if valid)
- **Historical Scanning**: Scans entire git history
- **High Accuracy**: Lower false positive rate

**Verified Detections**:
- AWS credentials (attempts AWS API call)
- GitHub tokens (validates via GitHub API)
- Slack tokens
- Database connection strings

## Running Scans Locally

### Prerequisites

```bash
# Install security tools
pip install bandit[toml] semgrep pip-audit safety

# Install gitleaks (macOS)
brew install gitleaks

# Install gitleaks (Linux)
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

### Running Individual Scans

#### Bandit

```bash
# Full scan with high/medium severity
bandit -r src/ -ll

# Generate JSON report
bandit -r src/ -f json -o bandit-report.json

# Scan specific file
bandit src/xai/core/defi/lending.py

# Exclude test files
bandit -r src/ -ll --exclude tests/
```

#### Semgrep

```bash
# Run all security rules
semgrep --config p/security-audit --config p/python src/

# Run OWASP Top 10 rules
semgrep --config p/owasp-top-ten src/

# Generate JSON output
semgrep --config p/security-audit src/ --json -o semgrep-report.json

# Auto-fix safe issues
semgrep --config p/python src/ --autofix
```

#### CodeQL (Requires GitHub CLI)

```bash
# Install CodeQL
gh extension install github/gh-codeql

# Create database
codeql database create xai-db --language=python

# Run analysis
codeql database analyze xai-db \
  python-security-and-quality.qls \
  --format=sarif-latest \
  --output=codeql-results.sarif
```

#### pip-audit

```bash
# Audit requirements.txt
pip-audit -r requirements.txt

# Audit installed packages
pip-audit

# Generate JSON report
pip-audit -f json -o pip-audit-report.json

# Fix vulnerabilities automatically
pip-audit --fix
```

#### Safety

```bash
# Check requirements.txt
safety check -r requirements.txt

# Check installed packages
safety check

# Output JSON
safety check --json --output safety-report.json
```

#### Gitleaks

```bash
# Scan current state
gitleaks detect --source . --report-path gitleaks-report.json

# Scan entire git history
gitleaks detect --source . --log-opts '--all'

# Scan specific commits
gitleaks detect --source . --log-opts 'HEAD~10..HEAD'

# Baseline mode (ignore existing issues)
gitleaks detect --source . --baseline-path .gitleaks-baseline.json
```

#### TruffleHog

```bash
# Scan repository with verification
trufflehog git file://. --only-verified

# Scan specific branch
trufflehog git file://. --branch main

# Output JSON
trufflehog git file://. --json > trufflehog-report.json
```

### Running Full Security Suite

```bash
#!/bin/bash
# scripts/run-security-suite.sh

echo "Running comprehensive security scan..."

# Create reports directory
mkdir -p security-reports

# 1. Bandit
echo "[1/7] Running Bandit..."
bandit -r src/ -ll -f json -o security-reports/bandit.json

# 2. Semgrep
echo "[2/7] Running Semgrep..."
semgrep --config p/security-audit --config p/python src/ \
  --json -o security-reports/semgrep.json

# 3. pip-audit
echo "[3/7] Running pip-audit..."
pip-audit -f json -o security-reports/pip-audit.json

# 4. Safety
echo "[4/7] Running Safety..."
safety check --json --output security-reports/safety.json || true

# 5. Gitleaks
echo "[5/7] Running Gitleaks..."
gitleaks detect --source . --report-path security-reports/gitleaks.json

# 6. TruffleHog
echo "[6/7] Running TruffleHog..."
trufflehog git file://. --only-verified --json > security-reports/trufflehog.json

# 7. Test coverage
echo "[7/7] Running tests with coverage..."
pytest tests/ -v --cov=src --cov-report=json --cov-report=html

echo "✓ Security scan complete. Reports in security-reports/"
```

## Interpreting Results

### Severity Classification

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| **CRITICAL** | Actively exploitable, high impact | Immediate fix, block deployment |
| **HIGH** | Exploitable with moderate effort | Fix before next release |
| **MEDIUM** | Potential vulnerability | Fix in upcoming sprint |
| **LOW** | Best practice violation | Address during refactoring |
| **INFO** | Code smell, not security issue | Optional improvement |

### False Positive Management

Common false positives and how to handle them:

#### Bandit False Positives

```python
# B101: Assert used (okay in tests)
# Solution: Use # nosec comment
assert user.is_authenticated  # nosec B101

# B608: SQL injection (but using parameterized query)
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))  # nosec B608
```

#### Semgrep False Positives

```yaml
# .semgrepignore
# Ignore test files for certain rules
tests/

# Ignore specific directories
archive/
examples/
```

### Baseline Approach

For existing codebases with historical issues:

```bash
# Create baseline (current state)
gitleaks detect --source . --report-path .gitleaks-baseline.json

# Future scans only report new issues
gitleaks detect --source . --baseline-path .gitleaks-baseline.json
```

## Security Workflow

### Pre-Commit Checks

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running pre-commit security checks..."

# Quick Bandit scan on staged files
git diff --cached --name-only --diff-filter=ACM | grep '\.py$' | xargs bandit -ll

# Gitleaks on staged changes
gitleaks protect --staged

if [ $? -ne 0 ]; then
    echo "❌ Security issues detected. Commit blocked."
    exit 1
fi

echo "✓ Pre-commit security checks passed"
```

### Pull Request Review

GitHub Actions automatically:
1. Runs full security suite
2. Posts results as PR comments
3. Blocks merge if critical/high severity issues found
4. Uploads SARIF results to Security tab

Reviewers should verify:
- No new security warnings introduced
- All flagged issues have valid justification
- Dependency updates don't introduce vulnerabilities

### Mainline Protection

On merge to `main`:
1. Full security rescan
2. Generate security summary artifact (retained 90 days)
3. Update security badge
4. Notify security team if new issues detected

## Known Issues and Remediation

### Previously Addressed Vulnerabilities

XAI has undergone comprehensive security hardening. Major fixes include:

#### Access Control Vulnerabilities (RESOLVED)

**Issue**: Simple address string matching allowed impersonation

**Fix**: Implemented cryptographic signature verification
- File: `src/xai/core/defi/access_control.py`
- Solution: ECDSA signatures + nonce-based replay protection
- Status: ✅ Resolved (all privileged functions now require signatures)

#### Integer Overflow/Underflow (RESOLVED)

**Issue**: Unchecked arithmetic could cause overflow

**Fix**: Comprehensive SafeMath library
- File: `src/xai/core/defi/safe_math.py`
- Solution: Bounds-checked arithmetic with explicit error messages
- Status: ✅ Resolved (all financial calculations use SafeMath)

#### Reentrancy Vulnerabilities (RESOLVED)

**Issue**: Flash loan callback could reenter during execution

**Fix**: Defense-in-depth reentrancy protection
- File: `src/xai/core/defi/flash_loans.py`
- Solution: Dual guards (explicit flag + execution lock) + checks-effects-interactions
- Status: ✅ Resolved (comprehensive reentrancy protection)

### Current Security Posture

XAI implements security best practices:

✅ **Access Control**: Signature-based authentication with replay protection
✅ **Arithmetic Safety**: SafeMath with overflow/underflow checks
✅ **Reentrancy Protection**: Lock-based guards on critical functions
✅ **Input Validation**: Comprehensive schema validation
✅ **Oracle Security**: TWAP implementation for manipulation resistance
✅ **Flash Loan Protection**: Multi-layer defenses
✅ **Circuit Breakers**: Emergency pause functionality
✅ **Proxy Patterns**: Secure upgrade mechanisms (EIP-1967, UUPS, Beacon)

### Security Metrics

Current coverage (as of January 2025):

- **Test Coverage**: 85%+ for core modules
- **Static Analysis**: Clean (zero high/critical issues)
- **Dependency Audit**: All dependencies up to date
- **Secret Scanning**: No exposed credentials
- **Code Review**: 100% of commits reviewed by security-aware developers

## Reporting Security Issues

### Responsible Disclosure

Found a security vulnerability? Please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. **Email**: security@xai.io with:
   - Detailed vulnerability description
   - Proof-of-concept (if available)
   - Suggested remediation
   - Your contact information

3. **PGP Key**: Available at https://xai.io/.well-known/security.txt

4. **Response Time**:
   - Acknowledgment: Within 24 hours
   - Initial assessment: Within 72 hours
   - Fix timeline: Depends on severity (critical: days, high: weeks)

5. **Disclosure Timeline**:
   - Coordinated disclosure after patch is deployed
   - Public disclosure 90 days after report (standard)
   - Credit given in security advisories (if desired)

### Bug Bounty Program

XAI operates a bug bounty program for responsible security researchers:

**Scope**: XAI blockchain core, smart contracts, wallet software

**Rewards**:
- Critical: $5,000 - $10,000
- High: $1,000 - $5,000
- Medium: $500 - $1,000
- Low: $100 - $500

**Out of Scope**: Testnet, documentation typos, social engineering

**Details**: https://xai.io/security/bug-bounty

## Additional Resources

- **Smart Contract Security**: `docs/security/contracts.md`
- **Wallet Security**: `docs/security/wallets.md`
- **CI/CD Workflow**: `.github/workflows/security.yml`
- **OpenSSF Best Practices**: https://bestpractices.coreinfrastructure.org/
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/

---

**Security is a continuous process, not a one-time event.** XAI's automated scanning provides ongoing protection, but developers must remain vigilant and follow secure coding practices.

**Last Updated**: January 2025
