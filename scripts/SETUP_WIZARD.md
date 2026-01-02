# Node Setup Wizard

The setup wizard helps create a local configuration for running a node.

## Run the Wizard

```bash
python scripts/setup_wizard.py
```

## What It Configures

- Network selection (`testnet` or `mainnet`)
- API and P2P ports
- Data directory
- Optional mining address
- Required secrets for mainnet

## Output

- `.env` file in the repo root (if you choose to write one)
- Optional wallet/keystore artifacts if you create a wallet during the flow

Review the generated values before starting a mainnet node.
