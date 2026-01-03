# XAI Blockchain

Python-based proof-of-work blockchain implementation with a UTXO transaction model, REST API, and wallet CLI. This repository also includes optional explorer, mobile, and SDK subprojects.

## Quickstart

See `docs/QUICKSTART.md` for a local node and wallet flow.

## Devnet

To join the XAI devnet, see the [networks repository](https://github.com/xai-blockchain/testnets) for configuration and network details.

| Network | Chain ID | Status |
|---------|----------|--------|
| [xai-testnet-1](https://github.com/xai-blockchain/testnets/tree/main/xai-testnet-1) | `testnet` | Devnet |

**Quick join:**
1. Clone and install: `git clone https://github.com/xai-blockchain/xai && cd xai && pip install .`
2. Configure: `cp .env.example .env` and set `XAI_NETWORK=testnet`
3. Start: `python -m xai.node`

## Documentation

- `docs/QUICKSTART.md`
- `docs/api/rest-api.md`
- `docs/api/websocket.md`
- `docs/protocol/PROTOCOL_SPECIFICATION.md`
- `docs/adr/README.md`

## Development

```bash
python -m venv venv
source venv/bin/activate
pip install .
pytest
```

## Subprojects

- `explorer/` - block explorer backend/frontend
- `mobile/` and `mobile-app/` - mobile clients
- `sdk/` - client SDKs (TypeScript, Flutter, Kotlin, Swift)

## Contributing

See `CONTRIBUTING.md`.

## Security

See `SECURITY.md`.

## License

Apache 2.0. See `LICENSE`.
