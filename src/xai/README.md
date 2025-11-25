# XAI

A blockchain with AI governance.

## Features

- Proof-of-work consensus
- Atomic swaps (11 cryptocurrencies)
- Smart contracts
- AI governance system
- Personal AI assistance
- AI safety controls (instant stop capabilities)
- Time capsules (lock coins until future date)
- 120M total supply
- AML reporting hooks (`/regulator/flagged`, `/history/<address>` metadata, etc.) documented in `docs/AML_REPORTING.md`
- Hardware wallet roadmap (Ledger + manager) in `docs/HARDWARE_WALLET.md` and ledger onboarding instructions in `docs/LEDGER_ONBOARDING.md`
- Embedded wallets/account abstraction documented in `docs/EMBEDDED_WALLETS.md`
- Micro-AI assistant network described in `docs/MICRO_ASSISTANTS.md`
- Mini App manifest for polls/votes/games plus AML cues documented in `docs/MINI_APPS.md`
- Light-client headers + SPV proofs (`docs/LIGHT_CLIENT.md`) and the mobile draft bridge/QR flow (`docs/MOBILE_BRIDGE.md`)

## Run a Node

```bash
pip install -r requirements.txt
python core/node.py
```

## Mine

```bash
python core/node.py --miner YOUR_ADDRESS
```

## Onboarding helpers

Follow `docs/onboarding.md` and run `python scripts/prepare_node.py --miner YOUR_ADDRESS` to create a data directory, persist a `node_config.json`, register for peer discovery, and see the exact `python core/node.py` + `curl /mining/start` commands you need to launch a miner.

## Testing policy

- `python -m pytest` now runs with `-m "not slow"` via `pytest.ini`, matching what staged CI jobs expect.
- To exercise the slow suites (e.g., nightly diagnostics), invoke `python -m pytest -m slow`.

## Early Adopters

Wallets available for early node operators.

## Technical Details

See TECHNICAL.md for architecture and specifications.

## Community expectations

See `docs/community_expectations.md` for a concise statement of the security/transparency/privacy/usability guarantees the community relies on; update that file whenever those guarantees evolve.

## License

MIT

## Disclaimer

Experimental software. Use at your own risk.
