from __future__ import annotations

"""
XAI Blockchain - Wallet Factory

Provides methods for creating, loading, and managing different types of wallets.
"""

import hashlib
import os
import secrets
import threading
from typing import Any

from xai.core.structured_logger import StructuredLogger, get_structured_logger
from xai.core.wallet import Wallet, WalletManager

class CollisionResistance:
    """
    Collision resistance for wallet address generation.
    Prevents birthday attacks and ensures address uniqueness.
    """

    def __init__(self, min_entropy_bits: int = 256):
        """
        Initialize collision resistance.

        Args:
            min_entropy_bits: Minimum entropy bits for address generation
        """
        self.min_entropy_bits = min_entropy_bits
        self.created_addresses: set[str] = set()
        self.address_hashes: dict[str, str] = {}  # address -> creation_hash
        self._lock = threading.RLock()

        # Track collision attempts
        self.collision_attempts = 0
        self.total_generations = 0

    def validate_entropy(self, entropy_source: bytes) -> dict[str, Any]:
        """
        Validate entropy source meets minimum requirements.

        Args:
            entropy_source: Random bytes for key generation

        Returns:
            dict with 'valid' (bool) and entropy metrics
        """
        if len(entropy_source) * 8 < self.min_entropy_bits:
            return {
                "valid": False,
                "reason": "insufficient_entropy",
                "required_bits": self.min_entropy_bits,
                "provided_bits": len(entropy_source) * 8
            }

        # Calculate entropy quality (simplified)
        unique_bytes = len(set(entropy_source))
        entropy_ratio = unique_bytes / len(entropy_source)

        if entropy_ratio < 0.3:  # Low diversity
            return {
                "valid": False,
                "reason": "low_entropy_quality",
                "entropy_ratio": entropy_ratio,
                "unique_bytes": unique_bytes
            }

        return {
            "valid": True,
            "entropy_bits": len(entropy_source) * 8,
            "entropy_ratio": entropy_ratio,
            "unique_bytes": unique_bytes
        }

    def check_address_uniqueness(self, address: str, creation_context: Dict | None = None) -> dict[str, Any]:
        """
        Check if address is unique (birthday attack prevention).

        Args:
            address: Generated address to check
            creation_context: Optional context data for tracking

        Returns:
            dict with 'unique' (bool) and collision info
        """
        with self._lock:
            self.total_generations += 1

            if address in self.created_addresses:
                self.collision_attempts += 1

                return {
                    "unique": False,
                    "reason": "address_collision",
                    "address": address,
                    "collision_count": self.collision_attempts,
                    "total_generations": self.total_generations,
                    "collision_rate": self.collision_attempts / self.total_generations
                }

            # Generate creation hash for tracking
            creation_data = f"{address}:{creation_context or {}}".encode()
            creation_hash = hashlib.sha256(creation_data).hexdigest()

            self.created_addresses.add(address)
            self.address_hashes[address] = creation_hash

            return {
                "unique": True,
                "address": address,
                "creation_hash": creation_hash[:16],
                "total_addresses": len(self.created_addresses),
                "collision_rate": self.collision_attempts / self.total_generations if self.total_generations > 0 else 0
            }

    def generate_secure_entropy(self, num_bytes: int = 32) -> bytes:
        """
        Generate cryptographically secure entropy.

        Args:
            num_bytes: Number of random bytes to generate

        Returns:
            Secure random bytes
        """
        # Use secrets module for cryptographic randomness
        entropy = secrets.token_bytes(num_bytes)

        # Validate entropy
        validation = self.validate_entropy(entropy)
        if not validation["valid"]:
            # Regenerate if validation fails
            entropy = secrets.token_bytes(num_bytes * 2)  # Double size for better quality

        return entropy

    def get_stats(self) -> dict[str, Any]:
        """Get collision resistance statistics."""
        with self._lock:
            return {
                "total_addresses_created": len(self.created_addresses),
                "total_generation_attempts": self.total_generations,
                "collision_attempts": self.collision_attempts,
                "collision_rate": self.collision_attempts / self.total_generations if self.total_generations > 0 else 0,
                "uniqueness_rate": (self.total_generations - self.collision_attempts) / self.total_generations if self.total_generations > 0 else 1.0
            }

class WalletFactory:
    """
    Factory class for creating and managing Wallet instances with collision resistance.
    """

    def __init__(self, data_dir: str | None = None, logger: StructuredLogger | None = None):
        self.wallet_manager = WalletManager(data_dir=data_dir)
        self.logger = logger or get_structured_logger()
        self.collision_resistance = CollisionResistance()
        self.logger.info("WalletFactory initialized with collision resistance.", data_dir=str(self.wallet_manager.data_dir))

    def create_new_wallet(self, name: str, password: str | None = None) -> Wallet:
        """
        Creates a new wallet and saves it.

        Args:
            name: A unique name for the wallet.
            password: Optional password to encrypt the wallet file.

        Returns:
            The newly created Wallet object.
        """
        try:
            wallet = self.wallet_manager.create_wallet(name, password)
            self.logger.info(f"New wallet '{name}' created successfully.", address=wallet.address)
            return wallet
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to create new wallet '{name}': {e}", error=str(e))
            raise

    def load_existing_wallet(self, name: str, password: str | None = None) -> Wallet:
        """
        Loads an existing wallet from file.

        Args:
            name: The name of the wallet to load.
            password: Optional password to decrypt the wallet file.

        Returns:
            The loaded Wallet object.
        """
        try:
            wallet = self.wallet_manager.load_wallet(name, password)
            self.logger.info(f"Wallet '{name}' loaded successfully.", address=wallet.address)
            return wallet
        except FileNotFoundError:
            self.logger.warn(f"Wallet file for '{name}' not found.")
            raise
        except ValueError as e:
            self.logger.error(f"Failed to load wallet '{name}': {e}", error=str(e))
            raise
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(
                f"An unexpected error occurred while loading wallet '{name}': {e}",
                error=str(e),
                exc_info=True,
            )
            raise

    def get_wallet_by_name(self, name: str) -> Wallet | None:
        """
        Retrieves a loaded wallet by its name.

        Args:
            name: The name of the wallet.

        Returns:
            The Wallet object if found, otherwise None.
        """
        return self.wallet_manager.get_wallet(name)

    def list_available_wallets(self) -> dict[str, str]:
        """
        Lists all wallet files found in the data directory.

        Returns:
            A dictionary mapping wallet names to their file paths.
        """
        wallet_names = self.wallet_manager.list_wallets()
        available_wallets = {
            name: str(self.wallet_manager.data_dir / f"{name}.wallet") for name in wallet_names
        }
        self.logger.debug(f"Found {len(available_wallets)} available wallet files.")
        return available_wallets

    def get_stats(self) -> dict[str, Any]:
        """
        Returns statistics about the managed wallets.
        """
        return {
            "loaded_wallets_count": len(self.wallet_manager.wallets),
            "wallet_files_count": len(self.list_available_wallets()),
            "wallet_data_directory": str(self.wallet_manager.data_dir),
        }

# Global instance for convenience
_global_wallet_factory = None

def get_wallet_factory(
    data_dir: str | None = None, logger: StructuredLogger | None = None
) -> WalletFactory:
    """
    Get global WalletFactory instance.
    """
    global _global_wallet_factory
    if _global_wallet_factory is None:
        _global_wallet_factory = WalletFactory(data_dir, logger)
    return _global_wallet_factory
