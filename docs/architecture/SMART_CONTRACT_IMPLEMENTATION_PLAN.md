# Smart-Contract Integration Plan

This document outlines the engineering scaffolding required to bring smart-contract programmability into the XAI blockchain while maintaining the hardened, production-grade posture established elsewhere in the project.  Two complementary tracks are described so we can deliver an immediate application-specific workflow with governance-controlled modules and simultaneously phase in a full VM (EVM/WASM compatible) for permissionless dApps.

---

## Track A — Full Smart-Contract VM (EVM/WASM Compatible)

### A1. Architecture & Specs
1. **Execution Specification**
   - Author `docs/architecture/VM_SPEC.md` defining opcode table, gas costs, deterministic execution rules, call stack depth, memory semantics, and contract storage model.
   - Align with Ethereum yellow-paper semantics where possible; document any deviations (e.g., block header fields, chain ID, intrinsic gas).
2. **ABI & Tooling**
   - Support standard ABI encoding (contract ABI JSON), event logs, topic hashing.
   - Provide `sdk/contracts/` utilities for compilation + deployment (wrapping Foundry/Hardhat/Wasm-pack flows).

### A2. Core Modules
| Module | Responsibility | File(s) |
| --- | --- | --- |
| `xai.core.vm.evm_state.py` | Maintains account/contract storage, nonce, balance. | New package `src/xai/core/vm/`. |
| `xai.core.vm.evm_executor.py` | Executes bytecode, enforces gas limits, handles opcodes. | Same package. |
| `xai.core.vm.precompiles` | Native contracts (hashing, sig verify, bridge hooks). | Submodule. |
| `xai.core.vm.tx_processor.py` | Integrates contract calls/deployments into `Blockchain.add_transaction`. | Hooks into `transaction_validator`. |
| `xai.core.vm.fee_market.py` | Calculates base fee (EIP-1559 style optional) and miner tips. | Optional but recommended for stability. |

### A3. Node Integration
1. **Transaction Types**
   - Extend `Transaction.tx_type` with `contract_call`, `contract_deploy`.
   - Add ABI-encoded payloads to `metadata["data"]`.
2. **Block Processing**
   - Update `Blockchain.add_block` to route each contract tx through `vm.tx_processor`, capturing execution receipts (status, gas used, logs).
   - Persist receipts in new `BlockchainStorage` column-family or append-only log.
3. **API Surface**
   - `/contracts/deploy`, `/contracts/call`, `/contracts/<addr>/state` endpoints in `node_api.py` with strict Pydantic schemas.
   - Websocket event stream for contract logs (subscribe by topic).
4. **Consensus Impact**
   - Gas accounting must be deterministic; block gas limit configurable via `Config.BLOCK_GAS_LIMIT`.
   - Include `gasUsed` and `logsBloom` in block serialization so fork-choice validation can reproduce state roots.

### A4. Tooling & Tests
1. **State Tests**
   - Port a subset of Ethereum reference tests (GeneralStateTests) to `tests/vm/`.
   - Build fuzzers for opcode edge cases (stack underflows, invalid jumpdest).
2. **Integration Harness**
   - Extend the planned multi-node docker-compose stack to deploy a sample contract, send txs, and assert deterministic receipts across nodes.
3. **DevEx Tools**
   - CLI `scripts/contracts/deploy.py` + `docs/contracts/QUICKSTART.md`.
   - SDK language bindings (Python/TypeScript) generating strongly-typed clients from ABI.

### A5. Rollout & Governance
1. **Feature Flag**
   - Gate VM activation via `Config.FEATURE_FLAGS["vm"]` to allow testnet soak.
2. **Governance Controls**
   - Document upgrade process (new opcode activation, gas schedule tweaks) in `UPGRADE.md`.

---

## Track B — Purpose-Built Module Set w/ Limited Programmability

While the full VM matures, we maintain momentum with application-specific modules that can be governed and upgraded safely.

### B1. Module Catalog & Interfaces
1. **Documented Module Registry**
   - Create `docs/architecture/MODULE_REGISTRY.md` listing every on-chain module (withdrawal guard, MEV redistribution, treasury, etc.), exposed hooks, and config parameters.
2. **Interface Contracts**
   - Define Python protocols (e.g., `IOnChainModule` with `validate_tx`, `apply_state_change`) so modules can be hot-swapped.
3. **Governance Hook**
   - Extend `governance_execution.py` to package module upgrades as proposals that, once approved, trigger code deployment via controlled CI/CD pipeline.

### B2. Scripting Hooks
1. **Condition Scripts**
   - Introduce a constrained scripting language (e.g., YAML-defined rule sets) validated by `xai.core.modules.rule_engine`.
   - Scripts compile into deterministic Python/bytecode executed inside the validator sandbox but referencing only whitelisted APIs.
2. **Sidecar Rollups**
   - Document how specialized logic can live on a WASM rollup anchored to XAI (state commitments verified via `state_root_verifier`).

### B3. Tooling
1. **Module SDK**
   - Provide scaffolding (`scripts/tools/create_module.py`) that generates boilerplate, tests, and documentation stubs for new modules.
2. **Compliance Tests**
   - Unit/integration suites ensuring modules respect rate limits, logging, and security event propagation.
3. **Ops Playbooks**
   - Update the runbook index (future task) with module deployment/rollback steps.

### B4. Governance & Auditing
1. **Proposal Templates**
   - `docs/governance/PROPOSAL_TEMPLATES.md` including risk analysis, dependency diff, and migration steps.
2. **Audit Requirements**
   - Mandate external audit + fuzzing coverage before enabling new modules; integrate into `SECURITY_AUDIT_CHECKLIST.md`.

---

## Sequencing & Milestones

| Phase | Deliverables |
| --- | --- |
| Phase 0 (current) | This plan, plus confirmation of requirements with stakeholders. |
| Phase 1 | Module registry + governance hooks (Track B) while VM spec drafting (Track A). |
| Phase 2 | VM core implementation, contract transaction plumbing, ABI tooling. |
| Phase 3 | Multi-node + state tests, SDKs, dev tooling, docs/runbooks. |
| Phase 4 | Testnet feature flag activation, bug bounty, and final mainnet governance vote. |

Each phase feeds AGENT_PROGRESS with executable tasks (code, tests, docs) so we maintain traceability from planning through implementation.
