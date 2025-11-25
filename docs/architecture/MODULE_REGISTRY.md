# On-Chain Module Registry

The XAI blockchain already ships dozens of hardened modules (withdrawal guards, MEV protections, treasury automation, oracle defense, etc.).  This registry enumerates every module, its responsibilities, integration points, and governance knobs so upgrades can be approved, audited, and rolled back consistently.  Future modules must extend the interfaces defined in `src/xai/core/modules/base.py` (introduced in this pass) and register themselves here.

## 1. Registry Format

| Module | File | Interface | Responsibilities | Upgrade knobs |
| --- | --- | --- | --- | --- |
| Withdrawal Limits | `blockchain/daily_withdrawal_limits.py`, `blockchain/time_locked_withdrawals.py` | `TransactionModule` | Enforce per-account/day caps, emit telemetry, gate early unlocks. | Threshold configs (`withdrawal_limits.json`), alerting ratios. |
| Anti-Whale Manager | `blockchain/anti_whale_manager.py` | `TransactionModule` | Restrict whale transactions, govern vote caps. | Whale thresholds, quarantine durations. |
| MEV Protections | `blockchain/mev_mitigation.py`, `blockchain/front_running_protection.py`, `blockchain/mev_redistributor.py` | `BlockModule`, `TransactionModule` | Commit-reveal auctions, slippage checks, redistribution logic. | Auction window, redistribution ratio, bundle policy. |
| Governance / Slashing | `blockchain/slashing_manager.py`, `blockchain/validator_rotation.py`, `core/governance_execution.py` | `ConsensusModule` | Validator rotation, slashing penalties, governance proposals. | Vote quorum, penalty weights, rotation cadence. |
| Oracle Safeguards | `blockchain/twap_oracle.py`, `blockchain/oracle_manipulation_detection.py` | `DataModule` | Detect price deviations, orchestrate pauses. | TWAP windows, deviation thresholds. |
| Cross-Chain Bridge | `blockchain/cross_chain_messaging.py`, `blockchain/fraud_proofs.py`, `blockchain/state_root_verifier.py` | `InteropModule` | Verify external state, process fraud proofs, manage insurance. | Quorum sizes, timeout periods, slash amounts. |
| Liquidity Programs | `blockchain/liquidity_locker.py`, `blockchain/liquidity_mining_manager.py`, `blockchain/impermanent_loss_protection.py` | `TransactionModule` | Lock liquidity, schedule rewards, guard impermanent loss. | Lock duration, reward multiplier tables. |
| Treasury & Taxes | `blockchain/transfer_tax_manager.py`, `treasury/treasury_metrics.py` | `TransactionModule`, `DataModule` | Apply taxes, fund treasury, expose metrics. | Tax brackets, exemption lists, treasury wallets. |
| Wallet Security | `core/wallet.*`, `core/social_recovery.py`, `core/secure_api_key_manager.py` | `ServiceModule` | Manage wallets, social recovery, key escrow. | Guardian thresholds, key retention policy. |
| Monitoring / Alerting | `core/monitoring.py`, `monitoring/*.md`, `scripts/tools/withdrawal_threshold_calibrator.py` | `ObserverModule` | Export Prometheus metrics, calibrate thresholds, publish alerts. | Alert thresholds, webhook configs, retention settings. |

The registry should be extended as new modules land.  Each entry links to the interface type so governance reviewers know which hooks are touched (transaction validation, block finalization, external data ingestion, etc.).

## 2. Module Interfaces

Defined in `src/xai/core/modules/base.py`:

- `class TransactionModule`: exposes `pre_validate(tx, context)` and `apply(tx, context)` hooks.  Used for withdrawal guards, anti-whale policies, tax modules.
- `class BlockModule`: exposes `pre_apply(block, context)` and `post_apply(block, context)` for MEV redistributors, liquidity programs requiring block-level data.
- `class ConsensusModule`: can veto blocks/transactions based on consensus state (e.g., slashing, validator rotation).
- `class DataModule`: registers external data feeds (oracles); includes validation + failover logic.
- `class ObserverModule`: publishes telemetry/logging outputs but never mutates consensus state.
- `class InteropModule`: handles cross-chain proof verification and submits slashing/fraud events.
- `class ServiceModule`: wraps auxiliary services (wallet managers, API auth).  They interact with consensus indirectly via gRPC/HTTP or internal APIs.

Modules declare metadata (`name`, `version`, `owner`, `governance_controls`) so the registry can render operator-facing tables.  See `ModuleMetadata` dataclass in the new base package.

## 3. Governance Lifecycle

1. **Proposal Draft** – Author a change proposal referencing the module entry, desired version bump, and diff summary.  Use the template in `docs/governance/PROPOSAL_TEMPLATES.md`.
2. **Audit & Testing** – Attach links to fuzz/unit tests, coverage reports, and external audit summaries.
3. **Staging Rollout** – Enable the module in a staging environment (feature flag) and capture telemetry/stress-test reports.
4. **Vote & Activation** – Governance executes the upgrade via `governance_execution.py`, which dynamically loads the new module version and updates the registry entry (persisted as JSON + docs).
5. **Rollback** – Every module must implement `rollback(context)` to revert state changes or disable itself if post-deployment issues arise.

## 4. Registry Automation

- Maintain `registry/modules.json` (generated from module metadata) so tooling and dashboards can introspect current versions.
- Provide `scripts/tools/module_registry.py` (future work) to add/update entries, validate metadata, and sync docs.
- Expose `/admin/modules` API endpoints listing active modules, versions, owner info, and feature flags.

## 5. Security Expectations

- All modules must emit structured logs via `structured_logger` and report anomalies through `SecurityEventRouter`.
- Modules touching funds or consensus must have regression tests under `tests/xai_tests/unit/` plus integration coverage if they interact with P2P or external services.
- Dependency upgrades must run through the nightly security workflow (`.github/workflows/nightly-security-audit.yml`).

Keeping this registry current ensures every seam between modules remains auditable, and it provides a canonical source of truth for governance, auditors, and ecosystem developers.
