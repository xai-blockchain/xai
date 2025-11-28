# Project Recovery Task Tracker

This file tracks the remediation work required to bring the Linux migration of the blockchain project back to a production-ready state.

## Open Tasks

| ID | Area | Description | Owner | Status |
|----|------|-------------|-------|--------|
| T1 | Node Init | Repair `BlockchainNode._initialize_optional_features` so the module imports cleanly on Linux and the optional feature flags are safe. | Codex | ✅ Completed |
| T2 | Faucet API | Implement `/faucet/claim` (and supporting logic) so the documented faucet tools actually work. | Codex | ✅ Completed |
| T3 | P2P | Add the missing `/transaction/receive` and `/block/receive` endpoints and integrate `P2PNetworkManager`. | Codex | ✅ Completed |
| T4 | Embedded Wallets | Instantiate `AccountAbstractionManager` in the node so `/wallet/embedded/*` stops returning 503. | Codex | ✅ Completed |
| T5 | CLI Tooling | Create the `xai.cli` and `xai.wallet.cli` entry points referenced in the README/pyproject. | Codex | ✅ Completed |
| T6 | Docs & Tests | Update README/TESTNET instructions and add pytest coverage for the restored features. | Codex | ✅ Completed |

## Notes

- Progress is serialized; downstream tasks depend on the node module compiling again.
- Update this file whenever a task changes state or new work is discovered.
