from __future__ import annotations

"""
Transaction Client for XAI SDK

Handles all transaction-related operations.
"""

from datetime import datetime
from typing import Any

from ..exceptions import TransactionError, ValidationError
from ..http_client import HTTPClient
from ..models import Transaction, TransactionStatus


class TransactionClient:
    """Client for transaction operations."""

    def __init__(self, http_client: HTTPClient) -> None:
        """
        Initialize Transaction Client.

        Args:
            http_client: HTTP client instance
        """
        self.http_client = http_client

    def send(
        self,
        from_address: str,
        to_address: str,
        amount: str,
        data: str | None = None,
        gas_limit: str | None = None,
        gas_price: str | None = None,
        nonce: int | None = None,
        signature: str | None = None,
    ) -> Transaction:
        """
        Send a transaction.

        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Transaction amount
            data: Optional transaction data
            gas_limit: Gas limit for transaction
            gas_price: Gas price per unit
            nonce: Transaction nonce
            signature: Signed transaction data

        Returns:
            Transaction details

        Raises:
            TransactionError: If transaction fails
        """
        if not from_address or not to_address or not amount:
            raise ValidationError("from_address, to_address, and amount are required")

        try:
            payload = {
                "from": from_address,
                "to": to_address,
                "amount": amount,
            }

            if data:
                payload["data"] = data
            if gas_limit:
                payload["gas_limit"] = gas_limit
            if gas_price:
                payload["gas_price"] = gas_price
            if nonce is not None:
                payload["nonce"] = nonce
            if signature:
                payload["signature"] = signature

            response = self.http_client.post("/transaction/send", data=payload)

            return Transaction(
                hash=response["hash"],
                from_address=response["from"],
                to_address=response["to"],
                amount=response["amount"],
                timestamp=datetime.fromisoformat(response["timestamp"]),
                status=TransactionStatus(response.get("status", "pending")),
                fee=response.get("fee", "0"),
                gas_used=response.get("gas_used", "0"),
            )
        except TransactionError:
            raise
        except TransactionError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise TransactionError(f"Failed to send transaction: {str(e)}") from e

    def get(self, tx_hash: str) -> Transaction:
        """
        Get transaction details.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction details

        Raises:
            TransactionError: If transaction retrieval fails
        """
        if not tx_hash:
            raise ValidationError("tx_hash is required")

        try:
            response = self.http_client.get(f"/transaction/{tx_hash}")

            return Transaction(
                hash=response["hash"],
                from_address=response["from"],
                to_address=response["to"],
                amount=response["amount"],
                timestamp=datetime.fromisoformat(response["timestamp"]),
                status=TransactionStatus(response.get("status", "pending")),
                fee=response.get("fee", "0"),
                gas_used=response.get("gas_used", "0"),
                block_number=response.get("block_number"),
                block_hash=response.get("block_hash"),
                confirmations=response.get("confirmations", 0),
            )
        except TransactionError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise TransactionError(f"Failed to get transaction: {str(e)}") from e

    def get_status(self, tx_hash: str) -> dict[str, Any]:
        """
        Get transaction status.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction status information

        Raises:
            TransactionError: If status retrieval fails
        """
        if not tx_hash:
            raise ValidationError("tx_hash is required")

        try:
            return self.http_client.get(f"/transaction/{tx_hash}/status")
        except TransactionError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise TransactionError(f"Failed to get transaction status: {str(e)}") from e

    def estimate_fee(
        self,
        from_address: str,
        to_address: str,
        amount: str,
        data: str | None = None,
    ) -> dict[str, Any]:
        """
        Estimate transaction fee.

        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Transaction amount
            data: Optional transaction data

        Returns:
            Fee estimation with gas details

        Raises:
            TransactionError: If estimation fails
        """
        if not from_address or not to_address or not amount:
            raise ValidationError("from_address, to_address, and amount are required")

        try:
            payload = {
                "from": from_address,
                "to": to_address,
                "amount": amount,
            }
            if data:
                payload["data"] = data

            return self.http_client.post("/transaction/estimate-fee", data=payload)
        except TransactionError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise TransactionError(f"Failed to estimate fee: {str(e)}") from e

    def is_confirmed(self, tx_hash: str, confirmations: int = 1) -> bool:
        """
        Check if transaction is confirmed.

        Args:
            tx_hash: Transaction hash
            confirmations: Number of required confirmations

        Returns:
            True if transaction is confirmed

        Raises:
            TransactionError: If check fails
        """
        try:
            status = self.get_status(tx_hash)
            return status.get("confirmations", 0) >= confirmations
        except TransactionError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise TransactionError(f"Failed to check confirmation: {str(e)}") from e

    def wait_for_confirmation(
        self,
        tx_hash: str,
        confirmations: int = 1,
        timeout: int = 600,
        poll_interval: int = 5,
    ) -> Transaction:
        """
        Wait for transaction confirmation.

        Args:
            tx_hash: Transaction hash
            confirmations: Number of required confirmations
            timeout: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds

        Returns:
            Confirmed transaction

        Raises:
            TransactionError: If confirmation fails or times out
        """
        import time

        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                raise TransactionError(
                    f"Transaction confirmation timeout after {timeout}s"
                )

            try:
                tx = self.get(tx_hash)
                if tx.confirmations >= confirmations:
                    return tx
            except TransactionError:

                raise

            except (KeyError, ValueError, TypeError) as e:

                raise TransactionError(f"Failed to wait for confirmation: {str(e)}") from e

            time.sleep(poll_interval)
