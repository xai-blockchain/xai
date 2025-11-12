# AML Reporting & Explorer Hooks

The XAI blockchain now tracks `risk_score`, `risk_level`, and `flag_reasons` for every transaction that passes through the mempool. These fields are attached to `Transaction.to_dict()` and therefore show up wherever the blockchain publishes transaction data¹.

## Key Survivors

1. **Explorer endpoints**  
   - `/transaction/<txid>` now returns `risk_score`, `risk_level`, and `flag_reasons` alongside the original transaction data. UIs can surface those values next to the amount/fee to describe whether a transaction is suspicious.
   - `/history/<address>` delivers the same `_risk_*` metadata per history entry (sent/received). Wallet GUIs can color rows or show badges for `{risk_score > 60 → warning}`.
2. **Regulator/Treasury feeds**  
   - `/regulator/flagged` (GET) lists the most recent flagged transactions from `RegulatorDashboard` plus `min_score`/`limit` query controls.
   - `/regulator/high-risk` lists addresses with average scores above the requested threshold; the response includes counts and max risk.
3. **Ledger metadata**  
   - All new blocks persist `risk_score` and `flag_reasons` inside transaction dictionaries, so both explorers and indexers can replay the values without re-running scoring.
   - `TransactionRiskScore` is fed the cached per-address history (last 200 events) so even once a score dips, the `flag_reasons` array explains why it once glowed red.

## Integration suggestions

- Show `risk_score` + `risk_level` badges in block/explorer tables; `flag_reasons` can power tooltips or collapsible logs.
- Highlight `/regulator/flagged` results in compliance dashboards and ship warnings (via email/webhook) when high-score matches appear.
- Keep `XAI_REGULATOR_SECRET` (or similar) confidential, but the endpoints themselves return sanitized data for auditors; no private keys are shared.
- Use `/mini-apps/manifest` to discover lightweight polls, votes, games, and the AML companion. The `aml_context` payload returns the same `risk_level`, `risk_score`, and `flag_reasons` so the UI knows whether to show an “open” experience or a “cautious” overlay around the embedded iframe.

## Mini-App reminders

- The manifest includes `recommended_flow` per widget. When `risk_level` is “high” yet a poll still appears, render the iframe inside a bordered compliance panel and add a short “risk-aware” label with the `flag_reasons`.
- Keep the manifest request near the wallet dashboard so you can pass `address` and re-cast the call if the user switches wallets; this keeps the AML signals synchronized with the rest of the regulator feeds.

## Notes

¹ Transactions loaded from existing history before this feature do not yet include risk metadata. Newly added transactions and any revalidation run after this version populate those fields automatically.
