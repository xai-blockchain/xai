# Governance Enforcement Runbook

This runbook captures how the XAI governance proposal lifecycle ties into the on-chain pipelines so every upgrade flows through the documented governance model (`SMART_CONTRACT_IMPLEMENTATION_PLAN.md`, `MODULE_REGISTRY.md`).

## Key responsibilities
- **Governance API handler (`src/xai/core/api_governance.py`)** exposes `/governance/proposals/submit`, `/governance/proposals`, `/governance/vote`, and `fiat-unlock` routes plus helpers such as `/governance/voting-power/<address>` (see `GovernanceAPIHandler`). Every HTTP request is translated into the transaction data that feeds the on-chain modules.
- **Governance transaction layer (`src/xai/core/governance_transactions.py`)** serializes every submit/vote/review/execution action into a `GovernanceTransaction`, stores it on-chain, and rebuilds the `GovernanceState` when the chain replays blocks.
- **Execution engine (`src/xai/core/governance_execution.py`)** is the enforcement gate. Only proposals recorded in the `GovernanceCapabilityRegistry` can mutate protocol parameters, wire new features (`active_features`), or trigger treasury/emergency operations once they pass the approval checks encoded in `GovernanceState`.

## Lifecycle (enforcement steps)
1. **Proposal submission**
   - Client POSTs to `/governance/proposals/submit`. The handler builds a deterministic `proposal_id`, wraps metadata into a `GovernanceTransaction` of type `SUBMIT_PROPOSAL`, and appends it to the blockchain (mirroring the mission statement in `governance_transactions.py`).
   - `GovernanceState.submit_proposal` records submission, puts the proposal in `active_proposals`, and returns the `proposal_id` for downstream tracking.

2. **Voting phase**
   - Each `CAST_VOTE` transaction lands via `/governance/vote` or the validator-balanced tooling. `GovernanceState.cast_vote` updates `votes`, records unique `voter` power, and re-checks approval requirements (`min_voters`, `approval_percent`, `max_individual_power_percent`).
   - If the vote tally satisfies the checks inside `_check_proposal_approved`, the proposal moves to `approved_proposals` and enters the “implementation prep” stage. _Enforcement point:_ until `min_voters` and approval percentage are met, the proposal remains pending no matter how the API tries to execute it, preventing unauthorized changes.

3. **Code review / implementation gate**
   - `submit_code_review` and `vote_implementation` transactions ensure two separations of duty: code reviewers and the original voters must sign off before execution. `_check_implementation_approved` requires ≥50% of the original “yes” voters to approve implementation, and the execution engine refuses to act otherwise.
   - The governance timeline is also subject to `timelock_queue`, giving operators a window to inspect/alert before final execution (see the timelock comments in `GovernanceState`).

4. **Execution**
   - Approved proposals pass through `GovernanceExecutionEngine.execute_proposal`. Each handler (`_execute_protocol_parameter`, `_execute_feature_activation`, `_execute_treasury_allocation`, `_execute_emergency_action`, and the meta-governance helpers) re-validates inputs via the `GovernanceCapabilityRegistry`.
   - Parameter changes must satisfy type/range checks (`validate_parameter_value`), so mutated fields such as `difficulty`, `block_reward`, `min_voters`, and `approval_percent` can never be set outside the safe ranges defined in the registry.
   - Feature toggles live in `active_features` and are only applied after the call succeeds; `execute_proposal` audits every change via `_log_execution`, providing traceability for operators.

5. **Rollback / Observability**
   - If something goes wrong, `GovernanceState.rollback_proposal` is submitted as another on-chain transaction, storing the original and rollback tx IDs so auditors can reconstruct timelines.
   - `ExecutionHistory` inside `GovernanceExecutionEngine` plus the logged execution entries make it straightforward to build Grafana panels or alert rules for `governance_execution` events.

## Operational guidance
- **Runbook integration:** Align this process with `docs/architecture/SMART_CONTRACT_IMPLEMENTATION_PLAN.md` since any VM/module rollout must follow the governance steps documented above (`proposal → vote → review → implementation → execution`). The module registry (`docs/architecture/MODULE_REGISTRY.md`) is the canonical list of upgrade targets managed by these proposals.
- **Auditability:** Operators can rebuild governance state by replaying `GovernanceTransactions` (the `reconstruct_from_blockchain` helper) to verify the chain honored the enforced quorum/percent thresholds before applying the change.
- **Testing & automation:** Use `scripts/tools/multi_node_harness.py` to exercise governance vote flows in isolation for staging and ensure the API/voting power guardrails never permit underpowered voters to accidentally reach `approved_proposals`.
- **Alerting:** Tie Prometheus counters (e.g., new metrics under `xai_governance_*`) or logs from `_log_execution` to Alertmanager runbooks so unexpected emergency actions or treasury allocations trigger PagerDuty with links back to `GOVERNANCE_ENFORCEMENT_RUNBOOK.md`.

## References
- `docs/architecture/SMART_CONTRACT_IMPLEMENTATION_PLAN.md` – governance-controlled module vs. full VM rollout description.
- `docs/architecture/MODULE_REGISTRY.md` – module metadata and governance control surface.
- `src/xai/core/api_governance.py` – HTTP surface for proposals, votes, and fiat unlock actions.
- `src/xai/core/governance_transactions.py` – the transaction/state machine enforcing `min_voters`, approval percentage, implementation votes, and rollbacks.
- `src/xai/core/governance_execution.py` – execution gatekeeper, parameter validation, and feature toggle enforcement.
