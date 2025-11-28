# DAST Guidance

- Run OWASP ZAP (baseline) against the API in non-production:
  - Target the RPC/API endpoints; exclude `/metrics`.
  - Fail on high/medium findings; document accepted risks.
- Include P2P endpoints only in isolated environments to avoid disrupting validators.
- Automate in CI (nightly) with a slim container; store HTML/JSON reports as artifacts.
- Sanitize secrets: use test API keys and non-production wallets.
- Combine with SAST (semgrep/bandit) and dependency audits for full coverage.
