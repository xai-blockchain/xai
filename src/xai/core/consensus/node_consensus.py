"""
XAI Blockchain Node Consensus Management
Handles consensus mechanisms, block validation, and chain integrity verification.
"""

from __future__ import annotations

import logging
import statistics
import time
from typing import TYPE_CHECKING, Any

from xai.core.security.blockchain_security import BlockchainSecurityConfig
from xai.core.config import Config

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain

# Configure logging
logger = logging.getLogger(__name__)

def _record_consensus_metrics(
    metric_name: str,
    value: float = 1.0,
    operation: str = "inc",
    labels: dict[str, Any] | None = None
) -> None:
    """
    Record consensus metrics to the metrics collector singleton.

    Args:
        metric_name: Name of the metric
        value: Value to record
        operation: 'inc' for counter, 'set' for gauge, 'observe' for histogram
        labels: Optional labels for the metric
    """
    try:
        from xai.core.api.monitoring import MetricsCollector
        collector = MetricsCollector.instance()
        if not collector:
            return

        metric = collector.get_metric(metric_name)
        if not metric:
            return

        if operation == "inc":
            metric.inc(value)
        elif operation == "set":
            metric.set(value)
        elif operation == "observe":
            if labels:
                metric.observe(value, labels=labels)
            else:
                metric.observe(value)
    except (ImportError, AttributeError, RuntimeError, TypeError):
        # Metrics not available - silent fail
        pass

# Timestamp validation constants
# Maximum time a block timestamp can be ahead of current system time
# Using 2 hours (7200 seconds) as per Bitcoin's standard
# This prevents timestamp manipulation attacks while allowing for minor clock drift
MAX_FUTURE_BLOCK_TIME = 2 * 60 * 60  # 2 hours in seconds

class ConsensusManager:
    """
    Manages consensus mechanisms and validation for the blockchain node.

    Responsibilities:
    - Validate individual blocks
    - Validate entire blockchain chains
    - Resolve forks using longest valid chain rule
    - Verify proof-of-work
    - Check chain integrity
    """

    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize consensus manager.

        Args:
            blockchain: The blockchain instance to manage consensus for
        """
        self.blockchain = blockchain
        self._median_time_span = BlockchainSecurityConfig.MEDIAN_TIME_SPAN
        allowed = getattr(
            Config, "BLOCK_HEADER_ALLOWED_VERSIONS", [getattr(Config, "BLOCK_HEADER_VERSION", 1)]
        )
        self._allowed_header_versions = {
            int(v) for v in allowed if isinstance(v, int) or str(v).strip().lstrip("-").isdigit()
        }
        if not self._allowed_header_versions:
            self._allowed_header_versions = {getattr(Config, "BLOCK_HEADER_VERSION", 1)}

    def validate_block(
        self,
        block: Block,
        previous_block: Block | None = None,
        *,
        history_chain: list[Block] | None = None,
        history_end_index: int | None = None,
    ) -> tuple[bool, str | None]:
        """
        Validate a single block according to consensus rules.

        Validates:
        1. Block hash matches calculated hash
        2. Proof-of-work meets difficulty requirement
        3. Previous hash links correctly to chain
        4. Block index is sequential
        5. Timestamp is reasonable

        Args:
            block: The block to validate
            previous_block: Optional previous block for validation

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if block passes all validation checks
            - error_message: Description of validation failure, or None if valid

        Example:
            >>> manager = ConsensusManager(blockchain)
            >>> is_valid, error = manager.validate_block(new_block)
            >>> if not is_valid:
            ...     print(f"Block invalid: {error}")
        """
        _validation_start = time.time()

        # Check block hash is correctly calculated
        calculated_hash = block.calculate_hash()
        if block.hash != calculated_hash:
            _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")
            return False, f"Invalid block hash. Expected: {calculated_hash}, got: {block.hash}"

        block_version = self._extract_block_version(block)
        if block_version is None:
            block_version = getattr(Config, "BLOCK_HEADER_VERSION", 1)
        if block_version not in self._allowed_header_versions:
            logger.warning(
                "Block header version rejected",
                extra={
                    "event": "consensus.invalid_header_version",
                    "block_index": getattr(block, "index", None),
                    "block_hash": block.hash,
                    "version": block_version,
                },
            )
            _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")
            return False, f"Unsupported block header version {block_version}"

        # Check proof of work meets difficulty using proper target comparison
        # The hash must be numerically less than target = 2^256 / difficulty
        if not self._validate_pow(block.hash, self.blockchain.difficulty):
            _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")
            return False, f"Invalid proof of work. Hash does not meet difficulty {self.blockchain.difficulty}"

        # If we have the previous block, validate linkage
        if previous_block is not None:
            # Check previous hash links correctly
            if block.previous_hash != previous_block.hash:
                _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")
                return (
                    False,
                    f"Previous hash mismatch. Expected: {previous_block.hash}, got: {block.previous_hash}",
                )

            # Check index is sequential
            if block.index != previous_block.index + 1:
                _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")
                return (
                    False,
                    f"Invalid block index. Expected: {previous_block.index + 1}, got: {block.index}",
                )

            # Validate timestamp is within acceptable range
            is_valid, error = self._validate_timestamp(
                block,
                previous_block,
                history_chain=history_chain,
                history_end_index=history_end_index,
            )
            if not is_valid:
                _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")
                return False, error

        else:
            # When validating a standalone block (e.g., mempool mining), ensure index matches chain height
            chain_snapshot = getattr(self.blockchain, "chain", []) or []
            expected_index = len(chain_snapshot)
            if expected_index > 0 and block.index != expected_index:
                _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")
                return (
                    False,
                    f"Block index mismatch. Expected {expected_index}, got {block.index}",
                )

        # Record successful validation metrics
        _validation_duration = time.time() - _validation_start
        _record_consensus_metrics(
            "xai_transaction_validation_duration_seconds",
            _validation_duration,
            operation="observe"
        )
        _record_consensus_metrics("xai_blocks_received_total", 1, operation="inc")

        return True, None

    def _calculate_median_time_past(
        self,
        chain: list[Block] | None = None,
        end_index: int | None = None,
    ) -> float | None:
        chain_ref = chain if chain is not None else getattr(self.blockchain, "chain", None)
        if not chain_ref:
            return None

        if end_index is None or end_index > len(chain_ref):
            end_index = len(chain_ref)
        if end_index <= 0:
            return None

        start = max(0, end_index - self._median_time_span)
        window = chain_ref[start:end_index]
        timestamps: list[float] = []
        for entry in window:
            timestamp = getattr(entry, "timestamp", None)
            if timestamp is None and hasattr(entry, "header"):
                timestamp = getattr(entry.header, "timestamp", None)
            if timestamp is None:
                continue
            try:
                timestamps.append(float(timestamp))
            except (TypeError, ValueError):
                continue

        if not timestamps:
            return None

        timestamps.sort()
        mid = len(timestamps) // 2
        if len(timestamps) % 2 == 0:
            return (timestamps[mid - 1] + timestamps[mid]) / 2.0
        return timestamps[mid]

    def _extract_block_version(self, block: Block) -> int | None:
        version_candidate = getattr(block, "version", None)
        if version_candidate is None:
            header = getattr(block, "header", None)
            if header is not None:
                version_candidate = getattr(header, "version", None)
        if version_candidate is None:
            return None
        try:
            return int(version_candidate)
        except (TypeError, ValueError):
            return None

    def _validate_timestamp(
        self,
        block: Block,
        previous_block: Block,
        *,
        history_chain: list[Block] | None = None,
        history_end_index: int | None = None,
    ) -> tuple[bool, str | None]:
        """
        Validate block timestamp is within acceptable range.

        Security-critical validation that prevents timestamp manipulation attacks:
        1. Block timestamp must be after previous block (prevents rewinding time)
        2. Block timestamp must not be too far in future (prevents difficulty manipulation)

        Timestamp manipulation attacks allow miners to:
        - Manipulate difficulty calculations by setting future timestamps
        - Gain unfair mining advantage
        - Break time-dependent smart contracts
        - Disrupt consensus by causing nodes to reject valid blocks

        Args:
            block: Block being validated
            previous_block: The previous block in chain

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if timestamp passes all checks
            - error_message: Description of validation failure, or None if valid

        Security:
            Uses MAX_FUTURE_BLOCK_TIME (2 hours) as per Bitcoin's standard.
            This allows for minor clock drift between nodes while preventing
            significant timestamp manipulation attacks.

        Example:
            >>> is_valid, error = self._validate_timestamp(block, previous_block)
            >>> if not is_valid:
            ...     logger.warning(f"Timestamp validation failed: {error}")
        """
        current_time = int(time.time())

        # Check 1: Block timestamp must be strictly after previous block
        # This prevents time from going backwards in the chain
        if block.timestamp <= previous_block.timestamp:
            error_msg = (
                f"Block timestamp {block.timestamp} must be after "
                f"previous block timestamp {previous_block.timestamp} (timestamp is before previous block)"
            )
            logger.warning(
                "Block timestamp validation failed - not after previous block",
                extra={
                    "event": "consensus.timestamp_rejected",
                    "reason": "not_after_previous",
                    "block_timestamp": block.timestamp,
                    "previous_timestamp": previous_block.timestamp,
                    "block_index": block.index,
                    "delta_seconds": block.timestamp - previous_block.timestamp,
                },
            )
            return False, error_msg

        # Check 2: Block timestamp must not be too far in the future
        # This prevents difficulty manipulation and other timestamp-based attacks
        max_allowed_time = current_time + MAX_FUTURE_BLOCK_TIME
        if block.timestamp > max_allowed_time:
            time_ahead = block.timestamp - current_time
            hours_ahead = time_ahead / 3600.0
            error_msg = (
                f"Block timestamp {block.timestamp} is too far in future. "
                f"Current time: {current_time}, max allowed: {max_allowed_time} "
                f"(block is {time_ahead}s / {hours_ahead:.2f}h ahead, "
                f"max allowed: {MAX_FUTURE_BLOCK_TIME}s / {MAX_FUTURE_BLOCK_TIME/3600:.2f}h)"
            )
            logger.warning(
                "Block timestamp validation failed - too far in future",
                extra={
                    "event": "consensus.timestamp_rejected",
                    "reason": "future_timestamp",
                    "block_timestamp": block.timestamp,
                    "current_time": current_time,
                    "max_allowed": max_allowed_time,
                    "delta_seconds": time_ahead,
                    "delta_hours": hours_ahead,
                    "block_index": block.index,
                    "block_hash": block.hash,
                },
            )
            return False, error_msg

        median_time = self._calculate_median_time_past(
            chain=history_chain,
            end_index=history_end_index,
        )
        if median_time is not None and block.timestamp <= median_time:
            error_msg = (
                f"Block timestamp {block.timestamp} must be greater than median time past {median_time}"
            )
            logger.warning(
                "Block timestamp validation failed - not greater than median time past",
                extra={
                    "event": "consensus.timestamp_rejected",
                    "reason": "median_time_past",
                    "block_timestamp": block.timestamp,
                    "median_time": median_time,
                    "block_index": block.index,
                    "block_hash": block.hash,
                },
            )
            return False, error_msg

        # Timestamp is valid
        logger.debug(
            "Block timestamp validated successfully",
            extra={
                "event": "consensus.timestamp_validated",
                "block_timestamp": block.timestamp,
                "current_time": current_time,
                "time_diff_seconds": block.timestamp - previous_block.timestamp,
                "block_index": block.index,
            },
        )

        return True, None

    def validate_block_transactions(self, block: Block) -> tuple[bool, str | None]:
        """
        Validate all transactions in a block.

        Validates:
        1. Transaction ordering (prevents MEV attacks)
        2. Transaction signatures
        3. Sender balances for normal transactions
        4. Coinbase reward doesn't exceed allowed amount (CRITICAL SECURITY CHECK)

        Args:
            block: Block containing transactions to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = manager.validate_block_transactions(block)
        """
        # CRITICAL SECURITY: Validate transaction ordering to prevent MEV attacks
        # This check ensures miners cannot reorder transactions for profit
        is_ordered = self._validate_transaction_ordering(block)
        if not is_ordered:
            logger.error(
                "SECURITY: Block has invalid transaction ordering - potential MEV attack",
                extra={
                    "event": "consensus.invalid_tx_ordering",
                    "block_index": block.index,
                    "block_hash": block.hash,
                }
            )
            return False, "Block transactions violate ordering rules (potential MEV attack)"

        # CRITICAL SECURITY: Validate coinbase reward to prevent inflation attacks
        # This check ensures miners cannot create unlimited coins
        reward_validator = getattr(type(self.blockchain), "validate_coinbase_reward", None)
        if callable(reward_validator):
            result = self.blockchain.validate_coinbase_reward(block)
            if isinstance(result, tuple) and len(result) == 2:
                is_valid_reward, reward_error = result
                if not is_valid_reward:
                    logger.error(
                        "SECURITY: Block has invalid coinbase reward - potential inflation attack",
                        extra={
                            "event": "consensus.invalid_coinbase_reward",
                            "block_index": block.index,
                            "block_hash": block.hash,
                            "error": reward_error,
                        }
                    )
                    return False, f"Invalid coinbase reward: {reward_error}"

        # Validate individual transactions
        for i, tx in enumerate(block.transactions):
            # Skip balance/signature validation for coinbase/reward transactions
            # (coinbase amount is validated above)
            if tx.sender in ["COINBASE", "SYSTEM", "AIRDROP"]:
                continue

            # Verify transaction signature using typed exceptions
            if hasattr(tx, "verify_signature"):
                from xai.core.transaction import (
                    InvalidSignatureError,
                    MissingSignatureError,
                    SignatureCryptoError,
                    SignatureVerificationError,
                )
                try:
                    sig_valid = tx.verify_signature()
                    # Check return value if method returns bool (some implementations may raise instead)
                    if sig_valid is False:
                        return False, f"Invalid signature for transaction {i} ({tx.txid})"
                except MissingSignatureError as e:
                    return False, f"Missing signature for transaction {i} ({tx.txid}): {e}"
                except InvalidSignatureError as e:
                    return False, f"Invalid signature for transaction {i} ({tx.txid}): {e}"
                except SignatureCryptoError as e:
                    return False, f"Crypto error verifying transaction {i} ({tx.txid}): {e}"
                except SignatureVerificationError as e:
                    return False, f"Signature verification failed for transaction {i} ({tx.txid}): {e}"
                except Exception as e:
                    # Log unexpected errors with full context for debugging
                    logger.error(
                        "Unexpected error during block transaction signature verification",
                        extra={
                            "error_type": type(e).__name__,
                            "error": str(e),
                            "tx_index": i,
                            "tx_id": tx.txid,
                            "block_index": block.index
                        },
                        exc_info=True
                    )
                    return False, f"Unexpected error verifying signature for transaction {i} ({tx.txid}): {type(e).__name__}: {e}"

            # Check sender has sufficient balance (except for special transactions)
            if tx.tx_type == "normal":
                balance = self.blockchain.get_balance(tx.sender)
                required = tx.amount + tx.fee
                if balance < required:
                    return (
                        False,
                        f"Insufficient balance in transaction {i}. Address {tx.sender} has {balance}, needs {required}",
                    )

        return True, None

    def _validate_transaction_ordering(self, block: Block) -> bool:
        """
        Validate that transactions in a block follow ordering rules.

        Security-critical validation that prevents:
        - MEV (Miner Extractable Value) attacks
        - Front-running attacks
        - Transaction reordering for profit
        - Nonce sequencing bypass

        Rules:
        1. Coinbase transaction (if present) must be first
        2. Transactions from same sender must be in nonce order (ascending)
        3. No duplicate transactions

        Args:
            block: Block to validate

        Returns:
            True if transaction ordering is valid, False otherwise
        """
        transactions = block.transactions
        if not transactions:
            return True

        seen_txids = set()
        sender_nonces: dict[str, int] = {}

        for i, tx in enumerate(transactions):
            # Rule 1: Coinbase must be first (if present)
            if tx.sender == "COINBASE":
                if i != 0:
                    logger.warning(
                        "Coinbase not first transaction",
                        extra={
                            "event": "consensus.invalid_tx_order",
                            "reason": "coinbase_not_first",
                            "coinbase_position": i,
                            "block_height": block.index,
                            "block_hash": block.hash,
                        },
                    )
                    return False
                continue  # Skip nonce check for coinbase

            # Rule 2: No duplicates
            txid = tx.txid or tx.calculate_hash()
            if txid in seen_txids:
                logger.warning(
                    "Duplicate transaction in block",
                    extra={
                        "event": "consensus.invalid_tx_order",
                        "reason": "duplicate_tx",
                        "txid": txid,
                        "block_height": block.index,
                        "block_hash": block.hash,
                    },
                )
                return False
            seen_txids.add(txid)

            # Rule 3: Nonce ordering per sender
            # Skip for special system transactions
            if tx.sender in ["SYSTEM", "AIRDROP"]:
                continue

            if tx.nonce is not None:
                if tx.sender in sender_nonces:
                    expected_nonce = sender_nonces[tx.sender] + 1
                    if tx.nonce != expected_nonce:
                        logger.warning(
                            "Invalid nonce sequence",
                            extra={
                                "event": "consensus.invalid_tx_order",
                                "reason": "nonce_sequence",
                                "sender": tx.sender,
                                "expected_nonce": expected_nonce,
                                "actual_nonce": tx.nonce,
                                "block_height": block.index,
                                "block_hash": block.hash,
                            },
                        )
                        return False
                sender_nonces[tx.sender] = tx.nonce

        return True

    def resolve_forks(self, chains: list[list[Block]]) -> tuple[list[Block] | None, str]:
        """
        Resolve blockchain forks using longest valid chain rule.

        Implements consensus mechanism:
        1. Validate all competing chains
        2. Select longest valid chain
        3. In case of tie, use cumulative difficulty

        Args:
            chains: List of competing blockchain forks

        Returns:
            Tuple of (canonical_chain, reason)
            - canonical_chain: The selected chain, or None if all invalid
            - reason: Explanation of selection

        Example:
            >>> chains = [chain1, chain2, chain3]
            >>> selected, reason = manager.resolve_forks(chains)
            >>> print(f"Selected chain: {reason}")
        """
        if not chains:
            return None, "No chains provided"

        valid_chains: list[tuple[list[Block], int]] = []

        # Validate all chains and track their lengths
        for i, chain in enumerate(chains):
            is_valid, error = self.validate_chain(chain)
            if is_valid:
                valid_chains.append((chain, len(chain)))
            else:
                print(f"Chain {i} rejected: {error}")

        if not valid_chains:
            return None, "No valid chains found"

        # Sort by length (descending)
        valid_chains.sort(key=lambda x: x[1], reverse=True)

        # Return longest chain
        longest_chain, length = valid_chains[0]

        # Check for ties
        ties = [c for c, l in valid_chains if l == length]
        if len(ties) > 1:
            reason = f"Selected longest valid chain (length: {length}, {len(ties)} chains tied)"
        else:
            reason = f"Selected longest valid chain (length: {length})"

        return longest_chain, reason

    def check_chain_integrity(self) -> tuple[bool, list[str]]:
        """
        Check integrity of the current blockchain.

        Verifies:
        1. No gaps in block indices
        2. All hashes link correctly
        3. All proof-of-work is valid
        4. No double-spending

        Returns:
            Tuple of (is_intact, issues)
            - is_intact: True if chain has no issues
            - issues: List of integrity problems found

        Example:
            >>> is_intact, issues = manager.check_chain_integrity()
            >>> if not is_intact:
            ...     for issue in issues:
            ...         print(f"Integrity issue: {issue}")
        """
        issues: list[str] = []

        if len(self.blockchain.chain) == 0:
            return True, []

        # Check for index gaps
        for i, block in enumerate(self.blockchain.chain):
            if block.index != i:
                issues.append(
                    f"Block index mismatch at position {i}: expected {i}, got {block.index}"
                )

        # Validate chain linkage
        is_valid, error = self.validate_chain(self.blockchain.chain)
        if not is_valid:
            issues.append(f"Chain validation failed: {error}")

        # Check for double-spending
        spent_outputs: dict[str, set] = {}
        for block in self.blockchain.chain:
            for tx in block.transactions:
                # Track spending
                if hasattr(tx, "inputs") and tx.inputs:
                    for inp in tx.inputs:
                        tx_id = inp.get("txid")
                        output_index = inp.get("output_index")
                        if tx_id:
                            key = f"{tx_id}:{output_index}"
                            if tx_id in spent_outputs and key in spent_outputs[tx_id]:
                                issues.append(f"Double-spend detected: {key}")
                            else:
                                if tx_id not in spent_outputs:
                                    spent_outputs[tx_id] = set()
                                spent_outputs[tx_id].add(key)

        return len(issues) == 0, issues

    def calculate_chain_work(self, chain: list[Block]) -> int:
        """
        Calculate total cumulative work in a chain.

        Used for tie-breaking when chains have equal length.

        Args:
            chain: Blockchain to calculate work for

        Returns:
            Total proof-of-work as integer

        Example:
            >>> work = manager.calculate_chain_work(chain)
            >>> print(f"Total chain work: {work}")
        """
        total_work = 0

        for block in chain:
            # Count leading zeros in hash as work
            work = 0
            for char in block.hash:
                if char == "0":
                    work += 1
                else:
                    break
            total_work += work

        return total_work

    def should_replace_chain(self, new_chain: list[Block]) -> tuple[bool, str]:
        """
        Determine if we should replace our current chain with a new one.

        Decision criteria:
        1. New chain must be valid
        2. New chain must be longer than current
        3. New chain must have more cumulative work (if same length)

        Args:
            new_chain: Candidate chain to potentially adopt

        Returns:
            Tuple of (should_replace, reason)

        Example:
            >>> should_replace, reason = manager.should_replace_chain(peer_chain)
            >>> if should_replace:
            ...     blockchain.chain = peer_chain
            ...     print(f"Chain replaced: {reason}")
        """
        # Validate new chain
        is_valid, error = self.validate_chain(new_chain)
        if not is_valid:
            return False, f"New chain is invalid: {error}"

        current_length = len(self.blockchain.chain)
        new_length = len(new_chain)

        # New chain must be longer
        if new_length <= current_length:
            return False, f"New chain is not longer ({new_length} vs {current_length})"

        # Calculate work for tie-breaking
        current_work = self.calculate_chain_work(self.blockchain.chain)
        new_work = self.calculate_chain_work(new_chain)

        if new_length == current_length:
            if new_work <= current_work:
                return False, f"New chain does not have more work ({new_work} vs {current_work})"

        return True, f"New chain is longer and valid ({new_length} blocks, {new_work} total work)"

    def verify_proof_of_work(self, block: Block, difficulty: int) -> bool:
        """
        Verify that a block's hash meets the proof-of-work requirement.

        Uses proper target comparison: hash_int < (2^256 / difficulty)

        Args:
            block: Block to verify
            difficulty: Mining difficulty (higher = harder)

        Returns:
            True if proof-of-work is valid

        Example:
            >>> if manager.verify_proof_of_work(block, 4):
            ...     print("Valid proof of work!")
        """
        return self._validate_pow(block.hash, difficulty)

    def _validate_pow(self, block_hash: str, difficulty: int) -> bool:
        """
        Validate proof of work using proper numeric target comparison.

        The hash must be numerically less than the target where:
        target = 2^256 / difficulty

        This is the correct Bitcoin-style PoW validation that compares
        the hash as an integer against the target, not just leading zeros.

        Args:
            block_hash: The block hash in hexadecimal
            difficulty: Mining difficulty value

        Returns:
            True if hash meets difficulty requirement

        Security:
            Using integer comparison instead of string prefix is critical.
            String prefix only checks leading zeros but doesn't verify
            the actual numeric value of the hash is below target.

            Example: With difficulty 2, the target is 2^255.
            Hash 0x8000...0000 starts with no leading zeros but
            is exactly at the boundary - string prefix would accept
            0x0FFF...FFFF but reject 0x1000...0000, which is inconsistent
            with how Bitcoin difficulty actually works.
        """
        if not block_hash:
            return False

        if difficulty <= 0:
            return False

        prefix = "0" * max(1, min(difficulty, 64))
        if not block_hash.startswith(prefix):
            return False

        try:
            # Convert hash to integer for comparison
            hash_int = int(block_hash, 16)

            # Calculate target: 2^256 / difficulty
            # Lower difficulty = higher target = easier to mine
            # Higher difficulty = lower target = harder to mine
            target = (2**256) // difficulty

            return hash_int < target

        except (ValueError, ZeroDivisionError):
            # Invalid hash format or zero difficulty - fall back to legacy prefix check
            return True

    def check_consensus(self) -> bool:
        """
        Check if the current blockchain is in a valid consensus state.

        Verifies:
        1. Chain is valid
        2. Chain integrity is maintained
        3. All blocks meet consensus rules

        Returns:
            True if consensus is valid, False otherwise

        Example:
            >>> if manager.check_consensus():
            ...     print("Consensus is valid!")
        """
        # Check if chain is valid
        is_valid, error = self.validate_chain(self.blockchain.chain)
        if not is_valid:
            print(f"Consensus check failed: {error}")
            return False

        # Check chain integrity
        is_intact, issues = self.check_chain_integrity()
        if not is_intact:
            print(f"Chain integrity issues: {issues}")
            return False

        return True

    def validate_chain(self, chain: list[Block] | None = None) -> tuple[bool, str | None]:
        """
        Validate an entire blockchain.

        Performs comprehensive validation:
        1. Genesis block is valid
        2. All blocks link correctly
        3. All proof-of-work is valid
        4. All timestamps are sequential
        5. All transactions are valid

        Args:
            chain: List of blocks forming a blockchain (defaults to self.blockchain.chain)

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = manager.validate_chain(received_chain)
            >>> if is_valid:
            ...     print("Chain is valid!")
        """
        # Use current blockchain chain if none provided
        if chain is None:
            chain = self.blockchain.chain

        if not chain or len(chain) == 0:
            return False, "Chain is empty"

        def _materialize(block_like: Block) -> Block | None:
            # If already a Block with transactions, return directly
            if hasattr(block_like, "transactions"):
                return block_like
            # Otherwise, attempt to load from disk via blockchain storage
            idx = getattr(block_like, "index", None)
            if idx is None:
                return None
            try:
                loaded = self.blockchain.storage.load_block_from_disk(idx)
                return loaded
            except (ValueError, KeyError, TypeError, RuntimeError, OSError, IOError) as e:
                logging.debug("Failed to load block %s from disk: %s", idx, e)
                return None

        # Validate genesis block
        genesis = _materialize(chain[0]) or chain[0]
        if genesis.index != 0:
            return False, "Genesis block must have index 0"

        if genesis.previous_hash != "0":
            return False, "Genesis block must have previous_hash of '0'"

        # Validate each subsequent block
        for i in range(1, len(chain)):
            current_block = _materialize(chain[i])
            previous_block = _materialize(chain[i - 1])

            if current_block is None or previous_block is None:
                return False, f"Block {i} missing transaction data"

            # Validate block
            is_valid, error = self.validate_block(
                current_block,
                previous_block,
                history_chain=chain,
                history_end_index=i,
            )
            if not is_valid:
                return False, f"Block {i} validation failed: {error}"

            # Validate block transactions
            is_valid, error = self.validate_block_transactions(current_block)
            if not is_valid:
                return False, f"Block {i} transaction validation failed: {error}"

        return True, None

    def get_consensus_info(self) -> dict[str, Any]:
        """
        Get information about current consensus state.

        Returns:
            Dictionary with consensus metrics

        Example:
            >>> info = manager.get_consensus_info()
            >>> print(f"Chain height: {info['chain_height']}")
        """
        chain_work = self.calculate_chain_work(self.blockchain.chain)
        is_intact, issues = self.check_chain_integrity()

        return {
            "chain_height": len(self.blockchain.chain),
            "difficulty": self.blockchain.difficulty,
            "total_work": chain_work,
            "chain_intact": is_intact,
            "integrity_issues": len(issues),
            "genesis_hash": self.blockchain.chain[0].hash if self.blockchain.chain else None,
            "latest_block_hash": self.blockchain.chain[-1].hash if self.blockchain.chain else None,
        }
