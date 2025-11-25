## Community Expectations for the XAI Chain

The community wants a blockchain that stays secure, transparent, private, and usable. The current implementation now explicitly delivers on those pillars:

1. **Security first**
   - The chain enforces UTXO reservation plus nonce tracking to prevent double spends before blocks are mined.
   - Trade and liquidity actions are signed/audited with `AuditSigner`, and the AI emergency-stop guard now has consistent, testable responses.
   - Pending trade settlements and miner rewards are tracked in the blockchain core so node operators can rely on a single truth.

2. **Transparency & validation**
   - The entire `python -m pytest` suite passes locally (431 tests) and the configuration now defines a `slow` marker so slow suites are opt-in.
   - Prometheus metrics (`xai_trade_*`, `xai_walletconnect_*`, miner gauges) and the Grafana JSON dashboard provide live telemetry for explorers and wallets.
   - Logs capture trading events, liquidity swaps, and audit signatures so whenever a swap or emergency stop occurs, it can be traced.

3. **Privacy assurances**
   - The codebase avoids embedding any creator- or origin-identifying data anywhere on-chain.
   - Sensitive directories (the UTF-8-artifact folders) are archived out of the active tree so no accidental leakage occurs during test collection.
   - Wallet creation/premine scripts run offline and leave only signed manifests (`generate_premine.py`) for auditing.

4. **Usability & APIs**
   - Wallet-to-wallet trading is exposed through `/wallet-trades/*` plus WalletConnect-like sessions, HTLC settlement, and escrow-safe logging.
   - Liquidity pools honor slippage limits and return protocol fee accounting, keeping both XAI→token and token→XAI paths consistent.
   - Additional modules (`exchange_wallet`, `wallet_trade_manager`) integrate with node endpoints so GUIs/Browser wallets can hook into the same orderbook and settlement state.

Documenting these expectations alongside the existing README ensures new contributors know what success looks like. Keep this file updated whenever you expand the chain’s accountability, metrics, or API surface.
