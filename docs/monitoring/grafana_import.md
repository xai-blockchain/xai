# Grafana Dashboard Import & Verification Guide

Use this runbook after updating any JSON inside `monitoring/dashboards/grafana/` or the production overrides. It ensures staging and production Grafana stay in sync and that the new panels are wired to the correct Prometheus metrics.

## 1. Prepare the JSON

1. Validate the JSON locally (example uses VS Code or `jq`):
   ```bash
   jq empty monitoring/dashboards/grafana/aixn_security_operations.json
   jq empty monitoring/dashboards/grafana/production/aixn_security_operations.json
   ```
2. Commit the JSON into git so the dashboard version is traceable (`git describe --tags` is recorded as the Grafana dashboard version).

## 2. Import into Grafana

Repeat the following for **staging** (use the base JSON) and **production** (use the `production/` JSON):

### Option A – CLI

Use the helper script to import via Grafana’s API (requires a token with `dashboards:write`):

```bash
export GRAFANA_API_TOKEN="..."  # or pass via --api-token
python scripts/tools/import_grafana_dashboard.py \
    --grafana-url https://grafana.staging.example.com \
    --dashboard-file monitoring/dashboards/grafana/aixn_security_operations.json \
    --folder-uid security-ops \
    --overwrite \
    --message "Import $(git rev-parse --short HEAD)"
```

Repeat for production using the `production/aixn_security_operations.json` file. The script prints the dashboard UID and version returned by Grafana for auditing.

### Option B – Grafana UI

1. Login to Grafana with an account that has “Edit” permissions for the *Security Operations* folder.
2. Navigate to **Dashboards → Import**.
3. Upload the JSON file:
   - Staging: `monitoring/dashboards/grafana/aixn_security_operations.json`
   - Production: `monitoring/dashboards/grafana/production/aixn_security_operations.json`
4. Select the correct folder (**Security Operations**) and Prometheus data source (usually named `Prometheus`).
5. Click **Import**. Grafana now stores the dashboard revision with the import timestamp.

## 3. Verify Panels & Metrics

The new withdrawal processor widgets depend on the following Prometheus metrics:

| Panel | Metric |
| --- | --- |
| Withdrawal Processor Queue Depth (stat panel) | `xai_withdrawal_pending_queue` |
| Withdrawal Processor Outcomes (24h) | `xai_withdrawal_processor_completed_total`, `xai_withdrawal_processor_flagged_total`, `xai_withdrawal_processor_failed_total` |

Verify in **staging** first:

```bash
PROM_URL="https://prometheus.staging.example.com"
TOKEN="$PROM_TOKEN"  # optional Bearer token

curl -s -H "Authorization: Bearer $TOKEN" \
  "$PROM_URL/api/v1/query?query=xai_withdrawal_pending_queue"

curl -s -H "Authorization: Bearer $TOKEN" \
  "$PROM_URL/api/v1/query?query=rate(xai_withdrawal_processor_completed_total[5m])"
```

Ensure the responses are HTTP 200 with non-empty data arrays. Repeat against the production Prometheus endpoint after staging passes review.

## 4. Functional Checks

1. Open the updated dashboard and filter the time range to the previous 24 hours.
2. Confirm:
   - The **Queue Depth** panel displays a numeric stat, not `N/A`.
   - The **Outcomes (24h)** panel shows three series (completed, flagged, failed). Even if they are zero, each legend entry should exist.
3. Hover over the graph to verify tooltips show Prometheus data values rather than “No data”.
4. Export the dashboard JSON from Grafana and diff it with the repository version to confirm no unexpected changes were auto-applied by Grafana (layout drift, UID changes, etc.).

## 5. Document the Import

Update `docs/security/withdrawal_processing.md` (or relevant ops runbook) with the Grafana import timestamp and dashboard UID so future engineers know the last verified version.

Example snippet to append to the ops journal:

```
2026-02-15 – Imported aixn_security_operations.json (commit abc1234) into staging/prod.
Verified xai_withdrawal_pending_queue and xai_withdrawal_processor_* metrics render correctly.
```
