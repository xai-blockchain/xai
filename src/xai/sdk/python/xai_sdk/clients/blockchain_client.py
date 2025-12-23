from __future__ import annotations

"""
Blockchain Client for XAI SDK

Handles blockchain querying and synchronization operations.
"""

from datetime import datetime
from typing import Any

from ..exceptions import ValidationError, XAIError
from ..http_client import HTTPClient
from ..models import Block, BlockchainStats


class BlockchainClient:
    """Client for blockchain operations."""

    def __init__(self, http_client: HTTPClient) -> None:
        """
        Initialize Blockchain Client.

        Args:
            http_client: HTTP client instance
        """
        self.http_client = http_client

    def get_block(self, block_number: int) -> Block:
        """
        Get block details.

        Args:
            block_number: Block number

        Returns:
            Block details

        Raises:
            XAIError: If block retrieval fails
        """
        if block_number < 0:
            raise ValidationError("block_number must be non-negative")

        try:
            response = self.http_client.get(f"/blocks/{block_number}")

            return Block(
                number=response["number"],
                hash=response["hash"],
                parent_hash=response["parent_hash"],
                timestamp=response["timestamp"],
                miner=response["miner"],
                difficulty=response["difficulty"],
                gas_limit=response.get("gas_limit", "0"),
                gas_used=response.get("gas_used", "0"),
                transactions=response.get("transaction_count", 0),
                transaction_hashes=response.get("transactions", []),
            )
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to get block: {str(e)}") from e

    def list_blocks(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """
        List recent blocks.

        Args:
            limit: Number of blocks to retrieve
            offset: Offset for pagination

        Returns:
            List of blocks with metadata

        Raises:
            XAIError: If block list retrieval fails
        """
        if limit > 100:
            limit = 100

        try:
            response = self.http_client.get(
                "/blocks",
                params={"limit": limit, "offset": offset},
            )

            blocks = [
                Block(
                    number=b["number"],
                    hash=b["hash"],
                    parent_hash=b["parent_hash"],
                    timestamp=b["timestamp"],
                    miner=b["miner"],
                    difficulty=b.get("difficulty", "0"),
                    gas_limit=b.get("gas_limit", "0"),
                    gas_used=b.get("gas_used", "0"),
                    transactions=b.get("transaction_count", 0),
                )
                for b in response.get("blocks", [])
            ]

            return {
                "blocks": blocks,
                "total": response.get("total", 0),
                "limit": response.get("limit", limit),
                "offset": response.get("offset", offset),
            }
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to list blocks: {str(e)}") from e

    def get_block_transactions(self, block_number: int) -> list[dict[str, Any]]:
        """
        Get transactions in a block.

        Args:
            block_number: Block number

        Returns:
            List of transactions

        Raises:
            XAIError: If transaction retrieval fails
        """
        if block_number < 0:
            raise ValidationError("block_number must be non-negative")

        try:
            response = self.http_client.get(
                f"/blocks/{block_number}/transactions"
            )
            return response.get("transactions", [])
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to get block transactions: {str(e)}") from e

    def get_sync_status(self) -> dict[str, Any]:
        """
        Get blockchain synchronization status.

        Returns:
            Sync status information

        Raises:
            XAIError: If sync status retrieval fails
        """
        try:
            return self.http_client.get("/sync")
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to get sync status: {str(e)}") from e

    def is_synced(self) -> bool:
        """
        Check if blockchain is synchronized.

        Returns:
            True if blockchain is synced

        Raises:
            XAIError: If check fails
        """
        try:
            status = self.get_sync_status()
            return not status.get("syncing", False)
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to check sync status: {str(e)}") from e

    def get_stats(self) -> BlockchainStats:
        """
        Get blockchain statistics.

        Returns:
            Blockchain statistics

        Raises:
            XAIError: If stats retrieval fails
        """
        try:
            response = self.http_client.get("/stats")

            return BlockchainStats(
                total_blocks=response["total_blocks"],
                total_transactions=response["total_transactions"],
                total_accounts=response["total_accounts"],
                difficulty=response["difficulty"],
                hashrate=response["hashrate"],
                average_block_time=response.get("average_block_time", 0),
                total_supply=response["total_supply"],
                network=response.get("network", "mainnet"),
            )
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to get blockchain stats: {str(e)}") from e

    def get_node_info(self) -> dict[str, Any]:
        """
        Get blockchain node information.

        Returns:
            Node information

        Raises:
            XAIError: If node info retrieval fails
        """
        try:
            return self.http_client.get("/")
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to get node info: {str(e)}") from e

    def get_health(self) -> dict[str, Any]:
        """
        Get node health status.

        Returns:
            Health information

        Raises:
            XAIError: If health check fails
        """
        try:
            return self.http_client.get("/health")
        except XAIError:

            raise

        except (KeyError, ValueError, TypeError) as e:

            raise XAIError(f"Failed to check node health: {str(e)}") from e
