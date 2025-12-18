"""
Mining Manager - Handles mining-related operations
Extracted from Blockchain god class for better separation of concerns
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, List, Any
import time
import os

from xai.core.block_header import BlockHeader
from xai.core.transaction import Transaction
from xai.core.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain


class MiningManager:
    """
    Manages all mining-related operations including:
    - Block mining (proof-of-work)
    - Pending transaction selection and prioritization
    - Block reward calculation
    - Mining difficulty management
    - Gamification features during mining
    """

    def __init__(self, blockchain: 'Blockchain'):
        """
        Initialize MiningManager with reference to blockchain.

        Args:
            blockchain: Parent blockchain instance for state access
        """
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def mine_pending_transactions(
        self,
        miner_address: str,
        node_identity: Optional[Dict[str, str]] = None
    ) -> Optional['Block']:
        """
        Mine a new block containing pending transactions.

        This is the main entry point for mining operations. It:
        1. Selects and prioritizes pending transactions
        2. Creates coinbase transaction with block reward
        3. Constructs block header
        4. Performs proof-of-work mining
        5. Processes gamification features
        6. Adds mined block to chain

        Security considerations:
        - Validates miner address format
        - Enforces transaction limits per block
        - Validates coinbase reward amount
        - Thread-safe transaction selection from mempool

        Args:
            miner_address: Address to receive block reward
            node_identity: Optional node identity with public/private keys

        Returns:
            Mined Block if successful, None if mining failed or no transactions

        Raises:
            ValueError: If miner_address is invalid
        """
        # Import here to avoid circular dependency
        from xai.core.blockchain import Block

        if not miner_address:
            raise ValueError("Miner address is required")

        # Thread-safe transaction selection from mempool
        with self.blockchain._mempool_lock:
            # Make a copy to avoid TOCTOU issues
            pending_txs = list(self.blockchain.pending_transactions)

        if not pending_txs:
            self.logger.debug("No pending transactions to mine")
            return None

        # Prioritize transactions by fee
        selected_txs = self.blockchain._prioritize_transactions(
            pending_txs,
            max_count=self.blockchain._max_transactions_per_block
        )

        # Get current chain state
        latest_block = self.blockchain.get_latest_block()
        next_index = latest_block.index + 1
        previous_hash = latest_block.hash

        # Calculate block reward for this height
        block_reward = self.blockchain.get_block_reward(next_index)

        # Calculate total transaction fees
        total_fees = sum(
            tx.fee if hasattr(tx, 'fee') and tx.fee is not None else 0.0
            for tx in selected_txs
        )

        # Create coinbase transaction
        coinbase_tx = Transaction(
            sender="COINBASE",
            recipient=miner_address,
            amount=block_reward + total_fees,
            fee=0.0,
            tx_type="coinbase",
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Combine coinbase with selected transactions
        block_transactions = [coinbase_tx] + selected_txs

        # Calculate next difficulty
        next_difficulty = self.blockchain.calculate_next_difficulty(
            latest_block.index,
            latest_block.timestamp
        )

        # Create block header
        header = BlockHeader(
            index=next_index,
            previous_hash=previous_hash,
            merkle_root="",  # Will be calculated during block construction
            timestamp=time.time(),
            difficulty=next_difficulty,
            nonce=0,
            miner_pubkey=node_identity.get("public_key") if node_identity else None,
            version=self.blockchain._default_block_header_version,
        )

        # Create block
        block = Block(
            header=header,
            transactions=block_transactions,
        )

        # Sign block if node identity provided
        if node_identity and node_identity.get("private_key"):
            block.sign_block(node_identity["private_key"])

        # Perform proof-of-work mining
        self.logger.info(
            "Starting proof-of-work mining",
            index=next_index,
            difficulty=next_difficulty,
            tx_count=len(block_transactions),
            reward=block_reward,
        )

        mined_hash = self.mine_block(header)
        block.header.hash = mined_hash

        # Process gamification features
        self._process_gamification_features(
            block=block,
            miner_address=miner_address,
            total_fees=total_fees,
        )

        # Add block to chain
        if self.blockchain.add_block(block):
            self.logger.info(
                "Successfully mined block",
                index=block.index,
                hash=block.hash,
                tx_count=len(block.transactions),
                reward=block_reward + total_fees,
            )
            return block
        else:
            self.logger.error(
                "Failed to add mined block to chain",
                index=block.index,
            )
            return None

    def mine_block(self, header: BlockHeader) -> str:
        """
        Perform proof-of-work mining on block header.

        Increments nonce until hash meets difficulty target.
        Supports fast mining mode for testing.

        Args:
            header: Block header to mine

        Returns:
            Final block hash meeting difficulty requirement
        """
        # Apply test difficulty cap if fast mining enabled
        effective_difficulty = header.difficulty
        if self.blockchain.fast_mining_enabled:
            effective_difficulty = min(
                header.difficulty,
                self.blockchain.max_test_mining_difficulty
            )
            header.difficulty = effective_difficulty

        # Proof-of-work mining loop
        while True:
            block_hash = header.calculate_hash()
            if block_hash.startswith("0" * effective_difficulty):
                return block_hash
            header.nonce += 1

    def _process_gamification_features(
        self,
        block: 'Block',
        miner_address: str,
        total_fees: float,
    ) -> None:
        """
        Process gamification features for newly mined block.

        Handles:
        - Airdrops
        - Streak tracking
        - Treasure hunts
        - Fee refunds
        - Time capsules

        Args:
            block: Newly mined block
            miner_address: Address that mined the block
            total_fees: Total transaction fees in block
        """
        try:
            # Process airdrop eligibility
            self.blockchain.airdrop_manager.process_block(block)

            # Track mining streak
            self.blockchain.streak_tracker.record_activity(
                address=miner_address,
                activity_type="mine_block",
                timestamp=block.timestamp,
            )

            # Process treasure hunt
            self.blockchain.treasure_manager.process_block(block)

            # Calculate fee refunds
            self.blockchain.fee_refund_calculator.process_block(block)

            # Process time capsules
            self.blockchain.timecapsule_manager.process_block(block)

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            # Don't fail mining due to gamification errors
            self.logger.warning(
                "Gamification processing failed for block",
                extra={
                    "index": block.index,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
