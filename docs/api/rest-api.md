# REST API Reference (Overview)

Use this as a quick map of key endpoints. Field-level contracts are in `docs/api/openapi.yaml`; error/rate details are in `docs/api/api_error_codes.md` and `docs/api/rate_limits.md`.

## Authentication
- `X-API-Key` or `Authorization: Bearer <JWT>` for protected endpoints.
- Admin endpoints may require elevated scopes.

## Core
- `GET /`, `/health`, `/stats`
- `GET /block/<hash>`
- `GET /address/<address>/nonce`
- `GET /mempool/stats`

## Wallet & Transactions
- `POST /wallet/create`, `/wallet/import`, `/wallet/sign`
- `POST /send` (enforces timestamp/txid checks, hash acknowledgement)
- `GET /transaction/<txid>`

## Contracts
- `POST /contracts/deploy`
- `GET /contracts/<address>/abi`
- `GET /contracts/<address>/events`

## Governance
- `GET /governance/proposals`
- `POST /governance/propose`
- `POST /governance/vote`

## Explorer/Analytics
- `GET /mempool` (paginated)
- `GET /address/<addr>/history` (paginated)
- `GET /peers` (`verbose=true` for details)

## WebSocket
- `GET /ws` — real-time blocks/tx/mempool; see `docs/api/websocket_messages.md`.

## Error/Size/Rate
- Size caps via `API_MAX_JSON_BYTES`; pagination caps default to 500.
- HTTP error codes and rate limiting behavior are described in the linked docs above.***
