# HTLC Smoke Test Setup

Use this guide to configure and run the local HTLC smokes.

## Config
- Copy `scripts/tools/.env.htlc-smokes.example` to `.env.htlc-smokes` and fill RPC creds.
  - `XAI_BTC_RPC_URL`, `XAI_BTC_RPC_USER`, `XAI_BTC_RPC_PASS` for bitcoind regtest.
  - `XAI_ETH_RPC` for Hardhat/Anvil.
  - Optional `XAI_SWAPS_FILE` for the refund runner input.

## Bitcoin regtest
1. Start bitcoind in regtest with RPC enabled (user/pass from env).
2. Fund the default wallet: `bitcoin-cli -regtest -rpcuser=user -rpcpassword=pass generatetoaddress 101 "$(bitcoin-cli -regtest getnewaddress)"`.
3. Run smoke: `python scripts/tools/htlc_regtest_smoke.py`.

## Ethereum/Hardhat
1. Start Hardhat/Anvil: `npx hardhat node` or `anvil`.
2. Run smoke: `python scripts/tools/htlc_hardhat_smoke.py`.

## Refund sweeps
1. Prepare `swaps.json` with expired swaps (fields: `id`, `timelock`, `status`, and `utxo` or `contract/sender`).
2. Run: `python scripts/tools/refund_sweep_runner.py`.

## Notes
- Ensure venv has `web3`, `py-solc-x`, and `bech32` installed (already in `requirements.txt`).
- The smoke scripts assume unlocked test wallets; use PSBT/hardware for production.***
