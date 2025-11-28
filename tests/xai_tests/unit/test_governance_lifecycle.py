"""
Comprehensive tests for governance proposal lifecycle

Tests proposal submission, voting, execution, rejection,
cancellation, vote delegation, and state transitions.
"""

import pytest
import time
from enum import Enum
from unittest.mock import Mock, patch


class ProposalStatus(Enum):
    """Governance proposal status"""
    PENDING = "pending"
    ACTIVE = "active"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class GovernanceProposal:
    """Mock governance proposal"""

    def __init__(self, proposal_id, proposer, title, description, voting_period):
        self.proposal_id = proposal_id
        self.proposer = proposer
        self.title = title
        self.description = description
        self.voting_period = voting_period
        self.status = ProposalStatus.PENDING
        self.votes_for = 0
        self.votes_against = 0
        self.voters = set()
        self.delegations = {}  # {delegator: delegate}
        self.created_at = time.time()
        self.voting_start = None
        self.voting_end = None
        self.quorum = 1000  # Minimum votes needed
        self.approval_threshold = 0.6  # 60% approval needed

    def start_voting(self):
        """Start voting period"""
        if self.status == ProposalStatus.PENDING:
            self.status = ProposalStatus.ACTIVE
            self.voting_start = time.time()
            self.voting_end = self.voting_start + self.voting_period
            return True
        return False

    def vote(self, voter, vote_for, voting_power=1):
        """Cast vote"""
        if self.status != ProposalStatus.ACTIVE:
            return False

        if time.time() > self.voting_end:
            return False

        if voter in self.voters:
            return False  # Already voted

        # Check if vote is delegated
        if voter in self.delegations:
            return False  # Cannot vote if delegated

        self.voters.add(voter)
        if vote_for:
            self.votes_for += voting_power
        else:
            self.votes_against += voting_power

        return True

    def delegate_vote(self, delegator, delegate):
        """Delegate vote to another address"""
        if delegator in self.voters:
            return False  # Already voted

        self.delegations[delegator] = delegate
        return True

    def finalize(self):
        """Finalize voting and determine outcome"""
        if self.status != ProposalStatus.ACTIVE:
            return False

        if time.time() < self.voting_end:
            return False

        total_votes = self.votes_for + self.votes_against

        # Check quorum
        if total_votes < self.quorum:
            self.status = ProposalStatus.REJECTED
            return True

        # Check approval threshold
        approval_rate = self.votes_for / total_votes if total_votes > 0 else 0
        if approval_rate >= self.approval_threshold:
            self.status = ProposalStatus.APPROVED
        else:
            self.status = ProposalStatus.REJECTED

        return True

    def execute(self):
        """Execute approved proposal"""
        if self.status != ProposalStatus.APPROVED:
            return False

        self.status = ProposalStatus.EXECUTED
        return True

    def cancel(self):
        """Cancel proposal"""
        if self.status in [ProposalStatus.EXECUTED, ProposalStatus.CANCELLED]:
            return False

        self.status = ProposalStatus.CANCELLED
        return True


class TestGovernanceLifecycle:
    """Tests for governance proposal lifecycle"""

    def test_proposal_submission(self):
        """Test submitting governance proposal"""
        proposal = GovernanceProposal(
            "prop_001",
            "proposer_address",
            "Upgrade Protocol",
            "Proposal to upgrade the protocol",
            3600  # 1 hour voting period
        )

        assert proposal.status == ProposalStatus.PENDING
        assert proposal.proposal_id == "prop_001"
        assert proposal.proposer == "proposer_address"

    def test_proposal_voting(self):
        """Test voting on proposal"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 3600
        )

        proposal.start_voting()
        assert proposal.status == ProposalStatus.ACTIVE

        # Cast votes
        assert proposal.vote("voter1", True, 100) is True
        assert proposal.vote("voter2", True, 50) is True
        assert proposal.vote("voter3", False, 30) is True

        assert proposal.votes_for == 150
        assert proposal.votes_against == 30

    def test_proposal_execution(self):
        """Test executing approved proposal"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 1
        )

        proposal.start_voting()

        # Vote in favor (above threshold)
        proposal.vote("voter1", True, 1000)
        proposal.vote("voter2", True, 500)
        proposal.vote("voter3", False, 100)

        # Wait for voting period
        time.sleep(1.1)

        # Finalize
        proposal.finalize()
        assert proposal.status == ProposalStatus.APPROVED

        # Execute
        result = proposal.execute()
        assert result is True
        assert proposal.status == ProposalStatus.EXECUTED

    def test_proposal_with_insufficient_votes_rejected(self):
        """Test proposal rejection with insufficient votes"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 1
        )

        proposal.start_voting()

        # Vote below quorum
        proposal.vote("voter1", True, 500)

        time.sleep(1.1)

        # Finalize
        proposal.finalize()
        assert proposal.status == ProposalStatus.REJECTED

    def test_proposal_cancellation(self):
        """Test cancelling proposal"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 3600
        )

        assert proposal.cancel() is True
        assert proposal.status == ProposalStatus.CANCELLED

    def test_cannot_cancel_executed_proposal(self):
        """Test executed proposal cannot be cancelled"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 1
        )

        proposal.start_voting()
        proposal.vote("voter1", True, 2000)

        time.sleep(1.1)
        proposal.finalize()
        proposal.execute()

        # Try to cancel
        result = proposal.cancel()
        assert result is False
        assert proposal.status == ProposalStatus.EXECUTED

    def test_vote_delegation(self):
        """Test delegating votes"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 3600
        )

        # Delegate vote
        result = proposal.delegate_vote("delegator1", "delegate1")
        assert result is True

        proposal.start_voting()

        # Delegator cannot vote
        result = proposal.vote("delegator1", True, 100)
        assert result is False

    def test_cannot_delegate_after_voting(self):
        """Test cannot delegate after already voting"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 3600
        )

        proposal.start_voting()

        # Vote first
        proposal.vote("voter1", True, 100)

        # Try to delegate (should fail)
        result = proposal.delegate_vote("voter1", "delegate")
        assert result is False

    def test_governance_state_transitions(self):
        """Test proposal state transitions"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 1
        )

        # PENDING -> ACTIVE
        assert proposal.status == ProposalStatus.PENDING
        proposal.start_voting()
        assert proposal.status == ProposalStatus.ACTIVE

        # ACTIVE -> APPROVED
        proposal.vote("voter1", True, 2000)
        time.sleep(1.1)
        proposal.finalize()
        assert proposal.status == ProposalStatus.APPROVED

        # APPROVED -> EXECUTED
        proposal.execute()
        assert proposal.status == ProposalStatus.EXECUTED

    def test_quorum_requirement(self):
        """Test quorum requirement for proposals"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 1
        )

        proposal.quorum = 1000
        proposal.start_voting()

        # Vote below quorum
        proposal.vote("voter1", True, 500)

        time.sleep(1.1)
        proposal.finalize()

        # Should be rejected due to quorum
        assert proposal.status == ProposalStatus.REJECTED

    def test_approval_threshold_requirement(self):
        """Test approval threshold requirement"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 1
        )

        proposal.approval_threshold = 0.6  # 60%
        proposal.start_voting()

        # Vote: 500 for, 600 against (45% approval)
        proposal.vote("voter1", True, 500)
        proposal.vote("voter2", False, 600)

        time.sleep(1.1)
        proposal.finalize()

        # Should be rejected due to threshold
        assert proposal.status == ProposalStatus.REJECTED

    def test_double_voting_prevented(self):
        """Test voters cannot vote twice"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 3600
        )

        proposal.start_voting()

        # First vote
        assert proposal.vote("voter1", True, 100) is True

        # Second vote (should fail)
        assert proposal.vote("voter1", False, 100) is False

        assert proposal.votes_for == 100
        assert proposal.votes_against == 0

    def test_voting_period_enforcement(self):
        """Test voting period is enforced"""
        proposal = GovernanceProposal(
            "prop_001", "proposer", "Test", "Description", 1
        )

        proposal.start_voting()

        # Vote during period
        assert proposal.vote("voter1", True, 100) is True

        # Wait for period to end
        time.sleep(1.1)

        # Vote after period (should fail)
        assert proposal.vote("voter2", True, 100) is False
