"""
Wallet Client for XAI SDK

Handles all wallet-related operations.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from ..http_client import HTTPClient
from ..models import Wallet, Balance, WalletType
from ..exceptions import WalletError, ValidationError


class WalletClient:
    """Client for wallet operations."""

    def __init__(self, http_client: HTTPClient) -> None:
        """
        Initialize Wallet Client.

        Args:
            http_client: HTTP client instance
        """
        self.http_client = http_client

    def create(
        self,
        wallet_type: WalletType = WalletType.STANDARD,
        name: Optional[str] = None,
    ) -> Wallet:
        """
        Create a new wallet.

        Args:
            wallet_type: Type of wallet to create
            name: Optional wallet name

        Returns:
            Created wallet

        Raises:
            WalletError: If wallet creation fails
        """
        try:
            payload = {
                "wallet_type": wallet_type.value,
            }
            if name:
                payload["name"] = name

            response = self.http_client.post("/wallet/create", data=payload)

            return Wallet(
                address=response["address"],
                public_key=response["public_key"],
                created_at=datetime.fromisoformat(response["created_at"]),
                wallet_type=WalletType(response.get("wallet_type", "standard")),
                private_key=response.get("private_key"),
            )
        except Exception as e:
            raise WalletError(f"Failed to create wallet: {str(e)}")

    def get(self, address: str) -> Wallet:
        """
        Get wallet information.

        Args:
            address: Wallet address

        Returns:
            Wallet details

        Raises:
            WalletError: If wallet retrieval fails
        """
        if not address:
            raise ValidationError("Address is required")

        try:
            response = self.http_client.get(f"/wallet/{address}")
            return Wallet(
                address=response["address"],
                public_key=response["public_key"],
                created_at=datetime.fromisoformat(response["created_at"]),
                wallet_type=WalletType(response.get("wallet_type", "standard")),
                nonce=response.get("nonce", 0),
            )
        except Exception as e:
            raise WalletError(f"Failed to get wallet: {str(e)}")

    def get_balance(self, address: str) -> Balance:
        """
        Get wallet balance.

        Args:
            address: Wallet address

        Returns:
            Balance information

        Raises:
            WalletError: If balance retrieval fails
        """
        if not address:
            raise ValidationError("Address is required")

        try:
            response = self.http_client.get(f"/wallet/{address}/balance")
            return Balance(
                address=response["address"],
                balance=response["balance"],
                locked_balance=response.get("locked_balance", "0"),
                available_balance=response.get("available_balance", response["balance"]),
                nonce=response.get("nonce", 0),
            )
        except Exception as e:
            raise WalletError(f"Failed to get balance: {str(e)}")

    def get_transactions(
        self,
        address: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get wallet transaction history.

        Args:
            address: Wallet address
            limit: Number of transactions to retrieve
            offset: Offset for pagination

        Returns:
            Transaction history with metadata

        Raises:
            WalletError: If transaction retrieval fails
        """
        if not address:
            raise ValidationError("Address is required")

        if limit > 100:
            limit = 100

        try:
            response = self.http_client.get(
                f"/wallet/{address}/transactions",
                params={"limit": limit, "offset": offset},
            )
            return {
                "transactions": response.get("transactions", []),
                "total": response.get("total", 0),
                "limit": response.get("limit", limit),
                "offset": response.get("offset", offset),
            }
        except Exception as e:
            raise WalletError(f"Failed to get transactions: {str(e)}")

    def create_embedded(
        self,
        app_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create an embedded wallet.

        Args:
            app_id: Application ID
            user_id: User ID
            metadata: Optional metadata

        Returns:
            Embedded wallet information

        Raises:
            WalletError: If embedded wallet creation fails
        """
        if not app_id or not user_id:
            raise ValidationError("app_id and user_id are required")

        try:
            payload = {
                "app_id": app_id,
                "user_id": user_id,
            }
            if metadata:
                payload["metadata"] = metadata

            return self.http_client.post("/wallet/embedded/create", data=payload)
        except Exception as e:
            raise WalletError(f"Failed to create embedded wallet: {str(e)}")

    def login_embedded(self, wallet_id: str, password: str) -> Dict[str, Any]:
        """
        Login to an embedded wallet.

        Args:
            wallet_id: Embedded wallet ID
            password: Wallet password

        Returns:
            Session information

        Raises:
            WalletError: If login fails
        """
        if not wallet_id or not password:
            raise ValidationError("wallet_id and password are required")

        try:
            payload = {
                "wallet_id": wallet_id,
                "password": password,
            }
            return self.http_client.post("/wallet/embedded/login", data=payload)
        except Exception as e:
            raise WalletError(f"Failed to login to embedded wallet: {str(e)}")
