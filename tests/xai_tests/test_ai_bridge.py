import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "xai-blockchain")))

import pytest

from xai.core.api.ai_metrics import metrics, reset_metrics
from xai.core.chain.blockchain_ai_bridge import BlockchainAIBridge
from xai.core.governance.ai_governance import AIGovernance, VoterType, VotingPowerDisplay
from xai.core.xai_blockchain.ai_governance_dao import (
    AIGovernanceDAO,
    ProposalCategory,
    ProposalStatus,
)


class DummyBlockchain:
    def get_balance(self, address):
        return 1000

    def get_height(self):
        return 1

    def get_balance_at_height(self, address, height):
        return 1000

    def get_total_circulating_supply(self):
        return 100000000


@pytest.fixture(autouse=True)
def clean_metrics():
    reset_metrics()
    yield
    reset_metrics()


def test_bridge_queues_proposal_and_records_metrics():
    blockchain = DummyBlockchain()
    dao = AIGovernanceDAO(blockchain)

    proposal = type("P", (), {})()
    proposal.proposal_id = "prop-test"
    proposal.category = ProposalCategory.SECURITY
    proposal.description = "Test"
    proposal.detailed_prompt = "Test prompt"
    proposal.estimated_tokens = 1000
    proposal.best_ai_model = "claude-opus-4"
    proposal.status = ProposalStatus.FULLY_FUNDED

    dao.proposals[proposal.proposal_id] = proposal

    bridge = BlockchainAIBridge(blockchain=blockchain, governance_dao=dao)
    before = metrics.get_snapshot()["queue_events"]

    out = bridge.sync_full_proposals()

    # Verify the output contains queued proposal
    assert out is not None, "sync_full_proposals should return a list"
    assert len(out) > 0, "sync_full_proposals should return at least one result"
    assert out[0].get("queued") is True, f"Proposal should be queued, got: {out[0]}"

    # Verify metrics were recorded
    after = metrics.get_snapshot()
    assert after["queue_events"] > before, \
        f"queue_events should increase from {before} to {after['queue_events']}"
    assert after["completed_tasks"] >= 0, \
        f"completed_tasks should be non-negative, got {after['completed_tasks']}"
