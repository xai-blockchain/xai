# Staking Guide

This guide covers staking basics for XAI (delegating to validators and claiming rewards). Interface specifics may vary by client.

## Prerequisites
- Wallet initialized and funded with XAI.
- Validator address or ID you wish to delegate to.

## Delegating Stake
1. Ensure your wallet is unlocked (password/2FA as configured).
2. Submit a delegation transaction:
   ```bash
   xai-wallet stake --validator <validator_addr> --amount <amount> --fee <fee>
   ```
3. Wait for confirmation; check the staking dashboard or CLI query to verify delegation.

## Claiming Rewards
- Rewards accrue per validator rules. To claim:
  ```bash
  xai-wallet claim-rewards --validator <validator_addr> --fee <fee>
  ```
- Rewards are credited to your wallet after confirmation.

## Undelegating / Unstaking
- Unstaking triggers an unbonding period; funds are locked until it expires.
  ```bash
  xai-wallet unstake --validator <validator_addr> --amount <amount> --fee <fee>
  ```
- After unbonding, funds return to your available balance.

## Best Practices
- Delegate to reputable validators with good uptime and reasonable commission.
- Keep your wallet secure: enable 2FA, use hardware wallets when possible.
- Monitor validator performance; redelegate if uptime/reputation drops.
- Keep fees set appropriately to avoid stuck transactions.

## Troubleshooting
- If transactions fail, ensure:
  - Sufficient balance for amount + fee.
  - Correct validator address.
  - Node is synced; check `/health` or `/stats`.
  - Your client clock is in sync (timestamps required).***
