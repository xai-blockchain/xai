# QUIC Transport Errors Runbook

Alerts:
- `P2PQuicErrors` (`increase(xai_p2p_quic_errors_total[5m]) > 0`, warning)
- `P2PQuicDialTimeouts` (`increase(xai_p2p_quic_timeouts_total[5m]) > 3`, critical)

## Triage
- Check QUIC service health: `kubectl get svc xai-blockchain-quic -n <ns>`; confirm UDP port is exposed.
- Confirm dial timeout is locked down: `XAI_P2P_QUIC_DIAL_TIMEOUT` defaults to `1.0` (staging) and should stay <= `1.0` in prod unless overrides are justified by soak data.
- Inspect pod logs for `QUIC` or `aioquic` errors on listeners/clients.
- Verify ConfigMap: `XAI_P2P_ENABLE_QUIC` should be `1` only where QUIC is supported and tested (staging by default).
- Ensure certificates/ALPN match (`xai-p2p`) and that `aioquic` is installed on the image.

## Remediation
- Restart pods after config changes: `kubectl rollout restart statefulset/xai-blockchain-node -n <ns>`.
- For repeated dial timeouts, tighten the timeout further (e.g., `0.75`) only if soak/latency tests still pass, or disable QUIC until UDP reachability is confirmed.
- If network path blocks UDP, temporarily disable QUIC by setting `XAI_P2P_ENABLE_QUIC=0` in ConfigMap and reloading pods.
- Validate metrics after remediation:
  - `curl -s localhost:9090/metrics | grep xai_p2p_quic_errors_total`
  - `curl -s localhost:9090/metrics | grep xai_p2p_quic_timeouts_total`
  Counters should stop increasing once the path is healthy.

## Validation
- Run `k8s/verify-deployment.sh --namespace=<ns>` to ensure QUIC service present when enabled and metrics exported.
- Run `k8s/verify-monitoring-overlays.sh --namespace=<monitoring-ns>` to confirm Alertmanager has `p2p.*` routes and Grafana renders QUIC error/timeout panels. Query `/api/v2/alerts` for `P2PQuic*` after firing a synthetic alert if needed.
- Execute QUIC integration test locally with `pytest tests/xai_tests/integration/test_p2p_quic_optional.py -q` (with `aioquic` installed).
