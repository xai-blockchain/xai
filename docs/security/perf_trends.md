# Performance Trends

- Benchmarks: `scripts/ci/perf_check.py` writes `benchmarks/crypto_report.json`.
- CI uploads artifacts; monitor signature verify and block serialization latency.
- Add alerting on regression (compare against baseline stored artifact).
- Run periodically (nightly) to catch drifts in dependencies or code changes.
