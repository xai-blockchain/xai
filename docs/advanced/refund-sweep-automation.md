# Refund Sweep Automation for Atomic Swaps

This note outlines an automated refund sweeper for HTLC-based atomic swaps to prevent stranded funds.

## Goals
- Detect expired HTLCs (UTXO and Ethereum) and broadcast refunds.
- Bump fees (RBF/CPFP or priority gas) to ensure inclusion under congestion.
- Avoid double-refunds and race conditions with late claims.
- Persist sweep attempts and outcomes for auditability.

## Workflow
1. **Discovery**: Iterate active swaps; identify those past `timelock + safety_margin` with no claim detected.
2. **Refund construction**:
   - UTXO: build refund witness spending the HTLC redeem script via timeout branch.
   - Ethereum: call `refund()` on the HTLC contract (or equivalent ERC-20 wrapper).
3. **Fee policy**:
   - UTXO: start with `calculate_atomic_swap_fee(...)`; if mempool pressure > threshold, bump via RBF/CPFP.
   - Ethereum: set `maxFeePerGas`/`maxPriorityFeePerGas` from fee oracle; include retry with +10-20% backoff.
4. **Broadcast & tracking**:
   - Broadcast transaction; persist txid/hash, attempts, and peer endpoints used.
   - Retry with bumped fees if unconfirmed after N blocks/minutes.
5. **Safety checks**:
   - Recheck chain state before each retry to avoid racing a successful claim.
   - Abort if HTLC already spent or balance is zero.
   - Rate-limit sweeps per address to avoid DoS.

## Implementation Hooks
- Add `RefundSweepManager`:
  - Scans swap state, uses `CrossChainVerifier` to detect claim/confirmations.
  - Builds refund txs via `AtomicSwapHTLC.build_utxo_redeem_script` and signer hooks for sender key.
  - Persists sweep metadata (JSON/DB) with timestamps and fee levels tried.
- Integrate with scheduler/daemon to run periodically.
- Emit structured logs and Prometheus metrics: sweeps attempted/successful, retries, fee escalations.

## Testing
- Unit: construct refund tx/witness for expired UTXO HTLC; Ethereum refund call data; fee bump logic.
- Integration: regtest/Hardhat flows for fund → expire → refund, with simulated congestion and bump retries.

