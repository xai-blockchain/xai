"""
Unit tests for Governance Transactions module

Tests on-chain governance transaction types, voting, and proposal management
"""

import pytest
import time
from xai.core.governance_transactions import (
    GovernanceTxType,
    GovernanceTransaction,
    OnChainProposal,
    GovernanceState,
)


class TestGovernanceTransaction:
    """Test governance transaction creation and serialization"""

    def test_init(self):
        """Test GovernanceTransaction initialization"""
        tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={"title": "Test proposal"},
        )
        
        assert tx.tx_type == GovernanceTxType.SUBMIT_PROPOSAL.value
        assert tx.submitter == "XAI_SUBMITTER"
        assert tx.proposal_id == "prop_001"
        assert tx.txid is not None

    def test_to_dict(self):
        """Test conversion to dictionary"""
        tx = GovernanceTransaction(
            tx_type=GovernanceTxType.CAST_VOTE,
            submitter="XAI_VOTER",
            proposal_id="prop_001",
            data={"vote": "yes"},
        )
        
        data = tx.to_dict()
        
        assert data["txid"] == tx.txid
        assert data["tx_type"] == GovernanceTxType.CAST_VOTE.value
        assert data["submitter"] == "XAI_VOTER"

    def test_from_dict(self):
        """Test reconstruction from dictionary"""
        original = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_CODE_REVIEW,
            submitter="XAI_REVIEWER",
            proposal_id="prop_001",
        )
        
        data = original.to_dict()
        reconstructed = GovernanceTransaction.from_dict(data)
        
        assert reconstructed.txid == original.txid
        assert reconstructed.submitter == original.submitter


class TestOnChainProposal:
    """Test on-chain proposal management"""

    def test_init(self):
        """Test OnChainProposal initialization"""
        proposal = OnChainProposal(
            proposal_id="prop_001",
            title="Increase block reward",
            description="Proposal to increase block reward to 15 XAI",
            proposal_type="parameter_change",
            submitter="XAI_PROPOSER",
            submitter_voting_power=100.0,
        )
        
        assert proposal.proposal_id == "prop_001"
        assert proposal.title == "Increase block reward"
        assert proposal.status == "proposed"
        assert len(proposal.vote_txids) == 0

    def test_to_dict(self):
        """Test proposal serialization"""
        proposal = OnChainProposal(
            proposal_id="prop_001",
            title="Test",
            description="Desc",
            proposal_type="ai_improvement",
            submitter="XAI_A",
            submitter_voting_power=50.0,
        )
        
        data = proposal.to_dict()
        
        assert data["proposal_id"] == "prop_001"
        assert data["title"] == "Test"
        assert data["status"] == "proposed"


class TestGovernanceState:
    """Test governance state management"""

    @pytest.fixture
    def gov_state(self):
        """Create GovernanceState instance"""
        return GovernanceState()

    def test_init(self, gov_state):
        """Test GovernanceState initialization"""
        assert len(gov_state.proposals) == 0
        assert len(gov_state.active_proposals) == 0
        assert gov_state.min_voters == 5
        assert gov_state.approval_percent == 66

    def test_submit_proposal(self, gov_state):
        """Test submitting a proposal"""
        tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={
                "title": "Test Proposal",
                "description": "Description",
                "proposal_type": "parameter_change",
                "submitter_voting_power": 100.0,
            }
        )
        
        result = gov_state.submit_proposal(tx)
        
        assert result["success"] is True
        assert result["proposal_id"] == "prop_001"
        assert "prop_001" in gov_state.proposals

    def test_cast_vote(self, gov_state):
        """Test casting a vote"""
        # Submit proposal first
        submit_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={
                "title": "Test",
                "description": "Desc",
                "proposal_type": "ai_improvement",
                "submitter_voting_power": 100.0,
            }
        )
        gov_state.submit_proposal(submit_tx)
        
        # Cast vote
        vote_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.CAST_VOTE,
            submitter="XAI_VOTER",
            proposal_id="prop_001",
            data={"vote": "yes", "voting_power": 50.0},
        )
        
        result = gov_state.cast_vote(vote_tx)
        
        assert result["success"] is True
        assert result["vote_count"] == 1

    def test_cast_vote_proposal_not_found(self, gov_state):
        """Test voting on non-existent proposal"""
        vote_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.CAST_VOTE,
            submitter="XAI_VOTER",
            proposal_id="nonexistent",
            data={"vote": "yes", "voting_power": 50.0},
        )
        
        result = gov_state.cast_vote(vote_tx)
        
        assert result["success"] is False

    def test_submit_code_review(self, gov_state):
        """Test submitting code review"""
        # Submit proposal
        submit_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={
                "title": "Test",
                "description": "Desc",
                "proposal_type": "ai_improvement",
                "submitter_voting_power": 100.0,
            }
        )
        gov_state.submit_proposal(submit_tx)
        
        # Submit review
        review_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_CODE_REVIEW,
            submitter="XAI_REVIEWER",
            proposal_id="prop_001",
            data={
                "approved": True,
                "comments": "Looks good",
                "voting_power": 50.0,
            }
        )
        
        result = gov_state.submit_code_review(review_tx)
        
        assert result["success"] is True
        assert result["review_count"] == 1

    def test_vote_implementation(self, gov_state):
        """Test voting on implementation"""
        # Setup: submit proposal and approve it
        submit_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={
                "title": "Test",
                "description": "Desc",
                "proposal_type": "ai_improvement",
                "submitter_voting_power": 100.0,
            }
        )
        gov_state.submit_proposal(submit_tx)
        
        # Cast initial vote to become original voter
        vote_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.CAST_VOTE,
            submitter="XAI_ORIGINAL_VOTER",
            proposal_id="prop_001",
            data={"vote": "yes", "voting_power": 50.0},
        )
        gov_state.cast_vote(vote_tx)
        
        # Vote on implementation
        impl_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.VOTE_IMPLEMENTATION,
            submitter="XAI_ORIGINAL_VOTER",
            proposal_id="prop_001",
            data={"approved": True},
        )
        
        result = gov_state.vote_implementation(impl_tx)
        
        assert result["success"] is True

    def test_vote_implementation_not_original_voter(self, gov_state):
        """Test implementation vote from non-original voter"""
        # Submit proposal
        submit_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={
                "title": "Test",
                "description": "Desc",
                "proposal_type": "ai_improvement",
                "submitter_voting_power": 100.0,
            }
        )
        gov_state.submit_proposal(submit_tx)
        
        # Try to vote on implementation without being original voter
        impl_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.VOTE_IMPLEMENTATION,
            submitter="XAI_NEW_VOTER",
            proposal_id="prop_001",
            data={"approved": True},
        )
        
        result = gov_state.vote_implementation(impl_tx)
        
        assert result["success"] is False
        assert result["error"] == "NOT_ORIGINAL_VOTER"

    def test_execute_proposal_not_approved(self, gov_state):
        """Test executing proposal without approval"""
        submit_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={
                "title": "Test",
                "description": "Desc",
                "proposal_type": "parameter_change",
                "submitter_voting_power": 100.0,
            }
        )
        gov_state.submit_proposal(submit_tx)
        
        exec_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.EXECUTE_PROPOSAL,
            submitter="XAI_EXECUTOR",
            proposal_id="prop_001",
            data={},
        )
        
        result = gov_state.execute_proposal(exec_tx)
        
        assert result["success"] is False
        assert "VOTING_NOT_APPROVED" in result["error"]

    def test_rollback_change(self, gov_state):
        """Test rolling back a change"""
        # Create original proposal
        submit_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="original",
            data={
                "title": "Original",
                "description": "Desc",
                "proposal_type": "parameter_change",
                "submitter_voting_power": 100.0,
            }
        )
        gov_state.submit_proposal(submit_tx)
        
        # Rollback
        rollback_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.ROLLBACK_CHANGE,
            submitter="XAI_ROLLBACK",
            proposal_id="rollback_001",
            data={"original_proposal_id": "original"},
        )
        
        result = gov_state.rollback_change(rollback_tx)
        
        assert result["success"] is True
        assert gov_state.proposals["original"].status == "rolled_back"

    def test_get_proposal_state(self, gov_state):
        """Test getting proposal state"""
        submit_tx = GovernanceTransaction(
            tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
            submitter="XAI_SUBMITTER",
            proposal_id="prop_001",
            data={
                "title": "Test",
                "description": "Desc",
                "proposal_type": "parameter_change",
                "submitter_voting_power": 100.0,
            }
        )
        gov_state.submit_proposal(submit_tx)
        
        state = gov_state.get_proposal_state("prop_001")
        
        assert state is not None
        assert state["proposal_id"] == "prop_001"
        assert state["status"] == "proposed"

    def test_get_proposal_state_not_found(self, gov_state):
        """Test getting non-existent proposal state"""
        state = gov_state.get_proposal_state("nonexistent")
        
        assert state is None

    def test_reconstruct_from_blockchain(self, gov_state):
        """Test reconstructing state from transactions"""
        transactions = [
            GovernanceTransaction(
                tx_type=GovernanceTxType.SUBMIT_PROPOSAL,
                submitter="XAI_SUBMITTER",
                proposal_id="prop_001",
                data={
                    "title": "Test",
                    "description": "Desc",
                    "proposal_type": "parameter_change",
                    "submitter_voting_power": 100.0,
                }
            ),
            GovernanceTransaction(
                tx_type=GovernanceTxType.CAST_VOTE,
                submitter="XAI_VOTER",
                proposal_id="prop_001",
                data={"vote": "yes", "voting_power": 50.0},
            ),
        ]
        
        gov_state.reconstruct_from_blockchain(transactions)
        
        assert "prop_001" in gov_state.proposals
        assert len(gov_state.votes.get("prop_001", {})) == 1
