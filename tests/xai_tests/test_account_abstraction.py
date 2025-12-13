"""
Comprehensive tests for Account Abstraction Gas Sponsorship (Task 178).

Tests cover:
- Sponsor registration and configuration
- Transaction authorization and signature verification
- Rate limiting enforcement
- Budget management and deduction
- Whitelist/blacklist access control
- Integration with transaction processing
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, patch

from xai.core.account_abstraction import (
    GasSponsor,
    SponsoredTransaction,
    SponsoredTransactionProcessor,
    SponsorshipResult,
    SponsorshipValidation,
    SponsorSignatureError,
    SponsorSignatureVerificationError,
    get_sponsored_transaction_processor,
    process_sponsored_transaction,
    AccountAbstractionManager,
)
from xai.core.transaction import Transaction
from xai.core.crypto_utils import generate_secp256k1_keypair_hex


class TestGasSponsor:
    """Tests for GasSponsor class."""

    def test_sponsor_initialization(self):
        """Test sponsor initializes with correct values."""
        sponsor = GasSponsor(
            sponsor_address="XAI1234567890abcdef",
            budget=100.0,
            rate_limit=10
        )

        assert sponsor.sponsor_address == "XAI1234567890abcdef"
        assert sponsor.total_budget == 100.0
        assert sponsor.remaining_budget == 100.0
        assert sponsor.rate_limit == 10
        assert sponsor.enabled is True
        assert len(sponsor.sponsored_transactions) == 0

    def test_sponsor_transaction_success(self):
        """Test successful transaction sponsorship."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=10)

        result = sponsor.sponsor_transaction("XAIuser123", 0.01)

        assert result is not None  # Returns preliminary txid
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hash
        assert sponsor.remaining_budget == 99.99
        assert len(sponsor.sponsored_transactions) == 1

    def test_sponsor_transaction_insufficient_budget(self):
        """Test sponsorship fails with insufficient budget."""
        sponsor = GasSponsor("XAI1234", 0.005, rate_limit=10)

        result = sponsor.sponsor_transaction("XAIuser123", 0.01)

        assert result is None
        assert sponsor.remaining_budget == 0.005  # Unchanged

    def test_sponsor_transaction_exceeds_per_tx_limit(self):
        """Test sponsorship fails when fee exceeds per-transaction limit."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=10)
        sponsor.max_gas_per_transaction = 0.05

        result = sponsor.sponsor_transaction("XAIuser123", 0.1)

        assert result is None

    def test_sponsor_transaction_disabled(self):
        """Test sponsorship fails when sponsor is disabled."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=10)
        sponsor.disable()

        result = sponsor.sponsor_transaction("XAIuser123", 0.01)

        assert result is None

    def test_sponsor_blacklist(self):
        """Test blacklisted users are rejected."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=10)
        sponsor.set_blacklist(["XAIbaduser"])

        result = sponsor.sponsor_transaction("XAIbaduser", 0.01)

        assert result is None

    def test_sponsor_whitelist(self):
        """Test whitelist enforcement."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=10)
        sponsor.set_whitelist(["XAIgooduser"])

        # Whitelisted user succeeds
        result = sponsor.sponsor_transaction("XAIgooduser", 0.01)
        assert result is not None

        # Non-whitelisted user fails
        result = sponsor.sponsor_transaction("XAIotheruser", 0.01)
        assert result is None

    def test_rate_limit_enforcement(self):
        """Test rate limiting prevents abuse."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=3)

        # First 3 transactions succeed
        assert sponsor.sponsor_transaction("XAIuser", 0.01) is not None
        assert sponsor.sponsor_transaction("XAIuser", 0.01) is not None
        assert sponsor.sponsor_transaction("XAIuser", 0.01) is not None

        # 4th transaction fails (rate limit exceeded)
        assert sponsor.sponsor_transaction("XAIuser", 0.01) is None

    def test_rate_limit_different_users(self):
        """Test rate limit is per-user."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=2)

        # User1 can do 2 transactions
        assert sponsor.sponsor_transaction("XAIuser1", 0.01) is not None
        assert sponsor.sponsor_transaction("XAIuser1", 0.01) is not None
        assert sponsor.sponsor_transaction("XAIuser1", 0.01) is None

        # User2 still has their own limit
        assert sponsor.sponsor_transaction("XAIuser2", 0.01) is not None
        assert sponsor.sponsor_transaction("XAIuser2", 0.01) is not None

    def test_add_budget(self):
        """Test budget can be increased."""
        sponsor = GasSponsor("XAI1234", 50.0, rate_limit=10)

        sponsor.add_budget(25.0)

        assert sponsor.total_budget == 75.0
        assert sponsor.remaining_budget == 75.0

    def test_get_stats(self):
        """Test stats reporting."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=10)
        sponsor.sponsor_transaction("XAIuser1", 0.01)
        sponsor.sponsor_transaction("XAIuser2", 0.02)

        stats = sponsor.get_stats()

        assert stats["sponsor_address"] == "XAI1234"
        assert stats["total_budget"] == 100.0
        assert stats["remaining_budget"] == 99.97
        assert stats["spent"] == 0.03
        assert stats["transaction_count"] == 2
        assert stats["unique_users"] == 2

    def test_get_user_usage(self):
        """Test per-user usage stats."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=10)
        sponsor.sponsor_transaction("XAIuser1", 0.01)
        sponsor.sponsor_transaction("XAIuser1", 0.02)

        usage = sponsor.get_user_usage("XAIuser1")

        assert usage["user_address"] == "XAIuser1"
        assert usage["total_transactions"] == 2
        assert usage["total_gas_sponsored"] == 0.03
        assert usage["rate_limit_remaining"] == 8


class TestSponsoredTransactionProcessor:
    """Tests for SponsoredTransactionProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create a fresh processor for each test."""
        return SponsoredTransactionProcessor()

    @pytest.fixture
    def sponsor_keys(self):
        """Generate sponsor key pair."""
        return generate_secp256k1_keypair_hex()

    @pytest.fixture
    def user_keys(self):
        """Generate user key pair."""
        return generate_secp256k1_keypair_hex()

    def test_register_sponsor(self, processor, sponsor_keys):
        """Test sponsor registration."""
        private_key, public_key = sponsor_keys
        sponsor_address = "XAI" + public_key[:40]

        sponsor = processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=public_key,
            budget=100.0,
            rate_limit=50
        )

        assert sponsor is not None
        assert sponsor.sponsor_address == sponsor_address
        assert sponsor.total_budget == 100.0
        assert processor.get_sponsor(sponsor_address) is sponsor

    def test_authorize_transaction(self, processor, sponsor_keys, user_keys):
        """Test transaction authorization with sponsor signature."""
        sponsor_private, sponsor_public = sponsor_keys
        user_private, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.01,
            public_key=user_public,
            gas_sponsor=sponsor_address
        )

        result = processor.authorize_transaction(tx, sponsor_private)

        assert result is True
        assert tx.gas_sponsor_signature is not None

    def test_verify_sponsor_signature(self, processor, sponsor_keys, user_keys):
        """Test sponsor signature verification."""
        sponsor_private, sponsor_public = sponsor_keys
        user_private, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.01,
            public_key=user_public,
            gas_sponsor=sponsor_address
        )

        processor.authorize_transaction(tx, sponsor_private)

        assert processor.verify_sponsor_signature(tx) is True

    def test_verify_invalid_signature(self, processor, sponsor_keys, user_keys):
        """Test invalid signature is rejected."""
        sponsor_private, sponsor_public = sponsor_keys
        user_private, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.01,
            public_key=user_public,
            gas_sponsor=sponsor_address
        )

        # Sign with wrong key (user key instead of sponsor key)
        processor.authorize_transaction(tx, user_private)

        # Signature verification should fail
        assert processor.verify_sponsor_signature(tx) is False

    def test_authorize_transaction_invalid_key_raises(self, processor, sponsor_keys, user_keys):
        """Signer errors should raise SponsorSignatureError instead of continuing."""
        sponsor_private, sponsor_public = sponsor_keys
        _, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=1.0,
        )
        tx = Transaction(
            sender="XAI1111111111111111111111111111111111111111",
            recipient="XAI2222222222222222222222222222222222222222",
            amount=1.0,
            fee=0.1,
            public_key=user_public,
            gas_sponsor=sponsor_address,
        )
        with pytest.raises(SponsorSignatureError):
            processor.authorize_transaction(tx, "not-a-hex-key")

    def test_verify_signature_malformed_payload_raises(self, processor, sponsor_keys, user_keys):
        """Malformed signatures must raise and stop execution."""
        sponsor_private, sponsor_public = sponsor_keys
        _, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=10.0,
        )
        tx = Transaction(
            sender="XAI1111111111111111111111111111111111111111",
            recipient="XAI2222222222222222222222222222222222222222",
            amount=1.0,
            fee=0.1,
            public_key=user_public,
            gas_sponsor=sponsor_address,
        )
        processor.authorize_transaction(tx, sponsor_private)
        tx.gas_sponsor_signature = "zzzz"  # invalid hex to force parsing failure
        with pytest.raises(SponsorSignatureVerificationError):
            processor.verify_sponsor_signature(tx)

    def test_validate_sponsored_transaction_approved(self, processor, sponsor_keys, user_keys):
        """Test validation approves valid sponsored transaction."""
        sponsor_private, sponsor_public = sponsor_keys
        user_private, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0,
            max_fee_per_tx=0.1
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.01,
            public_key=user_public,
            gas_sponsor=sponsor_address
        )

        processor.authorize_transaction(tx, sponsor_private)
        validation = processor.validate_sponsored_transaction(tx)

        assert validation.result == SponsorshipResult.APPROVED
        assert validation.sponsor_address == sponsor_address

    def test_validate_sponsor_not_found(self, processor, user_keys):
        """Test validation fails for unregistered sponsor."""
        user_private, user_public = user_keys
        user_address = "XAI" + user_public[:40]

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.01,
            public_key=user_public,
            gas_sponsor="XAIunknownsponsor12345678901234567890"
        )

        validation = processor.validate_sponsored_transaction(tx)

        assert validation.result == SponsorshipResult.SPONSOR_NOT_FOUND

    def test_validate_insufficient_budget(self, processor, sponsor_keys, user_keys):
        """Test validation fails with insufficient budget."""
        sponsor_private, sponsor_public = sponsor_keys
        user_private, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=0.005,  # Very low budget
            max_fee_per_tx=0.1
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.01,  # Higher than budget
            public_key=user_public,
            gas_sponsor=sponsor_address
        )

        processor.authorize_transaction(tx, sponsor_private)
        validation = processor.validate_sponsored_transaction(tx)

        assert validation.result == SponsorshipResult.INSUFFICIENT_BUDGET

    def test_validate_fee_too_high(self, processor, sponsor_keys, user_keys):
        """Test validation fails when fee exceeds per-tx limit."""
        sponsor_private, sponsor_public = sponsor_keys
        user_private, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0,
            max_fee_per_tx=0.01  # Low limit
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.05,  # Higher than limit
            public_key=user_public,
            gas_sponsor=sponsor_address
        )

        processor.authorize_transaction(tx, sponsor_private)
        validation = processor.validate_sponsored_transaction(tx)

        assert validation.result == SponsorshipResult.FEE_TOO_HIGH

    def test_deduct_sponsor_fee(self, processor, sponsor_keys, user_keys):
        """Test fee deduction from sponsor budget."""
        sponsor_private, sponsor_public = sponsor_keys
        user_private, user_public = user_keys
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        sponsor = processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.05,
            public_key=user_public,
            gas_sponsor=sponsor_address
        )
        tx.txid = "test_txid_123"

        result = processor.deduct_sponsor_fee(tx)

        assert result is True
        assert sponsor.remaining_budget == 99.95
        assert len(sponsor.sponsored_transactions) == 1

    def test_get_all_sponsors(self, processor, sponsor_keys):
        """Test retrieving all sponsor stats."""
        private1, public1 = sponsor_keys
        private2, public2 = generate_secp256k1_keypair_hex()

        processor.register_sponsor("XAIsponsor1", public1, 100.0)
        processor.register_sponsor("XAIsponsor2", public2, 200.0)

        all_sponsors = processor.get_all_sponsors()

        assert len(all_sponsors) == 2
        assert "XAIsponsor1" in all_sponsors
        assert "XAIsponsor2" in all_sponsors


class TestGlobalProcessor:
    """Tests for global processor singleton."""

    def test_get_global_processor(self):
        """Test global processor returns same instance."""
        processor1 = get_sponsored_transaction_processor()
        processor2 = get_sponsored_transaction_processor()

        assert processor1 is processor2

    def test_process_sponsored_transaction_helper(self):
        """Test convenience function for processing sponsored transactions."""
        processor = get_sponsored_transaction_processor()
        sponsor_private, sponsor_public = generate_secp256k1_keypair_hex()
        user_private, user_public = generate_secp256k1_keypair_hex()
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0,
            max_fee_per_tx=0.1
        )

        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.01,
            public_key=user_public,
            gas_sponsor=sponsor_address
        )

        processor.authorize_transaction(tx, sponsor_private)
        success, message = process_sponsored_transaction(tx)

        assert success is True
        assert sponsor_address[:16] in message


class TestTransactionIntegration:
    """Tests for Transaction class integration with gas sponsorship."""

    def test_transaction_with_sponsor(self):
        """Test creating transaction with gas sponsor field."""
        # Use valid hex addresses (40 hex chars after XAI prefix)
        tx = Transaction(
            sender="XAI1234567890abcdef1234567890abcdef12345678",
            recipient="XAI9876543210fedcba9876543210fedcba98765432",
            amount=10.0,
            fee=0.01,
            gas_sponsor="XAIabcdef1234567890abcdef1234567890abcdef12"
        )

        assert tx.gas_sponsor == "XAIabcdef1234567890abcdef1234567890abcdef12"
        assert tx.gas_sponsor_signature is None

    def test_transaction_to_dict_with_sponsor(self):
        """Test to_dict includes sponsor fields when present."""
        tx = Transaction(
            sender="XAI1234567890abcdef1234567890abcdef12345678",
            recipient="XAI9876543210fedcba9876543210fedcba98765432",
            amount=10.0,
            fee=0.01,
            gas_sponsor="XAIabcdef1234567890abcdef1234567890abcdef12"
        )
        tx.gas_sponsor_signature = "test_signature"

        tx_dict = tx.to_dict()

        assert "gas_sponsor" in tx_dict
        assert tx_dict["gas_sponsor"] == "XAIabcdef1234567890abcdef1234567890abcdef12"
        assert tx_dict["gas_sponsor_signature"] == "test_signature"

    def test_transaction_to_dict_without_sponsor(self):
        """Test to_dict excludes sponsor fields when not set."""
        tx = Transaction(
            sender="XAI1234567890abcdef1234567890abcdef12345678",
            recipient="XAI9876543210fedcba9876543210fedcba98765432",
            amount=10.0,
            fee=0.01
        )

        tx_dict = tx.to_dict()

        assert "gas_sponsor" not in tx_dict
        assert "gas_sponsor_signature" not in tx_dict


class TestBudgetArithmetic:
    """Tests for budget arithmetic to prevent overflow/underflow."""

    def test_budget_never_negative(self):
        """Ensure remaining budget cannot go negative."""
        sponsor = GasSponsor("XAI1234", 0.01, rate_limit=100)

        # Try to spend more than budget multiple times
        for _ in range(10):
            sponsor.sponsor_transaction("XAIuser", 0.005)

        # Budget should be 0 or positive, never negative
        assert sponsor.remaining_budget >= 0

    def test_large_budget_handling(self):
        """Test handling of large budget values."""
        large_budget = 1_000_000_000.0  # 1 billion
        sponsor = GasSponsor("XAI1234", large_budget, rate_limit=1000)

        sponsor.sponsor_transaction("XAIuser", 0.000001)

        assert sponsor.remaining_budget == large_budget - 0.000001

    def test_small_fee_precision(self):
        """Test precision with very small fees."""
        sponsor = GasSponsor("XAI1234", 1.0, rate_limit=100)

        # Sponsor many small transactions
        for _ in range(100):
            sponsor.sponsor_transaction("XAIuser", 0.00000001)

        # Budget should accurately reflect small deductions
        expected = 1.0 - (100 * 0.00000001)
        assert abs(sponsor.remaining_budget - expected) < 0.0000001


class TestRateLimitTimeBoundary:
    """Tests for rate limit time boundary handling."""

    def test_rate_limit_resets_after_24_hours(self):
        """Test rate limit resets after 24 hour window."""
        sponsor = GasSponsor("XAI1234", 100.0, rate_limit=2)

        # Use up rate limit
        sponsor.sponsor_transaction("XAIuser", 0.01)
        sponsor.sponsor_transaction("XAIuser", 0.01)
        assert sponsor.sponsor_transaction("XAIuser", 0.01) is None

        # Manually expire old timestamps (simulate 24+ hours passing)
        old_time = time.time() - 86500  # 24 hours + 100 seconds ago
        sponsor.user_daily_usage["XAIuser"] = [old_time, old_time]

        # Now should be able to transact again
        result = sponsor.sponsor_transaction("XAIuser", 0.01)
        assert result is not None
        assert isinstance(result, str)


class TestTransactionIdTracking:
    """Tests for transaction ID tracking and lifecycle management."""

    def test_preliminary_txid_generation(self):
        """Test preliminary txid is generated correctly."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.01)

        assert preliminary_txid is not None
        assert isinstance(preliminary_txid, str)
        assert len(preliminary_txid) == 64  # SHA256 hash
        # Verify it's a valid hex string
        int(preliminary_txid, 16)

    def test_preliminary_txid_uniqueness(self):
        """Test preliminary txids are unique for different transactions."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        txid1 = sponsor.sponsor_transaction("XAIuser1", 0.01)
        txid2 = sponsor.sponsor_transaction("XAIuser2", 0.01)

        assert txid1 != txid2

    def test_preliminary_txid_deterministic(self):
        """Test preliminary txid is deterministic for same parameters."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        # Generate txid directly with known parameters
        timestamp = 1234567890.0
        txid1 = sponsor._generate_preliminary_txid("XAIuser", 0.01, timestamp)
        txid2 = sponsor._generate_preliminary_txid("XAIuser", 0.01, timestamp)

        assert txid1 == txid2

    def test_sponsored_transaction_record_creation(self):
        """Test sponsored transaction record is created with preliminary txid."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.01)

        assert len(sponsor.sponsored_transactions) == 1
        tx = sponsor.sponsored_transactions[0]
        assert tx.txid == preliminary_txid
        assert tx.blockchain_txid is None
        assert tx.status == "pending"
        assert tx.user_address == "XAIuser123"
        assert tx.gas_amount == 0.01

    def test_confirm_sponsored_transaction(self):
        """Test confirming a transaction updates blockchain txid."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.01)
        blockchain_txid = "actual_blockchain_txid_abc123"

        result = sponsor.confirm_sponsored_transaction(preliminary_txid, blockchain_txid)

        assert result is True
        tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
        assert tx is not None
        assert tx.txid == preliminary_txid
        assert tx.blockchain_txid == blockchain_txid
        assert tx.status == "confirmed"

    def test_confirm_nonexistent_transaction(self):
        """Test confirming nonexistent transaction returns False."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        result = sponsor.confirm_sponsored_transaction("nonexistent_txid", "blockchain_txid")

        assert result is False

    def test_fail_sponsored_transaction(self):
        """Test failing a transaction refunds budget."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)
        initial_budget = sponsor.remaining_budget

        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.05)
        assert sponsor.remaining_budget == initial_budget - 0.05

        result = sponsor.fail_sponsored_transaction(preliminary_txid, "test failure")

        assert result is True
        assert sponsor.remaining_budget == initial_budget  # Budget refunded
        tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
        assert tx.status == "failed"

    def test_fail_already_confirmed_transaction(self):
        """Test failing already-confirmed transaction doesn't refund."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.05)
        sponsor.confirm_sponsored_transaction(preliminary_txid, "blockchain_txid")

        initial_budget = sponsor.remaining_budget
        result = sponsor.fail_sponsored_transaction(preliminary_txid, "test")

        assert result is False
        assert sponsor.remaining_budget == initial_budget  # No refund

    def test_get_transaction_by_preliminary_txid(self):
        """Test retrieving transaction by preliminary txid."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.01)
        tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)

        assert tx is not None
        assert tx.txid == preliminary_txid
        assert tx.user_address == "XAIuser123"

    def test_get_transaction_by_blockchain_txid(self):
        """Test retrieving transaction by blockchain txid."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.01)
        blockchain_txid = "blockchain_abc123"
        sponsor.confirm_sponsored_transaction(preliminary_txid, blockchain_txid)

        tx = sponsor.get_transaction_by_blockchain_txid(blockchain_txid)

        assert tx is not None
        assert tx.blockchain_txid == blockchain_txid
        assert tx.user_address == "XAIuser123"

    def test_get_nonexistent_transaction(self):
        """Test getting nonexistent transaction returns None."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        tx1 = sponsor.get_transaction_by_preliminary_txid("nonexistent")
        tx2 = sponsor.get_transaction_by_blockchain_txid("nonexistent")

        assert tx1 is None
        assert tx2 is None

    def test_transaction_lifecycle_complete(self):
        """Test complete transaction lifecycle from sponsorship to confirmation."""
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        # 1. Sponsor transaction - get preliminary txid
        preliminary_txid = sponsor.sponsor_transaction("XAIuser123", 0.05)
        assert preliminary_txid is not None

        # 2. Verify transaction is pending
        tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
        assert tx.status == "pending"
        assert tx.blockchain_txid is None

        # 3. Confirm transaction with blockchain txid
        blockchain_txid = "0x123abc456def789"
        success = sponsor.confirm_sponsored_transaction(preliminary_txid, blockchain_txid)
        assert success is True

        # 4. Verify transaction is confirmed
        tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
        assert tx.status == "confirmed"
        assert tx.blockchain_txid == blockchain_txid

        # 5. Can retrieve by either txid
        tx_by_prelim = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
        tx_by_blockchain = sponsor.get_transaction_by_blockchain_txid(blockchain_txid)
        assert tx_by_prelim is tx_by_blockchain

    def test_processor_deduct_fee_with_preliminary_txid(self):
        """Test processor deduct_fee updates transaction record properly."""
        processor = SponsoredTransactionProcessor()
        sponsor_private, sponsor_public = generate_secp256k1_keypair_hex()
        user_private, user_public = generate_secp256k1_keypair_hex()
        sponsor_address = "XAI" + sponsor_public[:40]
        user_address = "XAI" + user_public[:40]

        sponsor = processor.register_sponsor(
            sponsor_address=sponsor_address,
            sponsor_public_key=sponsor_public,
            budget=100.0,
            max_fee_per_tx=0.1
        )

        # Pre-authorize transaction
        preliminary_txid = sponsor.sponsor_transaction(user_address, 0.05)

        # Create transaction with blockchain txid
        tx = Transaction(
            sender=user_address,
            recipient="XAI9876543210abcdef1234567890abcdef12345678",
            amount=10.0,
            fee=0.05,
            public_key=user_public,
            gas_sponsor=sponsor_address
        )
        tx.txid = "blockchain_txid_xyz123"

        # Deduct fee with preliminary txid
        result = processor.deduct_sponsor_fee(tx, preliminary_txid)

        assert result is True
        # Verify transaction was updated
        sponsored_tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
        assert sponsored_tx.blockchain_txid == tx.txid
        assert sponsored_tx.status == "confirmed"

    def test_no_pending_placeholder_in_production(self):
        """
        CRITICAL SECURITY TEST: Verify no 'pending' string placeholders exist.

        This ensures the fix for the txid tracking bug is in place.
        All txids should be proper hashes or None, never string 'pending'.
        """
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        # Create several transactions
        txid1 = sponsor.sponsor_transaction("XAIuser1", 0.01)
        txid2 = sponsor.sponsor_transaction("XAIuser2", 0.02)
        txid3 = sponsor.sponsor_transaction("XAIuser3", 0.03)

        # Verify none are the string "pending"
        for tx in sponsor.sponsored_transactions:
            assert tx.txid != "pending", "Found 'pending' placeholder - security vulnerability!"
            assert tx.txid is not None
            assert len(tx.txid) == 64  # SHA256 hash length

    def test_audit_trail_completeness(self):
        """
        Test that transaction audit trail is complete and trackable.

        This verifies that every sponsored transaction has a complete
        audit trail from initial sponsorship through confirmation.
        """
        sponsor = GasSponsor("XAIsponsor123", 100.0, rate_limit=10)

        # Create and confirm multiple transactions
        transactions = []
        for i in range(5):
            preliminary_txid = sponsor.sponsor_transaction(f"XAIuser{i}", 0.01 * (i + 1))
            blockchain_txid = f"blockchain_tx_{i}"
            sponsor.confirm_sponsored_transaction(preliminary_txid, blockchain_txid)
            transactions.append((preliminary_txid, blockchain_txid))

        # Verify complete audit trail
        for preliminary, blockchain in transactions:
            # Can find by preliminary txid
            tx_by_prelim = sponsor.get_transaction_by_preliminary_txid(preliminary)
            assert tx_by_prelim is not None

            # Can find by blockchain txid
            tx_by_blockchain = sponsor.get_transaction_by_blockchain_txid(blockchain)
            assert tx_by_blockchain is not None

            # Both point to same record
            assert tx_by_prelim is tx_by_blockchain

            # Record has both IDs
            assert tx_by_prelim.txid == preliminary
            assert tx_by_prelim.blockchain_txid == blockchain
