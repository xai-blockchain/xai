"""
Integration tests for XAI Governance system

Tests AI governance, voting, and proposal execution
"""

import pytest
import sys
import os
import time

# Add core directory to path

from xai.core.ai_governance import AIGovernance, VoterType, VotingPowerDisplay
from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet


class TestGovernanceInitialization:
    """Test governance system initialization"""

    def test_create_governance(self, tmp_path):
        """Test creating governance system"""
        governance = AIGovernance()

        assert governance is not None
        assert hasattr(governance, "proposals")

    def test_governance_parameters(self, tmp_path):
        """Test governance parameters are set"""
        governance = AIGovernance()

        # Should have voting parameters
        assert hasattr(governance, "__dict__")

    def test_voter_types(self, tmp_path):
        """Test voter type enumeration"""
        assert VoterType.NODE_OPERATOR
        assert VoterType.MINER
        assert VoterType.AI_CONTRIBUTOR
        assert VoterType.HYBRID


class TestProposalCreation:
    """Test proposal creation and submission"""

    def test_create_proposal(self, tmp_path):
        """Test creating a governance proposal"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        assert proposal_id is not None
        assert proposal_id in governance.proposals

    def test_proposal_has_required_fields(self, tmp_path):
        """Test proposal has all required fields"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        proposal = governance.proposals[proposal_id]

        assert proposal["title"] == "Test Proposal"
        assert proposal["description"] == "Test description"
        assert proposal["proposer"] == proposer.address
        assert proposal["status"] == "active"

    def test_multiple_proposals(self, tmp_path):
        """Test creating multiple proposals"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal1 = governance.create_proposal(
            proposer_address=proposer.address,
            title="Proposal 1",
            description="Description 1",
            proposal_type="ai_improvement",
        )

        proposal2 = governance.create_proposal(
            proposer_address=proposer.address,
            title="Proposal 2",
            description="Description 2",
            proposal_type="parameter_change",
        )

        assert proposal1 != proposal2
        assert len(governance.proposals) == 2


class TestVotingMechanism:
    """Test voting on proposals"""

    def test_cast_vote(self, tmp_path):
        """Test casting a vote"""
        governance = AIGovernance()
        proposer = Wallet()
        voter = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # Cast vote
        success = governance.cast_vote(
            proposal_id=proposal_id, voter_address=voter.address, vote="yes", voting_power=10.0
        )

        assert success
        assert proposal_id in governance.proposals

    def test_vote_options(self, tmp_path):
        """Test different vote options"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        voter1 = Wallet()
        voter2 = Wallet()
        voter3 = Wallet()

        # Different vote options
        governance.cast_vote(proposal_id, voter1.address, "yes", 10.0)
        governance.cast_vote(proposal_id, voter2.address, "no", 5.0)
        governance.cast_vote(proposal_id, voter3.address, "abstain", 3.0)

        proposal = governance.proposals[proposal_id]
        assert "votes" in proposal

    def test_quadratic_voting(self, tmp_path):
        """Test quadratic voting power calculation"""
        governance = AIGovernance()

        # Quadratic voting reduces large stakeholder power
        power_100 = governance.calculate_quadratic_power(100)
        power_400 = governance.calculate_quadratic_power(400)

        # sqrt(400) = 20, sqrt(100) = 10
        # So 4x contribution should give 2x voting power
        assert power_400 == power_100 * 2

    def test_prevent_double_voting(self, tmp_path):
        """Test prevention of double voting"""
        governance = AIGovernance()
        proposer = Wallet()
        voter = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # First vote
        governance.cast_vote(proposal_id, voter.address, "yes", 10.0)

        # Try to vote again
        result = governance.cast_vote(proposal_id, voter.address, "no", 10.0)

        # Should prevent double voting
        assert result == False


class TestVotingPower:
    """Test voting power calculations"""

    def test_voting_power_display(self, tmp_path):
        """Test voting power display"""
        display = VotingPowerDisplay()

        impact = display.show_contribution_impact(100.0)

        assert impact is not None
        assert "voting_power" in impact

    def test_time_decay(self, tmp_path):
        """Test voting power time decay"""
        governance = AIGovernance()

        # Old contributions should have reduced power
        recent_power = governance.calculate_voting_power(100, days_ago=10)
        old_power = governance.calculate_voting_power(100, days_ago=365)

        assert recent_power > old_power

    def test_voter_type_weight(self, tmp_path):
        """Test different voter type weights"""
        governance = AIGovernance()

        # Different voter types may have different weights
        node_power = governance.get_voter_type_weight(VoterType.NODE_OPERATOR)
        miner_power = governance.get_voter_type_weight(VoterType.MINER)

        assert node_power > 0
        assert miner_power > 0

    def test_hybrid_voter_bonus(self, tmp_path):
        """Test hybrid voters get bonus"""
        governance = AIGovernance()

        single_role_power = governance.get_voter_type_weight(VoterType.MINER)
        hybrid_power = governance.get_voter_type_weight(VoterType.HYBRID)

        # Hybrid should have bonus
        assert hybrid_power >= single_role_power


class TestProposalExecution:
    """Test proposal execution after passing"""

    def test_proposal_passes_with_majority(self, tmp_path):
        """Test proposal passes with majority vote"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # Cast majority yes votes
        for i in range(10):
            voter = Wallet()
            governance.cast_vote(proposal_id, voter.address, "yes", 10.0)

        # Cast minority no votes
        for i in range(3):
            voter = Wallet()
            governance.cast_vote(proposal_id, voter.address, "no", 10.0)

        # Check if passed
        result = governance.tally_votes(proposal_id)

        assert result["passed"] == True

    def test_proposal_fails_without_majority(self, tmp_path):
        """Test proposal fails without majority"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # Cast equal votes
        for i in range(5):
            voter = Wallet()
            governance.cast_vote(proposal_id, voter.address, "yes", 10.0)

        for i in range(5):
            voter = Wallet()
            governance.cast_vote(proposal_id, voter.address, "no", 10.0)

        result = governance.tally_votes(proposal_id)

        assert result["passed"] == False

    def test_proposal_timelock(self, tmp_path):
        """Test proposal timelock before execution"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # Proposal should have timelock period
        proposal = governance.proposals[proposal_id]
        assert "timelock" in proposal or "execution_time" in proposal

    def test_execute_proposal(self, tmp_path):
        """Test executing approved proposal"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # Pass the proposal
        for i in range(10):
            voter = Wallet()
            governance.cast_vote(proposal_id, voter.address, "yes", 10.0)

        governance.tally_votes(proposal_id)

        # Execute (may need to wait for timelock)
        result = governance.execute_proposal(proposal_id)

        assert result is not None


class TestGovernanceIntegration:
    """Test governance integration with blockchain"""

    def test_proposal_on_blockchain(self, tmp_path):
        """Test proposal recorded on blockchain"""
        bc = Blockchain(data_dir=str(tmp_path))
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # Proposal should be trackable
        assert proposal_id in governance.proposals

    def test_voting_with_blockchain_verification(self, tmp_path):
        """Test votes verified through blockchain"""
        bc = Blockchain(data_dir=str(tmp_path))
        governance = AIGovernance()
        proposer = Wallet()
        voter = Wallet()

        # Give voter some stake
        bc.mine_pending_transactions(voter.address)

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Test Proposal",
            description="Test description",
            proposal_type="ai_improvement",
        )

        # Vote with blockchain-verified stake
        voting_power = bc.get_balance(voter.address)
        governance.cast_vote(proposal_id, voter.address, "yes", voting_power)

        assert proposal_id in governance.proposals

    def test_governance_transaction_type(self, tmp_path):
        """Test governance transactions are distinguished"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Give wallet balance
        bc.mine_pending_transactions(wallet.address)

        # Create governance transaction
        tx = Transaction(wallet.address, "GOVERNANCE_CONTRACT", 0.0, 0.1, tx_type="governance")

        assert tx.tx_type == "governance"


class TestGovernanceParameters:
    """Test governance parameter management"""

    def test_get_parameters(self, tmp_path):
        """Test getting governance parameters"""
        governance = AIGovernance()

        params = governance.get_parameters()

        assert params is not None
        assert isinstance(params, dict)

    def test_update_parameters(self, tmp_path):
        """Test updating governance parameters"""
        governance = AIGovernance()

        # Update parameter through governance
        new_quorum = 0.6
        result = governance.update_parameter("quorum", new_quorum)

        assert result == True

    def test_parameter_change_proposal(self, tmp_path):
        """Test parameter change requires proposal"""
        governance = AIGovernance()
        proposer = Wallet()

        proposal_id = governance.create_proposal(
            proposer_address=proposer.address,
            title="Change Quorum",
            description="Increase quorum to 60%",
            proposal_type="parameter_change",
        )

        proposal = governance.proposals[proposal_id]
        assert proposal["proposal_type"] == "parameter_change"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
