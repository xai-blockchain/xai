# Atomic Swap Artifact CLI

Use `scripts/tools/atomic_swap_artifacts.py` to generate deployable HTLC artifacts and automate refunds.

## Generate artifacts

```bash
python scripts/tools/atomic_swap_artifacts.py generate \
  --pair XAI/BTC \
  --axn-amount 1000 \
  --other-amount 0.01 \
  --counterparty recipient_pubkey \
  --sender-pubkey 02abcdef... \
  --recipient-pubkey 03abcdef... \
  --output btc_swap.json
```

Outputs include the P2WSH address, redeem script, funding template, **and a recommended fee** derived from `XAI_ATOMIC_SWAP_FEE_RATE` so you know the minimum sats to attach.  
For Ethereum, add:

```bash
python scripts/tools/atomic_swap_artifacts.py generate \
  --pair XAI/ETH \
  --axn-amount 1000 \
  --other-amount 1.0 \
  --counterparty 0xRecipient \
  --eth-sender 0xSender \
  --eth-provider http://127.0.0.1:8545 \
  --eth-auto-deploy \
  --output eth_swap.json
```

With `--eth-auto-deploy`, the HTLC contract is deployed immediately and the JSON file includes the contract address, ABI, and the recommended gas limits/fee caps used for deployment.

## Automated refunds

### Ethereum

```bash
python scripts/tools/atomic_swap_artifacts.py refund-eth \
  --provider http://127.0.0.1:8545 \
  --contract 0xContractAddress \
  --sender 0xSender
```

The tool compiles the HTLC ABI if none is provided and calls `refund()` with proper gas defaults.

### Bitcoin-style P2WSH

```bash
python scripts/tools/atomic_swap_artifacts.py refund-btc \
  --signature <sender_sig_hex> \
  --redeem-script <redeem_script_hex>
```

This prints the witness stack (`[signature, selector, redeem_script]`) so you can assemble the refund transaction with your preferred PSBT tooling.
