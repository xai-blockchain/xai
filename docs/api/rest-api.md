# REST API (Quick Reference)

Base URL: `http://<host>:<port>` (defaults to `localhost:8545` unless overridden).

## Authentication

If API auth is enabled (`XAI_API_AUTH_REQUIRED=1`), include one of:

- `X-API-Key: <key>`
- `Authorization: Bearer <token>`

## Core

- `GET /`
- `GET /health`
- `GET /stats`
- `GET /mempool`
- `GET /mempool/stats`
- `GET /metrics`

## Blockchain

- `GET /blocks`
- `GET /blocks/<index>`
- `GET /block/<hash>`
- `GET /chain/range`

## Transactions

- `GET /transactions`
- `GET /transaction/<txid>`
- `POST /send`

## Wallet

- `GET /balance/<address>`
- `GET /address/<address>/nonce`
- `GET /history/<address>`

## Peers

- `GET /peers`
- `POST /peers/add`

## Faucet (testnet only)

- `POST /faucet/claim`

## Full Surface

The API surface includes additional routes for mining, contracts, exchange, recovery, and admin operations. See `src/xai/core/api_routes/` for the full list and request/response shapes.
