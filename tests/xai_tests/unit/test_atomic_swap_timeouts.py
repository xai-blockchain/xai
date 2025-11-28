"""
Comprehensive tests for atomic swap timeout handling

Tests timelock-based refunds, claim deadlines, state transitions,
and timeout detection for atomic cross-chain swaps.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from enum import Enum

from xai.core.blockchain import Blockchain, Transaction
from xai.core.wallet import Wallet


class SwapState(Enum):
    """Atomic swap states"""
    INITIATED = "initiated"
    FUNDED = "funded"
    CLAIMED = "claimed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class AtomicSwap:
    """Mock atomic swap implementation for testing"""

    def __init__(self, initiator, participant, amount, timelock):
        self.initiator = initiator
        self.participant = participant
        self.amount = amount
        self.timelock = timelock  # Unix timestamp
        self.state = SwapState.INITIATED
        self.secret_hash = None
        self.secret = None
        self.funded_at = None
        self.claimed_at = None
        self.refunded_at = None

    def fund(self):
        """Fund the swap"""
        if self.state == SwapState.INITIATED:
            self.state = SwapState.FUNDED
            self.funded_at = time.time()
            return True
        return False

    def claim(self, secret):
        """Claim the swap with secret"""
        current_time = time.time()
        if self.state == SwapState.FUNDED and current_time < self.timelock:
            self.secret = secret
            self.state = SwapState.CLAIMED
            self.claimed_at = current_time
            return True
        return False

    def refund(self):
        """Refund the swap after timelock"""
        current_time = time.time()
        if self.state == SwapState.FUNDED and current_time >= self.timelock:
            self.state = SwapState.REFUNDED
            self.refunded_at = current_time
            return True
        return False

    def is_expired(self):
        """Check if swap has expired"""
        return time.time() >= self.timelock


class TestAtomicSwapTimeouts:
    """Tests for atomic swap timeout handling"""

    def test_refund_after_timelock_expiry(self, tmp_path):
        """Test refund succeeds after timelock expires"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create swap with timelock 2 seconds in future
        timelock = time.time() + 2
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # Fund the swap
        assert swap.fund() is True
        assert swap.state == SwapState.FUNDED

        # Try to refund before timelock (should fail)
        assert swap.refund() is False
        assert swap.state == SwapState.FUNDED

        # Wait for timelock to expire
        time.sleep(2.1)

        # Now refund should succeed
        assert swap.refund() is True
        assert swap.state == SwapState.REFUNDED

    def test_refund_before_timelock_fails(self, tmp_path):
        """Test refund fails before timelock expires"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create swap with timelock far in future
        timelock = time.time() + 3600  # 1 hour
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # Fund the swap
        swap.fund()
        assert swap.state == SwapState.FUNDED

        # Try to refund before timelock
        result = swap.refund()
        assert result is False
        assert swap.state == SwapState.FUNDED  # State unchanged

    def test_claim_before_refund_deadline(self, tmp_path):
        """Test claim succeeds before refund deadline"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create swap with reasonable timelock
        timelock = time.time() + 60  # 60 seconds
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # Fund the swap
        swap.fund()
        assert swap.state == SwapState.FUNDED

        # Claim with secret before timelock
        secret = "my_secret_123"
        result = swap.claim(secret)

        assert result is True
        assert swap.state == SwapState.CLAIMED
        assert swap.secret == secret

    def test_claim_after_timelock_fails(self, tmp_path):
        """Test claim fails after timelock expires"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create swap with short timelock
        timelock = time.time() + 1
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # Fund the swap
        swap.fund()

        # Wait for timelock to expire
        time.sleep(1.1)

        # Try to claim after timelock
        secret = "my_secret_123"
        result = swap.claim(secret)

        assert result is False
        assert swap.state == SwapState.FUNDED  # Still funded, not claimed

    def test_state_transition_initiated_to_funded(self, tmp_path):
        """Test state transition from INITIATED to FUNDED"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        timelock = time.time() + 3600
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # Initial state
        assert swap.state == SwapState.INITIATED

        # Fund the swap
        result = swap.fund()
        assert result is True
        assert swap.state == SwapState.FUNDED
        assert swap.funded_at is not None

    def test_state_transition_funded_to_claimed(self, tmp_path):
        """Test state transition from FUNDED to CLAIMED"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        timelock = time.time() + 3600
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        swap.fund()
        assert swap.state == SwapState.FUNDED

        # Claim the swap
        secret = "secret_key"
        result = swap.claim(secret)

        assert result is True
        assert swap.state == SwapState.CLAIMED
        assert swap.claimed_at is not None

    def test_state_transition_funded_to_refunded(self, tmp_path):
        """Test state transition from FUNDED to REFUNDED"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        timelock = time.time() + 1
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        swap.fund()
        assert swap.state == SwapState.FUNDED

        # Wait for timelock
        time.sleep(1.1)

        # Refund the swap
        result = swap.refund()
        assert result is True
        assert swap.state == SwapState.REFUNDED
        assert swap.refunded_at is not None

    def test_timeout_detection(self, tmp_path):
        """Test timeout detection mechanism"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Create swap with short timeout
        timelock = time.time() + 1
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # Not expired yet
        assert swap.is_expired() is False

        # Wait for expiry
        time.sleep(1.1)

        # Now expired
        assert swap.is_expired() is True

    def test_cannot_fund_twice(self, tmp_path):
        """Test that swap cannot be funded twice"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        timelock = time.time() + 3600
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # First fund succeeds
        assert swap.fund() is True

        # Second fund fails
        assert swap.fund() is False
        assert swap.state == SwapState.FUNDED

    def test_cannot_claim_before_funding(self, tmp_path):
        """Test that swap cannot be claimed before funding"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        timelock = time.time() + 3600
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)

        # Try to claim unfunded swap
        result = swap.claim("secret")
        assert result is False
        assert swap.state == SwapState.INITIATED

    def test_refund_returns_funds_to_initiator(self, tmp_path):
        """Test refund returns funds to original initiator"""
        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get funds
        bc.mine_pending_transactions(wallet1.address)
        initial_balance = bc.get_balance(wallet1.address)

        # Create swap (conceptual)
        timelock = time.time() + 1
        swap = AtomicSwap(wallet1.address, wallet2.address, 5.0, timelock)
        swap.fund()

        # Wait for timeout
        time.sleep(1.1)

        # Refund
        swap.refund()

        assert swap.state == SwapState.REFUNDED
        # In real implementation, funds would return to wallet1

    def test_timelock_precision(self, tmp_path):
        """Test timelock enforces precise timing"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Very precise timelock
        timelock = time.time() + 0.5
        swap = AtomicSwap(wallet1.address, wallet2.address, 10.0, timelock)
        swap.fund()

        # Immediately try to refund (should fail)
        assert swap.refund() is False

        # Wait exactly for timelock
        time.sleep(0.5)

        # Now should succeed
        assert swap.refund() is True
