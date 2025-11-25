"""
Mining Client for XAI SDK

Handles mining operations and reward management.
"""

from typing import Optional, Dict, Any

from ..http_client import HTTPClient
from ..models import MiningStatus
from ..exceptions import MiningError, ValidationError


class MiningClient:
    """Client for mining operations."""

    def __init__(self, http_client: HTTPClient) -> None:
        """
        Initialize Mining Client.

        Args:
            http_client: HTTP client instance
        """
        self.http_client = http_client

    def start(self, threads: int = 1) -> Dict[str, Any]:
        """
        Start mining.

        Args:
            threads: Number of mining threads (1-16)

        Returns:
            Mining status

        Raises:
            MiningError: If mining start fails
        """
        if threads < 1 or threads > 16:
            raise ValidationError("threads must be between 1 and 16")

        try:
            payload = {"threads": threads}
            return self.http_client.post("/mining/start", data=payload)
        except Exception as e:
            raise MiningError(f"Failed to start mining: {str(e)}")

    def stop(self) -> Dict[str, Any]:
        """
        Stop mining.

        Returns:
            Mining status

        Raises:
            MiningError: If mining stop fails
        """
        try:
            return self.http_client.post("/mining/stop", data={})
        except Exception as e:
            raise MiningError(f"Failed to stop mining: {str(e)}")

    def get_status(self) -> MiningStatus:
        """
        Get mining status.

        Returns:
            Mining status

        Raises:
            MiningError: If status retrieval fails
        """
        try:
            response = self.http_client.get("/mining/status")

            return MiningStatus(
                mining=response["mining"],
                threads=response["threads"],
                hashrate=response["hashrate"],
                blocks_found=response.get("blocks_found", 0),
                current_difficulty=response["current_difficulty"],
                uptime=response.get("uptime", 0),
                last_block_time=response.get("last_block_time"),
            )
        except Exception as e:
            raise MiningError(f"Failed to get mining status: {str(e)}")

    def get_rewards(self, address: str) -> Dict[str, Any]:
        """
        Get mining rewards for an address.

        Args:
            address: Wallet address

        Returns:
            Reward information

        Raises:
            MiningError: If reward retrieval fails
        """
        if not address:
            raise ValidationError("address is required")

        try:
            return self.http_client.get("/mining/rewards", params={"address": address})
        except Exception as e:
            raise MiningError(f"Failed to get mining rewards: {str(e)}")

    def is_mining(self) -> bool:
        """
        Check if mining is active.

        Returns:
            True if mining is active

        Raises:
            MiningError: If check fails
        """
        try:
            status = self.get_status()
            return status.mining
        except Exception as e:
            raise MiningError(f"Failed to check mining status: {str(e)}")
