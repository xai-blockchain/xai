# Withdrawal Threshold Telemetry Runbook


## 1. Prerequisites

- `scripts/tools/withdrawal_threshold_calibrator.py`, `threshold_artifact_ingest.py`, and `threshold_artifact_publish.py` are available in the deployment image (already baked into `main`).
- The node has write access to `monitoring/withdrawal_threshold_history.jsonl` (default location inside `/var/lib/xai/`).
- Promtail/Loki stack is reachable from the host.
- Grafana has access to the Loki data source named `Loki`.

## 2. Configure Threshold Artifact Publishing

   - Repository variable: `WITHDRAWAL_CALIBRATION_ISSUE` → the issue number that should receive comments.

2. **Slack (optional)**
   - Secret: `WITHDRAWAL_CALIBRATION_SLACK_WEBHOOK`.
   - Channel: create a dedicated `#withdrawal-runbooks` (or equivalent) channel and generate a webhook scoped to it.

3. **Jira (optional)**
   - Variable: `WITHDRAWAL_CALIBRATION_JIRA_ISSUE` (e.g., `SEC-201`).
   - Secrets: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`.
   - Permissions: the API token must have comment permissions on the chosen issue.

4. **History Retention**
   - `threshold_artifact_ingest.py --max-history-entries 500` (default in staging) truncates the JSONL file automatically.
   - Adjust the value via the workflow step or run `python scripts/tools/threshold_artifact_ingest.py ... --max-history-entries <N>` in a cron job if you need longer retention.

## 3. Enable Promtail Shipping

1. On the host running promtail, mount the history file:

```yaml
volumes:
  - /var/lib/xai/monitoring:/var/lib/xai/monitoring:ro
```

2. Add the scrape job (adapt the path if necessary) to `promtail-config.yml`:

```yaml
  - job_name: withdrawal-threshold-history
    static_configs:
      - targets: [localhost]
        labels:
          job: withdrawal_threshold_history
          __path__: /var/lib/xai/monitoring/withdrawal_threshold_history.jsonl
    pipeline_stages:
      - json:
          expressions:
            generated_at: generated_at
            environment: environment
            recommended_rate: recommended_rate
            recommended_backlog: recommended_backlog
            current_rate_threshold: current_rate_threshold
            current_backlog_threshold: current_backlog_threshold
            alert_required: alert_required
      - timestamp:
          source: generated_at
          format: RFC3339Nano
      - labels:
          environment:
          alert_required:
```

3. Restart promtail: `docker compose restart promtail` (or equivalent systemd command).

4. Verify ingestion using Loki:

```bash
curl -G "https://<loki>/loki/api/v1/query_range" \
  --data-urlencode 'query={job="withdrawal_threshold_history",environment="production"}' \
  --data-urlencode "start=$(date -u -d '1 hour ago' +%s)000000000" \
  --data-urlencode "end=$(date -u +%s)000000000"
```

## 4. Grafana Dashboard

1. Import `dashboards/grafana/production/aixn_withdrawal_threshold_history.json` (identical to the staging dashboard but pre-labeled for production) into the “Security Operations” folder.
2. Update panel defaults if your Loki datasource uses a non-default name.
3. Grant `Viewer` access to the operations/security teams.

## 5. Verification Checklist

- [ ] `monitoring/withdrawal_threshold_history.jsonl` exists on the target host and rotates automatically (file size stays stable).
- [ ] Loki query returns entries for the new environment.
- [ ] Grafana dashboard shows the latest deploy with correct environment selection.

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| History file not created | Workflow missing `threshold_details.json` (calibrator failure) | Inspect the “Withdrawal threshold summary” step logs, repair secrets (`STAGING_WITHDRAWAL_EVENTS_LOG`, `STAGING_TIMELOCK_FILE`). |
| Loki has no data | Promtail path incorrect or file not mounted | Confirm promtail container can read `/var/lib/xai/monitoring/withdrawal_threshold_history.jsonl`, check promtail logs for JSON parse errors. |
| Slack/Jira misses updates | Secret/variable unset | Verify repository secrets/variables, rerun workflow manually after setting them. |
| File grows too large | Retention not configured | Add/adjust `--max-history-entries` (default 500) or run a nightly cron that truncates the JSONL file. |

## 7. Manual Replay

If you need to regenerate history or republish old runs:

```bash
python scripts/tools/threshold_artifact_ingest.py \
  --details artifacts/run-123/threshold_details.json \
  --history-file /var/lib/xai/monitoring/withdrawal_threshold_history.jsonl \
  --environment production \
  --max-history-entries 500 \
  --markdown-output /tmp/threshold_summary.md \
  --print-markdown

python scripts/tools/threshold_artifact_publish.py \
  --details artifacts/run-123/threshold_details.json \
  --markdown /tmp/threshold_summary.md \
  --issue-number 1234 \
  --slack-webhook https://hooks.slack.com/... \
  --jira-base-url https://company.atlassian.net \
  --jira-issue-key SEC-201 \
  --jira-email ops@example.com \
  --jira-api-token <token>
```

This preserves history ordering (timestamps inside the JSON dictate chronology) and ensures external systems mirror the recalibration.

## 8. Production Adoption Checklist

Use this quick list whenever you roll the telemetry into a fresh production environment:

- [ ] **Promtail mount verified** – `/var/lib/xai/monitoring/withdrawal_threshold_history.jsonl` is mounted read-only into the promtail container or systemd service, and the `withdrawal_threshold_history` scrape job exists verbatim in `docker/monitoring/promtail/promtail-config.yml` (or your downstream override).
- [ ] **Production Grafana folder updated** – import `dashboards/grafana/production/aixn_withdrawal_threshold_history.json` (identical to the staging dashboard but tagged for production) into the “Security Operations” folder and wire it to the production Loki data source.
- [ ] **Verification CLI executed** – run `scripts/tools/verify_monitoring.py --environment production --history-dir /var/lib/xai/monitoring` and confirm both file checks and the Loki query succeed.
- [ ] **Fleet spot-check** – optionally append `--remote-host host1 --remote-host host2 --ssh-user ubuntu` so the CLI tails each node’s history file via SSH (requires public-key access or `WITHDRAWAL_SSH_KEY`).
