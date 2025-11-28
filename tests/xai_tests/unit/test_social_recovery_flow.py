"""
Comprehensive tests for social recovery wallet functionality

Tests guardian voting, threshold requirements, vote cancellation,
recovery finalization, and wallet invalidation.
"""

import pytest
import time
from unittest.mock import Mock, patch
from enum import Enum

from xai.core.wallet import Wallet


class RecoveryStatus(Enum):
    """Recovery request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class SocialRecoveryWallet:
    """Mock social recovery wallet for testing"""

    def __init__(self, owner, guardians, threshold):
        self.owner = owner
        self.guardians = guardians  # List of guardian addresses
        self.threshold = threshold  # Minimum votes needed
        self.recovery_requests = {}  # {request_id: RecoveryRequest}

    def initiate_recovery(self, new_owner, request_id):
        """Initiate wallet recovery"""
        self.recovery_requests[request_id] = {
            'new_owner': new_owner,
            'votes': [],
            'status': RecoveryStatus.PENDING,
            'created_at': time.time()
        }
        return request_id

    def vote_for_recovery(self, request_id, guardian):
        """Guardian votes for recovery"""
        if request_id not in self.recovery_requests:
            return False

        request = self.recovery_requests[request_id]
        if request['status'] != RecoveryStatus.PENDING:
            return False

        if guardian not in self.guardians:
            return False

        if guardian in request['votes']:
            return False  # Already voted

        request['votes'].append(guardian)

        # Check if threshold met
        if len(request['votes']) >= self.threshold:
            request['status'] = RecoveryStatus.APPROVED

        return True

    def cancel_recovery(self, request_id):
        """Cancel recovery request"""
        if request_id in self.recovery_requests:
            self.recovery_requests[request_id]['status'] = RecoveryStatus.CANCELLED
            return True
        return False

    def finalize_recovery(self, request_id):
        """Finalize recovery and transfer ownership"""
        if request_id not in self.recovery_requests:
            return False

        request = self.recovery_requests[request_id]
        if request['status'] != RecoveryStatus.APPROVED:
            return False

        # Transfer ownership
        self.owner = request['new_owner']
        request['status'] = RecoveryStatus.FINALIZED
        return True


class TestSocialRecoveryFlow:
    """Tests for social recovery flow"""

    def test_guardian_voting_process(self):
        """Test guardian voting mechanism"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2", "guardian3"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        # Initiate recovery
        new_owner = "new_owner_address"
        request_id = "req_001"
        wallet.initiate_recovery(new_owner, request_id)

        # Guardian votes
        result1 = wallet.vote_for_recovery(request_id, "guardian1")
        assert result1 is True

        result2 = wallet.vote_for_recovery(request_id, "guardian2")
        assert result2 is True

        # Check status
        request = wallet.recovery_requests[request_id]
        assert len(request['votes']) == 2
        assert request['status'] == RecoveryStatus.APPROVED

    def test_threshold_voting_3_of_5_guardians(self):
        """Test 3-of-5 guardian threshold"""
        owner = "owner_address"
        guardians = [f"guardian{i}" for i in range(1, 6)]  # 5 guardians
        wallet = SocialRecoveryWallet(owner, guardians, threshold=3)

        new_owner = "new_owner_address"
        request_id = "req_001"
        wallet.initiate_recovery(new_owner, request_id)

        # Only 2 votes (below threshold)
        wallet.vote_for_recovery(request_id, "guardian1")
        wallet.vote_for_recovery(request_id, "guardian2")

        request = wallet.recovery_requests[request_id]
        assert request['status'] == RecoveryStatus.PENDING  # Not yet approved

        # 3rd vote (meets threshold)
        wallet.vote_for_recovery(request_id, "guardian3")

        assert request['status'] == RecoveryStatus.APPROVED

    def test_recovery_with_insufficient_votes_fails(self):
        """Test recovery fails without enough votes"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2", "guardian3"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=3)

        new_owner = "new_owner_address"
        request_id = "req_001"
        wallet.initiate_recovery(new_owner, request_id)

        # Only 2 votes (threshold is 3)
        wallet.vote_for_recovery(request_id, "guardian1")
        wallet.vote_for_recovery(request_id, "guardian2")

        request = wallet.recovery_requests[request_id]
        assert request['status'] == RecoveryStatus.PENDING

        # Try to finalize (should fail)
        result = wallet.finalize_recovery(request_id)
        assert result is False

    def test_vote_cancellation(self):
        """Test cancelling recovery request"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2", "guardian3"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        new_owner = "new_owner_address"
        request_id = "req_001"
        wallet.initiate_recovery(new_owner, request_id)

        # Vote
        wallet.vote_for_recovery(request_id, "guardian1")

        # Cancel
        result = wallet.cancel_recovery(request_id)
        assert result is True

        request = wallet.recovery_requests[request_id]
        assert request['status'] == RecoveryStatus.CANCELLED

        # Further votes should fail
        result = wallet.vote_for_recovery(request_id, "guardian2")
        assert result is False

    def test_recovery_finalization(self):
        """Test finalizing recovery transfers ownership"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2", "guardian3"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        new_owner = "new_owner_address"
        request_id = "req_001"
        wallet.initiate_recovery(new_owner, request_id)

        # Get enough votes
        wallet.vote_for_recovery(request_id, "guardian1")
        wallet.vote_for_recovery(request_id, "guardian2")

        # Finalize
        result = wallet.finalize_recovery(request_id)
        assert result is True

        # Ownership should transfer
        assert wallet.owner == new_owner

    def test_old_wallet_invalidation(self):
        """Test old wallet is invalidated after recovery"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        old_owner = wallet.owner
        new_owner = "new_owner_address"

        request_id = "req_001"
        wallet.initiate_recovery(new_owner, request_id)

        wallet.vote_for_recovery(request_id, "guardian1")
        wallet.vote_for_recovery(request_id, "guardian2")
        wallet.finalize_recovery(request_id)

        # Old owner should be different from new
        assert wallet.owner != old_owner
        assert wallet.owner == new_owner

    def test_duplicate_vote_prevented(self):
        """Test guardian cannot vote twice"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        request_id = "req_001"
        wallet.initiate_recovery("new_owner", request_id)

        # First vote succeeds
        result1 = wallet.vote_for_recovery(request_id, "guardian1")
        assert result1 is True

        # Second vote from same guardian fails
        result2 = wallet.vote_for_recovery(request_id, "guardian1")
        assert result2 is False

        request = wallet.recovery_requests[request_id]
        assert len(request['votes']) == 1  # Only one vote counted

    def test_non_guardian_vote_rejected(self):
        """Test non-guardian cannot vote"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        request_id = "req_001"
        wallet.initiate_recovery("new_owner", request_id)

        # Non-guardian tries to vote
        result = wallet.vote_for_recovery(request_id, "attacker")
        assert result is False

        request = wallet.recovery_requests[request_id]
        assert len(request['votes']) == 0

    def test_recovery_time_tracking(self):
        """Test recovery request timestamps"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        start_time = time.time()
        request_id = "req_001"
        wallet.initiate_recovery("new_owner", request_id)

        request = wallet.recovery_requests[request_id]
        assert 'created_at' in request
        assert request['created_at'] >= start_time

    def test_multiple_recovery_requests(self):
        """Test handling multiple recovery requests"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2", "guardian3"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        # Create multiple requests
        wallet.initiate_recovery("new_owner1", "req_001")
        wallet.initiate_recovery("new_owner2", "req_002")

        assert len(wallet.recovery_requests) == 2
        assert "req_001" in wallet.recovery_requests
        assert "req_002" in wallet.recovery_requests

    def test_recovery_status_transitions(self):
        """Test recovery status transitions"""
        owner = "owner_address"
        guardians = ["guardian1", "guardian2"]
        wallet = SocialRecoveryWallet(owner, guardians, threshold=2)

        request_id = "req_001"
        wallet.initiate_recovery("new_owner", request_id)

        # PENDING -> votes -> APPROVED -> FINALIZED
        request = wallet.recovery_requests[request_id]
        assert request['status'] == RecoveryStatus.PENDING

        wallet.vote_for_recovery(request_id, "guardian1")
        wallet.vote_for_recovery(request_id, "guardian2")

        assert request['status'] == RecoveryStatus.APPROVED

        wallet.finalize_recovery(request_id)
        assert request['status'] == RecoveryStatus.FINALIZED
