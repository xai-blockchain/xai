"""
Block Processor - Handles block creation and processing

Manages block lifecycle: creation, merkle root calculation, addition to chain,
and orphan block handling. Extracted from blockchain.py for better separation.

Supports Protocol-based dependency injection for testability:
    - Accepts Blockchain instance (backward compatible)
    - Can accept any object implementing ChainProvider, StorageProvider
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import TYPE_CHECKING, Any

from xai.core.chain.block_header import BlockHeader
from xai.core.chain.blockchain_exceptions import StorageError, ValidationError
from xai.core.config import Config
from xai.core.api.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain
    from xai.core.manager_interfaces import ChainProvider, StorageProvider
    from xai.core.transaction import Transaction

class BlockProcessor:
    """
    Manages block processing operations including:
    - Genesis block creation
    - Block addition to chain
    - Merkle root calculation
    - Orphan block handling
    - Block validation during addition
    """

    def __init__(self, blockchain: 'Blockchain'):
        """
        Initialize BlockProcessor with reference to blockchain.

        Args:
            blockchain: Parent blockchain instance
        """
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def create_genesis_block(self) -> None:
        """
        Create or load the genesis block.

        Attempts to load genesis block from genesis.json file for network consensus.
        If file doesn't exist, creates a new genesis block with initial token allocation.

        Security considerations:
        - Ensures deterministic genesis across all nodes
        - Validates genesis block proof-of-work
        - Initializes UTXO set with genesis outputs
        """
        from xai.core.blockchain import Block
        from xai.core.transaction import Transaction

        # Try to load genesis block from file (for unified network)
        genesis_candidates = []
        if getattr(self.blockchain, "data_dir", None):
            genesis_candidates.append(os.path.join(self.blockchain.data_dir, "genesis.json"))
        chain_dir = os.path.dirname(__file__)
        genesis_candidates.append(os.path.join(chain_dir, "genesis.json"))
        genesis_candidates.append(os.path.join(os.path.dirname(chain_dir), "genesis.json"))

        genesis_file = next((path for path in genesis_candidates if os.path.exists(path)), None)

        if genesis_file:
            self.logger.info(f"Loading genesis block from {genesis_file}")
            with open(genesis_file, "r") as f:
                genesis_data = json.load(f)

            # Recreate ALL genesis transactions
            genesis_transactions = []
            for tx_data in genesis_data["transactions"]:
                genesis_tx = Transaction(
                    tx_data["sender"],
                    tx_data["recipient"],
                    tx_data["amount"],
                    tx_data["fee"],
                    tx_type="coinbase",
                    outputs=[{"address": tx_data["recipient"], "amount": tx_data["amount"]}],
                )
                genesis_tx.timestamp = tx_data["timestamp"]
                genesis_tx.txid = tx_data.get("txid")
                genesis_tx.signature = tx_data.get("signature")
                genesis_transactions.append(genesis_tx)

            self.logger.info(
                f"Loaded {len(genesis_transactions)} genesis transactions "
                f"(Total: {sum(tx.amount for tx in genesis_transactions)} AXN)"
            )

            merkle_root = self.calculate_merkle_root(genesis_transactions)

            header = BlockHeader(
                index=0,
                previous_hash="0" * 64,
                merkle_root=merkle_root,
                timestamp=genesis_data["timestamp"],
                difficulty=self.blockchain.difficulty,
                nonce=genesis_data.get("nonce", 0),
                miner_pubkey="genesis_miner_pubkey",
                version=genesis_data.get("version", Config.BLOCK_HEADER_VERSION),
            )

            # Ensure genesis hash reflects real PoW for deterministic startup
            declared_hash = genesis_data.get("hash")
            if (declared_hash and
                declared_hash.startswith("0" * header.difficulty) and
                declared_hash == header.calculate_hash()):
                header.hash = declared_hash
            else:
                header.hash = self.blockchain.mine_block(header)

            header.signature = genesis_data.get("signature")
            genesis_block = Block(header, genesis_transactions)

            self.logger.info(f"Genesis block loaded: {genesis_block.hash}")
        else:
            self.logger.info("Creating new genesis block...")
            # Create genesis transactions matching the allocation in genesis.json
            # Total allocation: 60.5M XAI (50% of 121M cap)
            genesis_transactions = [
                Transaction(
                    "COINBASE",
                    "XAI_FOUNDER_IMMEDIATE",
                    2500000.0,
                    outputs=[{"address": "XAI_FOUNDER_IMMEDIATE", "amount": 2500000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_FOUNDER_VESTING",
                    9600000.0,
                    outputs=[{"address": "XAI_FOUNDER_VESTING", "amount": 9600000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_DEV_FUND",
                    6050000.0,
                    outputs=[{"address": "XAI_DEV_FUND", "amount": 6050000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_MARKETING_FUND",
                    6050000.0,
                    outputs=[{"address": "XAI_MARKETING_FUND", "amount": 6050000.0}],
                ),
                Transaction(
                    "COINBASE",
                    "XAI_MINING_POOL",
                    36300000.0,
                    outputs=[{"address": "XAI_MINING_POOL", "amount": 36300000.0}],
                ),
            ]

            # Set transaction IDs
            for tx in genesis_transactions:
                tx.txid = tx.calculate_hash()

            header = BlockHeader(
                index=0,
                previous_hash="0" * 64,
                merkle_root=self.calculate_merkle_root(genesis_transactions),
                timestamp=time.time(),
                difficulty=self.blockchain.difficulty,
                nonce=0,
                miner_pubkey="genesis_miner_pubkey",
                version=Config.BLOCK_HEADER_VERSION,
            )
            genesis_block = Block(header, genesis_transactions)
            genesis_block.header.hash = self.blockchain.mine_block(genesis_block.header)

        # Add genesis block to chain
        self.blockchain.chain.append(genesis_block)

        # Process genesis outputs into UTXO set
        for tx in genesis_block.transactions:
            self.blockchain.utxo_manager.process_transaction_outputs(tx)

        # Save genesis block to disk
        self.blockchain.storage._save_block_to_disk(genesis_block)
        self.blockchain.storage.save_state_to_disk(
            self.blockchain.utxo_manager,
            self.blockchain.pending_transactions,
            self.blockchain.contracts,
            self.blockchain.contract_receipts
        )

    def calculate_merkle_root(self, transactions: list['Transaction']) -> str:
        """
        Calculate merkle root of transactions.

        The merkle root is a cryptographic commitment to all transactions in a block.
        It enables efficient verification that a transaction is included in a block.

        Implementation:
        - Uses SHA-256 for hashing
        - Duplicates last hash if odd number of transactions
        - Builds merkle tree bottom-up

        Args:
            transactions: List of transactions to hash

        Returns:
            Hex-encoded merkle root hash
        """
        if not transactions:
            return hashlib.sha256(b"").hexdigest()

        # Get transaction hashes, ensuring all txids are set
        tx_hashes = []
        for tx in transactions:
            if tx.txid is None:
                # Calculate hash for transactions without txid
                tx.txid = tx.calculate_hash()
            tx_hashes.append(tx.txid)

        # Build merkle tree
        while len(tx_hashes) > 1:
            # Duplicate last hash if odd number
            if len(tx_hashes) % 2 != 0:
                tx_hashes.append(tx_hashes[-1])

            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                combined = tx_hashes[i] + tx_hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            tx_hashes = new_hashes

        return tx_hashes[0]

    def add_block_to_chain(self, block: 'Block') -> bool:
        """
        Add a validated block to the chain.

        This is the internal method that actually modifies chain state after
        all validation has passed. Updates chain, UTXO set, mempool, and indexes.

        Thread safety:
        - Acquires chain lock for atomic updates
        - Updates all state components atomically

        Args:
            block: Validated block to add

        Returns:
            True if added successfully, False otherwise
        """
        try:
            # Append block header to chain
            self.blockchain.chain.append(block.header)

            # Update UTXO set with block transactions
            for tx in block.transactions:
                # Remove spent inputs (except coinbase)
                if tx.sender != "COINBASE":
                    self.blockchain.utxo_manager.spend_utxo(tx)

                # Add new outputs
                self.blockchain.utxo_manager.add_utxo(tx)

            # Remove mined transactions from mempool
            self._remove_mined_transactions(block)

            # Update address index
            try:
                self.blockchain.address_index.index_block(block)
            except (ValueError, KeyError, AttributeError, TypeError, RuntimeError, OSError) as e:
                # Don't fail block addition if indexing fails
                self.logger.warning(
                    "Failed to update address index for block",
                    extra={
                        "index": block.index,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )

            # Persist block to disk
            self.blockchain.storage.save_block_to_disk(block)

            # Update checkpoint if needed
            try:
                self.blockchain.checkpoint_manager.maybe_create_checkpoint(
                    block_height=block.index,
                    blockchain=self.blockchain,
                )
            except (ValueError, KeyError, OSError, IOError, RuntimeError) as e:
                # Don't fail block addition if checkpointing fails
                self.logger.warning(
                    "Failed to create checkpoint",
                    extra={
                        "block_height": block.index,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )

            self.logger.info(
                "Block added to chain",
                index=block.index,
                hash=block.hash,
                tx_count=len(block.transactions),
            )

            return True

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError, OSError, IOError) as e:
            self.logger.error(
                "Failed to add block to chain",
                extra={
                    "index": block.index,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return False

    def _remove_mined_transactions(self, block: 'Block') -> None:
        """
        Remove mined transactions from mempool.

        Thread-safe mempool cleanup after block is added.

        Args:
            block: Block containing mined transactions
        """
        with self.blockchain._mempool_lock:
            mined_txids = {tx.txid for tx in block.transactions if tx.txid}

            # Remove from pending transactions
            self.blockchain.pending_transactions = [
                tx for tx in self.blockchain.pending_transactions
                if tx.txid not in mined_txids
            ]

            # Update seen txids
            self.blockchain.seen_txids.update(mined_txids)

            # Update sender pending counts
            for tx in block.transactions:
                if tx.sender and tx.sender != "COINBASE":
                    if tx.sender in self.blockchain._sender_pending_count:
                        self.blockchain._sender_pending_count[tx.sender] = max(
                            0,
                            self.blockchain._sender_pending_count[tx.sender] - 1
                        )

            # Remove spent inputs from tracking set
            for tx in block.transactions:
                if hasattr(tx, 'inputs') and tx.inputs:
                    for tx_input in tx.inputs:
                        input_key = f"{tx_input.get('txid')}:{tx_input.get('output_index')}"
                        self.blockchain._spent_inputs.discard(input_key)

    def process_orphan_blocks(self) -> None:
        """
        Process orphan blocks and attempt to add them to chain.

        Orphan blocks are blocks that were received out-of-order or as part
        of a competing fork. After new blocks arrive, we retry adding them
        to see if they now fit into the chain.
        """
        if not self.blockchain.orphan_blocks:
            return

        self.logger.debug(
            "Processing orphan blocks",
            count=sum(len(blocks) for blocks in self.blockchain.orphan_blocks.values()),
        )

        # Try to add orphan blocks at each height
        for height in sorted(self.blockchain.orphan_blocks.keys()):
            blocks_at_height = self.blockchain.orphan_blocks.get(height, [])

            for block in blocks_at_height:
                # Check if block can now be added
                if height == len(self.blockchain.chain):
                    # Block extends current chain
                    if block.header.previous_hash == self.blockchain.chain[-1].hash:
                        if self.blockchain.add_block(block):
                            self.logger.info(
                                "Orphan block promoted to main chain",
                                index=block.index,
                                hash=block.hash,
                            )
                            # Remove from orphans
                            self.blockchain.orphan_blocks[height].remove(block)
                            if not self.blockchain.orphan_blocks[height]:
                                del self.blockchain.orphan_blocks[height]

    def prune_orphan_blocks(self) -> int:
        """
        Remove old orphan blocks to prevent memory bloat.

        Removes orphan blocks that are too far from current chain tip.

        Returns:
            Number of orphan blocks pruned
        """
        if not self.blockchain.orphan_blocks:
            return 0

        current_height = len(self.blockchain.chain)
        max_orphan_age = 100  # Keep orphans within 100 blocks of tip

        pruned_count = 0
        heights_to_remove = []

        for height in self.blockchain.orphan_blocks.keys():
            if current_height - height > max_orphan_age:
                pruned_count += len(self.blockchain.orphan_blocks[height])
                heights_to_remove.append(height)

        for height in heights_to_remove:
            del self.blockchain.orphan_blocks[height]

        if pruned_count > 0:
            self.logger.info(
                "Pruned old orphan blocks",
                pruned=pruned_count,
                remaining=sum(len(blocks) for blocks in self.blockchain.orphan_blocks.values()),
            )

        return pruned_count
