"""
Unit tests for FraudProofManager.

Coverage targets:
- Submission and retrieval
- Verification happy/expired/rejected paths
- Interaction with slashing manager
"""

import pytest

from xai.blockchain.fraud_proofs import FraudProofManager
from xai.blockchain.slashing_manager import SlashingManager


class _MockSlashingManager:
    def __init__(self):
        self.reports = []

    def report_malicious_behavior(self, validator_id, misbehavior_type, evidence=None):
        self.reports.append((validator_id, misbehavior_type, evidence))
        return True


def test_submit_and_get_proof(tmp_path):
    slashing = SlashingManager(tmp_path / "slash.db", initial_validators={"val1": 100})
    mgr = FraudProofManager(slashing_manager=slashing, time_provider=lambda: 0)
    proof_id = mgr.submit_fraud_proof("challenger", "val1", {"type": "invalid_state"}, 10, 100)
    proof = mgr.get_proof(proof_id)
    assert proof is not None
    assert proof.challenger_address == "challenger"


def test_verify_proof_happy_path_triggers_slash(tmp_path):
    slashing = _MockSlashingManager()
    mgr = FraudProofManager(slashing_manager=slashing, time_provider=lambda: 0)
    proof_id = mgr.submit_fraud_proof("challenger", "valX", {"type": "invalid_state"}, 10, 100)
    assert mgr.verify_fraud_proof(proof_id) is True
    assert slashing.reports == [("valX", "fraud_proven", {"type": "invalid_state"})]


def test_verify_proof_expired(tmp_path):
    slashing = _MockSlashingManager()
    # time_provider starts at 200 for submission, advances to 400 for verification
    times = iter([200, 400])
    mgr = FraudProofManager(slashing_manager=slashing, time_provider=lambda: next(times))
    proof_id = mgr.submit_fraud_proof("challenger", "valX", {"type": "invalid_state"}, 10, 100)
    assert mgr.verify_fraud_proof(proof_id) is False
    assert mgr.get_proof(proof_id).status == "expired"


def test_verify_proof_rejected(tmp_path):
    slashing = _MockSlashingManager()
    mgr = FraudProofManager(slashing_manager=slashing, time_provider=lambda: 0)
    proof_id = mgr.submit_fraud_proof("challenger", "valX", {"type": "noop"}, 10, 100)
    assert mgr.verify_fraud_proof(proof_id) is False
    assert mgr.get_proof(proof_id).status == "rejected"
