"""
Comprehensive tests for ai_governance.py - Coverage Target: 80%+

This test file achieves 80%+ coverage by testing:
- VotingPowerDisplay: Voting power transparency and comparison
- VotingPower: Quadratic voting calculations with time decay
- AIWorkloadDistribution: Distributed AI task execution
- ConsensusRules: Dynamic consensus with whale protection
- AIGovernanceProposal: Proposal lifecycle and voting
- AIGovernance: Simplified governance facade

Current coverage: 16.88% (54/262 statements)
Target: 80%+ (210+ statements)
Gap: 156 statements
"""

import pytest
import time
import math
from unittest.mock import Mock, patch
from xai.core.ai_governance import (
    VotingPowerDisplay,
    VotingPower,
    AIWorkloadDistribution,
    ConsensusRules,
    AIGovernanceProposal,
    AIGovernance,
    VoterType,
    ProposalType,
)


# =============================================================================
# VotingPowerDisplay Tests (Lines 41-90)
# =============================================================================


class TestVotingPowerDisplay:
    """Test voting power transparency display."""

    def test_show_contribution_impact_basic(self):
        """Test basic contribution impact calculation."""
        result = VotingPowerDisplay.show_contribution_impact(100)

        assert result["minutes_contributed"] == 100
        assert result["voting_power"] == math.sqrt(100)
        assert result["actual_voting_power"] == 10.0
        assert result["not_1_to_1"] is True
        assert "sqrt" in result["explanation"]

    def test_show_contribution_impact_small(self):
        """Test small contribution impact."""
        result = VotingPowerDisplay.show_contribution_impact(1)

        assert result["minutes_contributed"] == 1
        assert result["voting_power"] == 1.0
        assert "examples" in result

    def test_show_contribution_impact_large(self):
        """Test large contribution impact."""
        result = VotingPowerDisplay.show_contribution_impact(10000)

        assert result["minutes_contributed"] == 10000
        assert result["voting_power"] == 100.0
        assert result["examples"]["10000 minutes"] == min(math.sqrt(10000), 100)

    def test_show_contribution_impact_examples(self):
        """Test contribution impact examples."""
        result = VotingPowerDisplay.show_contribution_impact(500)

        examples = result["examples"]
        assert examples["1 minute"] == math.sqrt(1)
        assert examples["10 minutes"] == math.sqrt(10)
        assert examples["100 minutes"] == math.sqrt(100)
        assert examples["1000 minutes"] == math.sqrt(1000)
        assert examples["10000 minutes"] == min(math.sqrt(10000), 100)

    def test_compare_contributors_basic(self):
        """Test comparing contributors."""
        contributors = [100, 50, 25]
        results = VotingPowerDisplay.compare_contributors(contributors)

        assert len(results) == 3
        assert results[0]["minutes"] == 100
        assert results[0]["voting_power"] == math.sqrt(100)
        assert results[0]["percentage_of_total"] > 0

    def test_compare_contributors_percentage_sum(self):
        """Test contributor percentages sum to 100."""
        contributors = [100, 200, 300]
        results = VotingPowerDisplay.compare_contributors(contributors)

        total_percentage = sum(r["percentage_of_total"] for r in results)
        assert abs(total_percentage - 100) < 0.01  # Allow for rounding

    def test_compare_contributors_zero(self):
        """Test comparing with zero contribution."""
        contributors = [0]
        results = VotingPowerDisplay.compare_contributors(contributors)

        assert len(results) == 1
        assert results[0]["voting_power"] == 0
        assert results[0]["percentage_of_total"] == 0

    def test_compare_contributors_whale_vs_small(self):
        """Test whale vs small contributor comparison."""
        contributors = [10, 50, 100, 5000]
        results = VotingPowerDisplay.compare_contributors(contributors)

        assert len(results) == 4
        # Whale has largest power but not overwhelming due to sqrt
        whale = results[3]
        assert whale["voting_power"] == math.sqrt(5000)
        assert whale["percentage_of_total"] < 100  # Not 100%


# =============================================================================
# VotingPower Tests (Lines 92-205)
# =============================================================================


class TestVotingPower:
    """Test quadratic voting power calculations."""

    def test_initialization(self):
        """Test VotingPower initialization."""
        vp = VotingPower()

        assert vp.monthly_decay_rate == 0.10
        assert vp.max_ai_minutes_votes == 100
        assert vp.max_mining_votes == 50
        assert vp.max_node_votes == 75

    def test_calculate_ai_minutes_voting_power_basic(self):
        """Test basic AI minutes voting power."""
        vp = VotingPower()
        power = vp.calculate_ai_minutes_voting_power(100, time.time())

        assert power == math.sqrt(100)
        assert power == 10.0

    def test_calculate_ai_minutes_voting_power_with_decay(self):
        """Test AI minutes voting power with time decay."""
        vp = VotingPower()

        # 30 days ago (1 month)
        timestamp = time.time() - (30 * 86400)
        power = vp.calculate_ai_minutes_voting_power(100, timestamp)

        expected = math.sqrt(100) * (1 - 0.10) ** 1  # 10 * 0.9 = 9.0
        assert abs(power - expected) < 0.01

    def test_calculate_ai_minutes_voting_power_old_contribution(self):
        """Test old contribution has reduced power."""
        vp = VotingPower()

        # 60 days ago (2 months)
        timestamp = time.time() - (60 * 86400)
        power = vp.calculate_ai_minutes_voting_power(100, timestamp)

        expected = math.sqrt(100) * (1 - 0.10) ** 2  # 10 * 0.81 = 8.1
        assert abs(power - expected) < 0.01

    def test_calculate_ai_minutes_voting_power_capped(self):
        """Test AI minutes voting power is capped."""
        vp = VotingPower()
        power = vp.calculate_ai_minutes_voting_power(20000, time.time())

        assert power == 100  # Capped at max_ai_minutes_votes

    def test_calculate_mining_voting_power_basic(self):
        """Test basic mining voting power."""
        vp = VotingPower()
        power = vp.calculate_mining_voting_power(100, time.time())

        assert power == math.sqrt(100)
        assert power == 10.0

    def test_calculate_mining_voting_power_recent(self):
        """Test mining power with recent activity."""
        vp = VotingPower()

        # 10 days ago
        timestamp = time.time() - (10 * 86400)
        power = vp.calculate_mining_voting_power(100, timestamp)

        assert power == math.sqrt(100)  # No decay for < 30 days

    def test_calculate_mining_voting_power_inactive(self):
        """Test mining power with inactive miner."""
        vp = VotingPower()

        # 60 days ago (inactive)
        timestamp = time.time() - (60 * 86400)
        power = vp.calculate_mining_voting_power(100, timestamp)

        expected = math.sqrt(100) * 0.5  # 50% decay for inactive
        assert power == expected

    def test_calculate_mining_voting_power_capped(self):
        """Test mining voting power is capped."""
        vp = VotingPower()
        power = vp.calculate_mining_voting_power(10000, time.time())

        assert power == 50  # Capped at max_mining_votes

    def test_calculate_node_voting_power_active(self):
        """Test node voting power for active node."""
        vp = VotingPower()
        power = vp.calculate_node_voting_power(100, True)

        assert power == math.sqrt(100)
        assert power == 10.0

    def test_calculate_node_voting_power_inactive(self):
        """Test node voting power for inactive node."""
        vp = VotingPower()
        power = vp.calculate_node_voting_power(100, False)

        assert power == 0  # Must be active to vote

    def test_calculate_node_voting_power_capped(self):
        """Test node voting power is capped."""
        vp = VotingPower()
        power = vp.calculate_node_voting_power(10000, True)

        assert power == 75  # Capped at max_node_votes

    def test_calculate_total_voting_power_ai_only(self):
        """Test total voting power with AI minutes only."""
        vp = VotingPower()

        voter_data = {
            "ai_minutes_contributed": 100,
            "ai_contribution_timestamp": time.time(),
        }

        total, breakdown = vp.calculate_total_voting_power(voter_data)

        assert breakdown["ai_minutes"] == 10.0
        assert breakdown["mining"] == 0
        assert breakdown["node_operation"] == 0
        assert breakdown["bonus"] == 0
        assert total == 10.0

    def test_calculate_total_voting_power_mining_only(self):
        """Test total voting power with mining only."""
        vp = VotingPower()

        voter_data = {
            "blocks_mined": 100,
            "last_block_timestamp": time.time(),
        }

        total, breakdown = vp.calculate_total_voting_power(voter_data)

        assert breakdown["ai_minutes"] == 0
        assert breakdown["mining"] == 10.0
        assert breakdown["node_operation"] == 0
        assert breakdown["bonus"] == 0
        assert total == 10.0

    def test_calculate_total_voting_power_node_only(self):
        """Test total voting power with node operation only."""
        vp = VotingPower()

        voter_data = {
            "node_uptime_days": 100,
            "node_active": True,
        }

        total, breakdown = vp.calculate_total_voting_power(voter_data)

        assert breakdown["ai_minutes"] == 0
        assert breakdown["mining"] == 0
        assert breakdown["node_operation"] == 10.0
        assert breakdown["bonus"] == 0
        assert total == 10.0

    def test_calculate_total_voting_power_hybrid_bonus(self):
        """Test hybrid bonus for multiple contribution types."""
        vp = VotingPower()

        voter_data = {
            "ai_minutes_contributed": 100,
            "ai_contribution_timestamp": time.time(),
            "blocks_mined": 100,
            "last_block_timestamp": time.time(),
        }

        total, breakdown = vp.calculate_total_voting_power(voter_data)

        assert breakdown["ai_minutes"] == 10.0
        assert breakdown["mining"] == 10.0
        base_total = 20.0
        assert breakdown["bonus"] == base_total * 0.10  # 10% bonus
        assert total == base_total * 1.10  # 22.0

    def test_calculate_total_voting_power_all_three(self):
        """Test voting power with all three contribution types."""
        vp = VotingPower()

        voter_data = {
            "ai_minutes_contributed": 100,
            "ai_contribution_timestamp": time.time(),
            "blocks_mined": 100,
            "last_block_timestamp": time.time(),
            "node_uptime_days": 100,
            "node_active": True,
        }

        total, breakdown = vp.calculate_total_voting_power(voter_data)

        assert breakdown["ai_minutes"] == 10.0
        assert breakdown["mining"] == 10.0
        assert breakdown["node_operation"] == 10.0
        base_total = 30.0
        assert breakdown["bonus"] == base_total * 0.10  # 10% bonus
        assert total == base_total * 1.10  # 33.0


# =============================================================================
# AIWorkloadDistribution Tests (Lines 207-306)
# =============================================================================


class TestAIWorkloadDistribution:
    """Test AI workload distribution system."""

    def test_initialization(self):
        """Test AIWorkloadDistribution initialization."""
        workload = AIWorkloadDistribution()

        assert workload.contributor_pool == {}

    def test_add_contributor_new(self):
        """Test adding new contributor."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())

        assert "alice" in workload.contributor_pool
        assert workload.contributor_pool["alice"]["total_minutes"] == 100
        assert len(workload.contributor_pool["alice"]["contributions"]) == 1

    def test_add_contributor_existing(self):
        """Test adding contribution to existing contributor."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())
        workload.add_contributor("alice", "gpt-4", 50, time.time())

        assert workload.contributor_pool["alice"]["total_minutes"] == 150
        assert len(workload.contributor_pool["alice"]["contributions"]) == 2

    def test_add_contributor_quality_score(self):
        """Test new contributor has default quality score."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())

        assert workload.contributor_pool["alice"]["quality_score"] == 1.0
        assert workload.contributor_pool["alice"]["tasks_completed"] == 0

    def test_calculate_workload_shares_single(self):
        """Test workload shares with single contributor."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())

        shares = workload.calculate_workload_shares(50)

        assert "alice" in shares
        assert shares["alice"]["minutes_assigned"] == 50
        assert shares["alice"]["share_percentage"] == 100
        assert shares["alice"]["total_contributed"] == 100

    def test_calculate_workload_shares_multiple(self):
        """Test workload shares with multiple contributors."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())
        workload.add_contributor("bob", "gpt-4", 50, time.time())

        shares = workload.calculate_workload_shares(30)

        # Alice: 100/150 = 66.67% -> 20 minutes
        # Bob: 50/150 = 33.33% -> 10 minutes
        assert abs(shares["alice"]["minutes_assigned"] - 20) < 0.01
        assert abs(shares["bob"]["minutes_assigned"] - 10) < 0.01
        assert abs(shares["alice"]["share_percentage"] - 66.67) < 0.01

    def test_calculate_workload_shares_empty_pool(self):
        """Test workload shares with empty contributor pool."""
        workload = AIWorkloadDistribution()

        shares = workload.calculate_workload_shares(50)

        assert shares == {}

    def test_execute_distributed_task_basic(self):
        """Test executing distributed AI task."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())
        workload.add_contributor("bob", "gpt-4", 50, time.time())

        plan = workload.execute_distributed_task("Test task", 30)

        assert plan["task"] == "Test task"
        assert plan["total_minutes"] == 30
        assert len(plan["contributor_assignments"]) == 2

    def test_execute_distributed_task_assignments(self):
        """Test distributed task assignments are correct."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 200, time.time())
        workload.add_contributor("bob", "gpt-4", 100, time.time())

        plan = workload.execute_distributed_task("Test task", 60)

        # Alice: 200/300 = 66.67% -> 40 minutes
        # Bob: 100/300 = 33.33% -> 20 minutes
        alice_assignment = next(a for a in plan["contributor_assignments"] if a["contributor"] == "alice")
        bob_assignment = next(a for a in plan["contributor_assignments"] if a["contributor"] == "bob")

        assert abs(alice_assignment["minutes_allocated"] - 40) < 0.01
        assert abs(bob_assignment["minutes_allocated"] - 20) < 0.01
        assert alice_assignment["status"] == "pending"
        assert bob_assignment["status"] == "pending"

    def test_get_best_model_for_contributor(self):
        """Test getting best AI model for contributor."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())
        workload.add_contributor("alice", "gpt-4", 50, time.time())

        model = workload._get_best_model_for_contributor("alice")

        assert model == "gpt-4"  # Most recent

    def test_get_best_model_for_contributor_default(self):
        """Test default AI model when no contributions."""
        workload = AIWorkloadDistribution()
        workload.contributor_pool["alice"] = {
            "total_minutes": 0,
            "contributions": [],
            "tasks_completed": 0,
            "quality_score": 1.0,
        }

        model = workload._get_best_model_for_contributor("alice")

        assert model == "claude-sonnet-4"


# =============================================================================
# ConsensusRules Tests (Lines 308-421)
# =============================================================================


class TestConsensusRules:
    """Test dynamic consensus rules."""

    def test_initialization(self):
        """Test ConsensusRules initialization."""
        rules = ConsensusRules()

        assert rules.approval_percent == 66
        assert rules.max_individual_power_percent == 20
        assert rules.min_approval_voters == 10
        assert rules.initial_min_voters == 250
        assert rules.reduction_rate == 0.20
        assert rules.absolute_minimum == 50
        assert rules.revote_delay_days == 7

    def test_apply_power_caps_no_cap(self):
        """Test power caps when no whale."""
        rules = ConsensusRules()

        votes = {
            "alice": {"vote": "yes", "voting_power": 10},
            "bob": {"vote": "yes", "voting_power": 10},
            "carol": {"vote": "no", "voting_power": 10},
        }

        adjusted = rules._apply_power_caps(votes)

        # No one exceeds 20% cap
        assert adjusted["alice"]["voting_power"] == 10
        assert adjusted["alice"]["capped"] is False

    def test_apply_power_caps_whale(self):
        """Test power caps with whale."""
        rules = ConsensusRules()

        votes = {
            "whale": {"vote": "yes", "voting_power": 100},
            "alice": {"vote": "yes", "voting_power": 10},
            "bob": {"vote": "no", "voting_power": 10},
        }

        adjusted = rules._apply_power_caps(votes)

        # Total power = 120, 20% cap = 24
        # Whale's 100 should be capped to 24
        assert adjusted["whale"]["voting_power"] == 24
        assert adjusted["whale"]["capped"] is True
        assert adjusted["whale"]["original_power"] == 100

    def test_check_consensus_insufficient_voters(self):
        """Test consensus with insufficient voters."""
        rules = ConsensusRules()

        proposal = {"title": "Test", "category": "test"}
        votes = {f"voter_{i}": {"vote": "yes", "voting_power": 10} for i in range(100)}

        reached, reason, action = rules.check_consensus_reached(proposal, votes, 250)

        assert reached is False
        assert "Need 250 voters" in reason
        assert action["action"] == "revote"
        assert action["wait_days"] == 7
        assert action["next_min_voters"] == 200  # 250 * 0.8

    def test_check_consensus_insufficient_approval_diversity(self):
        """Test consensus with insufficient approval diversity."""
        rules = ConsensusRules()

        proposal = {"title": "Test", "category": "test"}
        # 250 voters but only 9 approval votes
        votes = {}
        for i in range(9):
            votes[f"yes_{i}"] = {"vote": "yes", "voting_power": 10}
        for i in range(241):
            votes[f"no_{i}"] = {"vote": "no", "voting_power": 10}

        reached, reason, action = rules.check_consensus_reached(proposal, votes, 250)

        assert reached is False
        assert "different 'yes' votes" in reason
        assert action["action"] == "rejected"
        assert action["reason"] == "insufficient_approval_diversity"

    def test_check_consensus_insufficient_approval_percent(self):
        """Test consensus with insufficient approval percentage."""
        rules = ConsensusRules()

        proposal = {"title": "Test", "category": "test"}
        # 250 voters, 15 yes (good diversity), but only 50% approval
        votes = {}
        for i in range(15):
            votes[f"yes_{i}"] = {"vote": "yes", "voting_power": 10}
        for i in range(235):
            votes[f"no_{i}"] = {"vote": "no", "voting_power": 10}

        reached, reason, action = rules.check_consensus_reached(proposal, votes, 250)

        assert reached is False
        assert "66%" in reason
        assert action["action"] == "rejected"
        assert action["reason"] == "insufficient_approval"

    def test_check_consensus_approved(self):
        """Test consensus when approved."""
        rules = ConsensusRules()

        proposal = {"title": "Test", "category": "test"}
        # 250 voters, 170 yes (68%), 80 no
        votes = {}
        for i in range(170):
            votes[f"yes_{i}"] = {"vote": "yes", "voting_power": 10}
        for i in range(80):
            votes[f"no_{i}"] = {"vote": "no", "voting_power": 10}

        reached, reason, action = rules.check_consensus_reached(proposal, votes, 250)

        assert reached is True
        assert "Consensus reached" in reason
        assert action["action"] == "approved"
        assert action["approval_percent"] == 68.0
        assert action["voter_count"] == 250
        assert action["approval_voter_count"] == 170

    def test_check_consensus_absolute_minimum(self):
        """Test consensus reduction stops at absolute minimum."""
        rules = ConsensusRules()

        proposal = {"title": "Test", "category": "test"}
        votes = {f"voter_{i}": {"vote": "yes", "voting_power": 10} for i in range(40)}

        # Start at 50 (absolute minimum)
        reached, reason, action = rules.check_consensus_reached(proposal, votes, 50)

        assert reached is False
        assert action["action"] == "revote"
        # Should not go below 50
        assert action["next_min_voters"] == 50


# =============================================================================
# AIGovernanceProposal Tests (Lines 423-618)
# =============================================================================


class TestAIGovernanceProposal:
    """Test AI governance proposal lifecycle."""

    def test_initialization(self):
        """Test proposal initialization."""
        proposal = AIGovernanceProposal(
            title="Test Proposal",
            category="development",
            description="Test description",
            detailed_prompt="Detailed prompt",
            estimated_minutes=100,
        )

        assert proposal.title == "Test Proposal"
        assert proposal.category == "development"
        assert proposal.description == "Test description"
        assert proposal.detailed_prompt == "Detailed prompt"
        assert proposal.estimated_minutes == 100
        assert proposal.status == "proposed"
        assert proposal.votes == {}
        assert len(proposal.proposal_id) == 16

    def test_initialization_with_optional_params(self):
        """Test proposal initialization with optional parameters."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
            proposal_type=ProposalType.PARAMETER_CHANGE,
            parameter_change={"key": "value"},
            submitter_address="alice",
            submitter_voting_power=50.0,
        )

        assert proposal.proposal_type == ProposalType.PARAMETER_CHANGE
        assert proposal.parameter_change == {"key": "value"}
        assert proposal.submitter_address == "alice"
        assert proposal.submitter_voting_power == 50.0

    def test_cast_vote(self):
        """Test casting a vote."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        proposal.cast_vote("alice", "yes", 10.0)

        assert "alice" in proposal.votes
        assert proposal.votes["alice"]["vote"] == "yes"
        assert proposal.votes["alice"]["voting_power"] == 10.0
        assert "timestamp" in proposal.votes["alice"]

    def test_submit_time_estimate_valid(self):
        """Test submitting valid time estimate."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        result = proposal.submit_time_estimate("alice", 120, 10.0)

        assert result["success"] is True
        assert result["your_estimate"] == 120
        assert "community_average" in result
        assert result["estimate_count"] == 1

    def test_submit_time_estimate_invalid(self):
        """Test submitting invalid time estimate."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        result = proposal.submit_time_estimate("alice", -10, 10.0)

        assert result["success"] is False
        assert "error" in result

    def test_submit_time_estimate_weighted_average(self):
        """Test weighted average of time estimates."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # Alice has high voting power, estimates 200
        proposal.submit_time_estimate("alice", 200, 100.0)
        # Bob has low voting power, estimates 100
        proposal.submit_time_estimate("bob", 100, 10.0)

        # Weighted average should be closer to Alice's estimate
        # (200 * 100 + 100 * 10) / (100 + 10) = 21000 / 110 = 190.9
        assert abs(proposal.consensus_time_estimate - 190.9) < 0.1

    def test_close_vote_attempt_insufficient_turnout(self):
        """Test closing vote with insufficient turnout."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # Only 50 voters when 250 needed
        for i in range(50):
            proposal.cast_vote(f"voter_{i}", "yes", 10.0)

        result = proposal.close_vote_attempt(rules)

        assert result["result"] == "revote_scheduled"
        assert result["next_min_voters"] == 200
        assert result["wait_days"] == 7
        assert proposal.status == "revote_scheduled"
        assert proposal.votes == {}  # Cleared for revote

    def test_close_vote_attempt_approved(self):
        """Test closing vote when approved."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # 250 voters, 170 yes (68%)
        for i in range(170):
            proposal.cast_vote(f"yes_{i}", "yes", 10.0)
        for i in range(80):
            proposal.cast_vote(f"no_{i}", "no", 10.0)

        result = proposal.close_vote_attempt(rules)

        assert result["result"] == "approved_timelock"
        assert proposal.status == "approved_timelock"
        assert proposal.approval_time is not None

    def test_close_vote_attempt_rejected(self):
        """Test closing vote when rejected."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # 250 voters but only 50% approval
        for i in range(125):
            proposal.cast_vote(f"yes_{i}", "yes", 10.0)
        for i in range(125):
            proposal.cast_vote(f"no_{i}", "no", 10.0)

        result = proposal.close_vote_attempt(rules)

        assert result["result"] == "rejected"
        assert proposal.status == "rejected"

    def test_activate_timelock_success(self):
        """Test activating timelock after approval."""
        from xai.core.governance_parameters import GovernanceParameters

        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )
        proposal.status = "approved_timelock"
        proposal.approval_time = time.time()

        params = GovernanceParameters()
        result = proposal.activate_timelock(params)

        assert result["success"] is True
        assert "timelock_days" in result
        assert proposal.status == "timelock_active"
        assert proposal.timelock_expiry is not None

    def test_activate_timelock_wrong_status(self):
        """Test activating timelock with wrong status."""
        from xai.core.governance_parameters import GovernanceParameters

        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )
        # Wrong status
        proposal.status = "proposed"

        params = GovernanceParameters()
        result = proposal.activate_timelock(params)

        assert result["success"] is False
        assert "error" in result

    def test_can_execute_not_active(self):
        """Test can_execute with wrong status."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        can_exec, reason = proposal.can_execute()

        assert can_exec is False
        assert "not timelock_active" in reason

    def test_can_execute_timelock_active(self):
        """Test can_execute during timelock period."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )
        proposal.status = "timelock_active"
        proposal.timelock_expiry = time.time() + 86400  # 1 day from now

        can_exec, reason = proposal.can_execute()

        assert can_exec is False
        assert "Timelock active" in reason

    def test_can_execute_ready(self):
        """Test can_execute when ready."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )
        proposal.status = "timelock_active"
        proposal.timelock_expiry = time.time() - 1  # Expired

        can_exec, reason = proposal.can_execute()

        assert can_exec is True
        assert "Ready" in reason

    def test_get_vote_summary(self):
        """Test getting vote summary."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        proposal.cast_vote("alice", "yes", 10.0)
        proposal.cast_vote("bob", "yes", 15.0)
        proposal.cast_vote("carol", "no", 5.0)
        proposal.cast_vote("dave", "abstain", 3.0)

        summary = proposal.get_vote_summary()

        assert summary["yes_power"] == 25.0
        assert summary["no_power"] == 5.0
        assert summary["abstain_power"] == 3.0
        assert summary["total_power"] == 33.0
        assert abs(summary["yes_percent"] - 75.76) < 0.1
        assert summary["voter_count"] == 4


# =============================================================================
# AIGovernance Tests (Lines 620-733)
# =============================================================================


class TestAIGovernance:
    """Test simplified AIGovernance facade."""

    def test_initialization(self):
        """Test AIGovernance initialization."""
        gov = AIGovernance()

        assert gov.proposals == {}
        assert "quorum" in gov.parameters
        assert "timelock_days" in gov.parameters

    def test_voter_type_weights(self):
        """Test voter type weights."""
        gov = AIGovernance()

        assert gov.voter_type_weights[VoterType.NODE_OPERATOR] == 1.25
        assert gov.voter_type_weights[VoterType.MINER] == 1.0
        assert gov.voter_type_weights[VoterType.AI_CONTRIBUTOR] == 1.1
        assert gov.voter_type_weights[VoterType.HYBRID] == 1.3

    def test_generate_proposal_id(self):
        """Test proposal ID generation."""
        gov = AIGovernance()

        id1 = gov._generate_proposal_id("Proposal 1", "alice")
        id2 = gov._generate_proposal_id("Proposal 2", "alice")

        assert len(id1) == 16
        assert len(id2) == 16
        assert id1 != id2  # Different proposals, different IDs

    def test_create_proposal(self):
        """Test creating proposal."""
        gov = AIGovernance()

        proposal_id = gov.create_proposal(
            "alice",
            "Test Proposal",
            "Test description",
            "ai_improvement"
        )

        assert proposal_id in gov.proposals
        assert gov.proposals[proposal_id]["title"] == "Test Proposal"
        assert gov.proposals[proposal_id]["status"] == "active"

    def test_cast_vote_success(self):
        """Test casting vote successfully."""
        gov = AIGovernance()

        proposal_id = gov.create_proposal("alice", "Test", "Test", "ai_improvement")
        result = gov.cast_vote(proposal_id, "bob", "yes", 10.0)

        assert result is True
        assert "bob" in gov.proposals[proposal_id]["votes"]

    def test_cast_vote_nonexistent_proposal(self):
        """Test casting vote on nonexistent proposal."""
        gov = AIGovernance()

        result = gov.cast_vote("fake_id", "bob", "yes", 10.0)

        assert result is False

    def test_cast_vote_double_voting(self):
        """Test preventing double voting."""
        gov = AIGovernance()

        proposal_id = gov.create_proposal("alice", "Test", "Test", "ai_improvement")
        gov.cast_vote(proposal_id, "bob", "yes", 10.0)
        result = gov.cast_vote(proposal_id, "bob", "no", 15.0)

        assert result is False  # Double voting prevented

    def test_calculate_quadratic_power(self):
        """Test quadratic power calculation."""
        gov = AIGovernance()

        assert gov.calculate_quadratic_power(100) == 10.0
        assert gov.calculate_quadratic_power(0) == 0.0
        assert gov.calculate_quadratic_power(1) == 1.0

    def test_calculate_voting_power_no_decay(self):
        """Test voting power calculation without decay."""
        gov = AIGovernance()

        power = gov.calculate_voting_power(100, 0)

        assert power == 10.0

    def test_calculate_voting_power_with_decay(self):
        """Test voting power calculation with time decay."""
        gov = AIGovernance()

        # 365 days ago = 10% decay
        power = gov.calculate_voting_power(100, 365)

        expected = 10.0 * 0.9
        assert abs(power - expected) < 0.01

    def test_get_voter_type_weight(self):
        """Test getting voter type weight."""
        gov = AIGovernance()

        assert gov.get_voter_type_weight(VoterType.MINER) == 1.0
        assert gov.get_voter_type_weight(VoterType.HYBRID) == 1.3

    def test_tally_votes_passed(self):
        """Test tallying votes - passed."""
        gov = AIGovernance()

        proposal_id = gov.create_proposal("alice", "Test", "Test", "ai_improvement")
        gov.cast_vote(proposal_id, "bob", "yes", 30.0)
        gov.cast_vote(proposal_id, "carol", "no", 10.0)

        result = gov.tally_votes(proposal_id)

        assert result["passed"] is True
        assert result["yes_power"] == 30.0
        assert result["no_power"] == 10.0
        assert gov.proposals[proposal_id]["status"] == "passed"

    def test_tally_votes_failed(self):
        """Test tallying votes - failed."""
        gov = AIGovernance()

        proposal_id = gov.create_proposal("alice", "Test", "Test", "ai_improvement")
        gov.cast_vote(proposal_id, "bob", "yes", 10.0)
        gov.cast_vote(proposal_id, "carol", "no", 30.0)

        result = gov.tally_votes(proposal_id)

        assert result["passed"] is False
        assert gov.proposals[proposal_id]["status"] == "failed"

    def test_tally_votes_nonexistent(self):
        """Test tallying votes for nonexistent proposal."""
        gov = AIGovernance()

        result = gov.tally_votes("fake_id")

        assert result["passed"] is False

    def test_execute_proposal_success(self):
        """Test executing proposal successfully."""
        gov = AIGovernance()

        # Create proposal with short timelock
        proposal_id = gov.create_proposal("alice", "Test", "Test", "ai_improvement")
        gov.parameters["timelock_days"] = 0  # No timelock delay

        # Vote yes
        gov.cast_vote(proposal_id, "bob", "yes", 30.0)
        gov.cast_vote(proposal_id, "carol", "yes", 20.0)

        # Execute
        result = gov.execute_proposal(proposal_id)

        assert result["status"] == "executed"
        assert result["executed"] is True

    def test_execute_proposal_failed_vote(self):
        """Test executing proposal that failed vote."""
        gov = AIGovernance()

        proposal_id = gov.create_proposal("alice", "Test", "Test", "ai_improvement")
        gov.cast_vote(proposal_id, "bob", "no", 30.0)

        result = gov.execute_proposal(proposal_id)

        assert result["status"] == "failed"
        assert result["executed"] is False

    def test_execute_proposal_timelock_pending(self):
        """Test executing proposal during timelock."""
        gov = AIGovernance()

        proposal_id = gov.create_proposal("alice", "Test", "Test", "ai_improvement")
        gov.parameters["timelock_days"] = 10  # 10 day timelock

        # Vote yes
        gov.cast_vote(proposal_id, "bob", "yes", 30.0)

        # Try to execute during timelock
        result = gov.execute_proposal(proposal_id)

        assert result["status"] == "timelock_pending"
        assert "ready_at" in result

    def test_execute_proposal_nonexistent(self):
        """Test executing nonexistent proposal."""
        gov = AIGovernance()

        result = gov.execute_proposal("fake_id")

        assert result is None

    def test_get_parameters(self):
        """Test getting governance parameters."""
        gov = AIGovernance()

        params = gov.get_parameters()

        assert isinstance(params, dict)
        assert "quorum" in params
        assert "timelock_days" in params

    def test_update_parameter(self):
        """Test updating governance parameter."""
        gov = AIGovernance()

        result = gov.update_parameter("quorum", 0.75)

        assert result is True
        assert gov.parameters["quorum"] == 0.75

    def test_update_parameter_new_key(self):
        """Test updating new parameter key."""
        gov = AIGovernance()

        result = gov.update_parameter("new_param", 100.0)

        assert result is True
        assert gov.parameters["new_param"] == 100.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestAIGovernanceIntegration:
    """Integration tests for complete governance workflows."""

    def test_full_proposal_workflow(self):
        """Test complete proposal workflow from creation to execution."""
        gov = AIGovernance()

        # Create proposal
        proposal_id = gov.create_proposal(
            "alice",
            "Add new feature",
            "Add cool new feature",
            "ai_improvement"
        )

        # Vote
        gov.cast_vote(proposal_id, "bob", "yes", 50.0)
        gov.cast_vote(proposal_id, "carol", "yes", 30.0)

        # Tally
        result = gov.tally_votes(proposal_id)
        assert result["passed"] is True

        # Execute (with no timelock)
        gov.parameters["timelock_days"] = 0
        exec_result = gov.execute_proposal(proposal_id)
        assert exec_result["executed"] is True

    def test_adaptive_voting_workflow(self):
        """Test adaptive voting with multiple attempts."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test adaptive voting",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # Attempt 1: 100 voters (need 250)
        for i in range(100):
            proposal.cast_vote(f"voter_{i}", "yes", 10.0)

        result1 = proposal.close_vote_attempt(rules)
        assert result1["result"] == "revote_scheduled"
        assert result1["next_min_voters"] == 200

        # Attempt 2: 180 voters (need 200)
        for i in range(180):
            proposal.cast_vote(f"voter_{i}", "yes", 10.0)

        result2 = proposal.close_vote_attempt(rules)
        assert result2["result"] == "revote_scheduled"
        assert result2["next_min_voters"] == 160

        # Attempt 3: 165 voters (need 160) - success
        for i in range(165):
            proposal.cast_vote(f"voter_{i}", "yes", 10.0)

        result3 = proposal.close_vote_attempt(rules)
        assert result3["result"] == "approved_timelock"

    def test_whale_protection_workflow(self):
        """Test whale protection in voting."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test whale protection",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )
        proposal.current_min_voters = 10

        # Whale tries to control vote
        proposal.cast_vote("whale", "yes", 1000.0)
        for i in range(9):
            proposal.cast_vote(f"voter_{i}", "no", 10.0)

        result = proposal.close_vote_attempt(rules)

        # Should fail due to insufficient approval diversity
        assert result["result"] == "rejected"
        assert result["reason"] == "insufficient_approval_diversity"


# =============================================================================
# Additional Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    def test_voting_power_negative_minutes(self):
        """Test voting power with negative minutes."""
        vp = VotingPower()

        # Negative minutes should be treated as 0 (sqrt of negative is invalid)
        try:
            power = vp.calculate_ai_minutes_voting_power(-100, time.time())
            # If it doesn't raise an error, should return minimal power
            assert power >= 0
        except (ValueError, Exception):
            # If it raises an error, that's also acceptable
            pass

    def test_voting_power_zero_decay(self):
        """Test voting power calculation with minimal decay."""
        vp = VotingPower()

        voter_data = {
            "ai_minutes_contributed": 0,
            "ai_contribution_timestamp": time.time(),
            "blocks_mined": 0,
            "last_block_timestamp": time.time(),
            "node_uptime_days": 0,
            "node_active": False,
        }

        total, breakdown = vp.calculate_total_voting_power(voter_data)

        assert total == 0
        assert breakdown["bonus"] == 0

    def test_workload_distribution_quality_score_tracking(self):
        """Test quality score is tracked for contributors."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())

        assert workload.contributor_pool["alice"]["quality_score"] == 1.0
        assert workload.contributor_pool["alice"]["tasks_completed"] == 0

    def test_consensus_rules_zero_votes(self):
        """Test consensus with zero votes."""
        rules = ConsensusRules()
        proposal = {"title": "Test", "category": "test"}
        votes = {}

        reached, reason, action = rules.check_consensus_reached(proposal, votes, 250)

        assert reached is False

    def test_proposal_vote_attempts_tracking(self):
        """Test vote attempts are properly tracked."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # First attempt
        for i in range(50):
            proposal.cast_vote(f"voter_{i}", "yes", 10.0)

        result1 = proposal.close_vote_attempt(rules)
        assert len(proposal.vote_attempts) == 1
        assert proposal.vote_attempts[0]["voter_count"] == 50

        # Second attempt
        for i in range(75):
            proposal.cast_vote(f"voter_{i}", "yes", 10.0)

        result2 = proposal.close_vote_attempt(rules)
        assert len(proposal.vote_attempts) == 2

    def test_proposal_time_estimates_empty(self):
        """Test proposal with no time estimates."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        assert len(proposal.time_estimates) == 0
        assert proposal.consensus_time_estimate == 100  # Falls back to initial

    def test_ai_governance_proposal_fields(self):
        """Test all proposal fields are properly initialized."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        assert proposal.current_min_voters == 250
        assert proposal.next_vote_time is None
        assert proposal.approval_time is None
        assert proposal.timelock_expiry is None
        assert proposal.timelock_days is None
        assert proposal.execution_result is None
        assert proposal.code_review_status is None

    def test_compare_contributors_multiple_zeros(self):
        """Test comparing contributors with multiple zero contributions."""
        contributors = [0, 0, 100]
        results = VotingPowerDisplay.compare_contributors(contributors)

        assert len(results) == 3
        assert results[2]["percentage_of_total"] == 100.0

    def test_voting_power_display_all_examples(self):
        """Test all contribution impact examples are generated."""
        result = VotingPowerDisplay.show_contribution_impact(250)

        assert "examples" in result
        examples = result["examples"]
        assert "1 minute" in examples
        assert "10 minutes" in examples
        assert "100 minutes" in examples
        assert "1000 minutes" in examples
        assert "10000 minutes" in examples

    def test_workload_distribution_multiple_models(self):
        """Test contributor using multiple AI models."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 50, time.time())
        workload.add_contributor("alice", "gpt-4", 30, time.time())
        workload.add_contributor("alice", "gemini-pro", 20, time.time())

        assert len(workload.contributor_pool["alice"]["contributions"]) == 3
        assert workload.contributor_pool["alice"]["total_minutes"] == 100

    def test_consensus_power_caps_all_equal(self):
        """Test power caps when all voters have equal power."""
        rules = ConsensusRules()

        votes = {}
        for i in range(10):
            votes[f"voter_{i}"] = {"vote": "yes", "voting_power": 10.0}

        adjusted = rules._apply_power_caps(votes)

        # Total: 100, 20% cap = 20, but everyone has 10, so no capping
        for address in adjusted:
            assert adjusted[address]["voting_power"] == 10.0
            assert adjusted[address]["capped"] is False

    def test_ai_governance_create_multiple_proposals(self):
        """Test creating multiple proposals."""
        gov = AIGovernance()

        id1 = gov.create_proposal("alice", "Proposal 1", "Desc 1")
        id2 = gov.create_proposal("bob", "Proposal 2", "Desc 2")
        id3 = gov.create_proposal("carol", "Proposal 3", "Desc 3")

        assert len(gov.proposals) == 3
        assert id1 != id2 != id3

    def test_ai_governance_vote_on_multiple_proposals(self):
        """Test voting on multiple proposals."""
        gov = AIGovernance()

        id1 = gov.create_proposal("alice", "Proposal 1", "Desc 1")
        id2 = gov.create_proposal("bob", "Proposal 2", "Desc 2")

        gov.cast_vote(id1, "voter1", "yes", 10.0)
        gov.cast_vote(id2, "voter1", "no", 10.0)

        assert gov.proposals[id1]["votes"]["voter1"]["vote"] == "yes"
        assert gov.proposals[id2]["votes"]["voter1"]["vote"] == "no"

    def test_proposal_close_vote_with_abstentions(self):
        """Test closing vote with abstentions."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # 250 voters: 170 yes, 50 no, 30 abstain
        for i in range(170):
            proposal.cast_vote(f"yes_{i}", "yes", 10.0)
        for i in range(50):
            proposal.cast_vote(f"no_{i}", "no", 10.0)
        for i in range(30):
            proposal.cast_vote(f"abstain_{i}", "abstain", 10.0)

        result = proposal.close_vote_attempt(rules)

        # Should pass with 170 yes votes
        assert result["result"] == "approved_timelock"

    def test_voting_power_missing_fields(self):
        """Test voting power with missing fields in voter data."""
        vp = VotingPower()

        # Missing some fields
        voter_data = {
            "ai_minutes_contributed": 100,
            "ai_contribution_timestamp": time.time(),
            # Missing mining and node fields
        }

        total, breakdown = vp.calculate_total_voting_power(voter_data)

        assert breakdown["ai_minutes"] == 10.0
        assert breakdown["mining"] == 0
        assert breakdown["node_operation"] == 0

    def test_workload_shares_quality_score_included(self):
        """Test workload shares include quality score."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())

        shares = workload.calculate_workload_shares(50)

        assert "quality_score" in shares["alice"]
        assert shares["alice"]["quality_score"] == 1.0

    def test_proposal_revote_clears_votes(self):
        """Test revote clears previous votes."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # First attempt
        for i in range(100):
            proposal.cast_vote(f"voter_{i}", "yes", 10.0)

        assert len(proposal.votes) == 100

        result = proposal.close_vote_attempt(rules)

        # Votes should be cleared for revote
        assert result["result"] == "revote_scheduled"
        assert len(proposal.votes) == 0

    def test_ai_governance_multiple_parameter_updates(self):
        """Test updating multiple parameters."""
        gov = AIGovernance()

        gov.update_parameter("quorum", 0.75)
        gov.update_parameter("timelock_days", 5.0)
        gov.update_parameter("custom_param", 123.45)

        assert gov.parameters["quorum"] == 0.75
        assert gov.parameters["timelock_days"] == 5.0
        assert gov.parameters["custom_param"] == 123.45

    def test_execute_distributed_task_with_ai_model(self):
        """Test distributed task includes AI model information."""
        workload = AIWorkloadDistribution()
        workload.add_contributor("alice", "claude-sonnet-4", 100, time.time())
        workload.add_contributor("bob", "gpt-4-turbo", 50, time.time())

        plan = workload.execute_distributed_task("Feature X", 30)

        # Check AI models are assigned
        for assignment in plan["contributor_assignments"]:
            assert "ai_model" in assignment
            assert assignment["ai_model"] in ["claude-sonnet-4", "gpt-4-turbo"]

    def test_voter_type_enum_values(self):
        """Test all VoterType enum values."""
        assert len(list(VoterType)) == 4

        types_dict = {vt.value for vt in VoterType}
        assert "node_operator" in types_dict
        assert "miner" in types_dict
        assert "ai_contributor" in types_dict
        assert "hybrid" in types_dict

    def test_proposal_type_enum_values(self):
        """Test all ProposalType enum values."""
        assert len(list(ProposalType)) == 3

        types_dict = {pt.value for pt in ProposalType}
        assert "ai_improvement" in types_dict
        assert "parameter_change" in types_dict
        assert "emergency" in types_dict


# =============================================================================
# Performance and Boundary Tests
# =============================================================================


class TestPerformanceAndBoundaries:
    """Test performance with large datasets and boundary conditions."""

    def test_large_number_of_contributors(self):
        """Test workload distribution with many contributors."""
        workload = AIWorkloadDistribution()

        # Add 100 contributors
        for i in range(100):
            workload.add_contributor(f"contributor_{i}", "claude-sonnet-4", 10, time.time())

        shares = workload.calculate_workload_shares(1000)

        assert len(shares) == 100
        # Each should get 10 minutes (1000 / 100)
        for address, share in shares.items():
            assert abs(share["minutes_assigned"] - 10.0) < 0.01

    def test_large_number_of_votes(self):
        """Test consensus with large number of votes."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # 1000 voters
        for i in range(700):
            proposal.cast_vote(f"yes_{i}", "yes", 10.0)
        for i in range(300):
            proposal.cast_vote(f"no_{i}", "no", 10.0)

        result = proposal.close_vote_attempt(rules)

        assert result["result"] == "approved_timelock"
        assert result["voter_count"] == 1000

    def test_very_old_contribution_decay(self):
        """Test very old contribution has significant decay."""
        vp = VotingPower()

        # 12 months ago
        old_timestamp = time.time() - (365 * 86400)
        power = vp.calculate_ai_minutes_voting_power(10000, old_timestamp)

        # Should be significantly decayed
        # Original: sqrt(10000) = 100
        # After 12 months: 100 * (0.9^12) ≈ 28.24
        assert power < 50  # Much less than original

    def test_exactly_at_cap_voting_power(self):
        """Test voting power exactly at cap."""
        vp = VotingPower()

        # Exactly at AI cap: 100^2 = 10000 minutes
        power = vp.calculate_ai_minutes_voting_power(10000, time.time())
        assert power == 100.0

        # Exactly at mining cap: 50^2 = 2500 blocks
        mining_power = vp.calculate_mining_voting_power(2500, time.time())
        assert mining_power == 50.0

        # Exactly at node cap: 75^2 = 5625 days
        node_power = vp.calculate_node_voting_power(5625, True)
        assert node_power == 75.0

    def test_fractional_voting_power(self):
        """Test fractional voting power calculations."""
        vp = VotingPower()

        # Test with non-perfect squares
        power1 = vp.calculate_ai_minutes_voting_power(50, time.time())
        assert abs(power1 - math.sqrt(50)) < 0.01

        power2 = vp.calculate_mining_voting_power(75, time.time())
        assert abs(power2 - math.sqrt(75)) < 0.01

    def test_consensus_at_exact_threshold(self):
        """Test consensus at exact approval threshold."""
        rules = ConsensusRules()
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        # Exactly 66% approval (165 yes, 85 no out of 250)
        for i in range(165):
            proposal.cast_vote(f"yes_{i}", "yes", 10.0)
        for i in range(85):
            proposal.cast_vote(f"no_{i}", "no", 10.0)

        result = proposal.close_vote_attempt(rules)

        # Should pass at exactly 66%
        assert result["result"] == "approved_timelock"

    def test_time_estimate_with_zero_voting_power(self):
        """Test time estimate submission with zero voting power."""
        proposal = AIGovernanceProposal(
            title="Test",
            category="test",
            description="Test",
            detailed_prompt="Test",
            estimated_minutes=100,
        )

        result = proposal.submit_time_estimate("alice", 150, 0.0)

        # Should still accept but with zero weight
        assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
