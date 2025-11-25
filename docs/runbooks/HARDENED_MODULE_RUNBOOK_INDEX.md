# Hardened Module & Monitoring Runbook Index

This index ties every hardened subsystem (`src/xai/core` modules, API guards, telemetry) to the operational runbooks, dashboards, and verification scripts operators and devs now rely on when the staging chaos/stress suites complete.

## Security & Operations Modules
- **API guards / P2P limits / wallet controls**: documented in `MONITORING_GUIDE.md`, `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md`, and covered by `tests/alerting/test_security_operations_alerts.py`. Operational scripts include `scripts/tools/withdrawal_threshold_calibrator.py`, `scripts/tools/withdrawal_alert_probe.py`, and the AI monitoring helpers described in `docs/runbooks/AI_MONITORING.md`.
- **API key lifecycle / audit logging**: `docs/runbooks/KEY_MANAGEMENT_RUNBOOK.md` plus `scripts/tools/manage_api_keys.py` and the nightly audit workflow (`.github/workflows/nightly-security-audit.yml`, `scripts/tools/security_audit_notifier.py`) document issuance/revocation, audit streaming, and abuse notification.
- **Monitoring+alerts**: `monitoring/README.md`, `MONITORING_GUIDE.md`, `prometheus/alerts/security_operations.yml`, and the Grafana dashboards (`dashboards/grafana/aixn_*`) anchor the production telemetry story; `scripts/tools/verify_monitoring.py` confirms the stack before deployments.

## Governance & Smart-Contract Guardrails
- **Governance enforcement**: `docs/runbooks/GOVERNANCE_ENFORCEMENT_RUNBOOK.md` explains the on-chain proposal/vote/execution chain, `docs/architecture/MODULE_REGISTRY.md` maps modules to governance controls, and the execution engine code resides in `src/xai/core/governance_execution.py`. The `docs/architecture/SMART_CONTRACT_IMPLEMENTATION_PLAN.md` and `docs/architecture/VM_SPEC.md` describe the rollout phases referenced by the governanced modules in `AGENT_PROGRESS`.
- **Upgrade/runbook orchestration**: `UPGRADE.md` captures storage migrations, staging rollouts, and the requirement to snapshot state (`scripts/tools/state_snapshot.py`, `docs/runbooks/STATE_SNAPSHOT_RUNBOOK.md`). The consolidated index ensures future upgrades reference these artifacts before writing new modules.

## Performance/Stress Verification
- **Stress validation**: `scripts/tools/run_performance_stress_suites.sh` runs the transactional/throughput/resilience batches, while `scripts/tools/run_performance_stress_heavy_suites.sh` covers the memory/resource and reorg stress tests; `docs/STRESS_TEST_QUICK_REFERENCE.md` documents them so QA reruns the suite after each deployment.
- **Contract tests**: `tests/api/test_openapi_contract.py` plus the schemathesis dependency guard the OpenAPI contract defined in `docs/api/openapi.yaml`, ensuring any new module surfaces in the API spec before deployment.

## Notes
- Keep this index aligned with `AGENT_PROGRESS`—the staged stress validation, consolidated runbooks, and monitoring/runbook docs drive the remaining task list. After every major subsystem change, update this index so operators can trace the hardened module → dashboard → runbook chain without guessing.
