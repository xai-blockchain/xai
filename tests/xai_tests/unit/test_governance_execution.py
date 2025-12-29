"""
Unit tests for governance execution engine behaviors.

Coverage areas:
- Parameter and feature execution routing
- Emergency timelock handling
- Snapshot and restore symmetry
"""

from types import SimpleNamespace

import pytest

from xai.core.governance.governance_execution import (
    GovernanceExecutionEngine,
    ProposalType,
)
from xai.core.governance.governance_transactions import GovernanceState


class DummyAirdrop:
    """Simple airdrop manager stub."""

    def __init__(self):
        self.airdrop_frequency = 100
        self.min_amount = 1.0
        self.max_amount = 10.0


class DummyTimelock:
    """Timelock stub to control emergency execution outcome."""

    def __init__(self, allowed: bool, message: str = ""):
        self._allowed = allowed
        self._message = message

    def can_execute_emergency_action(self, proposal_id, current_height):
        """Return configured timelock decision."""
        return self._allowed, self._message


class DummyBlockchain:
    """Lightweight blockchain stub for governance execution tests."""

    def __init__(self, timelock_allowed: bool = True, timelock_msg: str = ""):
        self.difficulty = 2
        self.initial_block_reward = 12.0
        self.transaction_fee_percent = 0.24
        self.halving_interval = 262800
        self.airdrop_manager = DummyAirdrop()
        self.governance_state = GovernanceState(mining_start_time=0)
        self.pending_transactions = []
        self.chain = []
        self.transactions_paused = False
        self.security_manager = SimpleNamespace(
            emergency_timelock=DummyTimelock(timelock_allowed, timelock_msg)
        )


def test_protocol_parameter_updates_and_logs(monkeypatch):
    """Parameter execution updates blockchain fields and logs history."""
    blockchain = DummyBlockchain()
    engine = GovernanceExecutionEngine(blockchain)

    result = engine.execute_proposal(
        "p-1",
        {
            "proposal_type": ProposalType.PROTOCOL_PARAMETER.value,
            "parameter": "difficulty",
            "new_value": 5,
        },
    )

    assert result["success"] is True
    assert blockchain.difficulty == 5
    assert engine.execution_history[-1]["execution_type"] == "protocol_parameter"


def test_invalid_parameter_rejected_without_side_effects():
    """Out-of-range parameter change is rejected and leaves state untouched."""
    blockchain = DummyBlockchain()
    engine = GovernanceExecutionEngine(blockchain)

    result = engine.execute_proposal(
        "p-err",
        {
            "proposal_type": ProposalType.PROTOCOL_PARAMETER.value,
            "parameter": "difficulty",
            "new_value": 0,  # Below minimum
        },
    )

    assert result["success"] is False
    assert blockchain.difficulty == 2
    assert engine.execution_history == []


def test_feature_activation_toggles_flag_and_history():
    """Feature activation proposal toggles feature availability and records entry."""
    blockchain = DummyBlockchain()
    engine = GovernanceExecutionEngine(blockchain)

    result = engine.execute_proposal(
        "p-feature",
        {
            "proposal_type": ProposalType.FEATURE_ACTIVATION.value,
            "feature_name": "airdrops",
            "enabled": False,
        },
    )

    assert result["success"] is True
    assert engine.capability_registry.active_features["airdrops"] is False
    assert engine.execution_history[-1]["execution_type"] == "feature_activation"


def test_emergency_action_blocked_by_timelock():
    """Emergency action refuses execution when timelock denies."""
    blockchain = DummyBlockchain(timelock_allowed=False, timelock_msg="locked")
    engine = GovernanceExecutionEngine(blockchain)

    result = engine.execute_proposal(
        "p-emergency",
        {
            "proposal_type": ProposalType.EMERGENCY_ACTION.value,
            "action_type": "pause_transactions",
        },
    )

    assert result["success"] is False
    assert "locked" in result["error"]
    assert blockchain.transactions_paused is False


def test_snapshot_and_restore_round_trip(monkeypatch):
    """Snapshot captures governance state and restore rehydrates it."""
    blockchain = DummyBlockchain()
    engine = GovernanceExecutionEngine(blockchain)

    # Apply a change to alter defaults and create execution history
    engine.execute_proposal(
        "p-restore",
        {
            "proposal_type": ProposalType.FEATURE_ACTIVATION.value,
            "feature_name": "treasure_hunts",
            "enabled": False,
        },
    )
    blockchain.governance_state.min_voters = 10

    snapshot = engine.snapshot()

    # Mutate state after snapshot
    engine.capability_registry.active_features["treasure_hunts"] = True
    engine.execution_history.append({"proposal_id": "p-mutated"})
    blockchain.governance_state.min_voters = 99

    engine.restore(snapshot)

    assert engine.capability_registry.active_features["treasure_hunts"] is False
    assert engine.execution_history[-1]["proposal_id"] == "p-restore"
    assert blockchain.governance_state.min_voters == 10
