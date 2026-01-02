# WebSocket API

WebSocket support is implemented in `xai.core.api.api_websocket`. It is available when API extensions are enabled (see `xai.core.api.api_extensions`).

## Endpoint

- `GET /ws`

If API auth is enabled, the same credentials as REST are required.

## Client Messages

Messages are JSON objects with `action` and `channel`:

```json
{ "action": "subscribe", "channel": "blocks" }
{ "action": "unsubscribe", "channel": "blocks" }
```

## Server Messages

Server messages are JSON objects that include a `channel` field. Example channels used by the codebase include:

- `blocks`
- `mining`
- `stats`
- `sync`
- `wallet-trades`

See `xai.core.api.api_websocket` and related handlers for exact payloads.
