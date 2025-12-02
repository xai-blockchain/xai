# Performance Alerts

- Monitor `benchmarks/crypto_report.json` in CI; alert when:
  - `signature_verify_avg_ms` increases > 50% vs baseline.
  - `block_header_serialize_avg_ms` increases > 50% vs baseline.
- Hook into CI to compare current run against a stored baseline artifact; fail build on regression.
- Optional: push perf metrics into Prometheus and alert on trend regression.
