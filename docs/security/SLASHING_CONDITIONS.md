# Slashing Conditions

This document summarizes slashing behavior implemented in code.

## Code References
- src/xai/blockchain/slashing_manager.py
- src/xai/core/defi/staking.py

## Slashing Manager Penalties
The slashing manager applies fixed percentage penalties to a validator's stake:
- DOUBLE_SIGNING: 10%
- OFFLINE: 1%
- EQUIVOCATION: 5%
- INVALID_BLOCK_PROPOSAL: 2%
- fraud_proven: 50%

## Staking Module Slashing
The staking module allows an authorized caller to slash a validator by a
basis-point fraction. Reasons are recorded as strings (for example,
"downtime" or "double_sign").

## Notes
- Slashing behavior may vary between testnet and mainnet configurations.
- For current values, treat code as the source of truth.
