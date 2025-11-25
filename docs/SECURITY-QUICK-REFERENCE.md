# Security Monitoring Quick Reference

## Commands

### Run Security Scans

```bash
# Quick scan (5 min)
python scripts/security_monitor.py --mode quick

# Standard scan (10 min)
python scripts/security_monitor.py --mode standard

# Comprehensive scan (20+ min)
python scripts/security_monitor.py --mode comprehensive
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run bandit --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

### Individual Tools

```bash
# Bandit - Python security
bandit -r src/ -f json -o bandit-report.json

# Safety - Dependency scan
safety check --json --output safety-report.json

# pip-audit - Package audit
pip-audit --format json --output pip-audit-report.json

# Semgrep - Static analysis
semgrep --config auto --json src/

# Trivy - Filesystem scan
trivy fs --format json .
```

### Manual Alerts

```bash
python scripts/security_alerts.py \
  --config .security/config.yml \
  --report security_reports/security_report_*.json
```

## File Locations

| File | Purpose |
|------|---------|
| `scripts/security_monitor.py` | Main monitoring script |
| `scripts/security_alerts.py` | Alert processing |
| `.security/config.yml` | Security configuration |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `SECURITY-DASHBOARD.md` | Security status |
| `docs/SECURITY-MONITORING-GUIDE.md` | Full documentation |
| `.github/workflows/security-monitoring.yml` | CI/CD workflow |

## Configuration Quick Reference

### Severity Thresholds

```yaml
severity_thresholds:
  critical: 0      # Zero tolerance
  high: 5          # Max 5
  medium: 20       # Max 20
  low: 100         # Max 100
```

### Enable/Disable Tools

```yaml
tools:
  bandit:
    enabled: true
  safety:
    enabled: true
  pip_audit:
    enabled: true
  semgrep:
    enabled: true
  trivy:
    enabled: false
```

### Alert Configuration

```yaml
alerts:
  email:
    enabled: false
  slack:
    enabled: false
  github:
    enabled: true
    create_issues: true
```

## Environment Variables

```bash
# Email alerts
export ALERT_EMAIL_FROM="your-email@domain.com"
export ALERT_EMAIL_PASSWORD="password"
export ALERT_EMAIL_TO="team@domain.com"

# Slack
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."

# GitHub
export GITHUB_TOKEN="ghp_..."
export GITHUB_REPOSITORY="decri/Crypto"
```

## Typical Workflow

### Before Committing

```bash
# Install hooks (first time only)
pre-commit install

# Hooks run automatically on commit
git add .
git commit -m "feat: add feature"  # Hooks run here
```

### Before Pushing

```bash
# Quick security check
python scripts/security_monitor.py --mode quick

# Fix any issues
# Then push
git push
```

### On Pull Request

- GitHub Actions automatically runs security scans
- Comments on PR with findings
- Blocks merge if critical issues

## Withdrawal Alert Tuning

1. After each staging deployment, open the GitHub Actions run and read the **Withdrawal Threshold Recommendation** summary section. It reflects the latest telemetry analyzed by `withdrawal_threshold_calibrator.py`.
2. If adjustments are needed, run the calibrator locally against the persisted JSONL log for the relevant environment to double-check percentile math:
   ```bash
   python scripts/tools/withdrawal_threshold_calibrator.py \
     --events-log /var/lib/xai/monitoring/withdrawals_events.jsonl \
     --locks-file /var/lib/xai/data/time_locked_withdrawals.json
   ```
3. Update the repository variables (`WITHDRAWAL_RATE_THRESHOLD`, `TIMELOCK_BACKLOG_THRESHOLD`) and mirror the change in `prometheus/alerts/security_operations.yml`.
4. Redeploy staging, confirm the new summary recommends values near the configured thresholds, then promote to production.

## Dashboard

View current status: Open `SECURITY-DASHBOARD.md`

- **Security Score**: 0-100
- **Recent Scans**: Status and results
- **Vulnerabilities**: By severity level
- **Trends**: 30-day analysis

## Troubleshooting

### Tools Not Working

```bash
# Reinstall tools
pip install --upgrade bandit safety pip-audit semgrep

# Check versions
bandit --version
safety --version
pip-audit --version
semgrep --version
```

### Pre-commit Issues

```bash
# Reinstall hooks
pre-commit install --install-hooks

# Check configuration
pre-commit validate-config

# Run test
pre-commit run --all-files
```

### Report Not Generated

```bash
# Check directory exists
mkdir -p security_reports

# Check permissions
ls -la security_reports/

# Run scan with verbose output
python scripts/security_monitor.py --mode standard
```

## Emergency Response

### Critical Vulnerability Found

1. **Assess Impact**
   ```bash
   # Review the finding
   cat security_reports/security_report_*.json | grep -A5 "critical"
   ```

2. **Create Branch**
   ```bash
   git checkout -b fix/security-issue
   ```

3. **Implement Fix**
   - Address the vulnerability
   - Add tests
   - Update dependencies if needed

4. **Verify Fix**
   ```bash
   python scripts/security_monitor.py --mode quick
   ```

5. **Create PR**
   - Mark as critical fix
   - Request immediate review
   - Link to security issue

## Integration with CI/CD

The GitHub Actions workflow automatically:
- ✅ Runs on every push
- ✅ Runs on every PR
- ✅ Runs daily at 02:00 UTC
- ✅ Runs weekly comprehensive scan
- ✅ Creates issues for critical findings
- ✅ Updates security dashboard

## Best Practices Checklist

- [ ] Review findings regularly
- [ ] Fix critical issues immediately
- [ ] Keep dependencies updated
- [ ] Run pre-commit hooks before committing
- [ ] Use strong passwords/tokens
- [ ] Rotate credentials regularly
- [ ] Document exceptions
- [ ] Track remediation efforts

## Performance Tips

### Make Scans Faster

```bash
# Skip certain checks
bandit -r src/ -ll --skip B101,B601

# Run in parallel
python scripts/security_monitor.py --mode quick

# Use cached results
# (Configure in .security/config.yml)
```

### Exclude False Positives

Edit `.bandit`:
```ini
[bandit]
exclude_dirs = ['/test/']
skips = B101
```

## Getting Help

1. **Check Documentation**
   - [Security Monitoring Guide](SECURITY-MONITORING-GUIDE.md)
   - [Main README](../README.md)

2. **Check Issues**
   - Search existing GitHub issues
   - Filter by `security` label

3. **Check Logs**
   - `security_monitor.log` for script errors
   - GitHub Actions logs for CI/CD issues

4. **Contact Team**
   - security@xai.crypto
   - Create confidential security issue

## Key Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Security Score | 90+ | TBD |
| Critical Issues | 0 | 0 |
| High Issues | <5 | 0 |
| Medium Issues | <20 | 0 |
| Scan Frequency | Daily | Yes |

## Tools Information

| Tool | Purpose | Frequency |
|------|---------|-----------|
| Bandit | Python security | Every push |
| Safety | Dependencies | Daily |
| pip-audit | Packages | Daily |
| Semgrep | Static analysis | Weekly |
| CodeQL | Code analysis | Every PR |
| Trivy | Filesystem | Weekly |

## Next Steps

1. **Setup**: Follow [SECURITY-MONITORING-GUIDE.md](SECURITY-MONITORING-GUIDE.md)
2. **Configure**: Update `.security/config.yml` for your needs
3. **Run**: Execute `python scripts/security_monitor.py --mode standard`
4. **Review**: Check `SECURITY-DASHBOARD.md` for results
5. **Integrate**: Enable GitHub Actions workflow
6. **Monitor**: Set up alerts and notifications

---

**Last Updated**: 2025-11-18
**Quick Reference v1.0**
