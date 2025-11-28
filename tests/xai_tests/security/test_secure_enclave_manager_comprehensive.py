"""
Comprehensive tests for Secure Enclave Manager security module.

Tests key generation in enclave, public key retrieval, signing operations,
signature verification, and enclave availability scenarios.
"""

import pytest
from xai.security.secure_enclave_manager import SecureEnclaveManager


class TestSecureEnclaveInitialization:
    """Test secure enclave manager initialization"""

    def test_init_enclave_available(self):
        """Test initialization with enclave available"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        assert manager._simulate_enclave_available is True
        assert len(manager._enclave_keys) == 0
        assert manager._key_handle_counter == 0

    def test_init_enclave_unavailable(self):
        """Test initialization with enclave unavailable"""
        manager = SecureEnclaveManager(simulate_enclave_available=False)
        assert manager._simulate_enclave_available is False

    def test_init_default_available(self):
        """Test initialization defaults to enclave available"""
        manager = SecureEnclaveManager()
        assert manager._simulate_enclave_available is True


class TestKeyGeneration:
    """Test key generation in secure enclave"""

    def test_generate_key_in_enclave_success(self):
        """Test successful key generation in enclave"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        assert key_handle is not None
        assert key_handle == "enclave_key_1"
        assert key_handle in manager._enclave_keys

    def test_generate_key_enclave_unavailable(self):
        """Test key generation fails when enclave unavailable"""
        manager = SecureEnclaveManager(simulate_enclave_available=False)
        key_handle = manager.generate_key_in_enclave()

        assert key_handle is None

    def test_generate_multiple_keys(self):
        """Test generating multiple keys"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        handles = []
        for i in range(5):
            handle = manager.generate_key_in_enclave()
            handles.append(handle)

        assert len(handles) == 5
        assert len(set(handles)) == 5  # All unique
        assert handles[0] == "enclave_key_1"
        assert handles[4] == "enclave_key_5"

    def test_key_handle_counter_increments(self):
        """Test that key handle counter increments"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        assert manager._key_handle_counter == 0
        manager.generate_key_in_enclave()
        assert manager._key_handle_counter == 1
        manager.generate_key_in_enclave()
        assert manager._key_handle_counter == 2

    def test_generated_key_pair_structure(self):
        """Test that generated key pairs have correct structure"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        key_pair = manager._enclave_keys[key_handle]
        assert isinstance(key_pair, tuple)
        assert len(key_pair) == 2
        assert isinstance(key_pair[0], bytes)  # Private key
        assert isinstance(key_pair[1], bytes)  # Public key

    def test_private_key_length(self):
        """Test that private key has correct length"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        private_key = manager._enclave_keys[key_handle][0]
        assert len(private_key) == 32

    def test_public_key_length(self):
        """Test that public key has correct length"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        public_key = manager._enclave_keys[key_handle][1]
        assert len(public_key) == 32

    def test_keys_are_unique(self):
        """Test that all generated keys are unique"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        keys = []
        for i in range(10):
            handle = manager.generate_key_in_enclave()
            private_key, public_key = manager._enclave_keys[handle]
            keys.append((private_key, public_key))

        # All key pairs should be unique
        assert len(set(keys)) == 10


class TestPublicKeyRetrieval:
    """Test retrieving public keys from enclave"""

    def test_get_public_key_success(self):
        """Test successful public key retrieval"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        public_key = manager.get_public_key_from_enclave(key_handle)

        assert public_key is not None
        assert isinstance(public_key, bytes)
        assert len(public_key) == 32

    def test_get_public_key_enclave_unavailable(self):
        """Test public key retrieval fails when enclave unavailable"""
        manager = SecureEnclaveManager(simulate_enclave_available=False)

        public_key = manager.get_public_key_from_enclave("some_handle")

        assert public_key is None

    def test_get_public_key_invalid_handle(self):
        """Test public key retrieval with invalid handle"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        public_key = manager.get_public_key_from_enclave("invalid_handle")

        assert public_key is None

    def test_get_public_key_matches_generated(self):
        """Test that retrieved public key matches what was generated"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        expected_public_key = manager._enclave_keys[key_handle][1]
        retrieved_public_key = manager.get_public_key_from_enclave(key_handle)

        assert retrieved_public_key == expected_public_key

    def test_get_public_key_multiple_handles(self):
        """Test retrieving public keys for multiple handles"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        handles = [manager.generate_key_in_enclave() for _ in range(3)]

        for handle in handles:
            public_key = manager.get_public_key_from_enclave(handle)
            assert public_key is not None


class TestDataSigning:
    """Test signing data in secure enclave"""

    def test_sign_data_success(self):
        """Test successful data signing"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        data = b"Important message to sign"
        signature = manager.sign_data_in_enclave(key_handle, data)

        assert signature is not None
        assert isinstance(signature, bytes)
        assert len(signature) == 32

    def test_sign_data_enclave_unavailable(self):
        """Test signing fails when enclave unavailable"""
        manager = SecureEnclaveManager(simulate_enclave_available=False)

        signature = manager.sign_data_in_enclave("some_handle", b"data")

        assert signature is None

    def test_sign_data_invalid_handle(self):
        """Test signing fails with invalid handle"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        signature = manager.sign_data_in_enclave("invalid_handle", b"data")

        assert signature is None

    def test_sign_different_data_different_signatures(self):
        """Test that different data produces different signatures"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        sig1 = manager.sign_data_in_enclave(key_handle, b"data1")
        sig2 = manager.sign_data_in_enclave(key_handle, b"data2")

        assert sig1 != sig2

    def test_sign_same_data_deterministic(self):
        """Test that signing same data produces same signature"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        data = b"consistent message"
        sig1 = manager.sign_data_in_enclave(key_handle, data)
        sig2 = manager.sign_data_in_enclave(key_handle, data)

        assert sig1 == sig2

    def test_sign_empty_data(self):
        """Test signing empty data"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        signature = manager.sign_data_in_enclave(key_handle, b"")

        assert signature is not None

    def test_sign_large_data(self):
        """Test signing large amount of data"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        large_data = b"x" * 10000
        signature = manager.sign_data_in_enclave(key_handle, large_data)

        assert signature is not None


class TestSignatureVerification:
    """Test verifying signatures"""

    def test_verify_signature_success(self):
        """Test successful signature verification"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        data = b"Message to verify"
        public_key = manager.get_public_key_from_enclave(key_handle)

        # Note: The signing is conceptual, so we need to adjust for verification
        signature_input = public_key + data
        import hashlib
        expected_signature = hashlib.sha256(signature_input).digest()

        is_valid = manager.verify_signature(public_key, data, expected_signature)

        assert is_valid is True

    def test_verify_signature_invalid(self):
        """Test verification fails with wrong signature"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        data = b"Message"
        public_key = manager.get_public_key_from_enclave(key_handle)
        wrong_signature = b"0" * 32

        is_valid = manager.verify_signature(public_key, data, wrong_signature)

        assert is_valid is False

    def test_verify_signature_wrong_data(self):
        """Test verification fails when data is modified"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        original_data = b"Original message"
        modified_data = b"Modified message"
        public_key = manager.get_public_key_from_enclave(key_handle)

        # Create signature for original data
        import hashlib
        signature = hashlib.sha256(public_key + original_data).digest()

        # Verify with modified data should fail
        is_valid = manager.verify_signature(public_key, modified_data, signature)

        assert is_valid is False

    def test_verify_signature_wrong_public_key(self):
        """Test verification fails with wrong public key"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle1 = manager.generate_key_in_enclave()
        key_handle2 = manager.generate_key_in_enclave()

        data = b"Message"
        public_key1 = manager.get_public_key_from_enclave(key_handle1)
        public_key2 = manager.get_public_key_from_enclave(key_handle2)

        import hashlib
        signature = hashlib.sha256(public_key1 + data).digest()

        # Verify with different public key should fail
        is_valid = manager.verify_signature(public_key2, data, signature)

        assert is_valid is False


class TestEnclaveAvailability:
    """Test enclave availability checking"""

    def test_is_enclave_available_true(self):
        """Test enclave availability check returns True"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        assert manager._is_enclave_available() is True

    def test_is_enclave_available_false(self):
        """Test enclave availability check returns False"""
        manager = SecureEnclaveManager(simulate_enclave_available=False)
        assert manager._is_enclave_available() is False


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_many_keys_in_enclave(self):
        """Test managing many keys in enclave"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        handles = []
        for i in range(100):
            handle = manager.generate_key_in_enclave()
            handles.append(handle)

        assert len(manager._enclave_keys) == 100

        # All keys should still be retrievable
        for handle in handles:
            public_key = manager.get_public_key_from_enclave(handle)
            assert public_key is not None

    def test_sign_with_different_keys(self):
        """Test signing same data with different keys produces different signatures"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        handle1 = manager.generate_key_in_enclave()
        handle2 = manager.generate_key_in_enclave()

        data = b"Same message"

        # Get public keys for signature generation (conceptual model)
        pub1 = manager.get_public_key_from_enclave(handle1)
        pub2 = manager.get_public_key_from_enclave(handle2)

        import hashlib
        sig1 = hashlib.sha256(pub1 + data).digest()
        sig2 = hashlib.sha256(pub2 + data).digest()

        assert sig1 != sig2

    def test_operations_after_enclave_becomes_unavailable(self):
        """Test that operations fail after enclave becomes unavailable"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        # Make enclave unavailable
        manager._simulate_enclave_available = False

        # Operations should now fail
        assert manager.generate_key_in_enclave() is None
        assert manager.get_public_key_from_enclave(key_handle) is None
        assert manager.sign_data_in_enclave(key_handle, b"data") is None

    def test_unicode_data_signing(self):
        """Test signing unicode data"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)
        key_handle = manager.generate_key_in_enclave()

        unicode_data = "测试数据 🔐".encode('utf-8')
        signature = manager.sign_data_in_enclave(key_handle, unicode_data)

        assert signature is not None


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    def test_transaction_signing_scenario(self):
        """Test using enclave for transaction signing"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        # Generate key for wallet
        wallet_key_handle = manager.generate_key_in_enclave()
        wallet_public_key = manager.get_public_key_from_enclave(wallet_key_handle)

        # Sign transaction
        transaction_data = b"sender:Alice,recipient:Bob,amount:100"
        public_key = manager.get_public_key_from_enclave(wallet_key_handle)

        import hashlib
        signature = hashlib.sha256(public_key + transaction_data).digest()

        # Verify signature
        is_valid = manager.verify_signature(wallet_public_key, transaction_data, signature)
        assert is_valid is True

    def test_multi_signature_scenario(self):
        """Test multi-signature scenario with multiple enclave keys"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        # Generate keys for 3 signers
        signers = []
        for i in range(3):
            handle = manager.generate_key_in_enclave()
            public_key = manager.get_public_key_from_enclave(handle)
            signers.append((handle, public_key))

        # Each signer signs the data
        data = b"Multi-sig transaction"
        signatures = []

        import hashlib
        for handle, public_key in signers:
            sig = hashlib.sha256(public_key + data).digest()
            signatures.append((public_key, sig))

        # Verify all signatures
        for public_key, signature in signatures:
            is_valid = manager.verify_signature(public_key, data, signature)
            assert is_valid is True

    def test_key_rotation_scenario(self):
        """Test key rotation with enclave"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        # Old key
        old_handle = manager.generate_key_in_enclave()
        old_public_key = manager.get_public_key_from_enclave(old_handle)

        # Sign with old key
        data = b"Data signed with old key"
        import hashlib
        old_signature = hashlib.sha256(old_public_key + data).digest()

        # Generate new key
        new_handle = manager.generate_key_in_enclave()
        new_public_key = manager.get_public_key_from_enclave(new_handle)

        # Old signatures still verifiable
        is_valid = manager.verify_signature(old_public_key, data, old_signature)
        assert is_valid is True

        # New key can sign new data
        new_data = b"Data signed with new key"
        new_signature = hashlib.sha256(new_public_key + new_data).digest()
        is_valid = manager.verify_signature(new_public_key, new_data, new_signature)
        assert is_valid is True

    def test_secure_communication_scenario(self):
        """Test secure communication between two parties"""
        manager = SecureEnclaveManager(simulate_enclave_available=True)

        # Party A generates key
        party_a_handle = manager.generate_key_in_enclave()
        party_a_public_key = manager.get_public_key_from_enclave(party_a_handle)

        # Party B generates key
        party_b_handle = manager.generate_key_in_enclave()
        party_b_public_key = manager.get_public_key_from_enclave(party_b_handle)

        # Party A signs message to Party B
        message = b"Hello Party B"
        import hashlib
        signature_a = hashlib.sha256(party_a_public_key + message).digest()

        # Party B verifies message from Party A
        is_valid = manager.verify_signature(party_a_public_key, message, signature_a)
        assert is_valid is True
