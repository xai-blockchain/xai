"""
Test suite for XAI Wallet functionality

Tests:
- Wallet creation
- Address generation
- Key pair generation
- Transaction signing
- Balance checking
"""

import pytest
import sys
import os
import time
import base64
from cryptography.fernet import Fernet

from xai.core.wallet import Wallet, WalletManager
from xai.core.blockchain import Transaction


class TestWalletCreation:
    """Test wallet creation and key generation"""

    def test_wallet_initialization(self, tmp_path):
        """Test that wallet initializes correctly"""
        wallet = Wallet()

        assert wallet.private_key is not None, "Private key should exist"
        assert wallet.public_key is not None, "Public key should exist"
        assert wallet.address is not None, "Address should exist"

    def test_unique_wallets(self, tmp_path):
        """Test that each wallet is unique"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        assert wallet1.private_key != wallet2.private_key, "Private keys should be unique"
        assert wallet1.address != wallet2.address, "Addresses should be unique"

    def test_address_format(self, tmp_path):
        """Test address format (should start with XAI or TXAI)"""
        wallet = Wallet()

        # Address should start with XAI or TXAI prefix
        assert wallet.address.startswith("XAI") or wallet.address.startswith(
            "TXAI"
        ), "Address should start with XAI or TXAI prefix"

    def test_private_key_length(self, tmp_path):
        """Test private key is correct length"""
        wallet = Wallet()

        # ECDSA private key should be 64 hex characters (32 bytes)
        assert len(wallet.private_key) == 64, "Private key should be 64 hex characters"

    def test_public_key_length(self, tmp_path):
        """Test public key is correct length"""
        wallet = Wallet()

        # ECDSA public key should be 128 hex characters (64 bytes uncompressed)
        assert len(wallet.public_key) == 128, "Public key should be 128 hex characters"


class TestWalletSigning:
    """Test transaction signing with wallet"""

    def test_sign_transaction(self, tmp_path):
        """Test that wallet can sign transactions"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
        tx.public_key = wallet1.public_key
        tx.sign_transaction(wallet1.private_key)

        assert tx.signature is not None, "Transaction should be signed"
        assert tx.verify_signature(), "Signature should be valid"

    def test_signature_uniqueness(self, tmp_path):
        """Test that signatures are unique per transaction"""
        wallet = Wallet()
        recipient = Wallet()  # Create a valid recipient wallet

        tx1 = Transaction(wallet.address, recipient.address, 10.0, 0.24)
        tx2 = Transaction(wallet.address, recipient.address, 10.0, 0.24)

        tx1.public_key = wallet.public_key
        tx2.public_key = wallet.public_key
        tx1.sign_transaction(wallet.private_key)
        tx2.sign_transaction(wallet.private_key)

        # Signatures should be different due to different timestamps
        assert tx1.signature != tx2.signature, "Signatures should be unique"


class TestWalletOperations:
    """Test wallet operations with blockchain"""

    def test_wallet_can_receive(self, tmp_path):
        """Test that wallet can receive XAI"""
        from xai.core.blockchain import Blockchain

        bc = Blockchain(data_dir=str(tmp_path))
        wallet = Wallet()

        # Mine block to wallet
        bc.mine_pending_transactions(wallet.address)

        balance = bc.get_balance(wallet.address)
        assert balance > 0, "Wallet should have balance after mining"

    def test_wallet_can_send(self, tmp_path):
        """Test that wallet can send XAI"""
        from xai.core.blockchain import Blockchain

        bc = Blockchain(data_dir=str(tmp_path))
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get some XAI
        bc.mine_pending_transactions(wallet1.address)

        initial_balance = bc.get_balance(wallet1.address)

        # Send transaction using blockchain's create_transaction method
        tx = bc.create_transaction(
            wallet1.address, wallet2.address, 5.0, 0.24, wallet1.private_key, wallet1.public_key
        )
        assert tx is not None, "Transaction creation should succeed"
        bc.add_transaction(tx)

        bc.mine_pending_transactions(wallet1.address)

        # Check wallet2 received
        balance2 = bc.get_balance(wallet2.address)
        assert balance2 == 5.0, "Wallet2 should have received 5 XAI"


class TestWalletSecurity:
    """Test wallet security features"""

    def test_cannot_forge_signature(self, tmp_path):
        """Test that signatures cannot be forged"""
        wallet1 = Wallet()
        wallet2 = Wallet()
        recipient = Wallet()  # Create a valid recipient

        tx = Transaction(wallet1.address, recipient.address, 10.0, 0.24)
        tx.public_key = wallet1.public_key  # Set the expected signer's public key

        # Try to sign with wrong wallet (wallet2's private key)
        tx.sign_transaction(wallet2.private_key)

        # Verification should fail because signature was made with wallet2's key
        # but public_key is set to wallet1's key
        assert not tx.verify_signature(), "Forged signature should not verify"

    def test_cannot_modify_signed_transaction(self, tmp_path):
        """Test that signed transactions cannot be modified"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
        tx.sign_transaction(wallet1.private_key)

        # Try to modify amount
        original_amount = tx.amount
        tx.amount = 1000.0

        # Signature should no longer be valid
        assert not tx.verify_signature(), "Modified transaction signature should fail"

        # Restore amount
        tx.amount = original_amount


class TestWalletPersistence:
    """Test wallet save/load functionality"""

    def test_wallet_data_structure(self, tmp_path):
        """Test that wallet can be serialized to JSON"""
        wallet = Wallet()

        wallet_data = {
            "address": wallet.address,
            "private_key": wallet.private_key,
            "public_key": wallet.public_key,
        }

        assert "address" in wallet_data, "Wallet data should have address"
        assert "private_key" in wallet_data, "Wallet data should have private key"
        assert "public_key" in wallet_data, "Wallet data should have public key"

    def test_save_and_load_unencrypted_wallet(self, tmp_path):
        """Test saving and loading an unencrypted wallet"""
        wallet_name = "test_unencrypted"
        wallet_file = tmp_path / f"{wallet_name}.wallet"

        original_wallet = Wallet()
        original_wallet.save_to_file(str(wallet_file))

        loaded_wallet = Wallet.load_from_file(str(wallet_file))

        assert loaded_wallet.private_key == original_wallet.private_key
        assert loaded_wallet.public_key == original_wallet.public_key
        assert loaded_wallet.address == original_wallet.address

    def test_save_and_load_encrypted_wallet(self, tmp_path):
        """Test saving and loading an encrypted wallet"""
        wallet_name = "test_encrypted"
        wallet_file = tmp_path / f"{wallet_name}.wallet"
        password = "test_password"

        original_wallet = Wallet()
        original_wallet.save_to_file(str(wallet_file), password)

        loaded_wallet = Wallet.load_from_file(str(wallet_file), password)

        assert loaded_wallet.private_key == original_wallet.private_key
        assert loaded_wallet.public_key == original_wallet.public_key
        assert loaded_wallet.address == original_wallet.address

    def test_load_encrypted_wallet_wrong_password(self, tmp_path):
        """Test loading an encrypted wallet with the wrong password"""
        wallet_name = "test_encrypted_wrong_pass"
        wallet_file = tmp_path / f"{wallet_name}.wallet"
        correct_password = "correct_password"
        wrong_password = "wrong_password"

        original_wallet = Wallet()
        original_wallet.save_to_file(str(wallet_file), correct_password)

        with pytest.raises(ValueError, match="Decryption failed"):
            Wallet.load_from_file(str(wallet_file), wrong_password)

    def test_load_encrypted_wallet_no_password(self, tmp_path):
        """Test loading an encrypted wallet without providing a password"""
        wallet_name = "test_encrypted_no_pass"
        wallet_file = tmp_path / f"{wallet_name}.wallet"
        password = "test_password"

        original_wallet = Wallet()
        original_wallet.save_to_file(str(wallet_file), password)

        with pytest.raises(ValueError, match="Password required for encrypted wallet"):
            Wallet.load_from_file(str(wallet_file))


@pytest.fixture
def wallet_manager_cleanup(tmp_path):
    """Fixture to create a WalletManager with a temporary directory and clean up afterwards."""
    manager = WalletManager(data_dir=str(tmp_path / "wallets"))
    yield manager
    # Cleanup is handled by tmp_path fixture for the directory itself


class TestWalletManager:
    """Test WalletManager functionality"""

    def test_manager_initialization(self, wallet_manager_cleanup):
        """Test that WalletManager initializes correctly"""
        manager = wallet_manager_cleanup
        assert manager.data_dir.is_dir()
        assert len(manager.wallets) == 0

    def test_create_and_load_unencrypted_wallet(self, wallet_manager_cleanup):
        """Test creating and loading an unencrypted wallet via WalletManager"""
        manager = wallet_manager_cleanup
        wallet_name = "manager_unencrypted"

        created_wallet = manager.create_wallet(wallet_name)
        assert created_wallet is not None
        assert wallet_name in manager.wallets
        assert (manager.data_dir / f"{wallet_name}.wallet").exists()

        loaded_wallet = manager.load_wallet(wallet_name)
        assert loaded_wallet.address == created_wallet.address
        assert loaded_wallet.private_key == created_wallet.private_key

    def test_create_and_load_encrypted_wallet(self, wallet_manager_cleanup):
        """Test creating and loading an encrypted wallet via WalletManager"""
        manager = wallet_manager_cleanup
        wallet_name = "manager_encrypted"
        password = "secure_password"

        created_wallet = manager.create_wallet(wallet_name, password)
        assert created_wallet is not None
        assert wallet_name in manager.wallets
        assert (manager.data_dir / f"{wallet_name}.wallet").exists()

        loaded_wallet = manager.load_wallet(wallet_name, password)
        assert loaded_wallet.address == created_wallet.address
        assert loaded_wallet.private_key == created_wallet.private_key

    def test_load_non_existent_wallet(self, wallet_manager_cleanup):
        """Test loading a wallet that does not exist"""
        manager = wallet_manager_cleanup
        with pytest.raises(FileNotFoundError):
            manager.load_wallet("non_existent_wallet")

    def test_load_encrypted_wallet_wrong_password_manager(self, wallet_manager_cleanup):
        """Test loading an encrypted wallet with the wrong password via WalletManager"""
        manager = wallet_manager_cleanup
        wallet_name = "manager_encrypted_wrong_pass"
        correct_password = "correct_password"
        wrong_password = "wrong_password"

        manager.create_wallet(wallet_name, correct_password)

        with pytest.raises(ValueError, match="Decryption failed"):
            manager.load_wallet(wallet_name, wrong_password)

    def test_list_wallets(self, wallet_manager_cleanup):
        """Test listing available wallets"""
        manager = wallet_manager_cleanup
        manager.create_wallet("wallet_a")
        manager.create_wallet("wallet_b", "pass")

        wallets = manager.list_wallets()
        assert "wallet_a" in wallets
        assert "wallet_b" in wallets
        assert len(wallets) == 2

    def test_get_loaded_wallet(self, wallet_manager_cleanup):
        """Test getting a wallet that is already loaded"""
        manager = wallet_manager_cleanup
        wallet_name = "loaded_wallet"
        created_wallet = manager.create_wallet(wallet_name)

        retrieved_wallet = manager.get_wallet(wallet_name)
        assert retrieved_wallet is not None
        assert retrieved_wallet.address == created_wallet.address

    def test_get_unloaded_wallet(self, wallet_manager_cleanup):
        """Test getting a wallet that is not loaded"""
        manager = wallet_manager_cleanup
        # Create a wallet file directly without loading it into manager.wallets
        wallet_name = "unloaded_wallet"
        Wallet().save_to_file(str(manager.data_dir / f"{wallet_name}.wallet"))

        retrieved_wallet = manager.get_wallet(wallet_name)
        assert retrieved_wallet is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
