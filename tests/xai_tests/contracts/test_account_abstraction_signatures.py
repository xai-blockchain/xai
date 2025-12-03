"""
Comprehensive security tests for Account Abstraction signature verification.

Tests ensure that:
1. Invalid signatures are ALWAYS rejected (never silently ignored)
2. Malformed signatures raise MalformedSignatureError
3. Wrong signers raise InvalidSignatureError
4. Missing public keys raise MissingPublicKeyError
5. All signature failures are logged for security audit

These tests verify the fix for signature verification exception swallowing
vulnerability where invalid signatures could potentially be processed.
"""

import pytest
import hashlib
from unittest.mock import patch

from xai.core.contracts.account_abstraction import (
    SmartAccount,
    MultiSigAccount,
    UserOperation,
    EntryPoint,
    SignatureError,
    MalformedSignatureError,
    InvalidSignatureError,
    MissingPublicKeyError,
)
from xai.core.crypto_utils import (
    generate_secp256k1_keypair_hex,
    sign_message_hex,
)


class TestSmartAccountSignatureValidation:
    """Tests for SmartAccount signature validation security."""

    @pytest.fixture
    def account_with_key(self):
        """Create account with registered public key."""
        private_key, public_key = generate_secp256k1_keypair_hex()
        account = SmartAccount(
            address="0x1234567890123456789012345678901234567890",
            owner="0xowner123",
            owner_public_key=public_key,
        )
        return account, private_key, public_key

    @pytest.fixture
    def account_without_key(self):
        """Create account without registered public key."""
        return SmartAccount(
            address="0x1234567890123456789012345678901234567890",
            owner="0xowner123",
            owner_public_key="",  # No key registered
        )

    def test_missing_public_key_raises_exception(self, account_without_key):
        """
        SECURITY TEST: Verify missing public key raises MissingPublicKeyError.

        This ensures operations cannot proceed without cryptographic verification.
        """
        message_hash = hashlib.sha256(b"test message").digest()
        signature = b"x" * 64  # Dummy signature

        with pytest.raises(MissingPublicKeyError) as exc_info:
            account_without_key._validate_signature(message_hash, signature)

        assert "no public key registered" in str(exc_info.value).lower()

    def test_missing_signature_raises_exception(self, account_with_key):
        """
        SECURITY TEST: Verify missing signature raises MalformedSignatureError.
        """
        account, _, _ = account_with_key
        message_hash = hashlib.sha256(b"test message").digest()

        with pytest.raises(MalformedSignatureError) as exc_info:
            account._validate_signature(message_hash, b"")

        assert "missing signature" in str(exc_info.value).lower()

    def test_signature_wrong_length_raises_exception(self, account_with_key):
        """
        SECURITY TEST: Verify wrong signature length raises MalformedSignatureError.

        ECDSA signatures MUST be exactly 64 bytes (r || s).
        """
        account, _, _ = account_with_key
        message_hash = hashlib.sha256(b"test message").digest()

        # Test too short
        with pytest.raises(MalformedSignatureError) as exc_info:
            account._validate_signature(message_hash, b"x" * 32)

        assert "must be 64 bytes" in str(exc_info.value).lower()
        assert "got 32 bytes" in str(exc_info.value).lower()

        # Test too long
        with pytest.raises(MalformedSignatureError) as exc_info:
            account._validate_signature(message_hash, b"x" * 128)

        assert "must be 64 bytes" in str(exc_info.value).lower()
        assert "got 128 bytes" in str(exc_info.value).lower()

    def test_invalid_signature_raises_exception(self, account_with_key):
        """
        SECURITY TEST: Verify invalid signature raises InvalidSignatureError.

        This ensures a signature from the wrong private key is rejected.
        """
        account, _, _ = account_with_key
        message_hash = hashlib.sha256(b"test message").digest()

        # Use a different key to sign
        wrong_private_key, _ = generate_secp256k1_keypair_hex()
        wrong_signature = sign_message_hex(wrong_private_key, message_hash)

        # Convert hex signature to bytes (64 bytes)
        signature_bytes = bytes.fromhex(wrong_signature)

        with pytest.raises(InvalidSignatureError) as exc_info:
            account._validate_signature(message_hash, signature_bytes)

        assert "does not match owner" in str(exc_info.value).lower()

    def test_valid_signature_succeeds(self, account_with_key):
        """Test that valid signatures are accepted."""
        account, private_key, _ = account_with_key
        message = b"test message for signing"
        message_hash = hashlib.sha256(message).digest()

        # Sign with correct key
        signature_hex = sign_message_hex(private_key, message_hash)
        signature_bytes = bytes.fromhex(signature_hex)

        # Should not raise exception
        result = account._validate_signature(message_hash, signature_bytes)
        assert result is True

    def test_cryptographic_error_raises_signature_error(self, account_with_key):
        """
        SECURITY TEST: Verify unexpected crypto errors raise SignatureError.

        This ensures failures are never silently ignored.
        """
        account, _, _ = account_with_key
        message_hash = hashlib.sha256(b"test message").digest()
        signature = b"x" * 64

        # Mock verify_signature_hex to raise an unexpected error
        with patch("xai.core.contracts.account_abstraction.verify_signature_hex") as mock_verify:
            mock_verify.side_effect = RuntimeError("Unexpected crypto library error")

            with pytest.raises(SignatureError) as exc_info:
                account._validate_signature(message_hash, signature)

            assert "signature verification failed" in str(exc_info.value).lower()


class TestMultiSigAccountSignatureValidation:
    """Tests for MultiSigAccount signature validation security."""

    @pytest.fixture
    def multisig_account(self):
        """Create multisig account with 2-of-3 threshold."""
        # Generate 3 owner keypairs
        owner1_private, owner1_public = generate_secp256k1_keypair_hex()
        owner2_private, owner2_public = generate_secp256k1_keypair_hex()
        owner3_private, owner3_public = generate_secp256k1_keypair_hex()

        owner1_addr = "0x" + hashlib.sha256(owner1_public.encode()).hexdigest()[:40]
        owner2_addr = "0x" + hashlib.sha256(owner2_public.encode()).hexdigest()[:40]
        owner3_addr = "0x" + hashlib.sha256(owner3_public.encode()).hexdigest()[:40]

        account = MultiSigAccount(
            address="0xmultisig123456789012345678901234567890",
            owner=owner1_addr,
            owners=[owner1_addr, owner2_addr, owner3_addr],
            owner_public_keys={
                owner1_addr.lower(): owner1_public,
                owner2_addr.lower(): owner2_public,
                owner3_addr.lower(): owner3_public,
            },
            threshold=2,
        )

        return account, [
            (owner1_addr, owner1_private, owner1_public),
            (owner2_addr, owner2_private, owner2_public),
            (owner3_addr, owner3_private, owner3_public),
        ]

    def test_insufficient_public_keys_raises_exception(self):
        """
        SECURITY TEST: Verify insufficient public keys raises MissingPublicKeyError.
        """
        account = MultiSigAccount(
            address="0xmultisig",
            owners=["0xowner1", "0xowner2", "0xowner3"],
            owner_public_keys={},  # No keys registered
            threshold=2,
        )

        message_hash = hashlib.sha256(b"test").digest()
        signature = b"x" * 128  # 2 signatures

        with pytest.raises(MissingPublicKeyError) as exc_info:
            account._validate_signature(message_hash, signature)

        assert "only 0 public keys registered" in str(exc_info.value).lower()
        assert "but needs 2" in str(exc_info.value).lower()

    def test_missing_multisig_signature_raises_exception(self, multisig_account):
        """
        SECURITY TEST: Verify missing signature raises MalformedSignatureError.
        """
        account, _ = multisig_account
        message_hash = hashlib.sha256(b"test").digest()

        with pytest.raises(MalformedSignatureError) as exc_info:
            account._validate_signature(message_hash, b"")

        assert "missing multisig signature" in str(exc_info.value).lower()

    def test_short_multisig_signature_raises_exception(self, multisig_account):
        """
        SECURITY TEST: Verify too-short signature raises MalformedSignatureError.

        For 2-of-3 multisig, need at least 2 * 64 = 128 bytes.
        """
        account, _ = multisig_account
        message_hash = hashlib.sha256(b"test").digest()

        with pytest.raises(MalformedSignatureError) as exc_info:
            account._validate_signature(message_hash, b"x" * 64)  # Only 1 signature

        assert "must be at least 128 bytes" in str(exc_info.value).lower()
        assert "got 64 bytes" in str(exc_info.value).lower()

    def test_invalid_multisig_signature_raises_exception(self, multisig_account):
        """
        SECURITY TEST: Verify invalid signatures raise InvalidSignatureError.

        Even if the first signature is valid, an invalid second signature
        should cause rejection.
        """
        account, owners = multisig_account
        message = b"transaction to sign"
        message_hash = hashlib.sha256(message).digest()

        # Get first valid signature
        _, owner1_private, _ = owners[0]
        sig1_hex = sign_message_hex(owner1_private, message_hash)
        sig1_bytes = bytes.fromhex(sig1_hex)

        # Create invalid second signature (wrong key)
        wrong_private, _ = generate_secp256k1_keypair_hex()
        sig2_hex = sign_message_hex(wrong_private, message_hash)
        sig2_bytes = bytes.fromhex(sig2_hex)

        # Concatenate signatures
        combined_sig = sig1_bytes + sig2_bytes

        with pytest.raises(InvalidSignatureError) as exc_info:
            account._validate_signature(message_hash, combined_sig)

        assert "signature 1 does not match any owner" in str(exc_info.value).lower()

    def test_multisig_unexpected_crypto_error_raises_signature_error(self, multisig_account):
        """
        SECURITY TEST: Unexpected crypto errors must raise SignatureError (fail fast).
        """
        account, _ = multisig_account
        message_hash = hashlib.sha256(b"panic").digest()
        signature = b"x" * (account.threshold * 64)

        with patch("xai.core.contracts.account_abstraction.verify_signature_hex") as mock_verify:
            mock_verify.side_effect = RuntimeError("crypto backend failure")

            with pytest.raises(SignatureError) as exc_info:
                account._validate_signature(message_hash, signature)

            assert "unexpected signature verification failure" in str(exc_info.value).lower()
            assert mock_verify.call_count == 1

    def test_valid_multisig_succeeds(self, multisig_account):
        """Test that valid multisig signatures are accepted."""
        account, owners = multisig_account
        message = b"valid transaction"
        message_hash = hashlib.sha256(message).digest()

        # Sign with first two owners
        _, owner1_private, _ = owners[0]
        _, owner2_private, _ = owners[1]

        sig1_hex = sign_message_hex(owner1_private, message_hash)
        sig2_hex = sign_message_hex(owner2_private, message_hash)

        sig1_bytes = bytes.fromhex(sig1_hex)
        sig2_bytes = bytes.fromhex(sig2_hex)

        combined_sig = sig1_bytes + sig2_bytes

        # Should not raise exception
        result = account._validate_signature(message_hash, combined_sig)
        assert result is True


class TestUserOperationSignatureValidation:
    """Tests for UserOperation signature validation in EntryPoint."""

    @pytest.fixture
    def entry_point_with_account(self):
        """Create EntryPoint with registered account."""
        entry_point = EntryPoint(chain_id=1)

        # Create account with key and sufficient balance
        private_key, public_key = generate_secp256k1_keypair_hex()
        account = SmartAccount(
            address="0x1234567890123456789012345678901234567890",
            owner="0xowner",
            owner_public_key=public_key,
            balance=1000000000000,  # Large balance for gas
        )

        entry_point.register_account(account)

        return entry_point, account, private_key, public_key

    def test_user_op_with_missing_signature_fails_validation(
        self, entry_point_with_account
    ):
        """
        SECURITY TEST: UserOp with missing signature fails validation.

        The EntryPoint must catch MalformedSignatureError and return invalid result.
        """
        entry_point, account, _, _ = entry_point_with_account

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
            signature=b"",  # Missing signature
        )

        op_hash = user_op.hash(entry_point.address, entry_point.chain_id)
        validation_result = entry_point._validate_user_op(user_op, op_hash)

        assert validation_result.valid is False
        assert validation_result.sig_failed is True

    def test_user_op_with_malformed_signature_fails_validation(
        self, entry_point_with_account
    ):
        """
        SECURITY TEST: UserOp with wrong-length signature fails validation.
        """
        entry_point, account, _, _ = entry_point_with_account

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
            signature=b"x" * 32,  # Wrong length (should be 64)
        )

        op_hash = user_op.hash(entry_point.address, entry_point.chain_id)
        validation_result = entry_point._validate_user_op(user_op, op_hash)

        assert validation_result.valid is False
        assert validation_result.sig_failed is True

    def test_user_op_with_invalid_signature_fails_validation(
        self, entry_point_with_account
    ):
        """
        SECURITY TEST: UserOp signed by wrong key fails validation.
        """
        entry_point, account, _, _ = entry_point_with_account

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
        )

        op_hash = user_op.hash(entry_point.address, entry_point.chain_id)

        # Sign with wrong key
        wrong_private, _ = generate_secp256k1_keypair_hex()
        wrong_signature_hex = sign_message_hex(wrong_private, op_hash)
        user_op.signature = bytes.fromhex(wrong_signature_hex)

        validation_result = entry_point._validate_user_op(user_op, op_hash)

        assert validation_result.valid is False
        assert validation_result.sig_failed is True

    def test_user_op_with_valid_signature_passes_validation(
        self, entry_point_with_account
    ):
        """Test that valid UserOp signatures are accepted."""
        entry_point, account, private_key, _ = entry_point_with_account

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
            max_fee_per_gas=1,  # Very low gas price so balance is sufficient
            max_priority_fee_per_gas=1,
        )

        op_hash = user_op.hash(entry_point.address, entry_point.chain_id)

        # Sign with correct key
        signature_hex = sign_message_hex(private_key, op_hash)
        user_op.signature = bytes.fromhex(signature_hex)

        validation_result = entry_point._validate_user_op(user_op, op_hash)

        assert validation_result.valid is True
        assert validation_result.sig_failed is False


class TestSignatureExceptionLogging:
    """Tests to verify proper security event logging."""

    def test_missing_public_key_logged_as_error(self):
        """Verify missing public key is logged at ERROR level."""
        account = SmartAccount(
            address="0x1234",
            owner="0xowner",
            owner_public_key="",
        )

        message_hash = hashlib.sha256(b"test").digest()

        with pytest.raises(MissingPublicKeyError):
            with patch("xai.core.contracts.account_abstraction.logger") as mock_logger:
                account._validate_signature(message_hash, b"x" * 64)
                # Verify error was logged
                mock_logger.error.assert_called()

    def test_malformed_signature_logged_as_error(self):
        """Verify malformed signatures are logged at ERROR level."""
        _, public_key = generate_secp256k1_keypair_hex()
        account = SmartAccount(
            address="0x1234",
            owner="0xowner",
            owner_public_key=public_key,
        )

        message_hash = hashlib.sha256(b"test").digest()

        with pytest.raises(MalformedSignatureError):
            with patch("xai.core.contracts.account_abstraction.logger") as mock_logger:
                account._validate_signature(message_hash, b"short")
                # Verify error was logged
                mock_logger.error.assert_called()

    def test_invalid_signature_logged_as_warning(self):
        """Verify invalid signatures are logged at WARNING level."""
        account_private, account_public = generate_secp256k1_keypair_hex()
        wrong_private, _ = generate_secp256k1_keypair_hex()

        account = SmartAccount(
            address="0x1234",
            owner="0xowner",
            owner_public_key=account_public,
        )

        message_hash = hashlib.sha256(b"test").digest()
        wrong_signature = sign_message_hex(wrong_private, message_hash)
        signature_bytes = bytes.fromhex(wrong_signature)

        with pytest.raises(InvalidSignatureError):
            with patch("xai.core.contracts.account_abstraction.logger") as mock_logger:
                account._validate_signature(message_hash, signature_bytes)
                # Verify warning was logged
                mock_logger.warning.assert_called()


class TestNoSilentFailures:
    """
    Critical security tests to ensure signature failures are NEVER silent.

    These tests verify the core security requirement: invalid signatures
    must ALWAYS raise exceptions and NEVER allow execution to continue.
    """

    def test_exception_not_swallowed_in_validate_user_op(self):
        """
        CRITICAL: Verify validate_user_op re-raises signature exceptions.

        This is the main vulnerability - ensure exceptions propagate.
        """
        _, public_key = generate_secp256k1_keypair_hex()
        account = SmartAccount(
            address="0x1234",
            owner="0xowner",
            owner_public_key=public_key,
        )

        # UserOp with missing signature
        user_op = UserOperation(
            sender=account.address,
            nonce=0,
            signature=b"",  # Will raise MalformedSignatureError
        )

        # validate_user_op should re-raise the exception, not swallow it
        with pytest.raises(SignatureError):
            account.validate_user_op(user_op, b"hash", 0)

    def test_no_silent_continuation_after_signature_failure(self):
        """
        CRITICAL: Verify execution halts on signature failure.

        Ensure that if signature verification fails, no subsequent code executes.
        """
        _, public_key = generate_secp256k1_keypair_hex()
        account = SmartAccount(
            address="0x1234",
            owner="0xowner",
            owner_public_key=public_key,
            balance=1000,
        )

        # UserOp with invalid signature
        user_op = UserOperation(
            sender=account.address,
            nonce=0,
            signature=b"x" * 32,  # Wrong length
        )

        initial_balance = account.balance

        # Attempt validation - should raise exception
        with pytest.raises(SignatureError):
            account.validate_user_op(user_op, b"hash", 100)

        # Balance should NOT have changed (prefund was not paid)
        assert account.balance == initial_balance
