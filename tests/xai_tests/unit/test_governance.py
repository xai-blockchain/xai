"""
Comprehensive tests for Governance module.

Tests cover:
- VoteLocker: Token locking, voting power calculation, time-weighted voting
- QuadraticVoter: Quadratic voting mechanics, sybil resistance
- ProposalManager: Proposal lifecycle, voting, tallying, finalization
"""

import time
import threading
from typing import Any

import pytest


# ============= VoteLocker Tests =============


class TestVoteLockerInit:
    """Tests for VoteLocker initialization."""

    def test_init_with_defaults(self):
        """Test VoteLocker initializes with default values."""
        from xai.governance.vote_locker import VoteLocker

        locker = VoteLocker()
        assert locker.base_duration == 86400
        assert locker.early_unlock_penalty_percentage == 10.0
        assert locker.locked_tokens == {}
        assert locker._lock_id_counter == 0

    def test_init_with_custom_values(self):
        """Test VoteLocker with custom parameters."""
        from xai.governance.vote_locker import VoteLocker

        locker = VoteLocker(base_duration=3600, early_unlock_penalty_percentage=5.0)
        assert locker.base_duration == 3600
        assert locker.early_unlock_penalty_percentage == 5.0


class TestVoteLockerLocking:
    """Tests for token locking functionality."""

    @pytest.fixture
    def locker(self):
        """Create a VoteLocker instance."""
        from xai.governance.vote_locker import VoteLocker
        return VoteLocker(base_duration=100)

    def test_lock_tokens_returns_id(self, locker):
        """Test that lock_tokens returns a unique ID."""
        lock_id = locker.lock_tokens("0xUser", 100.0, 1000)
        assert lock_id == 1

    def test_lock_tokens_increments_id(self, locker):
        """Test lock IDs increment properly."""
        id1 = locker.lock_tokens("0xUser", 100.0, 1000)
        id2 = locker.lock_tokens("0xUser", 50.0, 500)
        assert id2 == id1 + 1

    def test_lock_tokens_creates_entry(self, locker):
        """Test that lock creates correct entry."""
        locker.lock_tokens("0xUser", 100.0, 1000)

        assert "0xUser" in locker.locked_tokens
        assert len(locker.locked_tokens["0xUser"]) == 1

        entry = locker.locked_tokens["0xUser"][0]
        assert entry["amount"] == 100.0
        assert entry["lock_duration"] == 1000

    def test_lock_tokens_multiple_locks_same_user(self, locker):
        """Test multiple locks for the same user."""
        locker.lock_tokens("0xUser", 100.0, 1000)
        locker.lock_tokens("0xUser", 50.0, 500)
        locker.lock_tokens("0xUser", 25.0, 250)

        assert len(locker.locked_tokens["0xUser"]) == 3

    def test_lock_tokens_empty_address_raises(self, locker):
        """Test that empty address raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            locker.lock_tokens("", 100.0, 1000)

    def test_lock_tokens_zero_amount_raises(self, locker):
        """Test that zero amount raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            locker.lock_tokens("0xUser", 0, 1000)

    def test_lock_tokens_negative_amount_raises(self, locker):
        """Test that negative amount raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            locker.lock_tokens("0xUser", -100.0, 1000)

    def test_lock_tokens_zero_duration_raises(self, locker):
        """Test that zero duration raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            locker.lock_tokens("0xUser", 100.0, 0)

    def test_lock_tokens_negative_duration_raises(self, locker):
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="positive"):
            locker.lock_tokens("0xUser", 100.0, -1000)


class TestVoteLockerVotingPower:
    """Tests for voting power calculation."""

    @pytest.fixture
    def locker(self):
        """Create a VoteLocker instance."""
        from xai.governance.vote_locker import VoteLocker
        return VoteLocker(base_duration=100)

    def test_voting_power_no_locks(self, locker):
        """Test voting power is zero when no locks exist."""
        power = locker.get_voting_power("0xNoLocks")
        assert power == 0.0

    def test_voting_power_single_lock(self, locker):
        """Test voting power calculation for single lock."""
        locker.lock_tokens("0xUser", 100.0, 100)
        current_time = int(time.time())

        power = locker.get_voting_power("0xUser", current_time)
        # power = amount * (time_remaining / base_duration)
        # power = 100 * (100 / 100) = 100
        assert abs(power - 100.0) < 1.0  # Allow small timing variance

    def test_voting_power_decays_over_time(self, locker):
        """Test that voting power decays as lock expires."""
        locker.lock_tokens("0xUser", 100.0, 100)
        base_time = int(time.time())

        power_start = locker.get_voting_power("0xUser", base_time)
        power_mid = locker.get_voting_power("0xUser", base_time + 50)
        power_near_end = locker.get_voting_power("0xUser", base_time + 90)

        assert power_start > power_mid > power_near_end

    def test_voting_power_zero_after_expiry(self, locker):
        """Test voting power is zero after lock expires."""
        locker.lock_tokens("0xUser", 100.0, 100)
        expired_time = int(time.time()) + 200

        power = locker.get_voting_power("0xUser", expired_time)
        assert power == 0.0

    def test_voting_power_multiple_locks_summed(self, locker):
        """Test that voting power sums across multiple locks."""
        locker.lock_tokens("0xUser", 100.0, 100)
        locker.lock_tokens("0xUser", 50.0, 100)
        current_time = int(time.time())

        power = locker.get_voting_power("0xUser", current_time)
        # Both locks have similar multipliers
        assert power > 100.0  # At least sum of both

    def test_voting_power_longer_lock_more_power(self, locker):
        """Test longer locks get more voting power."""
        locker.lock_tokens("0xShort", 100.0, 100)
        locker.lock_tokens("0xLong", 100.0, 200)
        current_time = int(time.time())

        short_power = locker.get_voting_power("0xShort", current_time)
        long_power = locker.get_voting_power("0xLong", current_time)

        assert long_power > short_power


class TestVoteLockerLockDetails:
    """Tests for get_lock_details method."""

    @pytest.fixture
    def locker(self):
        """Create a VoteLocker instance."""
        from xai.governance.vote_locker import VoteLocker
        return VoteLocker(base_duration=100)

    def test_get_lock_details_empty(self, locker):
        """Test lock details for user with no locks."""
        details = locker.get_lock_details("0xNoLocks")
        assert details == []

    def test_get_lock_details_single_lock(self, locker):
        """Test lock details for single lock."""
        lock_id = locker.lock_tokens("0xUser", 100.0, 1000)
        details = locker.get_lock_details("0xUser")

        assert len(details) == 1
        assert details[0]["lock_id"] == lock_id
        assert details[0]["amount"] == 100.0
        assert details[0]["lock_duration"] == 1000
        assert details[0]["is_active"] is True

    def test_get_lock_details_expired_lock(self, locker):
        """Test lock details for expired lock."""
        locker.lock_tokens("0xUser", 100.0, 10)
        expired_time = int(time.time()) + 100

        details = locker.get_lock_details("0xUser", expired_time)

        assert len(details) == 1
        assert details[0]["is_active"] is False
        assert details[0]["voting_power"] == 0.0


class TestVoteLockerEarlyUnlock:
    """Tests for early unlock with penalty."""

    @pytest.fixture
    def locker(self):
        """Create a VoteLocker instance."""
        from xai.governance.vote_locker import VoteLocker
        return VoteLocker(base_duration=100, early_unlock_penalty_percentage=10.0)

    def test_early_unlock_applies_penalty(self, locker):
        """Test that early unlock applies penalty."""
        lock_id = locker.lock_tokens("0xUser", 100.0, 1000)
        result = locker.early_unlock("0xUser", lock_id)

        assert result["amount_returned"] == 90.0
        assert result["penalty_amount"] == 10.0
        assert result["total_locked"] == 100.0

    def test_early_unlock_removes_lock(self, locker):
        """Test that early unlock removes the lock."""
        lock_id = locker.lock_tokens("0xUser", 100.0, 1000)
        locker.early_unlock("0xUser", lock_id)

        assert len(locker.locked_tokens["0xUser"]) == 0

    def test_early_unlock_nonexistent_user_raises(self, locker):
        """Test early unlock for nonexistent user raises error."""
        with pytest.raises(ValueError, match="No locks found"):
            locker.early_unlock("0xNoUser", 1)

    def test_early_unlock_nonexistent_lock_raises(self, locker):
        """Test early unlock for nonexistent lock ID raises error."""
        locker.lock_tokens("0xUser", 100.0, 1000)
        with pytest.raises(ValueError, match="not found"):
            locker.early_unlock("0xUser", 999)

    def test_early_unlock_expired_lock_raises(self, locker):
        """Test early unlock for expired lock raises error."""
        lock_id = locker.lock_tokens("0xUser", 100.0, 10)
        expired_time = int(time.time()) + 100

        with pytest.raises(ValueError, match="already expired"):
            locker.early_unlock("0xUser", lock_id, expired_time)


class TestVoteLockerWithdraw:
    """Tests for token withdrawal."""

    @pytest.fixture
    def locker(self):
        """Create a VoteLocker instance."""
        from xai.governance.vote_locker import VoteLocker
        return VoteLocker(base_duration=100)

    def test_withdraw_expired_tokens(self, locker):
        """Test withdrawing expired tokens."""
        locker.lock_tokens("0xUser", 100.0, 10)
        expired_time = int(time.time()) + 100

        withdrawn = locker.withdraw_tokens("0xUser", expired_time)
        assert withdrawn == 100.0

    def test_withdraw_no_expired_tokens(self, locker):
        """Test withdrawal when no tokens expired."""
        locker.lock_tokens("0xUser", 100.0, 10000)
        current_time = int(time.time())

        withdrawn = locker.withdraw_tokens("0xUser", current_time)
        assert withdrawn == 0.0

    def test_withdraw_partial_expired(self, locker):
        """Test withdrawal when only some locks expired."""
        locker.lock_tokens("0xUser", 100.0, 10)
        locker.lock_tokens("0xUser", 50.0, 10000)

        expired_time = int(time.time()) + 100
        withdrawn = locker.withdraw_tokens("0xUser", expired_time)

        assert withdrawn == 100.0
        assert len(locker.locked_tokens["0xUser"]) == 1

    def test_withdraw_no_user_returns_zero(self, locker):
        """Test withdrawal for nonexistent user returns zero."""
        withdrawn = locker.withdraw_tokens("0xNoUser")
        assert withdrawn == 0.0


# ============= QuadraticVoter Tests =============


class TestQuadraticVoterInit:
    """Tests for QuadraticVoter initialization."""

    def test_init_with_defaults(self):
        """Test QuadraticVoter initializes with default values."""
        from xai.governance.quadratic_voter import QuadraticVoter

        voter = QuadraticVoter()
        assert voter.minimum_stake_for_verification == 100.0
        assert voter.minimum_account_age_seconds == 86400

    def test_init_with_custom_values(self):
        """Test QuadraticVoter with custom parameters."""
        from xai.governance.quadratic_voter import QuadraticVoter

        voter = QuadraticVoter(
            minimum_stake_for_verification=50.0,
            minimum_account_age_seconds=3600
        )
        assert voter.minimum_stake_for_verification == 50.0
        assert voter.minimum_account_age_seconds == 3600


class TestQuadraticVoterBalance:
    """Tests for balance management."""

    @pytest.fixture
    def voter(self):
        """Create a QuadraticVoter instance."""
        from xai.governance.quadratic_voter import QuadraticVoter
        return QuadraticVoter()

    def test_set_balance(self, voter):
        """Test setting a balance."""
        voter.set_balance("0xUser", 100.0)
        assert voter.get_balance("0xUser") == 100.0

    def test_get_balance_nonexistent(self, voter):
        """Test getting balance for nonexistent user."""
        assert voter.get_balance("0xNoUser") == 0.0

    def test_set_balance_overwrites(self, voter):
        """Test that set_balance overwrites existing balance."""
        voter.set_balance("0xUser", 100.0)
        voter.set_balance("0xUser", 200.0)
        assert voter.get_balance("0xUser") == 200.0

    def test_set_balance_negative_raises(self, voter):
        """Test that negative balance raises error."""
        with pytest.raises(ValueError):
            voter.set_balance("0xUser", -100.0)


class TestQuadraticVotingMechanics:
    """Tests for quadratic voting cost calculations."""

    @pytest.fixture
    def voter(self):
        """Create a QuadraticVoter instance."""
        from xai.governance.quadratic_voter import QuadraticVoter
        return QuadraticVoter()

    def test_calculate_vote_cost_squared(self, voter):
        """Test vote cost is votes squared."""
        assert voter.calculate_vote_cost(1) == 1.0
        assert voter.calculate_vote_cost(2) == 4.0
        assert voter.calculate_vote_cost(3) == 9.0
        assert voter.calculate_vote_cost(10) == 100.0

    def test_calculate_vote_cost_zero(self, voter):
        """Test zero votes costs zero."""
        assert voter.calculate_vote_cost(0) == 0.0

    def test_calculate_vote_cost_negative_raises(self, voter):
        """Test negative votes raises error."""
        with pytest.raises(ValueError):
            voter.calculate_vote_cost(-1)

    def test_calculate_effective_votes_sqrt(self, voter):
        """Test effective votes is sqrt of tokens."""
        assert voter.calculate_effective_votes(1) == 1.0
        assert voter.calculate_effective_votes(4) == 2.0
        assert voter.calculate_effective_votes(9) == 3.0
        assert voter.calculate_effective_votes(100) == 10.0

    def test_calculate_effective_votes_zero(self, voter):
        """Test zero tokens gives zero votes."""
        assert voter.calculate_effective_votes(0) == 0.0

    def test_calculate_effective_votes_negative_raises(self, voter):
        """Test negative tokens raises error."""
        with pytest.raises(ValueError):
            voter.calculate_effective_votes(-1)


class TestQuadraticVoterCasting:
    """Tests for casting votes."""

    @pytest.fixture
    def voter(self):
        """Create a QuadraticVoter instance with funded user."""
        from xai.governance.quadratic_voter import QuadraticVoter
        v = QuadraticVoter()
        v.set_balance("0xUser", 1000.0)
        return v

    def test_cast_votes_deducts_cost(self, voter):
        """Test casting votes deducts quadratic cost."""
        voter.cast_votes("0xUser", 10)  # Cost: 100
        assert voter.get_balance("0xUser") == 900.0

    def test_cast_votes_returns_effective_votes(self, voter):
        """Test cast_votes returns effective vote count."""
        effective = voter.cast_votes("0xUser", 10)  # Cost: 100, sqrt(100) = 10
        assert effective == 10.0

    def test_cast_votes_insufficient_balance_raises(self, voter):
        """Test casting too many votes raises error."""
        with pytest.raises(ValueError, match="insufficient"):
            voter.cast_votes("0xUser", 100)  # Cost: 10000, balance: 1000

    def test_cast_votes_no_balance_raises(self, voter):
        """Test casting with no balance raises error."""
        with pytest.raises(ValueError, match="no balance"):
            voter.cast_votes("0xNoBalance", 1)


class TestQuadraticVoterSybilResistance:
    """Tests for sybil resistance mechanisms."""

    @pytest.fixture
    def voter(self):
        """Create a QuadraticVoter instance."""
        from xai.governance.quadratic_voter import QuadraticVoter
        return QuadraticVoter(
            minimum_stake_for_verification=100.0,
            minimum_account_age_seconds=3600
        )

    def test_register_voter(self, voter):
        """Test voter registration."""
        current_time = int(time.time())
        voter.register_voter("0xUser", current_time)
        assert "0xUser" in voter.account_creation_times

    def test_register_voter_with_identity_proof(self, voter):
        """Test voter registration with identity proof."""
        current_time = int(time.time())
        voter.register_voter("0xUser", current_time, "unique_identity_123")

        assert "0xUser" in voter.identity_hashes
        assert len(voter.hash_to_voters) == 1

    def test_duplicate_identity_detected(self, voter):
        """Test that duplicate identities are detected."""
        current_time = int(time.time())
        voter.register_voter("0xUser1", current_time, "same_identity")
        voter.register_voter("0xUser2", current_time, "same_identity")

        identity_hash = voter.identity_hashes["0xUser1"]
        assert len(voter.hash_to_voters[identity_hash]) == 2

    def test_verify_voter_stake(self, voter):
        """Test stake-based verification."""
        result = voter.verify_voter_stake("0xUser", 150.0)
        assert result is True
        assert "0xUser" in voter.verified_voters
        assert voter.voter_stakes["0xUser"] == 150.0

    def test_verify_voter_stake_insufficient(self, voter):
        """Test verification fails with insufficient stake."""
        result = voter.verify_voter_stake("0xUser", 50.0)
        assert result is False
        assert "0xUser" not in voter.verified_voters

    def test_add_social_proof(self, voter):
        """Test social proof endorsement."""
        voter.verify_voter_stake("0xEndorser", 100.0)
        voter.add_social_proof("0xUser", "0xEndorser")

        assert "0xUser" in voter.endorsements
        assert "0xEndorser" in voter.endorsements["0xUser"]

    def test_social_proof_from_unverified_raises(self, voter):
        """Test endorsement from unverified voter raises error."""
        with pytest.raises(ValueError, match="not verified"):
            voter.add_social_proof("0xUser", "0xUnverified")

    def test_social_proof_auto_verification(self, voter):
        """Test auto-verification with 3+ endorsements."""
        for i in range(3):
            voter.verify_voter_stake(f"0xEndorser{i}", 100.0)
            voter.add_social_proof("0xUser", f"0xEndorser{i}")

        assert "0xUser" in voter.verified_voters

    def test_is_verified_checks_account_age(self, voter):
        """Test is_verified checks minimum account age."""
        current_time = int(time.time())
        voter.register_voter("0xNewUser", current_time)
        voter.verify_voter_stake("0xNewUser", 100.0)

        # Account too new
        assert voter.is_verified("0xNewUser", current_time) is False

        # Account old enough
        assert voter.is_verified("0xNewUser", current_time + 3601) is True


# ============= ProposalManager Tests =============


class TestProposalManagerInit:
    """Tests for ProposalManager initialization."""

    def test_init_with_valid_params(self):
        """Test ProposalManager initializes with valid parameters."""
        from xai.governance.proposal_manager import ProposalManager

        manager = ProposalManager(minimum_stake_for_proposal=100.0)
        assert manager.minimum_stake_for_proposal == 100.0
        assert manager.quorum_percentage == 10.0
        assert manager.approval_threshold == 51.0

    def test_init_with_custom_params(self):
        """Test ProposalManager with custom parameters."""
        from xai.governance.proposal_manager import ProposalManager

        manager = ProposalManager(
            minimum_stake_for_proposal=50.0,
            quorum_percentage=20.0,
            approval_threshold=60.0,
            voting_period_seconds=86400
        )
        assert manager.quorum_percentage == 20.0
        assert manager.approval_threshold == 60.0
        assert manager.voting_period_seconds == 86400

    def test_init_invalid_stake_raises(self):
        """Test invalid stake parameter raises error."""
        from xai.governance.proposal_manager import ProposalManager

        with pytest.raises(ValueError):
            ProposalManager(minimum_stake_for_proposal=0)

        with pytest.raises(ValueError):
            ProposalManager(minimum_stake_for_proposal=-100)

    def test_init_invalid_quorum_raises(self):
        """Test invalid quorum percentage raises error."""
        from xai.governance.proposal_manager import ProposalManager

        with pytest.raises(ValueError):
            ProposalManager(minimum_stake_for_proposal=100, quorum_percentage=0)

        with pytest.raises(ValueError):
            ProposalManager(minimum_stake_for_proposal=100, quorum_percentage=101)

    def test_init_invalid_threshold_raises(self):
        """Test invalid approval threshold raises error."""
        from xai.governance.proposal_manager import ProposalManager

        with pytest.raises(ValueError):
            ProposalManager(minimum_stake_for_proposal=100, approval_threshold=0)

        with pytest.raises(ValueError):
            ProposalManager(minimum_stake_for_proposal=100, approval_threshold=101)


class TestProposalManagerSubmission:
    """Tests for proposal submission."""

    @pytest.fixture
    def manager(self):
        """Create a ProposalManager instance."""
        from xai.governance.proposal_manager import ProposalManager
        return ProposalManager(minimum_stake_for_proposal=100.0)

    def test_submit_proposal_returns_id(self, manager):
        """Test proposal submission returns ID."""
        proposal_id = manager.submit_proposal("0xProposer", "Test proposal", 150.0)
        assert proposal_id == "proposal_1"

    def test_submit_proposal_increments_id(self, manager):
        """Test proposal IDs increment."""
        id1 = manager.submit_proposal("0xProposer", "Proposal 1", 150.0)
        id2 = manager.submit_proposal("0xProposer", "Proposal 2", 150.0)
        assert id1 == "proposal_1"
        assert id2 == "proposal_2"

    def test_submit_proposal_creates_entry(self, manager):
        """Test proposal creates correct entry."""
        proposal_id = manager.submit_proposal("0xProposer", "Test details", 150.0)

        assert proposal_id in manager.active_proposals
        proposal = manager.active_proposals[proposal_id]
        assert proposal["proposer"] == "0xProposer"
        assert proposal["proposal_details"] == "Test details"
        assert proposal["staked_amount"] == 150.0
        assert proposal["status"] == "voting"

    def test_submit_proposal_insufficient_stake_raises(self, manager):
        """Test submission with insufficient stake raises error."""
        with pytest.raises(ValueError, match="less than"):
            manager.submit_proposal("0xProposer", "Test", 50.0)

    def test_submit_proposal_empty_address_raises(self, manager):
        """Test submission with empty address raises error."""
        with pytest.raises(ValueError, match="empty"):
            manager.submit_proposal("", "Test", 150.0)

    def test_submit_proposal_empty_details_raises(self, manager):
        """Test submission with empty details raises error."""
        with pytest.raises(ValueError, match="empty"):
            manager.submit_proposal("0xProposer", "", 150.0)


class TestProposalManagerVoting:
    """Tests for voting on proposals."""

    @pytest.fixture
    def manager(self):
        """Create a ProposalManager with a proposal."""
        from xai.governance.proposal_manager import ProposalManager
        m = ProposalManager(
            minimum_stake_for_proposal=100.0,
            voting_period_seconds=3600
        )
        m.submit_proposal("0xProposer", "Test proposal", 150.0)
        m.set_total_voting_supply(1000.0)
        return m

    def test_cast_vote_for(self, manager):
        """Test casting a vote for a proposal."""
        manager.cast_vote("proposal_1", "0xVoter1", True, 50.0)

        proposal = manager.active_proposals["proposal_1"]
        assert proposal["votes_for"] == 50.0
        assert proposal["votes_against"] == 0.0

    def test_cast_vote_against(self, manager):
        """Test casting a vote against a proposal."""
        manager.cast_vote("proposal_1", "0xVoter1", False, 50.0)

        proposal = manager.active_proposals["proposal_1"]
        assert proposal["votes_for"] == 0.0
        assert proposal["votes_against"] == 50.0

    def test_cast_vote_tracks_voter(self, manager):
        """Test that voters are tracked."""
        manager.cast_vote("proposal_1", "0xVoter1", True, 50.0)

        proposal = manager.active_proposals["proposal_1"]
        assert "0xVoter1" in proposal["voters"]

    def test_double_vote_raises(self, manager):
        """Test that double voting raises error."""
        manager.cast_vote("proposal_1", "0xVoter1", True, 50.0)

        with pytest.raises(ValueError, match="already voted"):
            manager.cast_vote("proposal_1", "0xVoter1", False, 50.0)

    def test_vote_nonexistent_proposal_raises(self, manager):
        """Test voting on nonexistent proposal raises error."""
        with pytest.raises(ValueError, match="not found"):
            manager.cast_vote("proposal_999", "0xVoter", True, 50.0)

    def test_vote_zero_power_raises(self, manager):
        """Test voting with zero power raises error."""
        with pytest.raises(ValueError, match="positive"):
            manager.cast_vote("proposal_1", "0xVoter", True, 0)

    def test_vote_negative_power_raises(self, manager):
        """Test voting with negative power raises error."""
        with pytest.raises(ValueError, match="positive"):
            manager.cast_vote("proposal_1", "0xVoter", True, -50.0)


class TestProposalManagerTallying:
    """Tests for vote tallying."""

    @pytest.fixture
    def manager(self):
        """Create a ProposalManager with votes."""
        from xai.governance.proposal_manager import ProposalManager
        m = ProposalManager(
            minimum_stake_for_proposal=100.0,
            quorum_percentage=10.0,
            approval_threshold=51.0,
            voting_period_seconds=3600
        )
        m.set_total_voting_supply(1000.0)
        m.submit_proposal("0xProposer", "Test proposal", 150.0)
        return m

    def test_get_vote_tally(self, manager):
        """Test getting vote tally."""
        manager.cast_vote("proposal_1", "0xVoter1", True, 60.0)
        manager.cast_vote("proposal_1", "0xVoter2", False, 40.0)

        tally = manager.get_vote_tally("proposal_1")

        assert tally["votes_for"] == 60.0
        assert tally["votes_against"] == 40.0
        assert tally["total_votes"] == 100.0
        assert tally["voter_count"] == 2
        assert tally["approval_percentage"] == 60.0

    def test_tally_quorum_check(self, manager):
        """Test quorum checking in tally."""
        manager.cast_vote("proposal_1", "0xVoter1", True, 150.0)  # 15% of supply

        tally = manager.get_vote_tally("proposal_1")
        assert tally["quorum_required"] == 100.0  # 10% of 1000
        assert tally["quorum_met"] is True

    def test_tally_quorum_not_met(self, manager):
        """Test quorum not met in tally."""
        manager.cast_vote("proposal_1", "0xVoter1", True, 50.0)  # 5% of supply

        tally = manager.get_vote_tally("proposal_1")
        assert tally["quorum_met"] is False


class TestProposalManagerFinalization:
    """Tests for proposal finalization."""

    def test_finalize_proposal_passes(self):
        """Test finalizing a passing proposal by manipulating voting_end."""
        from xai.governance.proposal_manager import ProposalManager
        manager = ProposalManager(
            minimum_stake_for_proposal=100.0,
            quorum_percentage=10.0,
            approval_threshold=51.0,
            voting_period_seconds=3600  # Long period, we'll manipulate it
        )
        manager.set_total_voting_supply(1000.0)
        manager.submit_proposal("0xProposer", "Test", 150.0)
        manager.cast_vote("proposal_1", "0xVoter1", True, 200.0)

        # Force the voting period to have ended
        manager.active_proposals["proposal_1"]["voting_end"] = int(time.time()) - 10
        result = manager.finalize_proposal("proposal_1")

        assert result["passed"] is True
        assert manager.active_proposals["proposal_1"]["status"] == "passed"

    def test_finalize_proposal_rejected_quorum(self):
        """Test finalizing a proposal rejected for quorum."""
        from xai.governance.proposal_manager import ProposalManager
        manager = ProposalManager(
            minimum_stake_for_proposal=100.0,
            quorum_percentage=10.0,
            approval_threshold=51.0,
            voting_period_seconds=3600
        )
        manager.set_total_voting_supply(1000.0)
        manager.submit_proposal("0xProposer", "Test", 150.0)
        manager.cast_vote("proposal_1", "0xVoter1", True, 50.0)  # Below quorum

        # Force the voting period to have ended
        manager.active_proposals["proposal_1"]["voting_end"] = int(time.time()) - 10
        result = manager.finalize_proposal("proposal_1")

        assert result["passed"] is False
        assert result["quorum_met"] is False

    def test_finalize_proposal_rejected_threshold(self):
        """Test finalizing a proposal rejected for threshold."""
        from xai.governance.proposal_manager import ProposalManager
        manager = ProposalManager(
            minimum_stake_for_proposal=100.0,
            quorum_percentage=10.0,
            approval_threshold=51.0,
            voting_period_seconds=3600
        )
        manager.set_total_voting_supply(1000.0)
        manager.submit_proposal("0xProposer", "Test", 150.0)
        manager.cast_vote("proposal_1", "0xVoter1", True, 60.0)
        manager.cast_vote("proposal_1", "0xVoter2", False, 100.0)

        # Force the voting period to have ended
        manager.active_proposals["proposal_1"]["voting_end"] = int(time.time()) - 10
        result = manager.finalize_proposal("proposal_1")

        assert result["passed"] is False
        assert result["threshold_met"] is False

    def test_finalize_before_end_raises(self):
        """Test finalizing before voting ends raises error."""
        from xai.governance.proposal_manager import ProposalManager
        manager = ProposalManager(
            minimum_stake_for_proposal=100.0,
            quorum_percentage=10.0,
            approval_threshold=51.0,
            voting_period_seconds=3600
        )
        manager.set_total_voting_supply(1000.0)
        manager.submit_proposal("0xProposer", "Test", 150.0)

        with pytest.raises(ValueError, match="not ended"):
            manager.finalize_proposal("proposal_1")


class TestProposalManagerStakeManagement:
    """Tests for stake slashing and returning."""

    @pytest.fixture
    def manager(self):
        """Create a ProposalManager instance."""
        from xai.governance.proposal_manager import ProposalManager
        m = ProposalManager(minimum_stake_for_proposal=100.0)
        m.submit_proposal("0xProposer", "Test", 150.0)
        return m

    def test_get_staked_amount(self, manager):
        """Test getting staked amount."""
        staked = manager.get_staked_amount("proposal_1")
        assert staked == 150.0

    def test_get_staked_amount_nonexistent_raises(self, manager):
        """Test getting stake for nonexistent proposal raises error."""
        with pytest.raises(ValueError, match="not found"):
            manager.get_staked_amount("proposal_999")

    def test_slash_stake(self, manager):
        """Test slashing stake."""
        manager.slash_stake("proposal_1", "Malicious activity")
        assert manager.active_proposals["proposal_1"]["status"] == "slashed"

    def test_return_stake(self, manager):
        """Test returning stake."""
        manager.return_stake("proposal_1")
        assert manager.active_proposals["proposal_1"]["status"] == "stake_returned"


class TestGovernanceThreadSafety:
    """Tests for thread safety."""

    def test_vote_locker_concurrent_locks(self):
        """Test concurrent token locking."""
        from xai.governance.vote_locker import VoteLocker
        locker = VoteLocker()

        def lock_tokens(user_id):
            for _ in range(10):
                locker.lock_tokens(f"0xUser{user_id}", 10.0, 1000)

        threads = [threading.Thread(target=lock_tokens, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each user should have 10 locks
        for i in range(5):
            assert len(locker.locked_tokens[f"0xUser{i}"]) == 10

    def test_quadratic_voter_concurrent_balance_updates(self):
        """Test concurrent balance updates."""
        from xai.governance.quadratic_voter import QuadraticVoter
        voter = QuadraticVoter()

        def update_balance(user_id):
            for i in range(10):
                voter.set_balance(f"0xUser{user_id}", float(i * 100))

        threads = [threading.Thread(target=update_balance, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All users should have a balance
        for i in range(5):
            assert voter.get_balance(f"0xUser{i}") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
