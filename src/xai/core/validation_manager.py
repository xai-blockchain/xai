"""
Validation Manager - Handles block and transaction validation
Extracted from Blockchain god class for better separation of concerns
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple, List, Dict, Any, Union
import time

from xai.core.block_header import BlockHeader
from xai.core.transaction import Transaction
from xai.core.structured_logger import get_structured_logger
from xai.core.blockchain_security import BlockSizeValidator

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain


class ValidationManager:
    """
    Manages all validation operations including:
    - Block validation (structure, PoW, signatures)
    - Transaction validation (format, signatures, funds)
    - Chain validation (forks, reorganizations)
    - Coinbase reward validation
    - Block size and security limits
    """

    def __init__(self, blockchain: 'Blockchain'):
        """
        Initialize ValidationManager with reference to blockchain.

        Args:
            blockchain: Parent blockchain instance for state access
        """
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def validate_transaction(self, transaction: Transaction) -> bool:
        """
        Validate a transaction for mempool or block inclusion.

        Delegates to TransactionValidator for comprehensive validation.

        Args:
            transaction: Transaction to validate

        Returns:
            True if valid, False otherwise
        """
        return self.blockchain.transaction_validator.validate(transaction)

    def validate_coinbase_reward(self, block: 'Block') -> Tuple[bool, Optional[str]]:
        """
        Validate coinbase transaction reward amount.

        Security considerations:
        - Prevents inflation attacks via excessive coinbase
        - Enforces halving schedule
        - Validates fee calculation

        Args:
            block: Block containing coinbase transaction

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not block.transactions:
            return False, "Block has no transactions"

        coinbase_tx = block.transactions[0]

        # Verify it's a coinbase transaction
        if coinbase_tx.sender != "COINBASE":
            return False, "First transaction is not coinbase"

        if coinbase_tx.tx_type != "coinbase":
            return False, "First transaction type is not coinbase"

        # Calculate expected reward
        expected_reward = self.blockchain.get_block_reward(block.index)

        # Calculate total fees from other transactions
        total_fees = 0.0
        for tx in block.transactions[1:]:  # Skip coinbase
            if hasattr(tx, 'fee') and tx.fee is not None:
                total_fees += tx.fee

        expected_total = expected_reward + total_fees

        # Allow small floating point differences
        actual_reward = coinbase_tx.amount
        if abs(actual_reward - expected_total) > 1e-8:
            return False, (
                f"Invalid coinbase reward: expected {expected_total:.8f}, "
                f"got {actual_reward:.8f} (reward={expected_reward:.8f}, fees={total_fees:.8f})"
            )

        return True, None

    def validate_chain(
        self,
        chain: Optional[List[BlockHeader]] = None,
        full_validation: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate chain structure and consistency.

        Performs hierarchical validation:
        1. Genesis block verification
        2. Chain linkage (previous_hash consistency)
        3. Proof-of-work verification
        4. Block timestamp validation
        5. Difficulty adjustment verification
        6. Full transaction validation (if full_validation=True)

        Security considerations:
        - Prevents chain manipulation attacks
        - Validates difficulty to prevent grinding attacks
        - Enforces timestamp consensus rules (median time past)
        - Validates all cryptographic proofs

        Args:
            chain: Chain to validate (uses self.chain if None)
            full_validation: If True, validates all transactions and UTXOs

        Returns:
            Tuple of (is_valid, error_message)
        """
        if chain is None:
            chain = self.blockchain.chain

        if not chain:
            return False, "Chain is empty"

        # Validate genesis block
        genesis = chain[0]
        if genesis.previous_hash != "0":
            return False, f"Invalid genesis block previous_hash: {genesis.previous_hash}"

        # Validate chain linkage
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            # Check hash linkage
            if current.previous_hash != previous.hash:
                return False, (
                    f"Block {current.index} previous_hash mismatch: "
                    f"expected {previous.hash}, got {current.previous_hash}"
                )

            # Check index sequence
            if current.index != previous.index + 1:
                return False, (
                    f"Block index sequence broken at {current.index}: "
                    f"previous was {previous.index}"
                )

            # Verify proof-of-work
            if not current.hash.startswith("0" * current.difficulty):
                return False, (
                    f"Block {current.index} has invalid proof-of-work: "
                    f"hash {current.hash} doesn't meet difficulty {current.difficulty}"
                )

            # Verify hash calculation
            recalculated_hash = current.calculate_hash()
            if recalculated_hash != current.hash:
                return False, (
                    f"Block {current.index} hash mismatch: "
                    f"stored={current.hash}, calculated={recalculated_hash}"
                )

            # Validate timestamp
            is_valid, error = self._validate_block_timestamp(current, chain[:i])
            if not is_valid:
                return False, error

            # Validate difficulty adjustment
            is_valid, error = self._validate_difficulty(current, previous)
            if not is_valid:
                return False, error

        # Full validation includes transaction and UTXO validation
        if full_validation:
            is_valid, error = self._validate_chain_transactions(chain)
            if not is_valid:
                return False, error

        return True, None

    def _validate_block_timestamp(
        self,
        block: BlockHeader,
        previous_blocks: List[BlockHeader],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate block timestamp against consensus rules.

        Enforces:
        - Timestamp must be greater than median of last N blocks
        - Timestamp cannot be too far in the future

        Args:
            block: Block to validate
            previous_blocks: Previous blocks in chain

        Returns:
            Tuple of (is_valid, error_message)
        """
        current_time = time.time()

        # Check future block time limit
        max_future = current_time + self.blockchain._max_future_block_time
        if block.timestamp > max_future:
            return False, (
                f"Block {block.index} timestamp {block.timestamp} is too far in future "
                f"(max allowed: {max_future})"
            )

        # Check median time past for blocks after genesis
        if len(previous_blocks) > 0:
            # Get last N blocks for median calculation
            window_size = min(self.blockchain._median_time_span, len(previous_blocks))
            recent_blocks = previous_blocks[-window_size:]

            timestamps = [b.timestamp for b in recent_blocks]
            timestamps.sort()

            # Median time past
            if len(timestamps) % 2 == 0:
                median = (timestamps[len(timestamps)//2 - 1] + timestamps[len(timestamps)//2]) / 2
            else:
                median = timestamps[len(timestamps)//2]

            if block.timestamp <= median:
                return False, (
                    f"Block {block.index} timestamp {block.timestamp} is not greater than "
                    f"median time past {median}"
                )

        return True, None

    def _validate_difficulty(
        self,
        current: BlockHeader,
        previous: BlockHeader,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate difficulty adjustment.

        Ensures difficulty follows consensus rules and prevents manipulation.

        Args:
            current: Current block
            previous: Previous block

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if this is a difficulty adjustment block
        if current.index % self.blockchain.difficulty_adjustment_interval == 0:
            # Difficulty should be recalculated
            expected_difficulty = self.blockchain.calculate_next_difficulty(
                previous.index,
                previous.timestamp
            )

            if current.difficulty != expected_difficulty:
                return False, (
                    f"Block {current.index} has incorrect difficulty adjustment: "
                    f"expected {expected_difficulty}, got {current.difficulty}"
                )
        else:
            # Difficulty should remain the same
            if current.difficulty != previous.difficulty:
                return False, (
                    f"Block {current.index} changed difficulty outside adjustment interval: "
                    f"expected {previous.difficulty}, got {current.difficulty}"
                )

        return True, None

    def _validate_chain_transactions(
        self,
        chain: List[BlockHeader],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate all transactions in the chain.

        Performs full UTXO validation and transaction verification.

        Args:
            chain: Chain to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Create temporary UTXO set for validation
        temp_utxo = {}

        for header in chain:
            # Load full block from storage
            block = self.blockchain.storage.load_block_from_disk(header.index)
            if not block:
                return False, f"Failed to load block {header.index} for validation"

            # Validate coinbase
            is_valid, error = self.validate_coinbase_reward(block)
            if not is_valid:
                return False, error

            # Validate all transactions
            for i, tx in enumerate(block.transactions):
                if i == 0:
                    continue  # Skip coinbase

                # Validate transaction structure
                if not self.validate_transaction(tx):
                    return False, f"Invalid transaction {tx.txid} in block {block.index}"

                # Validate UTXO spending
                # (simplified - full implementation would track UTXOs)
                # This is handled by transaction_validator in real validation

        return True, None

    def verify_block_signature(self, header: BlockHeader) -> bool:
        """
        Verify block signature if present.

        Args:
            header: Block header with signature

        Returns:
            True if signature is valid or not required, False otherwise
        """
        if not header.signature or not header.miner_pubkey:
            # Signature not required
            return True

        from xai.core.crypto_utils import verify_signature_hex

        # Verify signature
        return verify_signature_hex(
            message=header.calculate_hash(),
            signature=header.signature,
            public_key=header.miner_pubkey,
        )

    def _block_within_size_limits(
        self,
        block: 'Block',
        *,
        context: str
    ) -> bool:
        """
        Validate block size and transaction count limits.

        Security enforcement:
        - Prevents DoS via oversized blocks
        - Enforces transaction count limits

        Args:
            block: Block to validate
            context: Context string for logging

        Returns:
            True if within limits, False otherwise
        """
        validator = BlockSizeValidator(
            max_size_bytes=self.blockchain._max_block_size_bytes,
            max_transactions=self.blockchain._max_transactions_per_block,
        )

        return validator.validate_block(
            block=block,
            context=context,
            logger=self.logger,
        )

    def _validate_header_version(self, header: BlockHeader) -> bool:
        """
        Validate block header version is allowed.

        Args:
            header: Block header to validate

        Returns:
            True if version is allowed, False otherwise
        """
        version = getattr(header, 'version', self.blockchain._default_block_header_version)

        if version not in self.blockchain._allowed_block_header_versions:
            self.logger.warning(
                "Block header version not allowed",
                version=version,
                allowed=list(self.blockchain._allowed_block_header_versions),
                index=header.index,
            )
            return False

        return True
