# Fiat/Card Rails Roadmap & AML Guardrails

## Current state (locked until Nov 2026)

- All `/exchange/buy-with-card`, `/exchange/payment-methods`, and `/exchange/calculate-purchase` routes immediately return `CARD_PAYMENTS_DISABLED` and reference the hard lock defined in `Config.FIAT_REENABLE_DATE` (currently `2026-11-01 UTC`).  
- The lock is enforced inside `BlockchainNode._fiat_lock_message`, so even if the PaymentProcessor reappears the rails will stay disabled until that date unless the lock is consciously extended.
- While fiat/card paths are offline, liquidity pools, wallet trades, atomic swaps, and on-chain wallet transfers remain fully operational; no functionality is removed.

## Roadmap to re-enable fiat rails

1. **Infrastructure readiness**
   - Integrate the real `PaymentProcessor`/`CryptoDepositManager` stack used in production so that Stripe/bank rails can reach live endpoints, mirrored by dedicated tests.  
   - Deploy secure, transient credentials for the processor and ensure request routing runs through `ExchangeWalletManager` to keep funds auditable.
2. **KYC & AML controls**  
   - Wire the onboarding flow to a KYC provider (or internal identity vault) so each fiat purchaser has a verified profile before a large transfer is allowed.  
   - Feed every fiat transaction into `TransactionRiskScore` (see `aixn/core/aml_compliance.py`) so the risk level, flagged reasons, and required approvals are captured before the trade is settled.  
   - Generate compliance-ready reports (timestamps, detection codes, flagged addresses) for auditors before allowing a fiat purchase to finalize.
3. **Security reviews & operator tooling**  
   - Harden the payment endpoints with rate limits, IP filtering, and proof-of-work (as needed) to match `SecurityValidator` expectations.  
   - Publish a change log that notes when the rails are re-enabled, along with the promised audit results and updated Grafana panels (treasury metrics were added in `treasury_metrics.py`).
4. **Re-open doors after the lock**
   - The earliest possible unlock is November 1, 2026; any earlier attempt to re-enable must update `Config.FIAT_REENABLE_DATE` and satisfy internal approvals (documented here for traceability).

## Treasury & observability

### Governance unlock mechanism

- Voting cannot start before March 12, 2026 UTC (`Config.FIAT_UNLOCK_GOVERNANCE_START`). Between that date and the auto-unlock on Nov 1, 2026 UTC (`Config.FIAT_REENABLE_DATE`), the rails remain locked until at least five governance votes reach the 66% support threshold.  
- A new endpoint, `POST /governance/fiat-unlock/vote` (see `aixn/core/api_extensions.py`), accepts `governance_address`, `support`, and optional `reason`. Submitters must use their XAI address (`XAI...`) to vote.  
- Check the `/governance/fiat-unlock/status` route to monitor votes, support ratio, and whether the rails are currently unlocked; the message returned mirrors what the node exposes in `CoreNode._fiat_lock_message`.  
- Once the vote threshold is met, nodes automatically treat the rails as unlocked even before Nov 1, 2026—the endpoint allows neutral parties to validate that `status.unlocked` is `true` before exposing fiat greed.

### Treasury reconciliation

- Run `python scripts/fee_treasury_reconcile.py` after each release or during audits to compare the actual UTXO balance of `Config.TRADE_FEE_ADDRESS` with the sum of fees collected from the wallet trade ledger (`trade_history`). If those numbers diverge by more than 0.0001 XAI, the script logs detailed stats; the same reconciliation is automatically invoked inside `Blockchain.mine_pending_transactions()` and recorded in the Prometheus gauge `xai_fee_treasury_balance`.  
- For nightly audits, produce the script’s output and store alongside your other compliance artifacts; the script prints actual balance, expected balance, and difference plus the governance and pool summaries from `treasury_metrics`.

- The fee treasury now emits Prometheus metrics (`xai_trade_fee_collected_total`, `xai_fee_treasury_balance`, etc.) in `aixn/core/treasury_metrics.py`, so Grafana dashboards can display how much XAI accrues from wallet trades.  
- Every trade settlement logs anonymous fee credits through `anonymous_logger.log_info`, providing a tamper-resistant trail for auditors that complements the metric counters.

## AML guardrails – code-backed diagnosis

- `TransactionRiskScore` assigns 0-100 scores based on large amounts, structuring, rapid succession, rounding patterns, and velocity spikes (`aixn/core/aml_compliance.py`).  
- `FlagReason` covers key investigation categories (large amounts, sanctioned addresses, structuring, velocity, mixing, new-account spikes).  
- Address monitoring keeps blacklists and sanctions lists that block known adversaries and can be enriched via governance proposals.  
- Because the system already tracks abuse patterns, the guardrails satisfy the “monitor & flag” requirement, but they do **not** yet enforce KYC during the initial fiat onboarding – that must be layered on top before rails reopen.

## Recommended next steps

1. Tie the fiat routes into a KYC/AML workflow before 2026-11-01 so that the lock can be lifted without a compliance gap.  
2. Publish the treasury metrics panel(s) in Grafana using the new counters/gauges so the community can audit the fees that eventually reward miners/LPs.  
3. After re-enabling, add recurring audits that compare the `fees` recorded via `treasury_metrics` with the actual UTXO balance at `Config.TRADE_FEE_ADDRESS` for proof-of-reserve.
