from __future__ import annotations

"""
XAI SDK Main Client

Provides unified interface to all blockchain operations.
"""

from .clients import (
    AIClient,
    BlockchainClient,
    GovernanceClient,
    MiningClient,
    TradingClient,
    TransactionClient,
    WalletClient,
)
from .http_client import HTTPClient


class XAIClient:
    """
    Main client for XAI blockchain operations.

    Provides unified interface to wallet, transaction, blockchain,
    mining, governance, trading, and AI operations.

    Example:
        >>> client = XAIClient(api_key="your-api-key")
        >>> wallet = client.wallet.create()
        >>> balance = client.wallet.get_balance(wallet.address)
        >>> tx = client.transaction.send(wallet.address, "0x...", "1000")
        >>> analysis = client.ai.analyze_wallet(wallet.address)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:12001",
        api_key: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize XAI Client.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests

        Example:
            >>> # Local development
            >>> client = XAIClient()
            >>>
            >>> # With API key
            >>> client = XAIClient(
            ...     base_url="https://api.xai-blockchain.io",
            ...     api_key="your-api-key"
            ... )
        """
        self.http_client = HTTPClient(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

        # Initialize service clients
        self.wallet = WalletClient(self.http_client)
        self.transaction = TransactionClient(self.http_client)
        self.blockchain = BlockchainClient(self.http_client)
        self.mining = MiningClient(self.http_client)
        self.governance = GovernanceClient(self.http_client)
        self.trading = TradingClient(self.http_client)
        self.ai = AIClient(self.http_client)

    def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        self.http_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def health_check(self) -> dict:
        """
        Quick health check of the API.

        Returns:
            Health status

        Example:
            >>> client = XAIClient()
            >>> health = client.health_check()
            >>> if health['status'] == 'ok':
            ...     print("API is healthy")
        """
        return self.blockchain.get_health()

    def get_info(self) -> dict:
        """
        Get blockchain node information.

        Returns:
            Node information

        Example:
            >>> client = XAIClient()
            >>> info = client.get_info()
            >>> print(f"Node version: {info['version']}")
        """
        return self.blockchain.get_node_info()
