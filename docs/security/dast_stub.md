# DAST Automation Stub

## ZAP Baseline Example (non-prod)

```bash
docker run --rm -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable zap-baseline.py \
  -t http://app:8546 \
  -x zap-report.xml -J zap-report.json \
  -m 5 -r zap-report.html \
  -I
```

## CI Integration (nightly)
- Run in staging/non-prod only.
- Use test API keys; never production secrets.
- Upload `zap-report.json`/`zap-report.html` as artifacts.
- Fail on HIGH/MEDIUM findings; document accepted risks.
