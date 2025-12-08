"""
Mining Mixin for XAI Blockchain

Extracted from blockchain.py as part of god class refactoring.
Contains mining-related methods: mine_pending_transactions, mine_block,
and gamification processing.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from xai.core.blockchain_components.block import Block
    from xai.core.block_header import BlockHeader
    from xai.core.transaction import Transaction
    from xai.core.gamification import GamificationBlockchainInterface


class BlockchainMiningMixin:
    """
    Mixin providing mining functionality for the Blockchain class.

    This mixin handles:
    - Block mining with proof-of-work
    - Transaction selection and prioritization
    - Coinbase transaction creation
    - Block reward calculation
    - Gamification feature processing

    Required attributes on the implementing class:
    - chain: List of blocks/headers
    - pending_transactions: List of pending transactions
    - difficulty: Current difficulty level
    - nonce_tracker: Transaction nonce tracker
    - utxo_manager: UTXO set manager
    - storage: Blockchain storage handler
    - streak_tracker: Mining streak tracker
    - checkpoint_manager: Checkpoint manager
    - smart_contract_manager: Smart contract manager
    - gamification_adapter: Gamification interface
    - airdrop_manager: Airdrop manager
    - fee_refund_calculator: Fee refund calculator
    - treasure_manager: Treasure hunt manager
    - contracts: Contract storage
    - contract_receipts: Contract execution receipts
    - logger: Structured logger instance
    - fast_mining_enabled: Whether fast mining is enabled (test mode)
    - max_test_mining_difficulty: Cap for test mining difficulty
    - network_type: Network type (mainnet/testnet)
    - _max_block_size_bytes: Maximum block size in bytes
    - _max_transactions_per_block: Maximum transactions per block
    - node_identity: Node's cryptographic identity
    """

    def mine_pending_transactions(
        self, miner_address: str, node_identity: Optional[Dict[str, str]] = None
    ) -> Optional["Block"]:
        """Mine a new block with pending transactions

        Implements block size limits to prevent DoS attacks and ensure network scalability.
        Maximum block size is 1 MB (1,000,000 bytes).

        Args:
            miner_address: Address to receive mining reward
            node_identity: Node's cryptographic identity with private_key and public_key

        Returns:
            Newly mined Block or None if mining fails

        Raises:
            ValueError: If node_identity is not provided or block violates size limits
        """
        from xai.core.blockchain_components.block import Block
        from xai.core.block_header import BlockHeader, canonical_json
        from xai.core.config import Config
        from xai.core.crypto_utils import sign_message_hex
        from xai.core.transaction import Transaction

        # Require a real node identity for block signing
        if node_identity is None:
            node_identity = getattr(self, "node_identity", None)
        if (
            not node_identity
            or not node_identity.get("private_key")
            or not node_identity.get("public_key")
        ):
            raise ValueError(
                "node_identity with private_key and public_key is required for block signing."
            )
        max_block_size_bytes = self._max_block_size_bytes
        max_transactions_per_block = self._max_transactions_per_block

        # Adjust difficulty based on recent block times
        self.difficulty = self.calculate_next_difficulty()
        if self.fast_mining_enabled and self.difficulty > self.max_test_mining_difficulty:
            self.logger.info(
                "Capping mining difficulty for fast-mining mode",
                requested_difficulty=self.difficulty,
                cap=self.max_test_mining_difficulty,
            )
            self.difficulty = self.max_test_mining_difficulty

        # Reset pending nonce reservations so block assembly validates from confirmed state in-order
        if hasattr(self.nonce_tracker, "pending_nonces"):
            self.nonce_tracker.pending_nonces.clear()

        # Prioritize pending transactions by fee rate
        prioritized_txs = self._prioritize_transactions(self.pending_transactions)
        prioritized_txs.sort(
            key=lambda tx: (tx.sender, tx.nonce if tx.nonce is not None else 0)
        )

        # Enforce strict in-block nonce sequencing per sender
        sender_next_nonce: Dict[str, int] = {}

        # Apply block size limits: Select transactions that fit within max block size
        selected_txs: List["Transaction"] = []
        current_block_size = 0

        for tx in prioritized_txs:
            if len(selected_txs) + 1 >= max_transactions_per_block:
                self.logger.info(
                    "Transaction limit reached for block assembly",
                    limit=max_transactions_per_block,
                )
                break
            # Re-validate transaction against current state before inclusion
            if tx.sender != "COINBASE":
                confirmed_nonce = self.nonce_tracker.get_nonce(tx.sender)
                expected = sender_next_nonce.get(tx.sender, confirmed_nonce + 1)
                tx.nonce = tx.nonce if tx.nonce is not None else expected
                if tx.nonce != expected:
                    self.logger.warn(
                        "Transaction skipped due to nonce mismatch during block assembly",
                        txid=tx.txid,
                        sender=tx.sender,
                        expected_nonce=expected,
                        got_nonce=tx.nonce,
                    )
                    continue
                # Align nonce tracker state so validation enforces strict sequencing
                self.nonce_tracker.nonces[tx.sender] = expected - 1
                # Temporarily reserve previous nonce so validate_nonce expects `expected`
                self.nonce_tracker.pending_nonces[tx.sender] = expected - 1
                if not self.validate_transaction(tx):
                    txid_display = (tx.txid or tx.calculate_hash() or "")[:10]
                    self.logger.warn(
                        f"Transaction {txid_display}... failed validation and was excluded from block."
                    )
                    self.nonce_tracker.pending_nonces.pop(tx.sender, None)
                    continue
                # Reserve this nonce for subsequent txs in the block
                self.nonce_tracker.pending_nonces[tx.sender] = expected
                sender_next_nonce[tx.sender] = expected + 1

            # Calculate transaction size using canonical JSON
            tx_size = len(canonical_json(tx.to_dict()).encode("utf-8"))

            # Check if adding this transaction would exceed block size limit
            if current_block_size + tx_size <= max_block_size_bytes:
                selected_txs.append(tx)
                current_block_size += tx_size
            else:
                # Block is full, skip remaining transactions
                break

        # Use selected transactions instead of all prioritized transactions
        prioritized_txs = selected_txs

        # Calculate block reward based on current chain height (with halving)
        block_height = len(self.chain)
        base_reward = self.get_block_reward(block_height)

        # Update miner streak and apply bonus
        self.streak_tracker.update_miner_streak(miner_address, time.time())
        final_reward, streak_bonus = self.streak_tracker.apply_streak_bonus(
            miner_address, base_reward
        )

        # Create coinbase transaction (block reward + transaction fees + streak bonus)
        total_fees = sum(tx.fee for tx in prioritized_txs)
        coinbase_reward = final_reward + total_fees

        coinbase_tx = Transaction(
            "COINBASE",
            miner_address,
            coinbase_reward,
            tx_type="coinbase",
            outputs=[{"address": miner_address, "amount": coinbase_reward}],
        )
        coinbase_tx.txid = coinbase_tx.calculate_hash()

        # Create new block with prioritized transactions
        block_transactions = [coinbase_tx] + prioritized_txs

        merkle_root = self.calculate_merkle_root(block_transactions)

        header = BlockHeader(
            index=len(self.chain),
            previous_hash=self.chain[-1].hash if self.chain else "0",
            merkle_root=merkle_root,
            timestamp=time.time(),
            difficulty=self.difficulty,
            nonce=0,
            miner_pubkey=node_identity["public_key"],
            version=Config.BLOCK_HEADER_VERSION,
        )

        # Mine the block
        header.hash = self.mine_block(header)
        header.signature = sign_message_hex(
            node_identity["private_key"], header.hash.encode()
        )

        new_block = Block(header, block_transactions)
        new_block.miner = miner_address
        # Provide ancestry context to peers for fork resolution without optional data loss
        new_block.lineage = list(self.chain)

        if not self._block_within_size_limits(new_block, context="local_mining"):
            raise ValueError("Locally mined block violates block size or transaction limits")

        if self.smart_contract_manager:
            receipts = self.smart_contract_manager.process_block(new_block)
            if receipts:
                self.contract_receipts.extend(receipts)

        # Snapshot state before any modifications for atomicity
        # If block persistence fails, we can rollback to this state
        utxo_snapshot = self.utxo_manager.snapshot()
        nonce_snapshot = self.nonce_tracker.snapshot()
        pending_txs_backup = list(self.pending_transactions)

        # Track nonce changes to commit only after successful persistence
        nonce_changes: List[Tuple[str, int]] = []

        try:
            # Add to chain (cache)
            self.chain.append(new_block)
            self._process_governance_block_transactions(new_block)
            self.storage._save_block_to_disk(new_block)

            # Update UTXO set (collect nonce changes but don't commit yet)
            for tx in new_block.transactions:
                if tx.sender != "COINBASE":  # Regular transactions spend inputs
                    self.utxo_manager.process_transaction_inputs(tx)
                    # Collect nonce change without committing
                    nonce_changes.append((tx.sender, tx.nonce))
                self.utxo_manager.process_transaction_outputs(tx)

            # Process gamification features for this block
            self._process_gamification_features(
                self.gamification_adapter, new_block, miner_address
            )

            # Unlock UTXOs for mined transactions (no longer pending)
            for tx in new_block.transactions:
                if tx.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in tx.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)

            # Clear pending transactions
            self.pending_transactions = []

            # Log streak bonus if applied
            if streak_bonus > 0:
                self.logger.info(
                    f"STREAK BONUS: +{streak_bonus:.4f} AXN ({self.streak_tracker.get_streak_bonus(miner_address) * 100:.0f}%)"
                )

            # Create checkpoint if needed (every N blocks)
            if self.checkpoint_manager.should_create_checkpoint(new_block.index):
                total_supply = self.get_circulating_supply()
                checkpoint = self.checkpoint_manager.create_checkpoint(
                    new_block, self.utxo_manager, total_supply
                )
                if checkpoint:
                    self.logger.info(f"Created checkpoint at block {new_block.index}")

            # Periodically compact the UTXO set to save memory
            if new_block.index % 100 == 0:  # Compact every 100 blocks
                self.utxo_manager.compact_utxo_set()

            # CRITICAL: Persist state to disk BEFORE committing nonces
            # This is the failure point we're protecting against
            self.storage.save_state_to_disk(
                self.utxo_manager,
                self.pending_transactions,
                self.contracts,
                self.contract_receipts,
            )

            # Only commit nonce increments AFTER successful persistence
            # This prevents nonce desynchronization if disk write fails
            for sender, nonce in nonce_changes:
                self.nonce_tracker.increment_nonce(sender, nonce)

            self.logger.info(
                "Block mined and persisted successfully",
                block_index=new_block.index,
                block_hash=new_block.hash[:16],
                nonce_updates=len(nonce_changes),
            )

            return new_block

        except Exception as e:
            # Block persistence failed - rollback all state changes
            self.logger.error(
                "Block persistence failed, rolling back state changes",
                block_index=new_block.index,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Rollback UTXO state
            self.utxo_manager.restore(utxo_snapshot)

            # Rollback nonce state
            self.nonce_tracker.restore(nonce_snapshot)

            # Remove block from chain
            if self.chain and self.chain[-1] == new_block:
                self.chain.pop()

            # Restore pending transactions
            self.pending_transactions = pending_txs_backup

            self.logger.warn(
                "State rolled back after block persistence failure",
                nonces_protected=len(nonce_changes),
                utxo_state_restored=True,
            )

            # Re-raise exception for caller to handle
            raise

    def _process_gamification_features(
        self,
        gamification_adapter: "GamificationBlockchainInterface",
        block: "Block",
        miner_address: str,
    ) -> None:
        """
        Apply gamification modules after a block is mined. Best-effort: log failures.

        Args:
            gamification_adapter: Gamification interface adapter
            block: The mined block
            miner_address: Address of the miner
        """
        try:
            if self.airdrop_manager:
                self.airdrop_manager.execute_airdrop(block.index, block.hash)
        except Exception as exc:
            self.logger.warn(f"Gamification airdrop processing failed: {exc}")

        try:
            if self.fee_refund_calculator:
                self.fee_refund_calculator.process_refunds(block)
        except Exception as exc:
            self.logger.warn(f"Gamification refund processing failed: {exc}")

        try:
            if self.treasure_manager:
                # Placeholder hook for future treasure processing
                pass
        except Exception as exc:
            self.logger.warn(f"Gamification treasure processing failed: {exc}")

        try:
            if self.streak_tracker:
                self.streak_tracker._save_streaks()
        except Exception as exc:
            self.logger.warn(f"Gamification streak persistence failed: {exc}")

    def mine_block(self, header: "BlockHeader") -> str:
        """Mine block with proof-of-work

        Performs proof-of-work by incrementing nonce until the block hash
        meets the difficulty target (required leading zeros).

        Args:
            header: BlockHeader to mine

        Returns:
            The valid block hash meeting the difficulty target
        """
        effective_difficulty = header.difficulty
        if self.fast_mining_enabled and effective_difficulty > self.max_test_mining_difficulty:
            self.logger.info(
                "Applying fast-mining difficulty cap",
                requested_difficulty=effective_difficulty,
                cap=self.max_test_mining_difficulty,
                network=self.network_type,
            )
            effective_difficulty = self.max_test_mining_difficulty
            header.difficulty = effective_difficulty

        target = "0" * effective_difficulty

        while True:
            hash_attempt = header.calculate_hash()
            if hash_attempt.startswith(target):
                self.logger.info(f"Block mined! Hash: {hash_attempt}")
                return hash_attempt
            header.nonce += 1
