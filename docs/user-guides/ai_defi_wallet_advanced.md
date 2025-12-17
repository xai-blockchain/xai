# XAI Advanced Feature Guide (AI + DeFi + Wallet Ops)

This guide captures the production flows that were undocumented: AI integration, DeFi operations, and advanced wallet handling. Keep secrets out of commands; use environment variables for tokens/keys.

## AI Integration
- **AI Marketplace Tasks:** `xai ai list|describe <task_id>` to inspect tasks; `xai ai run <task_id> --input file.json --budget 25` submits work with spend caps.
- **Model Staking:** `xai ai stake --amount 1000 --model-id my-model` locks stake; `xai ai rewards --model-id my-model` shows accrued rewards and slash history.
- **AI Task Webhooks:** Configure `AI_WEBHOOK_URL` + `AI_WEBHOOK_SECRET`; the node signs payloads with HMAC-SHA256, verified via `xai.core.ai_webhooks.verify_signature`.
- **Safety Controls:** Enable guardrails via `AI_SAFETY_ENFORCED=1`; all AI executions log to `ai_safety_events` with correlation IDs.

## DeFi Operations
- **Staking:** `xai defi stake --amount 500 --validator VAL` and `xai defi unstake --amount 100 --validator VAL`; cooldowns enforced via consensus constants.
- **Lending/Borrowing:** `xai defi lend --market USDC --amount 1000`; `xai defi borrow --market USDC --amount 300 --collateral XAI`; health factor visible via `xai defi health --market USDC`.
- **Swaps:** `xai swap --from XAI --to USDC --amount 25 --slippage 0.5 --deadline 120`; router enforces signature and nonce replay protection.
- **Circuit Breakers:** Sudden oracle deviation (>5%) or liquidity drain trips circuit breaker; status at `/admin/emergency/status` and via `xai admin emergency-status`.

## Advanced Wallet Handling
- **Hardware Wallets:** `xai wallet hw connect` to list; `xai wallet hw sign --path m/44'/700'/0'/0/0 --tx tx.json` performs on-device signing; private keys never leave hardware.
- **Watch-Only:** `xai wallet watch add --xpub <XPUB>` registers xpub; balances via `xai wallet watch list`; no signing permitted.
- **Backups & Migration:** Encrypted saves: `xai wallet save --password "$PW" --out wallet.json`; migration of legacy encryption: `xai wallet migrate --in legacy.json --out new.json --password "$PW"`.
- **2FA / TOTP:** `xai wallet 2fa enable --issuer XAI --account user@example.com` prints TOTP URI; backup codes are single-use and hashed on disk; verification enforced on high-value ops.

## Observability
- AI/DeFi metrics are exposed at `/metrics` (Prometheus): `xai_ai_tasks_total`, `xai_defi_liquidations_total`, `xai_wallet_hardware_sign_total`.
- Grafana dashboards: AI Ops, DeFi Health, Wallet Security (see `monitoring/dashboards/grafana`).
