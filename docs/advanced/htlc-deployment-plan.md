# HTLC Deployment Plan (BTC P2WSH + Ethereum)

## Goals
- Deliver deployable artifacts for atomic swap HTLCs on Bitcoin-like chains and Ethereum.
- Provide scripts/commands for funding, claim, and refund flows.
- Wire fee estimation and refund sweep automation.

## BTC P2WSH
- Redeem script: `OP_IF OP_SHA256 <secret_hash> OP_EQUALVERIFY <recipient_pubkey> OP_CHECKSIG OP_ELSE <timelock> OP_CHECKLOCKTIMEVERIFY OP_DROP <sender_pubkey> OP_CHECKSIG OP_ENDIF`
- Steps:
  1. Build redeem script with `AtomicSwapHTLC.build_utxo_redeem_script(secret_hash, recipient_pubkey, sender_pubkey, timelock)`.
  2. Derive P2WSH address (bech32) from `SHA256(redeem_script)`.
  3. Fund P2WSH output; wait for N confirmations.
  4. Claim: spend with witness stack `[<sig_recipient> <secret> 1 <redeem_script>]`.
  5. Refund: after timelock, witness stack `[<sig_sender> 0 <redeem_script>]`.
  6. Fee estimation: use `calculate_atomic_swap_fee(..., tx_size_bytes=~180)` and bump via RBF if needed.

## Ethereum
- Contract (see `docs/advanced/htlc-contracts.md`): constructor arguments `(secretHash, recipient, timelock)`; claim uses `claim(secret)`; refund uses `refund()`.
- Artifacts needed:
  - ABI + bytecode (compile with solc 0.8.x).
  - Deployment script (Hardhat/Foundry) emitting contract address.
  - CLI snippet to call `claim`/`refund` with gas estimation and maxFeePerGas bumping.
- Use SHA-256 for `secretHash` so the same preimage works across BTC and ETH HTLCs.

## Integration
- Add Python helpers:
  - `build_utxo_redeem_script`, `witness_script_hash` (already present).
  - Bech32 address derivation helper for P2WSH.
  - Ethereum deploy + claim/refund helpers (web3.py).
- Add tests:
  - Redeem/refund script assembly (offline).
  - ABI encoding for claim/refund payloads.
  - Happy-path regtest/Hardhat flows (future integration suite).
  - Smokes available:
    - BTC regtest: `scripts/tools/htlc_regtest_smoke.py` (claim), `scripts/tools/htlc_regtest_refund_smoke.py` (refund).
    - ETH Hardhat/Anvil: `scripts/tools/htlc_hardhat_smoke.py` (claim + refund with evm_increaseTime).
    - Latest Hardhat run (chainId 31337): claim HTLC `0x9A9f2CCfdE556A7E9Ff0848998Aa4a0CFD8863AE`, claim tx `512f88e164342ae7c850982e94b73513ee6221220660d5ef2791baa70441070c`; refund HTLC `0x68B1D87F95878fE05B998F19b66F4baba5De1aed`, refund tx `4e6506e5cd6b8d4a6bf8a42156c6f02ddab63db95e4ead95df4dba8e7a5673ba`.

## Automation
- Refund sweeper:
  - Detect expired swaps; build refund tx with fee bump policy.
  - Ethereum: retry `refund()` with +priority gas backoff.
  - Bitcoin: RBF/CPFP bump if unconfirmed.
- Logging/telemetry:
  - Emit swap_id, txid, attempts, fee levels.

### Operational snippets
- Start Anvil (Hardhat-compatible) for smokes: `docker run --rm -d -p 8545:8545 --name hardhat-node ghcr.io/foundry-rs/foundry:latest anvil`
- Run ETH smoke: `source .venv/bin/activate && python scripts/tools/htlc_hardhat_smoke.py`
- Run BTC regtest smokes against `bitcoind-regtest` (ports 18443/18444):
  - Claim: `source .venv/bin/activate && python scripts/tools/htlc_regtest_smoke.py`
  - Refund: `source .venv/bin/activate && python scripts/tools/htlc_regtest_refund_smoke.py`
