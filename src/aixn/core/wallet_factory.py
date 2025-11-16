"""
XAI Blockchain - Wallet Factory

Provides methods for creating, loading, and managing different types of wallets.
"""

from typing import Optional, Dict
from aixn.core.wallet import Wallet, WalletManager
from aixn.core.structured_logger import StructuredLogger, get_structured_logger


class WalletFactory:
    """
    Factory class for creating and managing Wallet instances.
    """

    def __init__(self, data_dir: Optional[str] = None, logger: Optional[StructuredLogger] = None):
        self.wallet_manager = WalletManager(data_dir=data_dir)
        self.logger = logger or get_structured_logger()
        self.logger.info("WalletFactory initialized.", data_dir=str(self.wallet_manager.data_dir))

    def create_new_wallet(self, name: str, password: Optional[str] = None) -> Wallet:
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
        except Exception as e:
            self.logger.error(f"Failed to create new wallet '{name}': {e}", error=str(e))
            raise

    def load_existing_wallet(self, name: str, password: Optional[str] = None) -> Wallet:
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
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred while loading wallet '{name}': {e}",
                error=str(e),
                exc_info=True,
            )
            raise

    def get_wallet_by_name(self, name: str) -> Optional[Wallet]:
        """
        Retrieves a loaded wallet by its name.

        Args:
            name: The name of the wallet.

        Returns:
            The Wallet object if found, otherwise None.
        """
        return self.wallet_manager.get_wallet(name)

    def list_available_wallets(self) -> Dict[str, str]:
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

    def get_stats(self) -> Dict[str, Any]:
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
    data_dir: Optional[str] = None, logger: Optional[StructuredLogger] = None
) -> WalletFactory:
    """
    Get global WalletFactory instance.
    """
    global _global_wallet_factory
    if _global_wallet_factory is None:
        _global_wallet_factory = WalletFactory(data_dir, logger)
    return _global_wallet_factory
