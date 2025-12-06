# XAI SLIP-0044 Registration

XAI wallets rely on the SLIP-0044 coin-type registry so HD derivation paths
remain unique across all chains and hardware vendors. The project reserves
coin type **22593**, which aligns with the network identifier `0x5841`.

## Registration Details

- **Symbol:** `XAI`
- **Coin type:** `22593`
- **Name:** Xai Blockchain
- **Reference:** [SLIP-0044 PR XAI-SLIP44-22593](https://github.com/satoshilabs/slips/pull/XAI-SLIP44-22593)

Any attempt to initialize the HD wallet without this registry entry results in
a startup failure so that wallets never fall back to unregistered coin types
such as 9999.
