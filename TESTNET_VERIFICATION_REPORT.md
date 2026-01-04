# XAI Testnet Infrastructure Verification Report

**Date:** 2026-01-03
**Server:** 54.39.129.11 (xai-testnet)
**Scope:** Public endpoints + core backend services
**Overall Status:** ⚠️ PARTIAL (DNS gaps)

---

## Executive Summary

Public RPC, Explorer, Faucet, GraphQL, and WebSocket endpoints are operational.
Two endpoints are configured locally but **not published in DNS**:
`testnet-rpc2.xaiblockchain.com` and `snapshots.xaiblockchain.com`.

**Results:**
- ✅ **PASS:** 7
- ⚠️ **PARTIAL / NOT PUBLISHED:** 2
- ❌ **FAIL:** 0

---

## Endpoint Checks

| Service | URL | Result | Notes |
| --- | --- | --- | --- |
| RPC | https://testnet-rpc.xaiblockchain.com/stats | ✅ 200 | Primary RPC (node1) |
| RPC (node2) | http://testnet-rpc2.xaiblockchain.com | ⚠️ DNS missing | Nginx vhost exists, no DNS |
| Explorer | https://testnet-explorer.xaiblockchain.com | ✅ 200 | Static UI |
| Faucet UI | https://testnet-faucet.xaiblockchain.com | ✅ 200 | UI served at root |
| Faucet health | https://testnet-faucet.xaiblockchain.com/faucet/health | ✅ 200 | API lives under `/faucet/` |
| GraphQL | https://testnet-graphql.xaiblockchain.com/graphql | ✅ 400 | 400 expected without query |
| WebSocket | https://testnet-ws.xaiblockchain.com | ✅ 426 | Upgrade required (expected for WS) |
| Docs | https://testnet-docs.xaiblockchain.com | ✅ 200 | Static docs |
| Snapshots | https://snapshots.xaiblockchain.com | ⚠️ DNS missing | Nginx vhost exists, no DNS |

---

## Backend Services (xai-testnet)

```
- xai.service (node1)           : 8545
- xai-node-2.service (node2)    : 8555
- xai-websocket.service         : 8765
- xai-websocket-proxy.service   : 4202
- xai-graphql.service           : 4102
- xai-indexer.service           : 8084
- xai-explorer.service          : 8082
- xai-faucet.service            : 8081
- nginx / prometheus / grafana  : 80/443, 9090, 3000
```

---

## Follow-ups

- Publish DNS for `testnet-rpc2.xaiblockchain.com` (node2).
- Publish DNS for `snapshots.xaiblockchain.com`.

