# Atomic Swaps (HTLC) Deployment Guide

This guide explains how to deploy and operate XAI's cross-chain atomic swaps using Hash Time-Locked Contracts (HTLCs) for UTXO chains (e.g., Bitcoin, Litecoin, Dogecoin) and account-based chains (e.g., Ethereum, ERC-20s).

## Components

- `AtomicSwapManager` (Python) orchestrates swaps and persists state.
- `AtomicSwapHTLC` emits HTLC scripts/contracts with shared secret/hash.
- `CrossChainVerifier` validates funding/claim transactions via SPV/API (deterministic fixtures in tests).
- Wallet CLI/AI assistant builds user flows; fee estimation uses `calculate_atomic_swap_fee`.

## Prerequisites

- Secure RPC/API endpoints for BTC/LTC/DOGE and ETH/JSON-RPC.
- Funded wallets on both chains.
- Shared swap parameters: `secret`, `hash`, `amount`, `refund_time`, participant addresses.
- Network fee rate sources (mempool.space or node RPC for sat/vbyte; `eth_gasPrice` for ETH).

## Deployment Steps (UTXO HTLC)

1. **Compute hash**: `hash = SHA256(secret)`; share hash, keep secret private.
2. **Construct redeem script** (P2WSH/P2SH): requires secret preimage and both keys; includes refund path after `refund_time`.
3. **Fund HTLC UTXO**: create/fund P2WSH output; include change.
4. **Confirmations**: wait `min_confirmations` (e.g., 2-6 for BTC mainnet) before counterpart funds their side.
5. **Reveal/Claim**: counterparty spends with secret preimage; secret is revealed on-chain for the other side to claim.
6. **Refund**: if `refund_time` passes without claim, refund path returns funds to funder.

## Deployment Steps (Ethereum HTLC)

1. **Deploy HTLC contract** (or reuse vetted bytecode) with:
   - `hash`, `sender`, `recipient`, `timeout`, `token` (address or zero for ETH), `amount`.
2. **Fund**: call `fund(hashlock, timelock, ...)` with ETH/value or ERC-20 `approve` + `fund`.
3. **Confirmations**: wait for `min_confirmations` blocks; use `CrossChainVerifier` to validate.
4. **Claim**: counterparty calls `claim(secret)` before timeout; emits event with preimage.
5. **Refund**: after timeout, funder calls `refund()`.

## Fee Calculation

Use `CrossChainVerifier.calculate_atomic_swap_fee(amount, fee_rate_per_byte, tx_size_bytes=300, safety_buffer_bps=15)` to size funding/claim/refund transactions. Fees are clamped between `min_fee` and `max_fee` to avoid dust or runaway costs; unit tests cover bounds.

## Monitoring & Recovery

- **SPV validation**: use `verify_spv_proof` for UTXO chains and `verify_transaction_on_chain` for API-backed account chains.
- **Timeout sweeps**: call `AtomicSwapManager.check_timeouts()` to identify refundable swaps; trigger `refund` transactions for expired contracts.
- **State persistence**: swaps are stored per-swap JSON; ensure storage directory is backed up and access-controlled.
- **Automatic recovery**: run a daemon that watches `check_timeouts()` and initiates refunds after safety margin (e.g., 30 minutes past timelock) with fee estimation.

## Security Checklist

- Use unique secrets per swap; never reuse hash/preimage pairs.
- Validate addresses and amounts against UI/CLI inputs; enforce minimum/maximum swap size.
- Require minimum confirmations before proceeding to the next leg.
- Verify counterpart HTLC matches hash, amount, timelock (refund window should favor the funder by margin, e.g., +50% time).
- Log all state transitions with correlation IDs; alert on stalled swaps or mismatched funding.
- Keep API keys for external explorers in environment variables (e.g., `XAI_ETHERSCAN_API_KEY`).

## Roadmap Items

- Add on-chain deployment scripts for Bitcoin P2WSH HTLCs and Ethereum bytecode (Solidity/compiled artifact) with CI-tested fixtures.
- Integrate real SPV proof ingestion and light-client headers for UTXO chains.
- Automate refund broadcasting with replace-by-fee (RBF) bumping when mempools are congested.
- Expand fee oracle sources and include dynamic `tx_size_bytes` per chain.
