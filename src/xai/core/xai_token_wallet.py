from __future__ import annotations

"""
XAI Blockchain - XAI Token Wallet

Extends the base Wallet functionality to specifically manage XAI token balances
and interact with the XAITokenManager.
"""

from typing import Any

from xai.core.structured_logger import StructuredLogger, get_structured_logger
from xai.core.wallet import Wallet
from xai.core.xai_token_manager import XAITokenManager, get_xai_token_manager


class XAITokenWallet(Wallet):
    """
    A wallet specifically designed to interact with XAI tokens.
    It extends the base Wallet class with token-specific functionalities.
    """

    def __init__(
        self,
        private_key: str | None = None,
        token_manager: XAITokenManager | None = None,
        logger: StructuredLogger | None = None,
    ):
        super().__init__(private_key)
        self.token_manager = token_manager or get_xai_token_manager()
        self.logger = logger or get_structured_logger()
        self.logger.info(
            f"XAITokenWallet initialized for address: {self.address}", address=self.address
        )

    def get_xai_balance(self) -> float:
        """
        Retrieves the current XAI token balance for this wallet's address.
        """
        balance = self.token_manager.get_balance(self.address)
        self.logger.debug(
            f"Retrieved XAI balance for {self.address}: {balance}",
            address=self.address,
            balance=balance,
        )
        return balance

    def send_xai(self, recipient_address: str, amount: float) -> bool:
        """
        Sends XAI tokens from this wallet to a recipient address.

        Args:
            recipient_address: The address of the recipient.
            amount: The amount of XAI tokens to send.

        Returns:
            True if the transfer was successful, False otherwise.
        """
        if not self.token_manager.transfer_tokens(self.address, recipient_address, amount):
            self.logger.warn(
                f"Failed to send {amount} XAI from {self.address} to {recipient_address}.",
                sender=self.address,
                recipient=recipient_address,
                amount=amount,
            )
            return False
        self.logger.info(
            f"Successfully sent {amount} XAI from {self.address} to {recipient_address}.",
            sender=self.address,
            recipient=recipient_address,
            amount=amount,
        )
        return True

    def receive_xai(self, sender_address: str, amount: float) -> bool:
        """
        Simulates receiving XAI tokens into this wallet.
        (In a real blockchain, this would be handled by transaction processing).

        Args:
            sender_address: The address of the sender.
            amount: The amount of XAI tokens received.

        Returns:
            True if the reception was successful, False otherwise.
        """
        # This is a simplified representation. In a real system, tokens are "received"
        # when a transaction output points to this wallet's address.
        # For this model, we'll directly update the balance via the token manager.
        # Note: The token_manager.transfer_tokens already handles the recipient's balance update.
        # This method might be redundant or used for specific scenarios like initial minting.
        self.logger.info(
            f"Received {amount} XAI from {sender_address} into {self.address}.",
            sender=sender_address,
            recipient=self.address,
            amount=amount,
        )
        return True  # Assuming the transfer_tokens call already handled the logic

    def get_wallet_info(self) -> dict[str, Any]:
        """
        Returns comprehensive information about the XAI token wallet.
        """
        info = super().to_public_dict()
        info["xai_balance"] = self.get_xai_balance()
        return info

# Global instance for convenience
_global_xai_token_wallet = None

def get_xai_token_wallet(
    private_key: str | None = None,
    token_manager: XAITokenManager | None = None,
    logger: StructuredLogger | None = None,
) -> XAITokenWallet:
    """
    Get global XAITokenWallet instance.
    """
    global _global_xai_token_wallet
    if _global_xai_token_wallet is None:
        _global_xai_token_wallet = XAITokenWallet(private_key, token_manager, logger)
    return _global_xai_token_wallet
