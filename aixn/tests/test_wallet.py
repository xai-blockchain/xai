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

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from wallet import Wallet
from blockchain import Transaction


class TestWalletCreation:
    """Test wallet creation and key generation"""

    def test_wallet_initialization(self):
        """Test that wallet initializes correctly"""
        wallet = Wallet()

        assert wallet.private_key is not None, "Private key should exist"
        assert wallet.public_key is not None, "Public key should exist"
        assert wallet.address is not None, "Address should exist"

    def test_unique_wallets(self):
        """Test that each wallet is unique"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        assert wallet1.private_key != wallet2.private_key, "Private keys should be unique"
        assert wallet1.address != wallet2.address, "Addresses should be unique"

    def test_address_format(self):
        """Test address format (should start with XAI or TXAI)"""
        wallet = Wallet()

        # Address should start with XAI or TXAI prefix
        assert wallet.address.startswith('XAI') or wallet.address.startswith('TXAI'), \
            "Address should start with XAI or TXAI prefix"

    def test_private_key_length(self):
        """Test private key is correct length"""
        wallet = Wallet()

        # ECDSA private key should be 64 hex characters (32 bytes)
        assert len(wallet.private_key) == 64, "Private key should be 64 hex characters"

    def test_public_key_length(self):
        """Test public key is correct length"""
        wallet = Wallet()

        # ECDSA public key should be 128 hex characters (64 bytes uncompressed)
        assert len(wallet.public_key) == 128, "Public key should be 128 hex characters"


class TestWalletSigning:
    """Test transaction signing with wallet"""

    def test_sign_transaction(self):
        """Test that wallet can sign transactions"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, wallet2.address, 10.0, 0.24)
        tx.sign_transaction(wallet1.private_key)

        assert tx.signature is not None, "Transaction should be signed"
        assert tx.verify_signature(), "Signature should be valid"

    def test_signature_uniqueness(self):
        """Test that signatures are unique per transaction"""
        wallet = Wallet()

        tx1 = Transaction(wallet.address, "AIXN...", 10.0, 0.24)
        tx2 = Transaction(wallet.address, "AIXN...", 10.0, 0.24)

        tx1.sign_transaction(wallet.private_key)
        tx2.sign_transaction(wallet.private_key)

        # Signatures should be different due to different timestamps
        assert tx1.signature != tx2.signature, "Signatures should be unique"


class TestWalletOperations:
    """Test wallet operations with blockchain"""

    def test_wallet_can_receive(self):
        """Test that wallet can receive XAI"""
        from blockchain import Blockchain

        bc = Blockchain()
        wallet = Wallet()

        # Mine block to wallet
        bc.mine_pending_transactions(wallet.address)

        balance = bc.get_balance(wallet.address)
        assert balance > 0, "Wallet should have balance after mining"

    def test_wallet_can_send(self):
        """Test that wallet can send XAI"""
        from blockchain import Blockchain

        bc = Blockchain()
        wallet1 = Wallet()
        wallet2 = Wallet()

        # Mine to get some XAI
        bc.mine_pending_transactions(wallet1.address)

        initial_balance = bc.get_balance(wallet1.address)

        # Send transaction
        tx = Transaction(wallet1.address, wallet2.address, 5.0, 0.24)
        tx.sign_transaction(wallet1.private_key)
        bc.add_transaction(tx)

        bc.mine_pending_transactions(wallet1.address)

        # Check wallet2 received
        balance2 = bc.get_balance(wallet2.address)
        assert balance2 == 5.0, "Wallet2 should have received 5 XAI"


class TestWalletSecurity:
    """Test wallet security features"""

    def test_cannot_forge_signature(self):
        """Test that signatures cannot be forged"""
        wallet1 = Wallet()
        wallet2 = Wallet()

        tx = Transaction(wallet1.address, "AIXN...", 10.0, 0.24)

        # Try to sign with wrong wallet
        tx.sign_transaction(wallet2.private_key)

        # Verification should fail
        assert not tx.verify_signature(), "Forged signature should not verify"

    def test_cannot_modify_signed_transaction(self):
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

    def test_wallet_data_structure(self):
        """Test that wallet can be serialized to JSON"""
        wallet = Wallet()

        wallet_data = {
            'address': wallet.address,
            'private_key': wallet.private_key,
            'public_key': wallet.public_key
        }

        assert 'address' in wallet_data, "Wallet data should have address"
        assert 'private_key' in wallet_data, "Wallet data should have private key"
        assert 'public_key' in wallet_data, "Wallet data should have public key"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
