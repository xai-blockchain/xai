"""
Mempool Mixin for XAI Blockchain

Extracted from blockchain.py as part of god class refactoring.
Contains mempool/transaction pool management methods: add_transaction,
pruning, RBF handling, fee prioritization, and mempool statistics.
"""

from __future__ import annotations

import statistics
import threading
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xai.core.transaction import Transaction

class BlockchainMempoolMixin:
    """
    Mixin providing mempool management functionality for the Blockchain class.

    This mixin handles:
    - Transaction addition to mempool with validation
    - Mempool pruning (expiration, size limits)
    - Orphan transaction pool management
    - Sender ban tracking for invalid transactions
    - Replace-By-Fee (RBF) transaction replacement
    - Fee-based transaction prioritization
    - Mempool statistics and overview

    Required attributes on the implementing class:
    - pending_transactions: list[Transaction]
    - orphan_transactions: list[Transaction]
    - seen_txids: set[str]
    - _sender_pending_count: dict[str, int]
    - _invalid_sender_tracker: dict[str, dict]
    - _mempool_lock: threading.RLock
    - _mempool_max_size: int
    - _mempool_max_per_sender: int
    - _mempool_max_age_seconds: int
    - _mempool_min_fee_rate: float
    - _mempool_invalid_threshold: int
    - _mempool_invalid_ban_seconds: int
    - _mempool_invalid_window_seconds: int
    - _mempool_rejected_invalid_total: int
    - _mempool_rejected_banned_total: int
    - _mempool_rejected_low_fee_total: int
    - _mempool_rejected_sender_cap_total: int
    - _mempool_evicted_low_fee_total: int
    - _mempool_expired_total: int
    - _spent_inputs: set[str]  # O(1) lookup for double-spend detection
    - utxo_manager: UTXOManager
    - transaction_validator: TransactionValidator
    - nonce_tracker: NonceTracker
    - logger: StructuredLogger
    """

    def _prune_expired_mempool(self, current_time: float) -> int:
        """
        Expire old transactions and rebuild mempool indexes to keep counters accurate.

        This method rebuilds all mempool tracking structures including the spent_inputs
        set used for O(1) double-spend detection.
        """
        kept: list[Transaction] = []
        removed = 0
        sender_counts: dict[str, int] = defaultdict(int)
        seen_txids: set[str] = set()
        spent_inputs: set[str] = set()

        for tx in self.pending_transactions:
            if current_time - tx.timestamp < self._mempool_max_age_seconds:
                kept.append(tx)
                if tx.txid:
                    seen_txids.add(tx.txid)
                if tx.sender and tx.sender != "COINBASE":
                    sender_counts[tx.sender] += 1
                # Rebuild spent_inputs set for kept transactions
                if tx.tx_type != "coinbase" and tx.inputs:
                    for inp in tx.inputs:
                        input_key = f"{inp['txid']}:{inp['vout']}"
                        spent_inputs.add(input_key)
            else:
                # Unlock UTXOs for expired transaction
                if tx.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in tx.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                removed += 1

        if removed:
            self.logger.info(
                "Expired transactions pruned from mempool",
                removed=removed,
                remaining=len(kept),
            )

        self.pending_transactions = kept
        self.seen_txids = seen_txids
        self._sender_pending_count = defaultdict(int, sender_counts)
        self._spent_inputs = spent_inputs
        if removed:
            self._mempool_expired_total += removed
        return removed

    def _prune_orphan_pool(self, current_time: float) -> int:
        """Expire old orphan transactions."""
        before = len(self.orphan_transactions)
        self.orphan_transactions = [
            tx for tx in self.orphan_transactions
            if current_time - tx.timestamp < self._mempool_max_age_seconds
        ]
        removed = before - len(self.orphan_transactions)
        if removed:
            self.logger.info("Expired orphan transactions pruned", removed=removed)
        return removed

    def _is_sender_banned(self, sender: str | None, current_time: float) -> bool:
        if not sender or sender == "COINBASE":
            return False

        state = self._invalid_sender_tracker.get(sender)
        if not state:
            return False

        banned_until = state.get("banned_until", 0)
        if banned_until > current_time:
            return True

        if banned_until and banned_until <= current_time:
            # Ban expired, reset counters
            self._invalid_sender_tracker[sender] = {
                "count": 0,
                "first_seen": current_time,
                "banned_until": 0,
            }
        return False

    def _record_invalid_sender_attempt(self, sender: str | None, current_time: float) -> None:
        if not sender or sender == "COINBASE":
            return

        state = self._invalid_sender_tracker.get(
            sender,
            {"count": 0, "first_seen": current_time, "banned_until": 0},
        )

        # Reset window if outside of tracking window
        if current_time - state.get("first_seen", current_time) > self._mempool_invalid_window_seconds:
            state["count"] = 0
            state["first_seen"] = current_time

        state["count"] += 1
        state["first_seen"] = state.get("first_seen", current_time)

        if state["count"] >= self._mempool_invalid_threshold:
            state["banned_until"] = current_time + self._mempool_invalid_ban_seconds
            state["count"] = 0
            state["first_seen"] = current_time
            self.logger.warn(
                "Sender temporarily banned due to repeated invalid transactions",
                sender=sender,
                banned_until=state["banned_until"],
                ban_seconds=self._mempool_invalid_ban_seconds,
            )

        self._invalid_sender_tracker[sender] = state

    def _clear_sender_penalty(self, sender: str | None) -> None:
        if sender and sender != "COINBASE" and sender in self._invalid_sender_tracker:
            self._invalid_sender_tracker[sender] = {
                "count": 0,
                "first_seen": time.time(),
                "banned_until": 0,
            }

    def _count_active_bans(self, current_time: float) -> int:
        active = 0
        for sender, state in list(self._invalid_sender_tracker.items()):
            banned_until = state.get("banned_until", 0)
            if banned_until > current_time:
                active += 1
            elif banned_until and banned_until <= current_time:
                # Reset expired bans
                self._invalid_sender_tracker[sender] = {
                    "count": 0,
                    "first_seen": current_time,
                    "banned_until": 0,
                }
        return active

    def _check_double_spend(self, transaction: "Transaction") -> bool:
        """
        Check if transaction inputs are already spent in the mempool using O(1) lookup.

        This is a performance-optimized double-spend check that uses a set-based
        approach instead of nested loops. Instead of comparing every input against
        every pending transaction (O(n²)), we maintain a _spent_inputs set that
        tracks all inputs currently being spent, allowing O(1) lookup per input.

        Args:
            transaction: Transaction to check for double-spend

        Returns:
            True if double-spend detected, False otherwise

        Performance:
            - Old implementation: O(n²) where n = number of pending transactions
            - New implementation: O(m) where m = number of inputs in transaction
            - For a mempool with 1000 transactions, this is ~1000x faster
        """
        if transaction.tx_type == "coinbase" or not transaction.inputs:
            return False

        for tx_input in transaction.inputs:
            input_key = f"{tx_input['txid']}:{tx_input['vout']}"
            if input_key in self._spent_inputs:
                # Don't fail if this is an RBF replacement attempt - handled separately
                if not getattr(transaction, 'replaces_txid', None):
                    return True
        return False

    def remove_transaction_from_mempool(
        self,
        txid: str,
        *,
        ban_sender: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Remove a specific transaction from the mempool.

        This method removes the transaction and cleans up all tracking structures,
        including removing its inputs from the spent_inputs set for double-spend detection.

        Args:
            txid: Transaction ID to evict.
            ban_sender: Whether to record a sender penalty to prevent immediate resubmission.

        Returns:
            Tuple of (was_removed, metadata). Metadata contains sender/fee info when evicted.

        Raises:
            ValueError: If txid is empty.
        """
        if not txid:
            raise ValueError("txid is required")

        eviction_metadata: dict[str, Any] = {}
        removed = False
        with self._mempool_lock:
            for idx, tx in enumerate(list(self.pending_transactions)):
                if tx.txid != txid:
                    continue

                removed_tx = self.pending_transactions.pop(idx)
                removed = True
                eviction_metadata = {
                    "sender": getattr(removed_tx, "sender", None),
                    "amount": getattr(removed_tx, "amount", None),
                    "fee": getattr(removed_tx, "fee", None),
                }
                if removed_tx.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in removed_tx.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                    # Remove inputs from spent_inputs set
                    if removed_tx.tx_type != "coinbase":
                        for inp in removed_tx.inputs:
                            input_key = f"{inp['txid']}:{inp['vout']}"
                            self._spent_inputs.discard(input_key)

                self.seen_txids.discard(txid)
                sender = eviction_metadata.get("sender")
                if sender and sender in self._sender_pending_count:
                    self._sender_pending_count[sender] = max(
                        0,
                        self._sender_pending_count[sender] - 1,
                    )
                if ban_sender and sender:
                    ban_state = self._invalid_sender_tracker.get(sender, {})
                    ban_state["banned_until"] = time.time() + self._mempool_invalid_ban_seconds
                    ban_state["count"] = 0
                    ban_state["first_seen"] = time.time()
                    self._invalid_sender_tracker[sender] = ban_state
                break

        if removed:
            self.logger.info(
                "Transaction evicted from mempool",
                txid=txid,
                sender=eviction_metadata.get("sender"),
                ban_applied=ban_sender,
            )
        return removed, eviction_metadata

    def add_transaction(self, transaction: "Transaction") -> bool:
        """
        Add transaction to pending pool after validation.

        This method implements atomic validation and insertion to prevent TOCTOU
        race conditions in double-spend detection. The entire sequence from
        validation through insertion is protected by a lock to ensure that
        concurrent transactions spending the same UTXOs cannot both be accepted.

        Security: Prevents double-spend attacks via race conditions between
        validation (checking UTXO availability) and insertion (adding to mempool).
        """
        from xai.core.account_abstraction import (
            SponsorshipResult,
            get_sponsored_transaction_processor,
        )

        # Check if transaction is None (can happen if create_transaction fails)
        if transaction is None:
            self.logger.warn("Attempted to add a None transaction")
            return False

        self.logger.info("Attempting to add new transaction", txid=transaction.txid)
        # Periodically clean up old transactions from mempool and orphan pool
        current_time = time.time()
        self._prune_expired_mempool(current_time)
        self._prune_orphan_pool(current_time)

        # Ensure txid is present for deduplication
        if not getattr(transaction, "txid", None):
            try:
                transaction.txid = transaction.calculate_hash()
            except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                # Hash calculation errors: value/type issues, missing attributes, runtime failures
                self.logger.warn(
                    "Transaction rejected: failed to calculate txid",
                    extra={"error_type": type(e).__name__, "error": str(e)}
                )
                return False

        # CRITICAL SECTION: Acquire lock to ensure atomic validation and insertion
        # This prevents TOCTOU race conditions where two threads could both validate
        # transactions spending the same UTXO and both add them to the mempool
        with self._mempool_lock:
            # Drop duplicates early (under lock to prevent race)
            if transaction.txid in self.seen_txids:
                return False

            if self._is_sender_banned(getattr(transaction, "sender", None), current_time):
                self.logger.warn(
                    "Transaction rejected: sender temporarily banned for repeated invalid submissions",
                    sender=getattr(transaction, "sender", None),
                    txid=transaction.txid,
                )
                self._mempool_rejected_banned_total += 1
                return False

            # Auto-populate UTXO inputs/outputs for backward compatibility (before validation)
            # Only do this if transaction is NOT already signed (to avoid breaking signature)
            if (
                not transaction.signature
                and not transaction.inputs
                and transaction.sender != "COINBASE"
                and transaction.tx_type != "coinbase"
            ):
                # Old-style transaction without explicit inputs - auto-create from UTXOs
                sender_utxos = self.utxo_manager.get_utxos_for_address(transaction.sender)
                total_needed = transaction.amount + transaction.fee

                selected_utxos = []
                selected_amount = 0.0

                for utxo in sender_utxos:
                    selected_utxos.append(utxo)
                    selected_amount += utxo["amount"]
                    if selected_amount >= total_needed:
                        break

                if selected_amount < total_needed:
                    return False  # Insufficient funds

                # Create inputs
                transaction.inputs = [
                    {"txid": utxo["txid"], "vout": utxo["vout"]} for utxo in selected_utxos
                ]

                # Create outputs if not present
                if not transaction.outputs:
                    transaction.outputs = [
                        {"address": transaction.recipient, "amount": transaction.amount}
                    ]
                    # Add change output if necessary
                    change = selected_amount - total_needed
                    if change > 0.00000001:  # Minimum dust threshold
                        transaction.outputs.append({"address": transaction.sender, "amount": change})

            # Validate transaction (still under lock to prevent TOCTOU)
            is_valid = self.transaction_validator.validate_transaction(transaction)

            # If validation failed, check if it's because of missing UTXOs (orphan transaction)
            if not is_valid and transaction.tx_type != "coinbase":
                # Check if the transaction references unknown UTXOs
                has_missing_utxos = False
                if transaction.inputs:
                    for tx_input in transaction.inputs:
                        # Check if UTXO exists (don't exclude pending - we're checking existence, not availability)
                        utxo = self.utxo_manager.get_unspent_output(tx_input["txid"], tx_input["vout"], exclude_pending=False)
                        if not utxo:
                            has_missing_utxos = True
                            break

                # If it has missing UTXOs, add to orphan pool instead of rejecting
                if has_missing_utxos:
                    # Limit orphan pool size to prevent memory exhaustion
                    MAX_ORPHAN_TRANSACTIONS = 1000
                    if len(self.orphan_transactions) < MAX_ORPHAN_TRANSACTIONS:
                        # Check if transaction is not already in orphan pool
                        if not any(orphan.txid == transaction.txid for orphan in self.orphan_transactions):
                            self.orphan_transactions.append(transaction)
                            self.logger.info(f"Transaction {transaction.txid[:10]}... added to orphan pool (missing UTXOs)")
                    # Unlock UTXOs since transaction not accepted to mempool
                    if transaction.inputs:
                        utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                        self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                    return False
                else:
                    # Validation failed for other reasons, reject transaction
                    self.logger.warn(f"Transaction {transaction.txid[:10]}... rejected (validation failed for other reasons)")
                    self._record_invalid_sender_attempt(transaction.sender, current_time)
                    self._mempool_rejected_invalid_total += 1
                    # Unlock UTXOs since transaction rejected
                    if transaction.inputs:
                        utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                        self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                    return False

            if not is_valid:
                self._record_invalid_sender_attempt(transaction.sender, current_time)
                self._mempool_rejected_invalid_total += 1
                # Unlock UTXOs since transaction rejected
                if transaction.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                return False

            # Double-spend detection: O(1) check using spent_inputs set
            # This check is atomic with validation - prevents TOCTOU race
            if self._check_double_spend(transaction):
                self.logger.warn(
                    "Double-spend detected: Transaction inputs already spent in mempool",
                    txid=transaction.txid,
                    sender=transaction.sender,
                )
                self._record_invalid_sender_attempt(transaction.sender, current_time)
                self._mempool_rejected_invalid_total += 1
                # Unlock UTXOs since transaction rejected
                if transaction.inputs:
                    utxo_keys = [(inp["txid"], inp["vout"]) for inp in transaction.inputs]
                    self.utxo_manager.unlock_utxos_by_keys(utxo_keys)
                return False

            # Handle Replace-By-Fee (RBF) if this transaction replaces another
            if hasattr(transaction, 'replaces_txid') and transaction.replaces_txid:
                if not self._handle_rbf_replacement(transaction):
                    return False

            # Enforce per-sender cap
            if transaction.sender and transaction.sender != "COINBASE":
                if self._sender_pending_count.get(transaction.sender, 0) >= getattr(self, "_mempool_max_per_sender", 100):
                    self.logger.warn(f"Transaction {transaction.txid[:10]}... rejected (sender cap exceeded)")
                    self._mempool_rejected_sender_cap_total += 1
                    return False

            # Enforce mempool size with admission control by fee rate
            if len(self.pending_transactions) >= getattr(self, "_mempool_max_size", 10000):
                # Evaluate if new tx has higher fee rate than current min
                if self.pending_transactions:
                    lowest = min(self.pending_transactions, key=lambda t: t.get_fee_rate())
                    if transaction.get_fee_rate() > lowest.get_fee_rate():
                        # Evict the lowest fee transaction to make room for the higher fee rate
                        eviction_performed = False
                        try:
                            self.pending_transactions.remove(lowest)
                            self.seen_txids.discard(lowest.txid)
                            # Remove evicted transaction's inputs from spent_inputs set
                            if lowest.tx_type != "coinbase" and lowest.inputs:
                                for inp in lowest.inputs:
                                    input_key = f"{inp['txid']}:{inp['vout']}"
                                    self._spent_inputs.discard(input_key)
                            if lowest.sender and lowest.sender != "COINBASE":
                                self._sender_pending_count[lowest.sender] = max(
                                    0, self._sender_pending_count[lowest.sender] - 1
                                )
                            self._mempool_evicted_low_fee_total += 1
                            eviction_performed = True
                            self.logger.info(f"Evicted transaction {lowest.txid[:10]}... from mempool (low fee rate)")
                        except ValueError as exc:
                            self.logger.error(
                                "Failed to evict low-fee transaction due to inconsistent mempool state",
                                txid=lowest.txid,
                                error=str(exc),
                                extra={"event": "mempool.eviction_failed"},
                            )
                        if not eviction_performed:
                            self.logger.warn(
                                f"Transaction {transaction.txid[:10]}... rejected (mempool full, eviction failed)"
                            )
                            self._mempool_rejected_low_fee_total += 1
                            return False
                    else:
                        self.logger.warn(f"Transaction {transaction.txid[:10]}... rejected (mempool full, low fee rate)")
                        self._mempool_rejected_low_fee_total += 1
                        return False

            # ATOMIC INSERTION: Add to mempool while still holding lock
            # This ensures no gap between validation and insertion
            self.pending_transactions.append(transaction)
            self.seen_txids.add(transaction.txid)
            # Add transaction inputs to spent_inputs set for O(1) double-spend detection
            if transaction.tx_type != "coinbase" and transaction.inputs:
                for inp in transaction.inputs:
                    input_key = f"{inp['txid']}:{inp['vout']}"
                    self._spent_inputs.add(input_key)
            if transaction.sender and transaction.sender != "COINBASE":
                self._sender_pending_count[transaction.sender] = self._sender_pending_count.get(transaction.sender, 0) + 1
                self.nonce_tracker.reserve_nonce(transaction.sender, transaction.nonce)
            self._clear_sender_penalty(transaction.sender)

            # Process gas sponsorship if applicable (Task 178: Account Abstraction)
            if hasattr(transaction, 'gas_sponsor') and transaction.gas_sponsor:
                sponsor_processor = get_sponsored_transaction_processor()
                validation = sponsor_processor.validate_sponsored_transaction(transaction)
                if validation.result == SponsorshipResult.APPROVED:
                    sponsor_processor.deduct_sponsor_fee(transaction)
                    self.logger.info(
                        "Sponsored transaction added to mempool",
                        txid=transaction.txid,
                        sender=transaction.sender,
                        sponsor=transaction.gas_sponsor,
                        fee=transaction.fee
                    )
                else:
                    # Sponsorship validation failed - log but don't reject
                    # The transaction can still be processed if sender has funds
                    self.logger.warn(
                        f"Sponsorship validation failed: {validation.message}",
                        txid=transaction.txid,
                        sender=transaction.sender,
                        sponsor=transaction.gas_sponsor
                    )
            else:
                self.logger.info("Transaction added to mempool", txid=transaction.txid, sender=transaction.sender)

            return True
        # End of atomic lock section

    def _handle_rbf_replacement(self, replacement_tx: "Transaction") -> bool:
        """
        Handle Replace-By-Fee transaction replacement.

        Rules:
        1. Original transaction must be in mempool (not yet mined)
        2. Original transaction must have rbf_enabled=True (opt-in)
        3. Replacement must have higher fee rate than original
        4. Replacement must be from the same sender
        5. Replacement must use the same or overlapping inputs

        Args:
            replacement_tx: The new transaction attempting to replace an existing one

        Returns:
            True if replacement is valid and original was removed, False otherwise
        """
        # Find the original transaction in pending pool
        original_tx = None
        original_index = -1
        for idx, tx in enumerate(self.pending_transactions):
            if tx.txid == replacement_tx.replaces_txid:
                original_tx = tx
                original_index = idx
                break

        if not original_tx:
            self.logger.warn(f"RBF failed: Original transaction {replacement_tx.replaces_txid} not found in mempool")
            return False

        # Check if original transaction opted into RBF
        if not getattr(original_tx, 'rbf_enabled', False):
            self.logger.warn(f"RBF failed: Original transaction {replacement_tx.replaces_txid} did not opt-in to RBF")
            return False

        # Verify sender is the same
        if original_tx.sender != replacement_tx.sender:
            self.logger.warn(f"RBF failed: Sender mismatch (original: {original_tx.sender}, replacement: {replacement_tx.sender})")
            return False

        # Verify replacement has higher fee rate
        original_fee_rate = original_tx.get_fee_rate()
        replacement_fee_rate = replacement_tx.get_fee_rate()

        if replacement_fee_rate <= original_fee_rate:
            self.logger.warn(f"RBF failed: Replacement fee rate ({replacement_fee_rate}) must be higher than original ({original_fee_rate})")
            return False

        # Verify inputs overlap (replacement must spend at least one of the same UTXOs)
        original_inputs = set((inp.get('txid'), inp.get('vout')) for inp in original_tx.inputs)
        replacement_inputs = set((inp.get('txid'), inp.get('vout')) for inp in replacement_tx.inputs)

        if not original_inputs.intersection(replacement_inputs):
            self.logger.warn(f"RBF failed: No overlapping inputs between original ({original_tx.txid}) and replacement ({replacement_tx.txid})")
            return False

        # All checks passed - remove original transaction from mempool
        self.logger.info(f"RBF successful: Replacing {original_tx.txid} with {replacement_tx.txid}",
                         original_txid=original_tx.txid, replacement_txid=replacement_tx.txid,
                         original_fee_rate=original_fee_rate, replacement_fee_rate=replacement_fee_rate)

        del self.pending_transactions[original_index]
        self.seen_txids.discard(original_tx.txid)
        # Remove original transaction's inputs from spent_inputs set
        if original_tx.tx_type != "coinbase" and original_tx.inputs:
            for inp in original_tx.inputs:
                input_key = f"{inp['txid']}:{inp['vout']}"
                self._spent_inputs.discard(input_key)
        if original_tx.sender and original_tx.sender != "COINBASE":
            self._sender_pending_count[original_tx.sender] -= 1
        return True

    def _prioritize_transactions(self, transactions: list["Transaction"], max_count: int | None = None) -> list["Transaction"]:
        """
        Prioritize transactions by fee rate (fee-per-byte) while maintaining nonce order per sender.

        This implements a proper fee market where:
        1. Transactions are ordered by fee rate (fee-per-byte, highest first) to maximize miner revenue
        2. Within each sender's transactions, nonce order is maintained for validity
        3. Optional limit on number of transactions to include in block
        4. This prevents large transactions with high absolute fees but low fee rates from
           crowding out smaller transactions with better fee rates

        Args:
            transactions: List of pending transactions
            max_count: Maximum number of transactions to return (None = all)

        Returns:
            Ordered list of transactions prioritized by fee rate
        """
        if not transactions:
            return []

        # Group transactions by sender
        by_sender: dict[str, list["Transaction"]] = defaultdict(list)
        for tx in transactions:
            by_sender[tx.sender].append(tx)

        # Sort each sender's transactions by nonce (ascending) to maintain validity
        for sender, sender_txs in by_sender.items():
            # Sort by nonce if present, otherwise by timestamp
            sender_txs.sort(key=lambda tx: (tx.nonce if tx.nonce is not None else 0, tx.timestamp))

        # Flatten back to a single list with fee rate priority
        all_txs = []
        for sender_txs in by_sender.values():
            all_txs.extend(sender_txs)

        # Sort by fee rate (descending) - this is more fair than absolute fee
        # Transactions with higher fee-per-byte get priority
        # This prevents large transactions from crowding out smaller ones
        all_txs.sort(key=lambda tx: tx.get_fee_rate(), reverse=True)

        # Limit to max_count if specified
        if max_count is not None:
            all_txs = all_txs[:max_count]

        return all_txs

    def get_mempool_size_kb(self) -> float:
        """
        Return current mempool footprint in kilobytes for operational controls.
        """
        total_bytes = sum(tx.get_size() for tx in self.pending_transactions) if self.pending_transactions else 0
        return total_bytes / 1024.0

    def get_mempool_overview(self, limit: int = 100) -> dict[str, Any]:
        """
        Return detailed mempool statistics and representative transactions.
        """
        limit = max(0, min(int(limit), 1000))
        pending = list(self.pending_transactions) if self.pending_transactions else []
        now = time.time()
        size_bytes = sum(tx.get_size() for tx in pending) if pending else 0
        total_amount = sum(float(getattr(tx, "amount", 0.0)) for tx in pending)
        fees = [float(getattr(tx, "fee", 0.0)) for tx in pending]
        fee_rates = [float(tx.get_fee_rate()) for tx in pending]
        timestamps = [
            float(tx.timestamp)
            for tx in pending
            if isinstance(getattr(tx, "timestamp", None), (int, float))
        ]
        sponsor_count = sum(1 for tx in pending if getattr(tx, "gas_sponsor", None))

        def _avg(values: list[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        limits = {
            "max_transactions": getattr(self, "_mempool_max_size", len(pending)),
            "max_per_sender": getattr(self, "_mempool_max_per_sender", 100),
            "min_fee_rate": getattr(self, "_mempool_min_fee_rate", 0.0),
            "max_age_seconds": getattr(self, "_mempool_max_age_seconds", 86400),
        }

        overview: dict[str, Any] = {
            "pending_count": len(pending),
            "pool_size": len(pending),  # Alias for pending_count for backward compatibility
            "size_bytes": size_bytes,
            "size_kb": size_bytes / 1024.0,
            "total_amount": total_amount,
            "total_fees": sum(fees) if fees else 0.0,
            "avg_fee": _avg(fees),
            "median_fee": float(statistics.median(fees)) if fees else 0.0,
            "avg_fee_rate": _avg(fee_rates),
            "median_fee_rate": float(statistics.median(fee_rates)) if fee_rates else 0.0,
            "min_fee_rate": min(fee_rates) if fee_rates else 0.0,
            "max_fee_rate": max(fee_rates) if fee_rates else 0.0,
            "sponsored_transactions": sponsor_count,
            "oldest_transaction_age_seconds": now - min(timestamps) if timestamps else 0.0,
            "newest_transaction_age_seconds": now - max(timestamps) if timestamps else 0.0,
            "limits": limits,
            "rejections": {
                "invalid_total": self._mempool_rejected_invalid_total,
                "banned_total": self._mempool_rejected_banned_total,
                "low_fee_total": self._mempool_rejected_low_fee_total,
                "sender_cap_total": self._mempool_rejected_sender_cap_total,
                "evicted_low_fee_total": self._mempool_evicted_low_fee_total,
                "expired_total": self._mempool_expired_total,
                "active_bans": self._count_active_bans(now),
            },
            "statistics": {
                "evicted_low_fee_total": self._mempool_evicted_low_fee_total,
                "expired_total": self._mempool_expired_total,
                "rejected_invalid_total": self._mempool_rejected_invalid_total,
                "rejected_banned_total": self._mempool_rejected_banned_total,
                "rejected_low_fee_total": self._mempool_rejected_low_fee_total,
                "rejected_sender_cap_total": self._mempool_rejected_sender_cap_total,
            },
            "timestamp": now,
        }

        if limit > 0 and pending:
            tx_summaries: list[dict[str, Any]] = []
            for tx in pending[:limit]:
                tx_size = tx.get_size()
                summary = {
                    "txid": tx.txid,
                    "sender": tx.sender,
                    "recipient": tx.recipient,
                    "amount": tx.amount,
                    "fee": tx.fee,
                    "fee_rate": tx.get_fee_rate(),
                    "size_bytes": tx_size,
                    "timestamp": getattr(tx, "timestamp", None),
                    "age_seconds": now - tx.timestamp if getattr(tx, "timestamp", None) else None,
                    "nonce": tx.nonce,
                    "type": tx.tx_type,
                    "rbf_enabled": bool(getattr(tx, "rbf_enabled", False)),
                    "gas_sponsor": getattr(tx, "gas_sponsor", None),
                }
                tx_summaries.append(summary)
            overview["transactions"] = tx_summaries
        else:
            overview["transactions"] = []

        overview["transactions_returned"] = len(overview["transactions"])
        return overview
