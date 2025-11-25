# Upgrade and Migration Strategy

This document captures the gating, migration, and rollback playbooks required before promoting any protocol change, configuration migration, or new client to production. It assumes the governance enforcement flow described in `docs/runbooks/GOVERNANCE_ENFORCEMENT_RUNBOOK.md` governs every upgrade.

## Objectives

- Keep deterministic state accessible via `state_snapshot.py` so rollbacks can restore validators exactly as they were before changes.
- Ensure every upgrade is wrapped by an approved governance proposal and accompanied by regression coverage for API, security, and monitoring guardrails.
- Roll out upgrades through staging/canary tiers and monitor with the same counters/alerts (`monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md`, `prometheus/alerts/blockchain_alerts.yml`).

## Version gating & governance checkpoints

1. Draft a governance proposal referencing `docs/architecture/MODULE_REGISTRY.md` so reviewers know which module, parameter, or feature is targeted.
2. Submit votes via `/governance/vote` and rely on `GovernanceState` thresholds (`min_voters`, `approval_percent`, `max_individual_power_percent`).
3. After the proposal is approved, publish code and plan in the same issue/PR, linking to `docs/architecture/SMART_CONTRACT_IMPLEMENTATION_PLAN.md` for smart-contract rollouts or `docs/architecture/VM_SPEC.md` for opcode changes.
4. Gate execution behind the smart contract feature flag or module registry entry to prevent unapproved activation.

## Storage & data migration

- Snapshot the chain (`scripts/tools/state_snapshot.py`, `docs/runbooks/STATE_SNAPSHOT_RUNBOOK.md`) before making on-disk migrations.
- Any schema change to `blockchain_storage.py`, consensus data, or wallet caches must include a migration script and a compatibility flag for nodes running old binaries.
- Maintain `migration_manifest.json` that records applied migrations, the proposal ID, and the hash of the `state_snapshot` used to verify rollbacks.
- Validate migrations by replaying `tests/xai_tests/unit/test_contract_governance.py` plus new tests that exercise the target storage path.

## Deployment rollout phases

1. **Staging/canary:** Deploy the new binary with `--data-dir` pointing at a snapshot directory. Use `scripts/tools/multi_node_harness.py` to ensure peer discovery, faucet flows, and governance endpoints behave as expected.
2. **Monitoring verification:** Confirm the security dashboard counters, withdrawal metrics, and governance execution logs remain healthy. Use `scripts/tools/verify_monitoring.py` to confirm dashboards/datasources respond before switching traffic.
3. **Production:** Gradually roll the release across validator nodes. Apply API gateway rules to drain connections from the node before restarting so there is no double spend window.
4. **Post-upgrade validation:** Re-run `tests/api/test_openapi_contract.py` using `[API_BASE_URL=http://localhost:8545]` to ensure schema drift has not occurred.

## Rollback & remediation

- If the upgrade fails post-deployment, trigger the governance rollback transaction (`GovernanceState.rollback_proposal`) and restore the snapshot recorded in `migration_manifest.json`.
- Ensure rollback is documented in the same governance ticket and note revisions to `AGENT_PROGRESS`/runbooks.
- Inform operators via the security webhook channel described in `MONITORING_GUIDE.md` so they can re-review Prometheus alerts and Loki logs.

## Communication & runbook links

- Announce the upgrade plan (proposal ID, expected activation height, risk areas) to validator operators via the same Slack/PagerDuty channels referenced in `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md` and `SECURITY.md`.
- Document any manual steps required for clients running alternate implementations inside `docs/CLIENT_DIVERSITY_ROADMAP.md` so they can synchronize releases.
- After verification, close the governance proposal and append a short summary to `docs/runbooks/HARDENED_MODULE_RUNBOOK_INDEX.md` (when staging validation is complete) so operators can trace the change history.
