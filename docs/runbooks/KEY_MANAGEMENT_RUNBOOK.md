# Key Management & Rotation Runbook

This runbook explains how operators provision, rotate, revoke, and audit every API-facing secret in the XAI blockchain stack.  It covers the HTTP API keys that gate public routes, the scoped admin keys that unlock `/admin/*` endpoints, and the shared peer key that signs inter-node gossip.  All procedures map directly to the reference implementation in:

- `src/xai/core/api_auth.py` (APIKeyStore + APIAuthManager)
- `src/xai/core/node_api.py` (admin key issuance/deletion endpoints)
- `scripts/tools/manage_api_keys.py` (CLI wrapper for offline ops)
- `Config` variables in `src/xai/core/config.py` (paths, feature flags)

## 1. Key Types & Storage

| Key | Scope | Where it lives | Notes |
| --- | --- | --- | --- |
| **User API key** | Grants access to `/send`, `/wallet/*`, `/peer` routes when `XAI_API_AUTH_REQUIRED=1`. | `secure_keys/api_keys.json` (overridable via `XAI_API_KEY_STORE`). | Issued via CLI or `/admin/api-keys` with scope `user`. |
| **Admin API key** | Required for `/admin/*` (key lifecycle, telemetry, withdrawal tooling). | Same store; records include `{"scope": "admin"}`. | Usually seeded from `XAI_BOOTSTRAP_ADMIN_KEY` during bootstrap. |
| **Peer shared key** | Signs `/transaction/receive`, `/block/receive`, `/sync`, etc. between nodes. | Environment variable `XAI_PEER_API_KEY`; never written to disk by default. | Reference in `Config.PEER_API_KEY` and `NodeP2PNetworkManager._build_peer_headers()`. |
| **Bootstrap admin secret** | One-time admin credential for new clusters. | Environment variable `XAI_BOOTSTRAP_ADMIN_KEY` or supplied to the CLI. | Immediately persisted as an admin key via `manage_api_keys.py bootstrap-admin`. |

All persistent stores sit on disk as prettified JSON accompanied by an append-only audit log (`<store>.log`).  The store path MUST reside on an encrypted volume (LUKS, dm-crypt, LUKS-on-LVM, BitLocker, etc.) or on an HSM-backed filesystem mount.

## 2. Required Environment & Filesystem Controls

1. Set `XAI_API_KEY_STORE=/opt/xai/secrets/api_keys.json` (or your secure path).
2. Mount the directory with `0700` permissions owned by the node operator account.
3. Export `XAI_API_AUTH_REQUIRED=1` in every production node environment.
4. Export `XAI_PEER_API_KEY` to the same value on every validator participating in gossip.
5. For HSM/Vault-backed deployments, bind-mount the decrypted secret file into the container/VM so that the node sees a regular file path (the reference code only uses filesystem IO).

## 3. Tooling Overview

- **CLI (`scripts/tools/manage_api_keys.py`)**
  - `list` – inspect stored metadata without revealing plaintext keys.
  - `issue --scope user|admin` – emits plaintext + hashed id.
  - `revoke <key_id>` – removes key, writes audit log, increments Prometheus counters via `log_security_event`.
  - `events --limit N` – dumps audit history (mirrors `/admin/api-key-events`).
  - `watch-events` – tails the audit log for SOC/SecOps streaming.
  - `bootstrap-admin --secret <value>` – saves a pre-provisioned admin token without generating a new random key.
- **HTTP Admin API (`/admin/api-keys`, `/admin/api-key-events`)**
  - Protected by admin-scope API keys; intended for automation (e.g., CI/CD generating per-service credentials).
  - Returns plaintext when issuing keys; clients must capture once and store securely.
- **Security telemetry**
  - `log_security_event("api_key_audit", …)` entries flow to Prometheus (`xai_security_events_total`) and webhook publishers.  SOC teams should confirm alerts fire whenever keys are issued or revoked outside a planned window.

## 4. Standard Rotation Workflow

1. **Preparation**
   - Confirm maintenance window and downstream consumers (wallet services, explorers).
   - Run `python scripts/tools/manage_api_keys.py list` to snapshot current key IDs.
   - Ensure promtail/Loki and webhook sinks are healthy so audit events are captured.
2. **Issue replacement key**
   - Run `python scripts/tools/manage_api_keys.py issue --label "<service>-2024-rotation" --scope user`.
   - Copy the returned `api_key` into a hardware security module, password manager, or secret manager (HashiCorp Vault, AWS Secrets Manager, etc.).
   - Record the `key_id` hash for future revocation.
3. **Distribute**
   - Update client deployments (CI/CD secrets, Kubernetes Secrets, systemd drop-ins) with the new plaintext key.
   - For peer nodes, update `XAI_PEER_API_KEY` simultaneously across all validators.  Because the peer requests use a single shared value, perform this as a coordinated change to avoid temporary gossip failures.
4. **Validate**
   - Hit `/send` or `/peers/add` using the new credential and confirm a 200 response.
   - Monitor `xai_security_events_total{event="api_key_audit"}` and `withdrawal telemetry` dashboards to verify the event was recorded.
5. **Revoke old key**
   - After confirming all clients flipped, revoke via `python scripts/tools/manage_api_keys.py revoke <old_key_id>` or `DELETE /admin/api-keys/<key_id>`.
   - Watch the audit stream (`watch-events`) or `/admin/api-key-events?limit=10` for the corresponding `revoke` action.
6. **Document**
   - Append the rotation details to your ops change log (who, when, why, related ticket).

## 5. Emergency Rotation (Compromise Response)

1. Trigger the incident response playbook and freeze external API access (set `XAI_API_AUTH_REQUIRED=1` if not already, and temporarily firewall `/admin/*` to VPN networks only).
2. Revoke the suspected key ID(s) immediately.
3. Issue fresh keys with the `--label compromised-<ticket>` naming convention so downstream parsers can spot them.
4. Force a redeploy of every client using environment-specific secret stores.
5. Rotate the peer shared key by updating `XAI_PEER_API_KEY` on every validator and restarting the node processes so the new header is applied.
6. Verify `SecurityEventRouter` webhooks fired to Slack/PagerDuty and that Grafana alert histories show the compromise.

## 6. Backup & Recovery

The API key store is a single JSON document plus an append-only `.log`.  These files must be backed up daily using encrypted, access-controlled tooling (e.g., restic, Velero, AWS Backup) with the following guarantees:

- Never copy plaintext keys into ticketing systems or chat.
- Use OS-level ACLs to restrict backup jobs to a minimal service account.
- On restore, stop the node, replace `api_keys.json` + log, restart, and run `manage_api_keys.py list` to confirm integrity.
- After restoration, run `scripts/tools/manage_api_keys.py watch-events --limit 20` to ensure no unexpected issues occurred while the store was offline.

## 7. HSM / Vault Integration

While the reference implementation expects filesystem storage, you can harden deployments by:

1. Generating keys within the HSM (AWS CloudHSM, Azure Key Vault) and copying only the hashed `key_id` into `api_keys.json`.  Use the CLI’s `--plaintext` plumbing (see `APIKeyStore.issue_key(..., plaintext=secret)`) to persist the server-side hash while keeping plaintext in the HSM.
2. Mounting a decrypted view of the store via `gpgfs`, eCryptfs, or a Vault Agent sidecar that writes the JSON onto an in-memory filesystem exposed to the node container.
3. Leveraging the audit log to cross-check the HSM’s own audit feed so that mismatched events surface immediately.

## 8. Monitoring & Compliance Checklist

- ✅ `xai_security_events_total` counters increase for every issue/revoke.
- ✅ Grafana’s Security Operations dashboard (see `dashboards/grafana/aixn_security_operations.json`) shows the latest rotation events.
- ✅ Alertmanager routes (`prometheus/alerts/security_operations.yml`) fire if an admin key is issued outside a change window or if revocations spike.
- ✅ `scripts/tools/manage_api_keys.py watch-events` is running (or supervised) on at least one bastion host, shipping logs to SIEM.
- ✅ `PEER_AUTH_BOOTSTRAP.md` procedure is cross-referenced during new validator onboarding.

Keeping this runbook up to date, and executing it for every credential lifecycle event, ensures the hardened API/authentication layers remain trustworthy ahead of mainnet launch.
