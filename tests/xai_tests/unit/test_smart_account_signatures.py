"""
Comprehensive tests for SmartAccount and MultiSigAccount ECDSA signature validation.

These tests verify that:
- SmartAccount properly validates ECDSA signatures
- MultiSigAccount properly validates multi-party signatures
- Invalid signatures are rejected
- Missing public keys cause validation failure (fail-closed)
- Edge cases are handled securely
"""

import pytest
import hashlib
from xai.core.contracts.account_abstraction import (
    SmartAccount,
    MultiSigAccount,
    AccountFactory,
    UserOperation,
    EntryPoint,
    SIG_VALIDATION_SUCCESS,
    SIG_VALIDATION_FAILED,
)
from xai.core.crypto_utils import (
    generate_secp256k1_keypair_hex,
    sign_message_hex,
    verify_signature_hex,
)


class TestSmartAccountSignatureValidation:
    """Tests for SmartAccount ECDSA signature validation."""

    @pytest.fixture
    def owner_keys(self):
        """Generate owner key pair."""
        return generate_secp256k1_keypair_hex()

    @pytest.fixture
    def account_with_key(self, owner_keys):
        """Create account with registered public key."""
        private_key, public_key = owner_keys
        return SmartAccount(
            owner="0xowner1234567890abcdef",
            owner_public_key=public_key,
        )

    @pytest.fixture
    def account_without_key(self):
        """Create account without registered public key."""
        return SmartAccount(
            owner="0xowner1234567890abcdef",
            owner_public_key="",  # No public key
        )

    def test_valid_signature_accepted(self, owner_keys, account_with_key):
        """Test that valid ECDSA signature is accepted."""
        private_key, public_key = owner_keys
        message_hash = hashlib.sha3_256(b"test message").digest()

        # Sign with owner's private key
        signature_hex = sign_message_hex(private_key, message_hash)
        signature_bytes = bytes.fromhex(signature_hex)

        result = account_with_key._validate_signature(message_hash, signature_bytes)

        assert result is True

    def test_invalid_signature_rejected(self, owner_keys, account_with_key):
        """Test that invalid signature is rejected."""
        private_key, public_key = owner_keys
        message_hash = hashlib.sha3_256(b"test message").digest()

        # Create invalid signature (random bytes)
        invalid_signature = bytes(64)  # All zeros - invalid

        result = account_with_key._validate_signature(message_hash, invalid_signature)

        assert result is False

    def test_wrong_key_signature_rejected(self, account_with_key):
        """Test that signature from wrong key is rejected."""
        # Sign with a different private key
        different_private, different_public = generate_secp256k1_keypair_hex()
        message_hash = hashlib.sha3_256(b"test message").digest()

        signature_hex = sign_message_hex(different_private, message_hash)
        signature_bytes = bytes.fromhex(signature_hex)

        result = account_with_key._validate_signature(message_hash, signature_bytes)

        assert result is False

    def test_missing_public_key_fails_closed(self, account_without_key):
        """Test that missing public key causes validation failure (fail-closed)."""
        # Even with a "valid looking" signature, should fail without public key
        message_hash = hashlib.sha3_256(b"test message").digest()
        fake_signature = b"x" * 64

        result = account_without_key._validate_signature(message_hash, fake_signature)

        assert result is False

    def test_empty_signature_rejected(self, account_with_key):
        """Test that empty signature is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        result = account_with_key._validate_signature(message_hash, b"")

        assert result is False

    def test_short_signature_rejected(self, account_with_key):
        """Test that signature shorter than 64 bytes is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        result = account_with_key._validate_signature(message_hash, b"short")

        assert result is False

    def test_long_signature_rejected(self, account_with_key):
        """Test that signature longer than 64 bytes is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        result = account_with_key._validate_signature(message_hash, b"x" * 65)

        assert result is False

    def test_none_signature_rejected(self, account_with_key):
        """Test that None signature is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        result = account_with_key._validate_signature(message_hash, None)

        assert result is False

    def test_validate_user_op_with_valid_signature(self, owner_keys):
        """Test full UserOp validation flow with valid signature."""
        private_key, public_key = owner_keys

        account = SmartAccount(
            owner="0xowner123",
            owner_public_key=public_key,
            balance=1000000,  # Enough for prefund
        )

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
        )

        # Hash the user op
        op_hash = user_op.hash("0xEntryPoint", chain_id=1)

        # Sign it
        signature_hex = sign_message_hex(private_key, op_hash)
        user_op.signature = bytes.fromhex(signature_hex)

        result = account.validate_user_op(user_op, op_hash, missing_account_funds=0)

        assert result == SIG_VALIDATION_SUCCESS

    def test_validate_user_op_with_invalid_signature(self, owner_keys):
        """Test UserOp validation fails with invalid signature."""
        private_key, public_key = owner_keys

        account = SmartAccount(
            owner="0xowner123",
            owner_public_key=public_key,
            balance=1000000,
        )

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
        )

        op_hash = user_op.hash("0xEntryPoint", chain_id=1)

        # Use wrong signature
        user_op.signature = bytes(64)  # Invalid signature

        result = account.validate_user_op(user_op, op_hash, missing_account_funds=0)

        assert result == SIG_VALIDATION_FAILED


class TestMultiSigAccountSignatureValidation:
    """Tests for MultiSigAccount multi-party ECDSA signature validation."""

    @pytest.fixture
    def owner_keys_list(self):
        """Generate 3 owner key pairs."""
        return [generate_secp256k1_keypair_hex() for _ in range(3)]

    @pytest.fixture
    def multisig_account(self, owner_keys_list):
        """Create 2-of-3 multisig account."""
        owners = [f"0xowner{i}" for i in range(3)]
        public_keys = {
            owners[i].lower(): owner_keys_list[i][1]
            for i in range(3)
        }

        return MultiSigAccount(
            owner=owners[0],
            owners=owners,
            owner_public_keys=public_keys,
            threshold=2,
        )

    def test_valid_multisig_accepted(self, owner_keys_list, multisig_account):
        """Test that valid multi-signature (2-of-3) is accepted."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        # Sign with first two owners
        sig1 = bytes.fromhex(sign_message_hex(owner_keys_list[0][0], message_hash))
        sig2 = bytes.fromhex(sign_message_hex(owner_keys_list[1][0], message_hash))

        # Concatenate signatures
        combined_sig = sig1 + sig2

        result = multisig_account._validate_signature(message_hash, combined_sig)

        assert result is True

    def test_different_signers_accepted(self, owner_keys_list, multisig_account):
        """Test that different valid signer combinations work."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        # Sign with owners 0 and 2 (skipping owner 1)
        sig1 = bytes.fromhex(sign_message_hex(owner_keys_list[0][0], message_hash))
        sig3 = bytes.fromhex(sign_message_hex(owner_keys_list[2][0], message_hash))

        combined_sig = sig1 + sig3

        result = multisig_account._validate_signature(message_hash, combined_sig)

        assert result is True

    def test_insufficient_signatures_rejected(self, owner_keys_list, multisig_account):
        """Test that insufficient signatures (1-of-3 when 2 required) is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        # Only one signature when 2 required
        sig1 = bytes.fromhex(sign_message_hex(owner_keys_list[0][0], message_hash))

        result = multisig_account._validate_signature(message_hash, sig1)

        assert result is False

    def test_duplicate_signer_rejected(self, owner_keys_list, multisig_account):
        """Test that same signer signing twice is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        # Same owner signs twice - should not count as 2 valid signatures
        sig1 = bytes.fromhex(sign_message_hex(owner_keys_list[0][0], message_hash))
        sig1_again = bytes.fromhex(sign_message_hex(owner_keys_list[0][0], message_hash))

        # Different signature bytes but same signer
        combined_sig = sig1 + sig1_again

        result = multisig_account._validate_signature(message_hash, combined_sig)

        # Should fail because same owner cannot be counted twice
        assert result is False

    def test_non_owner_signature_rejected(self, owner_keys_list, multisig_account):
        """Test that signature from non-owner is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        # One valid owner signature
        sig1 = bytes.fromhex(sign_message_hex(owner_keys_list[0][0], message_hash))

        # One signature from non-owner
        outsider_private, _ = generate_secp256k1_keypair_hex()
        sig_outsider = bytes.fromhex(sign_message_hex(outsider_private, message_hash))

        combined_sig = sig1 + sig_outsider

        result = multisig_account._validate_signature(message_hash, combined_sig)

        assert result is False

    def test_missing_public_keys_fails(self):
        """Test that missing public keys cause validation failure."""
        # Create multisig without registering public keys
        account = MultiSigAccount(
            owner="0xowner0",
            owners=["0xowner0", "0xowner1", "0xowner2"],
            owner_public_keys={},  # No keys registered
            threshold=2,
        )

        message_hash = hashlib.sha3_256(b"test message").digest()
        fake_sig = b"x" * 128  # Two fake signatures

        result = account._validate_signature(message_hash, fake_sig)

        assert result is False

    def test_partial_public_keys_fails(self, owner_keys_list):
        """Test that insufficient registered keys cause failure."""
        owners = [f"0xowner{i}" for i in range(3)]

        # Only register 1 public key when 2 are needed for threshold
        account = MultiSigAccount(
            owner=owners[0],
            owners=owners,
            owner_public_keys={owners[0].lower(): owner_keys_list[0][1]},
            threshold=2,
        )

        message_hash = hashlib.sha3_256(b"test message").digest()
        sig1 = bytes.fromhex(sign_message_hex(owner_keys_list[0][0], message_hash))
        sig2 = bytes.fromhex(sign_message_hex(owner_keys_list[1][0], message_hash))

        combined_sig = sig1 + sig2

        result = account._validate_signature(message_hash, combined_sig)

        assert result is False

    def test_empty_signature_rejected(self, multisig_account):
        """Test that empty signature is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        result = multisig_account._validate_signature(message_hash, b"")

        assert result is False

    def test_short_signature_rejected(self, multisig_account):
        """Test that signature shorter than expected is rejected."""
        message_hash = hashlib.sha3_256(b"test message").digest()

        # Need 128 bytes for 2 signatures, only provide 64
        result = multisig_account._validate_signature(message_hash, b"x" * 64)

        assert result is False

    def test_register_owner_public_key(self, owner_keys_list):
        """Test registering owner public key after creation."""
        owners = ["0xowner0", "0xowner1"]
        private1, public1 = owner_keys_list[0]
        private2, public2 = owner_keys_list[1]

        account = MultiSigAccount(
            owner=owners[0],
            owners=owners,
            owner_public_keys={owners[0].lower(): public1},  # Only first key
            threshold=2,
        )

        # Register second key
        result = account.register_owner_public_key(
            caller=owners[0],
            owner=owners[1],
            public_key=public2
        )

        assert result is True
        assert owners[1].lower() in account.owner_public_keys

        # Now signatures should validate
        message_hash = hashlib.sha3_256(b"test message").digest()
        sig1 = bytes.fromhex(sign_message_hex(private1, message_hash))
        sig2 = bytes.fromhex(sign_message_hex(private2, message_hash))

        assert account._validate_signature(message_hash, sig1 + sig2) is True


class TestAccountFactory:
    """Tests for AccountFactory creating accounts with public keys."""

    def test_create_account_with_public_key(self):
        """Test factory creates account with public key."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        factory = AccountFactory()
        account = factory.create_account(
            owner="0xowner123",
            salt=12345,
            owner_public_key=public_key,
        )

        assert account.owner_public_key == public_key
        assert account.address.startswith("0x")

    def test_create_account_without_public_key(self):
        """Test factory creates account without public key (for backwards compat)."""
        factory = AccountFactory()
        account = factory.create_account(
            owner="0xowner123",
            salt=12345,
        )

        assert account.owner_public_key == ""

    def test_create_multisig_with_public_keys(self):
        """Test factory creates multisig with public keys."""
        keys = [generate_secp256k1_keypair_hex() for _ in range(3)]
        owners = [f"0xowner{i}" for i in range(3)]
        public_keys = {owners[i]: keys[i][1] for i in range(3)}

        factory = AccountFactory()
        account = factory.create_multisig_account(
            owners=owners,
            threshold=2,
            salt=12345,
            owner_public_keys=public_keys,
        )

        assert len(account.owner_public_keys) == 3
        assert account.threshold == 2

    def test_deterministic_address_unchanged_with_public_key(self):
        """Test that adding public key doesn't change deterministic address."""
        factory = AccountFactory(address="0xfactory123")

        # Create same account with and without public key
        account1 = factory.create_account("0xowner", salt=1)
        # Reset factory accounts to test
        factory.accounts = {}
        _, public_key = generate_secp256k1_keypair_hex()
        account2 = factory.create_account("0xowner", salt=1, owner_public_key=public_key)

        # Address should be deterministic based on owner and salt only
        assert account1.address == account2.address


class TestEntryPointIntegration:
    """Tests for EntryPoint integration with signature validation."""

    def test_entrypoint_validates_signatures(self):
        """Test EntryPoint properly validates UserOp signatures."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        entry_point = EntryPoint(chain_id=1)
        factory = AccountFactory(entry_point=entry_point.address)

        account = factory.create_account(
            owner="0xowner123",
            salt=12345,
            owner_public_key=public_key,
        )
        account.balance = 10_000_000_000  # Ensure sufficient balance

        entry_point.register_account(account)

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
            call_gas_limit=100_000,
            verification_gas_limit=100_000,
            pre_verification_gas=50_000,
            max_fee_per_gas=1,
        )

        op_hash = user_op.hash(entry_point.address, entry_point.chain_id)
        signature_hex = sign_message_hex(private_key, op_hash)
        user_op.signature = bytes.fromhex(signature_hex)

        # Process should succeed with valid signature
        results = entry_point.handle_ops([user_op], beneficiary="0xbeneficiary")

        assert len(results) == 1
        assert results[0].success is True

    def test_entrypoint_rejects_invalid_signatures(self):
        """Test EntryPoint rejects UserOp with invalid signature."""
        private_key, public_key = generate_secp256k1_keypair_hex()

        entry_point = EntryPoint(chain_id=1)
        factory = AccountFactory(entry_point=entry_point.address)

        account = factory.create_account(
            owner="0xowner123",
            salt=12345,
            owner_public_key=public_key,
        )
        account.balance = 10_000_000_000

        entry_point.register_account(account)

        user_op = UserOperation(
            sender=account.address,
            nonce=0,
            call_gas_limit=100_000,
            verification_gas_limit=100_000,
            pre_verification_gas=50_000,
            max_fee_per_gas=1,
        )

        # Use invalid signature
        user_op.signature = bytes(64)

        results = entry_point.handle_ops([user_op], beneficiary="0xbeneficiary")

        assert len(results) == 1
        assert results[0].success is False
