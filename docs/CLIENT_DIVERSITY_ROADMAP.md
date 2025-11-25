# Client Diversity Roadmap

The health of the XAI ecosystem depends on multiple independent client implementations that obey the consensus rules defined in `docs/architecture/CONSENSUS_NETWORK_SPEC.md` and the VM/Module lifecycle described in `docs/architecture/VM_SPEC.md`. This roadmap coordinates the workstream for additional clients, the interoperability gates, and the testing required before governance approves them.

## Phase 0 – Reference client stabilization (complete)

- Harden the Python reference client (`src/xai/core`) with structured logging, deterministic time providers, API key enforcement, and the suite of regression tests described throughout `AGENT_PROGRESS` and `tests/xai_tests/*`.
- Document governance checkpoints so every upgrade uses the same on-chain lifecycle (`docs/runbooks/GOVERNANCE_ENFORCEMENT_RUNBOOK.md`).

## Phase 1 – Language diversity pilots (1–3 months)

1. **Rust validator blueprint** – implement `xai-client-rust` with the same block validation/mempool rules, focusing on the light-client and consensus parser modules in `docs/architecture/CONSENSUS_NETWORK_SPEC.md`. Publish a `README` describing how the Rust node can connect to the staging network (port/channel expectations, API key handling).
2. **Go relay client** – build an API-focused client that can submit governance proposals, interact with `/governance/vote`, and stream security telemetry via the new webhook pipeline (`MONITORING_GUIDE.md`). Share Go modules via `sdk/` or `docs/examples` for community adoption.
3. **Interoperability tests** – use `scripts/tools/multi_node_harness.py` augmented with cross-client peers to ensure block propagation, faucet claims, and withdrawal guardrails succeed even when peers run different implementations.

## Phase 2 – External client contributions (3–6 months)

- Publish a modular specification (currently `docs/architecture/VM_SPEC.md` and `docs/architecture/MODULE_REGISTRY.md`) plus code templates that external teams can fork, extend, and submit as governance proposals.
- Maintain a `client-diversity` test matrix (prometheus, API, consensus) and tie results into the nightly security audit workflow (`.github/workflows/nightly-security-audit.yml`) so regressions surface automatically.
- Accept contributions once an external client passes the integration checklist (Go/Rust/JavaScript) and confirm via `tests/api/test_openapi_contract.py` plus targeted module unit tests.

## Phase 3 – Governance onboarding (ongoing)

- For every new client candidate, create a governance proposal describing the release plan, risk analysis, and migration steps. Use `docs/architecture/MODULE_REGISTRY.md` to lock down which modules the client touches.
- Coordinate rollout with the upgrade strategy (`UPGRADE.md`), staging harness, and runbook updates (once staging validation completes, add entries to the consolidated runbook index mentioned in `AGENT_PROGRESS`).
- Encourage the community to document their implementation details (e.g., CLI flags, default ports, API key expectations) inside `docs/client-implementations/README.md` or similar indexes.

## Feedback loop

- Track on-chain metrics (`xai_governance_*`, `xai_security_events_*`) after every client addition and update `MONITORING_GUIDE.md` so operators understand how to instrument the new variant.
- Keep this roadmap in sync with `AGENT_PROGRESS` to ensure every milestone is tied to the remaining TODO items.
