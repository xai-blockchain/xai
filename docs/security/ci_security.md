# CI Security Gates

- **Static Analysis:** Semgrep (`scripts/ci/run_p2p_checks.sh` hook) and Bandit via pre-commit/CI.
- **Dependency Audits:** `pip-audit` via pre-commit; installs pinned with `constraints.txt`.
- **P2P Hardening Checks:** `scripts/ci/p2p_hardening_check.sh` fails builds on missing envs/trust stores.
- **Security Tests:** P2P-focused pytest subset in `scripts/ci/run_p2p_checks.sh`.
- **Perf Guardrails:** `scripts/ci/perf_check.py` with artifact `benchmarks/crypto_report.json`.
- **Optional SIEM Probe:** `scripts/ci/smoke_siem_webhook.sh` when webhook envs set.

Recommended additions:
- DAST smoke (e.g., OWASP ZAP) against API in non-prod.
- Periodic dependency report artifact from `pip-audit` or `safety`.
- Governance/consensus invariant tests (difficulty bounds, nonce progression) in CI.
- Capture perf trend over time; alert on regression vs baseline.
- Optional perf regression gating: compare `benchmarks/crypto_report.json` against a stored baseline and fail on >50% regression.
