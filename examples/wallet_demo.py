#!/usr/bin/env python3
"""
XAI Wallet Demo - Safe Examples

This demonstrates wallet functionality WITHOUT exposing private keys.
For production use, never log or print private key material.
"""

import logging
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xai.core.wallet import Wallet, WalletManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def demo_wallet_creation():
    """Demonstrate creating a new wallet safely."""
    logger.info("=== Wallet Creation Demo ===")

    # Create new wallet
    wallet = Wallet()

    # SAFE: Only show public information
    logger.info("Wallet Created Successfully")
    logger.info("Address: %s", wallet.address)
    logger.info("Public Key (first 32 chars): %s...", wallet.public_key[:32])

    # SECURITY: Never log private keys in production!
    # logger.info("Private Key: %s", wallet.private_key)  # NEVER DO THIS

    return wallet


def demo_message_signing(wallet: Wallet):
    """Demonstrate message signing and verification."""
    logger.info("\n=== Message Signing Demo ===")

    message = "Hello XAI Blockchain!"
    signature = wallet.sign_message(message)

    logger.info("Message: %s", message)
    logger.info("Signature (first 64 chars): %s...", signature[:64])

    # Verify signature
    is_valid = wallet.verify_signature(message, signature, wallet.public_key)
    logger.info("Signature Valid: %s", is_valid)

    # Demonstrate invalid signature detection
    tampered_message = "Tampered message"
    is_invalid = wallet.verify_signature(tampered_message, signature, wallet.public_key)
    logger.info("Tampered message verification (should be False): %s", is_invalid)


def demo_wallet_persistence(wallet: Wallet):
    """Demonstrate saving and loading wallets securely."""
    logger.info("\n=== Wallet Persistence Demo ===")

    # Use a temporary directory for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        wallet_path = Path(tmpdir) / "demo_wallet.json"
        password = "demo_password_123"

        # Save with encryption
        wallet.save_to_file(str(wallet_path), password=password)
        logger.info("Wallet saved (encrypted) to: %s", wallet_path)

        # Load wallet
        loaded_wallet = Wallet.load_from_file(str(wallet_path), password=password)
        logger.info("Wallet loaded successfully")
        logger.info("Address matches: %s", wallet.address == loaded_wallet.address)

        # Demonstrate wrong password handling
        try:
            Wallet.load_from_file(str(wallet_path), password="wrong_password")
            logger.error("Should have raised an exception!")
        except Exception as e:
            logger.info("Wrong password correctly rejected: %s", type(e).__name__)


def demo_wallet_manager():
    """Demonstrate WalletManager for multiple wallets."""
    logger.info("\n=== Wallet Manager Demo ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = WalletManager(data_dir=tmpdir)

        # Create multiple wallets
        wallet1 = manager.create_wallet("alice", password="alice_pass")
        wallet2 = manager.create_wallet("bob", password="bob_pass")

        logger.info("Created wallets: %s", manager.list_wallets())
        logger.info("Alice's address: %s", wallet1.address)
        logger.info("Bob's address: %s", wallet2.address)


def main():
    """Run all demos."""
    logger.info("XAI Wallet Demo")
    logger.info("===============")
    logger.info("This demo shows wallet operations without exposing private keys.\n")

    # Run demos
    wallet = demo_wallet_creation()
    demo_message_signing(wallet)
    demo_wallet_persistence(wallet)
    demo_wallet_manager()

    logger.info("\n=== Demo Complete ===")
    logger.info("For production use, ensure you:")
    logger.info("  1. Never log or print private keys")
    logger.info("  2. Always encrypt wallets with strong passwords")
    logger.info("  3. Use secure key storage (HSM, secure enclave)")


if __name__ == "__main__":
    main()
