# Operations Handbook Index

Documents the dashboards, alerts, CLI helpers, and remediation/runbook recipes operators need to observe, diagnose, and recover the hardened node stack.

## Dashboards & Metrics
- `dashboards/grafana/aixn_blockchain_overview.json` – top-line view of block height, production rate, TPS, peer count, and system resources; import instructions live in `prometheus/README.md` (Linux/Windows sections) and the Docker stack quick start in `monitoring/README.md`.
- `dashboards/grafana/aixn_network_health.json` – peer connectivity, latency percentiles, bandwidth, and message mix; referenced by the `Network Health` chapter of `prometheus/README.md`.
- `dashboards/grafana/aixn_api_performance.json` – API request rates, p50/p95/p99 latencies, and error breakdowns per endpoint; described in the `API Performance` section of `prometheus/README.md`.
- `dashboards/grafana/aixn_security_operations.json` – security event rate, webhook delivery lag, API key audit stream, and peer-auth coverage panels; the layout and PromQL targets are explained in `MONITORING_GUIDE.md` alongside `prometheus/alerts/security_operations.yml`.
- `dashboards/grafana/aixn_withdrawal_threshold_history.json` – staging threshold history (recommended vs. configured rates/backlogs) plus Promtail/Loki ingestion guidance from `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md`.
- `dashboards/grafana/production/aixn_withdrawal_threshold_history.json` – production copy that binds to the production Loki datasource so historical threshold artifacts appear in prod Grafana; the same runbook describes the Promtail mounts and Grafana import steps.

## Alerts & Escalations
- `monitoring/prometheus_alerts.yml` – canonical production rules for node availability, network health, block production, transaction throughput, system limits, API health, mining/validation events, and supply anomalies; `monitoring/README.md` walks through the stack, the Alertmanager config, and the runbook links embedded in the annotations.
- `prometheus/alerts/blockchain_alerts.yml` – development/test alert pack that mirrors the same categories plus AI/chain integrity rules; the `prometheus/README.md` sections on alert configuration and Alertmanager setup refer operators back to this file for exports.
- `prometheus/alerts/security_operations.yml` – security-specific rule group that translates `xai_security_events_*` counters into Alertmanager notifications; `MONITORING_GUIDE.md` lists the metrics, counters, and expected Loki/Grafana panels that consume these alerts.
- `monitoring/alertmanager.yml` – routing rules for Slack, PagerDuty, and email grouped by severity/service; documented in `monitoring/README.md` (see “AlertManager Configuration” and Notification templates).
- `monitoring/alert_templates.tmpl` – Slack/PagerDuty/Email templates referenced by `alertmanager.yml` so every alert includes actionable context and links back to the relevant runbook.

## CLI Tools
- `scripts/tools/manage_api_keys.py` – list/issue/revoke scoped admin/user keys, stream the audit log, and bootstrap admin secrets; referenced directly from `SECURITY_AUDIT_CHECKLIST.md` and `PRODUCTION_READINESS_CHECKLIST.md` in the new admin workflow.
- `scripts/tools/security_audit_notifier.py` – nightly `pip-audit`, `bandit`, and `pytest` runner that posts summaries to Slack/Jira; the `SECURITY_AUDIT_CHECKLIST.md` and `.github/workflows/nightly-security-audit.yml` describe how the notifier integrates with the broader security workflow.
- `scripts/tools/multi_node_harness.py` – spins up isolated nodes with `--data-dir`, warms up peers/faucet flows, and exercises `/blocks`, `/peers`, and `/faucet/claim` to validate consensus; operators follow `docs/runbooks/MULTI_NODE_HARNESS.md` for the recommended staging checks.
- `scripts/tools/state_snapshot.py` – captures/verifies/restores deterministic state snapshots with manifest hashes so rollbacks and audits can replay known-good states; see `docs/runbooks/STATE_SNAPSHOT_RUNBOOK.md` for the capture checklist, verification steps, and restore guidance.
- `scripts/tools/withdrawal_threshold_calibrator.py` – emits percentile-based threshold recommendations and the `alert_required` flag; the `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md` explains how this CLI feeds the Grafana dashboard, Promtail/Loki ingestion, and the artifact workflow.
- `scripts/tools/threshold_artifact_ingest.py` – normalizes threshold artifacts, prunes the append-only history, and writes Markdown summaries consumed by dashboards/alerts; again, `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md` describes the ingestion knobs (`--max-history-entries`) and history location.
- `scripts/tools/threshold_artifact_publish.py` – publishes the Markdown summaries to Slack, PagerDuty, GitHub issues, or Jira hooks; the runbook lists the environment variable knobs and verification steps for the downstream automation.
- `scripts/tools/withdrawal_alert_probe.py` – probes `/admin/withdrawals/telemetry` (rate, backlog, recent actors) and supplements alerts with offender context; usage notes live in `MONITORING_GUIDE.md` under the withdrawal telemetry sections.
- `scripts/tools/verify_monitoring.py` – sanity-checks that Prometheus/Loki/Grafana endpoints respond and that the dashboard JSON files import (some CLI targets iterate through `dashboards/grafana/*.json`); `MONITORING_GUIDE.md` and `monitoring/README.md` describe when to plug this into deployment automation.
- `scripts/tools/ai_inspect.py` & `scripts/tools/ai_alert.py` – AI bridge observability helpers (`ai_inspect` dumps status/metrics, `ai_alert` posts to optional webhooks when tokens spike); `docs/runbooks/AI_MONITORING.md` documents flags, thresholds, and expected webhook payloads.
- `scripts/tools/run_monitoring.sh`, `scripts/tools/start_monitoring.sh`, and `scripts/tools/start_monitoring.ps1` – wrappers that run the AI inspect/alert loop every 5 minutes so Prometheus rules like `AITokensHigh` can be verified; `docs/runbooks/AI_MONITORING.md` explains scheduling options and Alertmanager hooks.

## Playbooks & Runbooks
- `monitoring/README.md` – hardware/software quick start, stack composition, Grafana import steps, Prometheus queries, and troubleshooting commands for the entire stack.
- `MONITORING_GUIDE.md` – deep dive into the security operations dashboard, Prometheus counters (`xai_security_events_*`), withdrawal telemetry endpoint, webhook forwarding, Slack/PagerDuty hooks, and Alertmanager routing.
- `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md` – step-by-step checklist for Promtail mounts, Grafana imports, threshold artifact ingestion, Slack/PagerDuty publications, and the `withdrawal_threshold_history.jsonl` monitoring that operators rely on.
- `SECURITY_AUDIT_CHECKLIST.md` – nightly audit workflow (pip-audit + bandit + pytest), Slack/Jira notifier integration, and how to surface the summarized findings for leadership.
- `PRODUCTION_READINESS_CHECKLIST.md` – documents the admin bootstrap/watch workflow plus the verification steps for API key lifecycle event logging so the runbook indexes the latest hardened guardrails.
- `SECURITY_DEPLOYMENT-GUIDE.md` – API key bootstrapping, vulnerability disclosure channels, and emergency response guidance for hardened endpoints.
- `SECURITY.md` – vulnerability disclosure/bug bounty policy with contact instructions, expected timelines, and reporting guidance.
- `docs/runbooks/KEY_MANAGEMENT_RUNBOOK.md` – API/peer/admin key lifecycle, HSM/vault usage, backup/rotation, and CLI anchor points in `APIKeyStore`.
- `docs/runbooks/MULTI_NODE_HARNESS.md` – consensus validation playbook tied to `scripts/tools/multi_node_harness.py`, peer bootstrapping, and faucet checks before promoting to staging.
- `docs/runbooks/STATE_SNAPSHOT_RUNBOOK.md` – snapshot capture, manifest verification, and restore paths so operators can pin deterministic state before/after critical fixes.
- `docs/runbooks/AI_MONITORING.md` – AI bridge telemetry/runbook summary for the helper scripts, webhooks, and the monitoring loop so operators keep the AI metrics in scope.
- `docs/architecture/SMART_CONTRACT_IMPLEMENTATION_PLAN.md` & `docs/architecture/VM_SPEC.md` – governance and VM rollout references that operators consult before gating new module/contract functionality behind governance votes.

## Notes
- Keep this index in sync with `AGENT_PROGRESS` and the dashboards/alerts/CLIs it references; add an entry whenever a new dashboard JSON, alert rule, or remediation helper lands so engineers can immediately point operators to the right source of truth.
