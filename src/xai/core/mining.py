"""
Mining Coordinator - Handles mining coordination and difficulty management

Manages mining pause logic, difficulty calculations, and mining coordination
between nodes. Extracted from blockchain.py for better separation.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from xai.core.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain


class MiningCoordinator:
    """
    Manages mining coordination including:
    - Mining pause logic (cooldown after peer blocks)
    - Block work calculation (cumulative PoW)
    - Chain work comparison for fork resolution
    - Mining abort coordination
    """

    def __init__(self, blockchain: 'Blockchain'):
        """
        Initialize MiningCoordinator with reference to blockchain.

        Args:
            blockchain: Parent blockchain instance
        """
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def should_pause_mining(self) -> bool:
        """
        Determine if mining should be paused.

        Mining is paused after receiving a peer block to allow network
        propagation and prevent wasted work on competing blocks.

        Returns:
            True if mining should pause, False if mining can proceed
        """
        # Check if we're in cooldown period after receiving peer block
        if self.blockchain._last_peer_block_time == 0.0:
            return False

        current_time = time.time()
        time_since_peer_block = current_time - self.blockchain._last_peer_block_time

        # If cooldown period has passed, resume mining
        if time_since_peer_block >= self.blockchain._mining_cooldown_seconds:
            return False

        # Still in cooldown period
        return True

    def calculate_block_work(self, block_like: Any) -> int:
        """
        Calculate proof-of-work for a single block.

        Work is calculated as 2^difficulty, representing the expected
        number of hash attempts needed to mine the block.

        Args:
            block_like: Block or BlockHeader object

        Returns:
            Integer representing block work
        """
        # Extract difficulty from block or header
        difficulty = None

        if hasattr(block_like, 'difficulty'):
            difficulty = block_like.difficulty
        elif hasattr(block_like, 'header'):
            header = block_like.header
            if hasattr(header, 'difficulty'):
                difficulty = header.difficulty

        if difficulty is None:
            self.logger.warning(
                "Cannot calculate block work: difficulty not found",
                block=str(block_like)[:100],
            )
            return 0

        # Calculate work as 2^difficulty
        # Cache the result to avoid repeated calculation
        block_hash = None
        if hasattr(block_like, 'hash'):
            block_hash = block_like.hash
        elif hasattr(block_like, 'header'):
            block_hash = block_like.header.hash if hasattr(block_like.header, 'hash') else None

        if block_hash and block_hash in self.blockchain._block_work_cache:
            return self.blockchain._block_work_cache[block_hash]

        # Calculate work
        work = 2 ** difficulty

        # Cache for future lookups
        if block_hash:
            self.blockchain._block_work_cache[block_hash] = work

        return work

    def calculate_chain_work(self, chain: list[Any]) -> int:
        """
        Calculate cumulative proof-of-work for entire chain.

        The chain with the most cumulative work is considered the canonical chain.
        This is used for fork resolution.

        Args:
            chain: List of blocks or headers

        Returns:
            Total cumulative work for the chain
        """
        total_work = 0

        for block in chain:
            total_work += self.calculate_block_work(block)

        return total_work

    def record_peer_block_received(self) -> None:
        """
        Record that a peer block was received.

        This triggers the mining cooldown period to allow network
        propagation before resuming mining.
        """
        self.blockchain._last_peer_block_time = time.time()
        self.blockchain._abort_current_mining = True

        self.logger.debug(
            "Peer block received - mining pause activated",
            cooldown_seconds=self.blockchain._mining_cooldown_seconds,
        )

    def reset_mining_abort_flag(self) -> None:
        """Reset the abort mining flag after cooldown period."""
        self.blockchain._abort_current_mining = False

    def set_mining_target_height(self, height: int | None) -> None:
        """
        Set the block height currently being mined.

        Args:
            height: Block height being mined, or None if not mining
        """
        self.blockchain._mining_target_height = height

    def get_mining_target_height(self) -> int | None:
        """
        Get the block height currently being mined.

        Returns:
            Block height being mined, or None if not mining
        """
        return self.blockchain._mining_target_height

    def is_mining_aborted(self) -> bool:
        """
        Check if current mining should be aborted.

        Returns:
            True if mining should be aborted, False otherwise
        """
        return self.blockchain._abort_current_mining

    def get_mining_cooldown_remaining(self) -> float:
        """
        Get remaining mining cooldown time in seconds.

        Returns:
            Seconds remaining in cooldown, or 0.0 if not in cooldown
        """
        if self.blockchain._last_peer_block_time == 0.0:
            return 0.0

        current_time = time.time()
        elapsed = current_time - self.blockchain._last_peer_block_time
        remaining = self.blockchain._mining_cooldown_seconds - elapsed

        return max(0.0, remaining)

    def get_mining_status(self) -> dict[str, Any]:
        """
        Get current mining status.

        Returns:
            Dictionary with mining status information
        """
        return {
            "should_pause": self.should_pause_mining(),
            "cooldown_remaining": self.get_mining_cooldown_remaining(),
            "target_height": self.get_mining_target_height(),
            "abort_flag": self.is_mining_aborted(),
            "last_peer_block_time": self.blockchain._last_peer_block_time,
        }

    def configure_cooldown(self, seconds: float) -> None:
        """
        Configure mining cooldown period.

        Args:
            seconds: Cooldown period in seconds

        Raises:
            ValueError: If seconds is negative
        """
        if seconds < 0:
            raise ValueError("Cooldown period cannot be negative")

        old_cooldown = self.blockchain._mining_cooldown_seconds
        self.blockchain._mining_cooldown_seconds = seconds

        self.logger.info(
            "Mining cooldown period updated",
            old_seconds=old_cooldown,
            new_seconds=seconds,
        )

    def get_cooldown_config(self) -> float:
        """
        Get current mining cooldown configuration.

        Returns:
            Cooldown period in seconds
        """
        return self.blockchain._mining_cooldown_seconds
