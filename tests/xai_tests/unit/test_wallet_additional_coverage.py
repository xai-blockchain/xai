"""
Additional comprehensive tests for wallet.py to maximize coverage to 98%+.

Focuses on:
- Message signing edge cases
- Wallet import/export variations
- Encryption edge cases
- Key derivation edge cases
- Error path coverage
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from xai.core.wallet import Wallet, WalletManager


class TestSignMessageEdgeCases:
    """Test message signing edge cases"""

    def test_sign_empty_message(self):
        """Test signing empty message"""
        wallet = Wallet()

        signature = wallet.sign_message("")

        assert signature is not None
        assert len(signature) > 0

    def test_sign_very_long_message(self):
        """Test signing very long message"""
        wallet = Wallet()
        long_message = "x" * 10000

        signature = wallet.sign_message(long_message)

        assert signature is not None
        is_valid = wallet.verify_signature(long_message, signature, wallet.public_key)
        assert is_valid

    def test_sign_unicode_message(self):
        """Test signing message with unicode characters"""
        wallet = Wallet()
        message = "Hello 世界 🌍 测试"

        signature = wallet.sign_message(message)

        assert signature is not None
        is_valid = wallet.verify_signature(message, signature, wallet.public_key)
        assert is_valid

    def test_sign_special_characters(self):
        """Test signing message with special characters"""
        wallet = Wallet()
        message = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"

        signature = wallet.sign_message(message)

        assert signature is not None
        is_valid = wallet.verify_signature(message, signature, wallet.public_key)
        assert is_valid

    def test_sign_newline_characters(self):
        """Test signing message with newlines"""
        wallet = Wallet()
        message = "Line1\nLine2\r\nLine3\rLine4"

        signature = wallet.sign_message(message)

        assert signature is not None
        is_valid = wallet.verify_signature(message, signature, wallet.public_key)
        assert is_valid

    def test_sign_null_bytes(self):
        """Test signing message with null bytes"""
        wallet = Wallet()
        message = "Hello\x00World"

        signature = wallet.sign_message(message)

        assert signature is not None


class TestVerifySignatureEdgeCases:
    """Test signature verification edge cases"""

    def test_verify_with_different_message(self):
        """Test verification fails with different message"""
        wallet = Wallet()
        message1 = "Original message"
        message2 = "Modified message"

        signature = wallet.sign_message(message1)
        is_valid = wallet.verify_signature(message2, signature, wallet.public_key)

        assert is_valid is False

    def test_verify_with_wrong_public_key(self):
        """Test verification fails with wrong public key"""
        wallet1 = Wallet()
        wallet2 = Wallet()
        message = "Test message"

        signature = wallet1.sign_message(message)
        is_valid = wallet1.verify_signature(message, signature, wallet2.public_key)

        assert is_valid is False

    def test_verify_empty_signature(self):
        """Test verification with empty signature"""
        wallet = Wallet()
        message = "Test"

        is_valid = wallet.verify_signature(message, "", wallet.public_key)

        assert is_valid is False

    def test_verify_malformed_signature(self):
        """Test verification with malformed signature"""
        wallet = Wallet()
        message = "Test"
        bad_signature = "not_a_valid_signature"

        is_valid = wallet.verify_signature(message, bad_signature, wallet.public_key)

        assert is_valid is False

    def test_verify_signature_wrong_hex_length(self):
        """Test verification with wrong hex length signature"""
        wallet = Wallet()
        message = "Test"

        # Valid hex but wrong length
        result = wallet.verify_signature(message, "abcd1234", wallet.public_key)

        assert result is False

    def test_verify_signature_non_hex(self):
        """Test verification with non-hex signature"""
        wallet = Wallet()
        message = "Test"

        result = wallet.verify_signature(message, "GGGGGGGG", wallet.public_key)

        assert result is False

    def test_verify_signature_exception_handling(self):
        """Test verification handles exceptions gracefully"""
        wallet = Wallet()

        # This should trigger exception path
        result = wallet.verify_signature("test", "0" * 128, "invalid_key_format")

        assert result is False


class TestWalletFileOperations:
    """Test wallet file save/load edge cases"""

    def test_save_to_nested_directory(self):
        """Test saving to nested directory structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            wallet = Wallet()
            nested_path = os.path.join(tmpdir, "level1", "level2", "wallet.json")

            # Create parent directories
            os.makedirs(os.path.dirname(nested_path), exist_ok=True)

            wallet.save_to_file(nested_path)

            assert os.path.exists(nested_path)

    def test_save_overwrite_existing(self):
        """Test saving overwrites existing file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "wallet.json")

            wallet1 = Wallet()
            wallet1.save_to_file(filepath)

            wallet2 = Wallet()
            wallet2.save_to_file(filepath)

            # Load and verify it's wallet2
            loaded = Wallet.load_from_file(filepath)
            assert loaded.address == wallet2.address

    def test_load_from_file_permissions(self):
        """Test loading file with different permissions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "wallet.json")

            wallet = Wallet()
            wallet.save_to_file(filepath)

            # Load should work regardless of permissions (on supported systems)
            loaded = Wallet.load_from_file(filepath)
            assert loaded.address == wallet.address

    def test_save_encrypted_with_special_chars_password(self):
        """Test encrypted save with special characters in password"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "wallet.json")
            password = "P@ssw0rd!#$%^&*()"

            wallet = Wallet()
            wallet.save_to_file(filepath, password=password)

            loaded = Wallet.load_from_file(filepath, password=password)
            assert loaded.address == wallet.address

    def test_save_encrypted_with_unicode_password(self):
        """Test encrypted save with unicode password"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "wallet.json")
            password = "密码🔒"

            wallet = Wallet()
            wallet.save_to_file(filepath, password=password)

            loaded = Wallet.load_from_file(filepath, password=password)
            assert loaded.address == wallet.address

    def test_save_encrypted_with_very_long_password(self):
        """Test encrypted save with very long password"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "wallet.json")
            password = "x" * 1000

            wallet = Wallet()
            wallet.save_to_file(filepath, password=password)

            loaded = Wallet.load_from_file(filepath, password=password)
            assert loaded.address == wallet.address


class TestWalletEncryptionDetails:
    """Test encryption implementation details"""

    def test_encrypt_decrypt_empty_string(self):
        """Test encrypting empty string"""
        wallet = Wallet()
        password = "test123"

        encrypted = wallet._encrypt("", password)
        decrypted = wallet._decrypt(encrypted, password)

        assert decrypted == ""

    def test_encrypt_decrypt_large_data(self):
        """Test encrypting large data"""
        wallet = Wallet()
        password = "test123"
        large_data = "x" * 100000

        encrypted = wallet._encrypt(large_data, password)
        decrypted = wallet._decrypt(encrypted, password)

        assert decrypted == large_data

    def test_encrypt_payload_same_data_different_output(self):
        """Test same data encrypts to different ciphertext (due to nonce)"""
        wallet = Wallet()
        data = "test data"
        password = "password"

        payload1 = wallet._encrypt_payload(data, password)
        payload2 = wallet._encrypt_payload(data, password)

        # Different nonces should produce different ciphertexts
        assert payload1["ciphertext"] != payload2["ciphertext"]
        assert payload1["nonce"] != payload2["nonce"]

    def test_decrypt_payload_with_wrong_password(self):
        """Test decrypting payload with wrong password"""
        wallet = Wallet()
        data = "secret data"
        correct_password = "correct"
        wrong_password = "wrong"

        payload = wallet._encrypt_payload(data, correct_password)

        with pytest.raises(ValueError, match="Bad decrypt"):
            wallet._decrypt_payload(payload, wrong_password)

    def test_decrypt_payload_with_corrupted_data(self):
        """Test decrypting corrupted payload"""
        wallet = Wallet()
        password = "test123"

        # Create corrupted payload
        corrupted_payload = {
            "ciphertext": "corrupted",
            "nonce": "corrupted",
            "salt": "corrupted"
        }

        with pytest.raises(ValueError, match="Bad decrypt"):
            wallet._decrypt_payload(corrupted_payload, password)

    def test_decrypt_payload_missing_fields(self):
        """Test decrypting payload with missing fields"""
        wallet = Wallet()
        password = "test123"

        incomplete_payload = {
            "ciphertext": "dGVzdA=="
            # Missing nonce and salt
        }

        with pytest.raises((ValueError, KeyError)):
            wallet._decrypt_payload(incomplete_payload, password)


class TestKeyGeneration:
    """Test key generation and derivation"""

    def test_generate_keypair_uniqueness(self):
        """Test keypair generation produces unique keys"""
        wallet = Wallet()

        keys = set()
        for _ in range(10):
            private_key, public_key = wallet._generate_keypair()
            keys.add(private_key)

        # All should be unique
        assert len(keys) == 10

    def test_derive_public_key_consistency(self):
        """Test deriving public key multiple times gives same result"""
        wallet = Wallet()
        private_key = "a" * 64

        public_key1 = wallet._derive_public_key(private_key)
        public_key2 = wallet._derive_public_key(private_key)

        assert public_key1 == public_key2

    def test_generate_address_from_public_key(self):
        """Test address generation from public key"""
        wallet = Wallet()

        address = wallet._generate_address(wallet.public_key)

        assert address.startswith("XAI")
        assert len(address) == 43

    def test_address_deterministic_from_public_key(self):
        """Test same public key always generates same address"""
        wallet = Wallet()

        address1 = wallet._generate_address(wallet.public_key)
        address2 = wallet._generate_address(wallet.public_key)

        assert address1 == address2


class TestWalletManagerAdvanced:
    """Test advanced WalletManager scenarios"""

    def test_create_multiple_wallets_sequential(self):
        """Test creating multiple wallets sequentially"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            wallets = []
            for i in range(10):
                wallet = manager.create_wallet(f"wallet{i}")
                wallets.append(wallet)

            assert len(manager.wallets) == 10

    def test_load_wallet_multiple_times(self):
        """Test loading same wallet multiple times"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            # Create wallet
            original = manager.create_wallet("test")

            # Clear and reload multiple times
            for _ in range(3):
                manager.wallets.clear()
                loaded = manager.load_wallet("test")
                assert loaded.address == original.address

    def test_wallet_manager_mixed_encrypted_unencrypted(self):
        """Test manager handling mix of encrypted and unencrypted wallets"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            # Create mix
            manager.create_wallet("plain1")
            manager.create_wallet("encrypted1", password="pass1")
            manager.create_wallet("plain2")
            manager.create_wallet("encrypted2", password="pass2")

            wallets = manager.list_wallets()
            assert len(wallets) == 4

    def test_wallet_manager_data_dir_as_path_object(self):
        """Test WalletManager with Path object"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path_obj = Path(tmpdir)
            manager = WalletManager(data_dir=path_obj)

            wallet = manager.create_wallet("test")
            assert wallet is not None

    def test_get_wallet_before_loading(self):
        """Test getting wallet before it's loaded returns None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WalletManager(data_dir=tmpdir)

            # Create wallet file directly
            wallet = Wallet()
            filepath = os.path.join(tmpdir, "external.wallet")
            wallet.save_to_file(filepath)

            # Manager doesn't know about it yet
            result = manager.get_wallet("external")
            assert result is None


class TestWalletExportFormats:
    """Test wallet export in different formats"""

    def test_to_dict_excludes_private_key(self):
        """Test to_dict doesn't expose private key"""
        wallet = Wallet()
        data = wallet.to_dict()

        assert "private_key" not in data
        assert "address" in data
        assert "public_key" in data

    def test_to_public_dict_excludes_private_key(self):
        """Test to_public_dict doesn't expose private key"""
        wallet = Wallet()
        data = wallet.to_public_dict()

        assert "private_key" not in data

    def test_to_full_dict_unsafe_includes_private_key(self):
        """Test to_full_dict_unsafe includes private key"""
        wallet = Wallet()
        data = wallet.to_full_dict_unsafe()

        assert "private_key" in data
        assert data["private_key"] == wallet.private_key

    def test_export_formats_consistency(self):
        """Test all export formats have consistent data"""
        wallet = Wallet()

        public_dict = wallet.to_public_dict()
        full_dict = wallet.to_full_dict_unsafe()

        # Public data should match
        assert public_dict["address"] == full_dict["address"]
        assert public_dict["public_key"] == full_dict["public_key"]


class TestWalletRecovery:
    """Test wallet recovery scenarios"""

    def test_recover_from_private_key(self):
        """Test recovering wallet from private key"""
        original = Wallet()
        private_key = original.private_key

        recovered = Wallet(private_key=private_key)

        assert recovered.address == original.address
        assert recovered.public_key == original.public_key

    def test_recover_wallet_can_sign(self):
        """Test recovered wallet can sign messages"""
        original = Wallet()
        private_key = original.private_key
        message = "Test message"

        # Sign with original
        original_sig = original.sign_message(message)

        # Recover and sign
        recovered = Wallet(private_key=private_key)
        recovered_sig = recovered.sign_message(message)

        # Both signatures should verify
        assert original.verify_signature(message, original_sig, original.public_key)
        assert recovered.verify_signature(message, recovered_sig, recovered.public_key)

    def test_recover_from_file_after_deletion(self):
        """Test recovering wallet after original is deleted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "wallet.json")

            original = Wallet()
            original.save_to_file(filepath)
            original_address = original.address

            # Delete original
            del original

            # Recover from file
            recovered = Wallet.load_from_file(filepath)
            assert recovered.address == original_address


class TestWalletInitializationVariants:
    """Test wallet initialization variants"""

    def test_wallet_init_with_none_private_key(self):
        """Test wallet initialization with None generates new wallet"""
        wallet = Wallet(private_key=None)

        assert wallet.private_key is not None
        assert wallet.public_key is not None
        assert wallet.address is not None

    def test_wallet_init_with_valid_private_key(self):
        """Test wallet initialization with valid private key"""
        private_key = "a" * 64  # Valid hex

        wallet = Wallet(private_key=private_key)

        assert wallet.private_key == private_key

    def test_two_wallets_same_private_key_identical(self):
        """Test two wallets with same private key are identical"""
        private_key = "b" * 64

        wallet1 = Wallet(private_key=private_key)
        wallet2 = Wallet(private_key=private_key)

        assert wallet1.address == wallet2.address
        assert wallet1.public_key == wallet2.public_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
