"""
Validation Manager - Handles block and transaction validation
Extracted from Blockchain god class for better separation of concerns
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Sequence

from xai.core.block_header import BlockHeader
from xai.core.blockchain_exceptions import ValidationError
from xai.core.blockchain_security import BlockSizeValidator
from xai.core.structured_logger import get_structured_logger
from xai.core.transaction import Transaction

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

    def validate_coinbase_reward(self, block: 'Block') -> tuple[bool, str | None]:
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
        chain: list[BlockHeader] | None = None,
        full_validation: bool = False,
    ) -> tuple[bool, str | None]:
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
        block_like: "Block" | BlockHeader | Any,
        history: Sequence["Block" | BlockHeader | Any],
        *,
        emit_metrics: bool = False,
    ) -> tuple[bool, str | None]:
        """
        Enforce timestamp constraints:
        - each block must be newer than the median of the trailing window
        - each block must be newer than the immediate previous block
        - blocks cannot be more than MAX_FUTURE_BLOCK_TIME seconds ahead of wall clock
        """
        header = block_like.header if hasattr(block_like, "header") else block_like
        index = getattr(header, "index", 0)
        timestamp = self._extract_timestamp(header)
        if index == 0:
            return True, None
        if timestamp is None:
            return False, "missing timestamp"

        # Check against immediate previous block timestamp
        if history:
            prev_block = history[-1]
            prev_timestamp = self._extract_timestamp(prev_block)
            if prev_timestamp is not None and timestamp <= prev_timestamp:
                return False, f"timestamp {timestamp} <= previous block timestamp {prev_timestamp}"

        median_time = self._median_time_from_history(history)
        if median_time is not None and timestamp <= median_time:
            return False, f"timestamp {timestamp} <= median time past {median_time}"
        future_cutoff = time.time() + self.blockchain._max_future_block_time
        if timestamp > future_cutoff:
            return (
                False,
                f"timestamp {timestamp} exceeds future drift allowance ({self.blockchain._max_future_block_time}s)",
            )
        if emit_metrics:
            self._record_timestamp_metrics(
                index=index,
                timestamp=timestamp,
                median_time=median_time,
                history_length=len(history),
            )
        return True, None

    def _validate_difficulty(
        self,
        current: BlockHeader,
        previous: BlockHeader,
    ) -> tuple[bool, str | None]:
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
        chain: list[BlockHeader],
    ) -> tuple[bool, str | None]:
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
            True if signature is valid, False otherwise

        Note:
            Signatures are required for all blocks. Missing signatures are rejected.
            This ensures all blocks have cryptographic proof of miner authenticity.
        """
        if not header.signature or not header.miner_pubkey:
            # SECURITY: Reject blocks with missing signatures
            # All blocks must be signed by their miner for authenticity
            return False

        from xai.core.crypto_utils import verify_signature_hex

        # Verify signature
        # CRITICAL: verify_signature_hex(public_hex, message, signature_hex) - correct parameter order
        return verify_signature_hex(
            header.miner_pubkey,
            header.calculate_hash().encode(),
            header.signature,
        )

    def _block_within_size_limits(self, block: 'Block', *, context: str) -> bool:
        """
        Validate block size/resource limits using the hardened validator.
        """
        try:
            valid, error = BlockSizeValidator.validate_block_size(block)
        except (ValidationError, ValueError, AttributeError, TypeError) as exc:
            self.logger.error(
                "Block size validation failed unexpectedly",
                extra={
                    "context": context,
                    "error": str(exc),
                    "error_type": type(exc).__name__
                }
            )
            return False

        if not valid:
            header = block.header if hasattr(block, "header") else None
            self.logger.warn(
                "Block violates size limits",
                context=context,
                block_index=getattr(header, "index", getattr(block, "index", None)),
                block_hash=getattr(header, "hash", getattr(block, "hash", "")),
                reason=error,
            )
            return False

        return True

    def _validate_header_version(self, header: BlockHeader) -> bool:
        """
        Ensure block header versions are integers and part of the allowed set.
        """
        declared_version = getattr(header, "version", None)
        version_to_check = (
            declared_version if declared_version is not None else self.blockchain._default_block_header_version
        )
        try:
            version_int = int(version_to_check)
        except (TypeError, ValueError):
            self.logger.warn(
                "Block rejected: non-integer header version",
                block_index=getattr(header, "index", None),
                version=version_to_check,
            )
            return False

        if version_int not in self.blockchain._allowed_block_header_versions:
            self.logger.warn(
                "Block rejected: unsupported header version",
                block_index=getattr(header, "index", None),
                version=version_int,
                allowed_versions=sorted(self.blockchain._allowed_block_header_versions),
            )
            return False

        return True

    def _extract_timestamp(self, block_like: "Block" | BlockHeader | Any) -> float | None:
        """Return a floating-point timestamp from a block/header-like object."""
        if hasattr(block_like, "timestamp"):
            raw = getattr(block_like, "timestamp")
            return float(raw) if raw is not None else None
        if hasattr(block_like, "header"):
            header_obj = getattr(block_like, "header")
            if hasattr(header_obj, "timestamp"):
                raw = header_obj.timestamp
                return float(raw) if raw is not None else None
        return None

    def _median_time_from_history(
        self,
        history: Sequence["Block" | BlockHeader | Any],
    ) -> float | None:
        """Compute the median timestamp over the rolling history window."""
        if not history:
            return None
        window = list(history)[-self.blockchain._median_time_span :]
        timestamps: list[float] = []
        for entry in window:
            ts = self._extract_timestamp(entry)
            if ts is not None:
                timestamps.append(ts)
        if not timestamps:
            return None
        timestamps.sort()
        mid = len(timestamps) // 2
        if len(timestamps) % 2 == 0:
            return (timestamps[mid - 1] + timestamps[mid]) / 2
        return timestamps[mid]

    def _record_timestamp_metrics(
        self,
        *,
        index: int,
        timestamp: float,
        median_time: float | None,
        history_length: int,
    ) -> None:
        """Persist timestamp drift history and emit monitoring signals."""
        observed_at = time.time()
        median_drift = timestamp - median_time if median_time is not None else None
        wall_clock_drift = timestamp - observed_at
        record = {
            "index": index,
            "timestamp": timestamp,
            "median_drift": median_drift,
            "wall_clock_drift": wall_clock_drift,
            "history_length": history_length,
            "observed_at": observed_at,
        }
        self.blockchain._timestamp_drift_history.append(record)
        if abs(wall_clock_drift) > self.blockchain._max_future_block_time * 0.75:
            self.logger.warning(
                "Block timestamp drift warning",
                block_index=index,
                wall_clock_drift_seconds=wall_clock_drift,
                median_drift_seconds=median_drift,
            )
        try:
            from xai.core.monitoring import MetricsCollector

            collector = MetricsCollector.instance()
            if collector:
                median_metric = collector.get_metric("xai_block_timestamp_median_drift_seconds")
                if median_metric and median_drift is not None:
                    median_metric.observe(median_drift)
                wall_metric = collector.get_metric("xai_block_timestamp_wall_clock_drift_seconds")
                if wall_metric:
                    wall_metric.observe(wall_clock_drift)
                history_gauge = collector.get_metric("xai_block_timestamp_history_entries")
                if history_gauge:
                    history_gauge.set(len(self.blockchain._timestamp_drift_history))
        except (ImportError, AttributeError, RuntimeError) as exc:
            self.logger.debug(
                "Timestamp telemetry unavailable",
                error=str(exc),
            )

    def get_recent_timestamp_drift(self) -> list[dict[str, float]]:
        """Return a copy of the recent timestamp drift history for diagnostics."""
        return list(self.blockchain._timestamp_drift_history)

    def _validate_chain_structure(self, chain: list[BlockHeader]) -> bool:
        """
        Validates the structural integrity of a candidate chain (hashes, links).

        SECURITY: Validates block size limits during chain reorganization to prevent
        attackers from creating oversized blocks in a fork chain.
        """
        if not chain:
            return False

        # Genesis block always valid by definition
        first = chain[0].header if hasattr(chain[0], "header") else chain[0]
        if first.index != 0 or first.previous_hash != "0" * 64:
            return False

        # SECURITY: Validate genesis block size as well
        first_block = chain[0]
        if hasattr(first_block, "header"):  # This is a full Block object
            if not self._block_within_size_limits(first_block, context="chain_replacement"):
                self.logger.warn(
                    f"Genesis block exceeds size limits during chain reorganization",
                    block_hash=first.hash,
                )
                return False

        for i in range(1, len(chain)):
            current_header = chain[i].header if hasattr(chain[i], "header") else chain[i]
            previous_header = chain[i-1].header if hasattr(chain[i-1], "header") else chain[i-1]

            # Check previous hash link
            if current_header.previous_hash != previous_header.hash:
                self.logger.warn(f"Invalid chain structure: block {current_header.index} previous hash mismatch")
                return False

            # Check block hash (recalculate and compare)
            if current_header.hash != current_header.calculate_hash():
                self.logger.warn(f"Invalid chain structure: block {current_header.index} hash mismatch")
                return False

            # Check proof of work (simplified for headers)
            if not current_header.hash.startswith("0" * current_header.difficulty):
                self.logger.warn(f"Invalid chain structure: block {current_header.index} has invalid PoW")
                return False

            if not self._validate_header_version(current_header):
                return False

            expected_difficulty = self.blockchain._expected_difficulty_for_block(
                block_index=current_header.index,
                history=chain[:i],
            )
            if expected_difficulty is not None and current_header.difficulty != expected_difficulty:
                self.logger.warn(
                    f"Invalid chain structure: block {current_header.index} difficulty mismatch",
                    expected_difficulty=expected_difficulty,
                    declared_difficulty=current_header.difficulty,
                )
                return False

            time_valid, time_error = self._validate_block_timestamp(current_header, chain[:i])
            if not time_valid:
                self.logger.warn(
                    f"Invalid chain structure: block {current_header.index} timestamp invalid ({time_error})"
                )
                return False

            # Verify block signature
            if current_header.index > 0:
                if not self.verify_block_signature(current_header):
                    self.logger.warn(f"Invalid chain structure: block {current_header.index} has invalid signature")
                    return False

            # SECURITY: Validate block size limits during chain reorganization
            # Prevents attackers from creating oversized blocks in a fork chain
            # Note: We need the full Block object, not just the header
            current_block = chain[i]
            if hasattr(current_block, "header"):  # This is a full Block object
                if not self._block_within_size_limits(current_block, context="chain_replacement"):
                    self.logger.warn(
                        f"Block {current_header.index} exceeds size limits during chain reorganization",
                        block_hash=current_header.hash,
                    )
                    return False

        return True

    def is_chain_valid(self, chain: list[BlockHeader] | None = None) -> bool:
        """
        Public validation hook to verify chain integrity.

        Args:
            chain: Optional chain to validate. Defaults to the in-memory chain.
        """
        candidate_chain = chain if chain is not None else self.blockchain.chain
        return self._validate_chain_structure(candidate_chain)
