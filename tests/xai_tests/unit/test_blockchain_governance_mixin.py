"""Unit tests for BlockchainGovernanceMixin methods."""

import pytest
from unittest.mock import MagicMock

from xai.core.blockchain_components.governance_mixin import BlockchainGovernanceMixin


class MockBlockchain(BlockchainGovernanceMixin):
    """Mock blockchain for testing governance mixin methods."""

    def __init__(self):
        self.governance_manager = MagicMock()


class TestSubmitGovernanceProposal:
    """Tests for submit_governance_proposal method."""

    def test_delegates_to_governance_manager(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.submit_governance_proposal.return_value = {
            "proposal_id": "prop123",
            "status": "pending",
        }

        result = blockchain.submit_governance_proposal(
            submitter="XAI123",
            title="Test Proposal",
            description="A test description",
            proposal_type="parameter_change",
            proposal_data={"param": "value"},
        )

        blockchain.governance_manager.submit_governance_proposal.assert_called_once_with(
            "XAI123", "Test Proposal", "A test description", "parameter_change", {"param": "value"}
        )
        assert result["proposal_id"] == "prop123"

    def test_handles_none_proposal_data(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.submit_governance_proposal.return_value = {"proposal_id": "prop456"}

        result = blockchain.submit_governance_proposal(
            submitter="XAI123",
            title="Simple Proposal",
            description="No data",
            proposal_type="text",
            proposal_data=None,
        )

        blockchain.governance_manager.submit_governance_proposal.assert_called_once_with(
            "XAI123", "Simple Proposal", "No data", "text", None
        )
        assert result["proposal_id"] == "prop456"


class TestCastGovernanceVote:
    """Tests for cast_governance_vote method."""

    def test_delegates_to_governance_manager(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.cast_governance_vote.return_value = {
            "success": True,
            "vote_id": "vote123",
        }

        result = blockchain.cast_governance_vote(
            voter="XAI456",
            proposal_id="prop123",
            vote="yes",
            voting_power=100.0,
        )

        blockchain.governance_manager.cast_governance_vote.assert_called_once_with(
            "XAI456", "prop123", "yes", 100.0
        )
        assert result["success"] is True

    def test_default_voting_power(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.cast_governance_vote.return_value = {"success": True}

        blockchain.cast_governance_vote(
            voter="XAI789",
            proposal_id="prop456",
            vote="no",
        )

        blockchain.governance_manager.cast_governance_vote.assert_called_once_with(
            "XAI789", "prop456", "no", 0.0
        )


class TestSubmitCodeReview:
    """Tests for submit_code_review method."""

    def test_delegates_to_governance_manager(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.submit_code_review.return_value = {
            "success": True,
            "review_id": "rev123",
        }

        result = blockchain.submit_code_review(
            reviewer="XAI_REVIEWER",
            proposal_id="prop123",
            approved=True,
            comments="Looks good!",
            voting_power=50.0,
        )

        blockchain.governance_manager.submit_code_review.assert_called_once_with(
            "XAI_REVIEWER", "prop123", True, "Looks good!", 50.0
        )
        assert result["success"] is True

    def test_defaults_for_comments_and_voting_power(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.submit_code_review.return_value = {"success": True}

        blockchain.submit_code_review(
            reviewer="XAI_REVIEWER",
            proposal_id="prop456",
            approved=False,
        )

        blockchain.governance_manager.submit_code_review.assert_called_once_with(
            "XAI_REVIEWER", "prop456", False, "", 0.0
        )


class TestExecuteGovernanceProposal:
    """Tests for execute_governance_proposal method."""

    def test_delegates_to_governance_manager(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.execute_governance_proposal.return_value = {
            "success": True,
            "execution_hash": "exec123",
        }

        result = blockchain.execute_governance_proposal(
            proposal_id="prop123",
            executor="admin",
        )

        blockchain.governance_manager.execute_governance_proposal.assert_called_once_with(
            "prop123", "admin"
        )
        assert result["success"] is True

    def test_default_executor(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.execute_governance_proposal.return_value = {"success": True}

        blockchain.execute_governance_proposal(proposal_id="prop789")

        blockchain.governance_manager.execute_governance_proposal.assert_called_once_with(
            "prop789", "system"
        )


class TestVoteImplementation:
    """Tests for vote_implementation method."""

    def test_delegates_to_governance_manager(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.vote_implementation.return_value = {
            "success": True,
        }

        result = blockchain.vote_implementation(
            voter="XAI_DEV",
            proposal_id="prop123",
            approved=True,
            voting_power=75.0,
        )

        blockchain.governance_manager.vote_implementation.assert_called_once_with(
            "XAI_DEV", "prop123", True, 75.0
        )
        assert result["success"] is True

    def test_defaults(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.vote_implementation.return_value = {"success": True}

        blockchain.vote_implementation(
            voter="XAI_DEV2",
            proposal_id="prop456",
        )

        blockchain.governance_manager.vote_implementation.assert_called_once_with(
            "XAI_DEV2", "prop456", True, 0.0
        )


class TestExecuteProposal:
    """Tests for execute_proposal method."""

    def test_delegates_to_governance_manager(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.execute_proposal.return_value = {
            "success": True,
            "result": {"changes_applied": 5},
        }

        result = blockchain.execute_proposal(
            executor="XAI_ADMIN",
            proposal_id="prop123",
        )

        blockchain.governance_manager.execute_proposal.assert_called_once_with(
            "XAI_ADMIN", "prop123"
        )
        assert result["success"] is True
        assert result["result"]["changes_applied"] == 5


class TestGetGovernanceProposal:
    """Tests for get_governance_proposal method."""

    def test_returns_proposal(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.get_governance_proposal.return_value = {
            "proposal_id": "prop123",
            "title": "Test",
            "status": "approved",
        }

        result = blockchain.get_governance_proposal("prop123")

        blockchain.governance_manager.get_governance_proposal.assert_called_once_with("prop123")
        assert result["proposal_id"] == "prop123"
        assert result["status"] == "approved"

    def test_returns_none_for_nonexistent(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.get_governance_proposal.return_value = None

        result = blockchain.get_governance_proposal("nonexistent")

        assert result is None


class TestListGovernanceProposals:
    """Tests for list_governance_proposals method."""

    def test_returns_all_proposals(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.list_governance_proposals.return_value = [
            {"proposal_id": "prop1", "status": "pending"},
            {"proposal_id": "prop2", "status": "approved"},
        ]

        result = blockchain.list_governance_proposals()

        blockchain.governance_manager.list_governance_proposals.assert_called_once_with(None)
        assert len(result) == 2

    def test_filters_by_status(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.list_governance_proposals.return_value = [
            {"proposal_id": "prop2", "status": "approved"},
        ]

        result = blockchain.list_governance_proposals(status="approved")

        blockchain.governance_manager.list_governance_proposals.assert_called_once_with("approved")
        assert len(result) == 1
        assert result[0]["status"] == "approved"

    def test_returns_empty_list(self):
        blockchain = MockBlockchain()
        blockchain.governance_manager.list_governance_proposals.return_value = []

        result = blockchain.list_governance_proposals(status="rejected")

        assert result == []
