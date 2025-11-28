# Release Checklist

## Pre-Release
- CI green: hardening checks, security tests, perf guardrails.
- Trust stores updated and rolled; placeholder values removed.
- Run `k8s/verify-deployment.sh` in staging (P2P metrics + SIEM probe).
- Confirm NetworkPolicy CIDRs for target environment.
- Update versioned P2P supported versions (if changed) and document in `docs/api/p2p_handshake.md`.
- Dependency audit: `pip-audit`/`safety` clean; constraints updated if needed.
- Bench artifact captured; check for perf regressions.
- Run chaos/reorg tests and P2P security tests.

## Deployment
- Apply ConfigMap/Secrets updates (webhook, trust stores).
- Apply NetworkPolicy for environment.
- Rollout strategy: blue/green or canary; monitor P2P/security alerts.
- Verify SIEM/webhook ingest with probe.

## Post-Release
- Monitor P2P metrics/dashboards for 1–2 hours.
- Validate alerts fire/clear properly.
- Archive release notes with supported P2P version.
