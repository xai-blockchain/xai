# Manager Consolidation: This module handles mining orchestration (start/stop).
# For the core mining logic (PoW, block building, transaction selection), use:
#     from xai.core.mining.mining_manager import MiningManager
#
# This module provides high-level mining control for nodes.

"""
AXN Blockchain Node - Mining Module

Handles all mining-related functionality including:
- Continuous mining
- Mining control (start/stop)
- Block broadcasting
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

import random
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain

class MiningController:
    """
    Controls mining thread operations for a blockchain node.

    Handles continuous mining in a background thread, broadcasting mined blocks,
    and controlling mining state.

    Note: For core mining logic (block mining, transaction selection, reward calculation),
    see MiningManager in mining_manager.py.
    """

    def __init__(self, blockchain: Blockchain, miner_address: str) -> None:
        """
        Initialize the mining manager.

        Args:
            blockchain: The blockchain instance to mine on
            miner_address: Address to receive mining rewards
        """
        self.blockchain = blockchain
        self.miner_address = miner_address
        self.is_mining = False
        self.mining_thread: threading.Thread | None = None
        self.broadcast_callback = None

    def set_broadcast_callback(self, callback) -> None:
        """
        Set callback function for broadcasting newly mined blocks.

        Args:
            callback: Function that takes a block and broadcasts it to peers
        """
        self.broadcast_callback = callback

    def start_mining(self) -> None:
        """Start automatic mining in background thread."""
        if self.is_mining:
            print("⚠️  Mining already active")
            return

        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mine_continuously, daemon=True)
        self.mining_thread.start()
        print("⛏️  Auto-mining started")

    def stop_mining(self) -> None:
        """Stop automatic mining."""
        if not self.is_mining:
            print("⚠️  Mining not active")
            return

        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        print("⏸️  Auto-mining stopped")

    def _mine_continuously(self) -> None:
        """
        Continuously mine blocks in a loop.

        This method runs in a background thread and continuously checks for
        pending transactions to mine. When transactions are available, it mines
        a new block and broadcasts it to peers.

        Mining is paused for a cooldown period after receiving blocks from peers
        to prevent race conditions during block propagation across the network.
        """
        while self.is_mining:
            # Check if mining should be paused due to recent peer block reception
            if self.blockchain.should_pause_mining():
                time.sleep(0.5)  # Wait briefly and check again
                continue

            # Add random jitter (0-1 second) to prevent synchronized mining attempts
            # This ensures nodes don't all start mining at exactly the same moment
            time.sleep(random.uniform(0, 1.0))

            if self.blockchain.pending_transactions:
                tx_count = len(self.blockchain.pending_transactions)
                print(f"⛏️  Mining block with {tx_count} transactions...")

                try:
                    block = self.blockchain.mine_pending_transactions(self.miner_address)
                    if block:
                        print(f"✅ Block {block.index} mined! Hash: {block.hash}")

                        # Broadcast to peers if callback is set
                        if self.broadcast_callback:
                            self.broadcast_callback(block)
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    logger.error(
                        "Exception in _mine_continuously",
                        extra={
                            "error_type": "Exception",
                            "error": str(e),
                            "function": "_mine_continuously"
                        }
                    )
                    print(f"❌ Mining error: {e}")

            time.sleep(1)  # Small delay between mining attempts

    def mine_single_block(self) -> Block | None:
        """
        Mine a single block with current pending transactions.

        Returns:
            The mined block, or None if no transactions available

        Raises:
            Exception: If mining fails
        """
        if not self.blockchain.pending_transactions:
            raise ValueError("No pending transactions to mine")

        return self.blockchain.mine_pending_transactions(self.miner_address)
