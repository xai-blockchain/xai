# Peer Authentication Bootstrap Guide

Protecting `/transaction/receive` and `/block/receive` with API-key auth means peer nodes must attach a trusted key to every broadcast. This guide documents the minimal bootstrap required to keep the federation healthy once `XAI_API_AUTH_REQUIRED=1` is enabled.

## 1. Issue a peer-scoped API key on every receiving node

```bash
./scripts/tools/manage_api_keys.py issue --label peer-node-A --scope user
# => copy the "api_key" field – this is the only time it is shown
```

The key is stored (hashed) in `secure_keys/api_keys.json` and audit logged in `secure_keys/api_keys.json.log`.

## 2. Distribute the plaintext secret out-of-band

Send the one-time plaintext value to every upstream node that should be allowed to push blocks/transactions into this node. Treat it like any other shared secret (out-of-band channel, password vault, etc.).

## 3. Configure peers to attach the key automatically

On every node that must broadcast to others, export the secret via `XAI_PEER_API_KEY` so `P2PNetworkManager` can attach it to each POST:

```bash
export XAI_API_AUTH_REQUIRED=1        # enable inbound auth on this node
export XAI_PEER_API_KEY="<peer api key>"
./run_node.sh
```

Nodes can use different keys per downstream peer. Just repeat step 1 for each destination and configure the corresponding environment file/systemd unit to point at the right value.

## 4. Validate connectivity

- `tail -f secure_keys/api_keys.json.log` or run `./scripts/tools/manage_api_keys.py watch-events` while peers reconnect. You should see `"action": "issue"` or `"revoke"` entries appear.
- From a remote node, send a manual probe:

```bash
curl -X POST https://peer-A/transaction/receive \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $XAI_PEER_API_KEY" \
  -d '{"sender":"XAI...",...}'
```

If the key is missing or incorrect, the node responds with `401` and `code=unauthorized`.

## 5. Rotate peer keys safely

1. Issue a new key using step 1 (with a new `--label`).
2. Update `XAI_PEER_API_KEY` on every broadcaster and reload the service.
3. Run `./scripts/tools/manage_api_keys.py revoke <old_key_id>` on the receiver.

Because rotation events emit `api_key_audit` log entries, you can monitor the `xai.security` logger or ship the audit file into your SIEM to alert on unexpected changes.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Remote peers now get HTTP 401 after enabling auth | Ensure `XAI_PEER_API_KEY` is exported on the sending node and matches a key issued on the receiver |
| Audit log missing | Ensure the `secure_keys` directory is writable by the node process |
| Need to bootstrap without CLI access | Copy a pre-generated secret into `XAI_BOOTSTRAP_ADMIN_KEY` and run `./scripts/tools/manage_api_keys.py bootstrap-admin --label peer-seed` to persist it |

Keep this document with your deployment runbooks so on-call operators have a deterministic flow when adding or rotating nodes in authenticated clusters.
