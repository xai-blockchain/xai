import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "aixn-blockchain")))

import pytest

from aixn.core.ai_metrics import metrics, reset_metrics
from aixn.core.blockchain_ai_bridge import BlockchainAIBridge
from aixn.core.ai_governance import AIGovernance, VoterType, VotingPowerDisplay


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

    assert out and out[0]["queued"]
    after = metrics.get_snapshot()
    assert after["queue_events"] > before
    assert after["completed_tasks"] >= 0
