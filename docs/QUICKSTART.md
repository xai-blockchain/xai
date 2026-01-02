# Quickstart

This guide walks through a local node and wallet flow.

## Install

```bash
python -m venv venv
source venv/bin/activate
pip install .
```

## Run a node

```bash
# Choose explicit ports so tooling defaults align
xai-node --port 12001 --p2p-port 12002
```

## Generate a wallet address

```bash
xai-wallet generate-address
```

## Check balance

```bash
export XAI_API_URL=http://localhost:12001
xai-wallet balance --address TXAI_YOUR_ADDRESS
```

## Send a transaction

```bash
xai-wallet send \
  --sender TXAI_SENDER \
  --recipient TXAI_RECIPIENT \
  --amount 1.0
```

## Faucet (testnet only)

If the faucet is enabled on your node (testnet config):

```bash
xai-wallet request-faucet --address TXAI_YOUR_ADDRESS
```

## Notes

- `XAI_NETWORK` defaults to `testnet` unless set to `mainnet`.
- `XAI_API_PORT` controls the node HTTP port; `XAI_API_URL` controls the CLI base URL.
- `xai-wallet` defaults to `http://localhost:12001` unless `XAI_API_URL` or `--base-url` is set.
- If you run `xai-node` without `--port`, it defaults to `8545`, so set `XAI_API_URL` to match.
- See `docs/api/rest-api.md` for HTTP endpoints.
