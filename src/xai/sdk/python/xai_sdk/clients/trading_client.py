"""
Trading Client for XAI SDK

Handles peer-to-peer trading and order management.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from ..http_client import HTTPClient
from ..models import TradeOrder
from ..exceptions import XAIError, ValidationError


class TradingClient:
    """Client for trading operations."""

    def __init__(self, http_client: HTTPClient) -> None:
        """
        Initialize Trading Client.

        Args:
            http_client: HTTP client instance
        """
        self.http_client = http_client

    def register_session(
        self,
        wallet_address: str,
        peer_id: str,
    ) -> Dict[str, Any]:
        """
        Register a trading session.

        Args:
            wallet_address: Wallet address
            peer_id: Peer identifier

        Returns:
            Session information

        Raises:
            XAIError: If session registration fails
        """
        if not wallet_address or not peer_id:
            raise ValidationError("wallet_address and peer_id are required")

        try:
            payload = {
                "wallet_address": wallet_address,
                "peer_id": peer_id,
            }
            return self.http_client.post("/wallet-trades/register", data=payload)
        except Exception as e:
            raise XAIError(f"Failed to register trading session: {str(e)}")

    def list_orders(self) -> List[TradeOrder]:
        """
        List active trade orders.

        Returns:
            List of trade orders

        Raises:
            XAIError: If order list retrieval fails
        """
        try:
            response = self.http_client.get("/wallet-trades/orders")

            orders = [
                TradeOrder(
                    id=o["id"],
                    from_address=o["from_address"],
                    to_address=o["to_address"],
                    from_amount=o["from_amount"],
                    to_amount=o["to_amount"],
                    created_at=datetime.fromisoformat(o["created_at"]),
                    status=o.get("status", "pending"),
                    expires_at=datetime.fromisoformat(o["expires_at"])
                    if o.get("expires_at")
                    else None,
                )
                for o in (response if isinstance(response, list) else response.get("orders", []))
            ]

            return orders
        except Exception as e:
            raise XAIError(f"Failed to list trade orders: {str(e)}")

    def create_order(
        self,
        from_address: str,
        to_address: str,
        from_amount: str,
        to_amount: str,
        timeout: Optional[int] = None,
    ) -> TradeOrder:
        """
        Create a trade order.

        Args:
            from_address: Sender address
            to_address: Recipient address
            from_amount: Amount to send
            to_amount: Amount to receive
            timeout: Order timeout in seconds

        Returns:
            Created trade order

        Raises:
            XAIError: If order creation fails
        """
        if not from_address or not to_address or not from_amount or not to_amount:
            raise ValidationError(
                "from_address, to_address, from_amount, and to_amount are required"
            )

        try:
            payload = {
                "from_address": from_address,
                "to_address": to_address,
                "from_amount": from_amount,
                "to_amount": to_amount,
            }

            if timeout:
                payload["timeout"] = timeout

            response = self.http_client.post("/wallet-trades/orders", data=payload)

            return TradeOrder(
                id=response["id"],
                from_address=response["from_address"],
                to_address=response["to_address"],
                from_amount=response["from_amount"],
                to_amount=response["to_amount"],
                created_at=datetime.fromisoformat(response["created_at"]),
                status=response.get("status", "pending"),
            )
        except Exception as e:
            raise XAIError(f"Failed to create trade order: {str(e)}")

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a trade order.

        Args:
            order_id: Order ID

        Returns:
            Cancellation confirmation

        Raises:
            XAIError: If cancellation fails
        """
        if not order_id:
            raise ValidationError("order_id is required")

        try:
            return self.http_client.post(
                f"/wallet-trades/orders/{order_id}/cancel", data={}
            )
        except Exception as e:
            raise XAIError(f"Failed to cancel order: {str(e)}")

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get trade order status.

        Args:
            order_id: Order ID

        Returns:
            Order status

        Raises:
            XAIError: If status retrieval fails
        """
        if not order_id:
            raise ValidationError("order_id is required")

        try:
            return self.http_client.get(f"/wallet-trades/orders/{order_id}/status")
        except Exception as e:
            raise XAIError(f"Failed to get order status: {str(e)}")
