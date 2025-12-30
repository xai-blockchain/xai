from __future__ import annotations

"""
XAI Blockchain - UTXO Manager

Manages the Unspent Transaction Output (UTXO) set for the blockchain.
Ensures that transactions spend only available UTXOs and prevents double-spending.
Thread-safe implementation with RLock to prevent race conditions and double-spend attacks.

Supports pluggable storage backends:
- MemoryUTXOStore: In-memory dict-based storage (default, JSON-serializable)
- LevelDBUTXOStore: High-performance LevelDB storage for production

Security Notes:
- All UTXO amounts are validated before adding to the set
- Negative, NaN, and Infinity amounts are rejected
- Maximum amount is bounded by total supply cap
"""

import hashlib
import json
import math
from collections import defaultdict
from threading import RLock
from typing import TYPE_CHECKING, Any

from xai.core.api.structured_logger import StructuredLogger, get_structured_logger
from xai.core.transactions.utxo_store import UTXOStore, MemoryUTXOStore, create_utxo_store
from xai.core.consensus.validation import validate_amount

if TYPE_CHECKING:
    from xai.core.blockchain import Transaction

# Validation constants
MAX_UTXO_AMOUNT = 121_000_000.0  # Total supply cap
MIN_UTXO_AMOUNT = 0.0

class UTXOValidationError(ValueError):
    """Raised when UTXO validation fails."""
    pass

class UTXOManager:
    """
    Manages the UTXO set, providing functionality to add, remove, and query UTXOs.
    Thread-safe implementation using RLock to prevent concurrent access issues.

    Supports pluggable storage backends via UTXOStore interface:
    - MemoryUTXOStore: In-memory dict-based storage (default)
    - LevelDBUTXOStore: High-performance LevelDB storage for production

    Usage:
        # Memory backend (default, backward compatible)
        manager = UTXOManager()

        # LevelDB backend for production
        from xai.core.transactions.utxo_store import create_utxo_store
        store = create_utxo_store("leveldb", db_path="/path/to/utxo.db")
        manager = UTXOManager(store=store)
    """

    def __init__(
        self,
        logger: StructuredLogger | None = None,
        store: UTXOStore | None = None,
    ) -> None:
        """
        Initialize the UTXO Manager.

        Args:
            logger: Optional structured logger instance
            store: Optional UTXOStore backend. Defaults to MemoryUTXOStore for
                   backward compatibility. Use LevelDBUTXOStore for production.
        """
        self.logger = logger or get_structured_logger()

        # Storage backend (defaults to memory for backward compatibility)
        self._store: UTXOStore = store if store is not None else MemoryUTXOStore()

        # Legacy compatibility: expose utxo_set as property
        # Note: Direct access is deprecated; use store methods instead
        self._use_legacy_storage = store is None

        # Thread safety: RLock allows same thread to acquire lock multiple times
        self._lock = RLock()

        # Pending UTXOs: Track UTXOs selected for pending transactions to prevent double-spend
        # Format: {(txid, vout): timestamp} - timestamp enables timeout-based cleanup
        self._pending_utxos: dict[tuple, float] = {}
        # Timeout for pending UTXO locks (5 minutes)
        self._pending_timeout = 300.0

    @property
    def utxo_set(self) -> dict[str, list[dict[str, Any]]]:
        """Legacy access to UTXO set. Prefer store methods for new code."""
        return self._store.to_dict()

    @utxo_set.setter
    def utxo_set(self, value: dict[str, list[dict[str, Any]]]) -> None:
        """Legacy setter for UTXO set. Loads data into storage backend."""
        self._store.clear()
        self._store.load_from_dict(value)

    @property
    def total_utxos(self) -> int:
        """Get total number of unspent UTXOs."""
        return self._store.get_stats()["total_utxos"]

    @total_utxos.setter
    def total_utxos(self, value: int) -> None:
        """Legacy setter - no-op as store manages this internally."""
        pass  # Store manages internally

    @property
    def total_value(self) -> float:
        """Get total value of all unspent UTXOs."""
        return self._store.get_stats()["total_value"]

    @total_value.setter
    def total_value(self, value: float) -> None:
        """Legacy setter - no-op as store manages this internally."""
        pass  # Store manages internally

    @property
    def _utxo_index(self) -> dict[str, tuple[str, dict[str, Any]]]:
        """Legacy index access - returns empty dict as store manages indexing."""
        # Store handles indexing internally
        return {}

    @_utxo_index.setter
    def _utxo_index(self, value: dict[str, tuple[str, dict[str, Any]]]) -> None:
        """Legacy setter - no-op as store manages indexing internally."""
        pass  # Store manages internally

    def snapshot_digest(self) -> str:
        """
        Return a deterministic hash of the current UTXO set for integrity checks.
        Delegated to storage backend for consistent hashing.
        """
        with self._lock:
            return self._store.snapshot_digest()

    @staticmethod
    def _validate_amount(amount: Any, context: str = "amount") -> float:
        """Validate a UTXO amount using centralized validation.

        Args:
            amount: Value to validate
            context: Context for error messages

        Returns:
            Validated float amount

        Raises:
            UTXOValidationError: If validation fails
        """
        if amount is None:
            raise UTXOValidationError(f"UTXO {context} cannot be None")

        try:
            return validate_amount(
                amount,
                allow_zero=True,
                min_value=MIN_UTXO_AMOUNT,
                max_value=MAX_UTXO_AMOUNT
            )
        except ValueError as e:
            raise UTXOValidationError(f"UTXO {context}: {e}") from e

    def add_utxo(self, address: str, txid: str, vout: int, amount: float, script_pubkey: str) -> None:
        """
        Adds a new UTXO to the set via the storage backend.

        Performance: O(1) operation with hash-based indexing (storage handles internally).

        Args:
            address: The address to which the UTXO belongs.
            txid: The transaction ID that created this UTXO.
            vout: The output index within the transaction.
            amount: The amount of the UTXO (must be >= 0 and <= MAX_UTXO_AMOUNT).
            script_pubkey: The script public key (or similar locking script).

        Raises:
            UTXOValidationError: If amount validation fails
        """
        # Validate amount before adding
        validated_amount = self._validate_amount(amount)

        with self._lock:
            added = self._store.add_utxo(address, txid, vout, validated_amount, script_pubkey)
            if added:
                self.logger.debug(
                    f"Added UTXO: {txid}:{vout} for {address} with {validated_amount} XAI",
                    address=address,
                    txid=txid,
                    vout=vout,
                    amount=validated_amount,
                )
            else:
                self.logger.debug(
                    f"Duplicate UTXO: {txid}:{vout} for {address} already exists",
                    address=address,
                    txid=txid,
                    vout=vout,
                )

    def mark_utxo_spent(self, address: str, txid: str, vout: int) -> bool:
        """
        Marks a specific UTXO as spent via the storage backend.

        Performance: O(1) operation using hash-based indexing (storage handles internally).

        Security: Validates ownership before marking spent to prevent unauthorized
        spending attacks where an attacker could mark another user's UTXOs as spent.

        Args:
            address: The address that owned the UTXO.
            txid: The transaction ID of the UTXO to mark as spent.
            vout: The output index of the UTXO to mark as spent.

        Returns:
            True if the UTXO was found, owned by address, and marked as spent.
            False if UTXO not found, already spent, or ownership mismatch.
        """
        with self._lock:
            # Security: Validate ownership before marking spent
            utxo = self._store.get_utxo(txid, vout)
            if utxo is None:
                self.logger.warn(
                    f"UTXO not found or already spent: {txid}:{vout}",
                    address=address,
                    txid=txid,
                    vout=vout,
                )
                return False

            # Check ownership - UTXO must belong to the specified address
            utxo_address = utxo.get("address")
            if utxo_address and utxo_address != address:
                self.logger.warn(
                    f"Ownership validation failed for UTXO {txid}:{vout}: "
                    f"expected {address}, found {utxo_address}",
                    address=address,
                    utxo_address=utxo_address,
                    txid=txid,
                    vout=vout,
                )
                return False

            # Delegate to storage backend
            marked = self._store.mark_spent(txid, vout)

            if marked:
                self.logger.debug(
                    f"Marked UTXO: {txid}:{vout} for {address} as spent",
                    address=address,
                    txid=txid,
                    vout=vout,
                )
            else:
                self.logger.warn(
                    f"Failed to mark UTXO: {txid}:{vout} for {address} as spent",
                    address=address,
                    txid=txid,
                    vout=vout,
                )

            return marked

    def get_utxos_for_address(self, address: str, exclude_pending: bool = True) -> list[dict[str, Any]]:
        """
        Retrieves all unspent UTXOs for a given address via storage backend.

        Args:
            address: The address to query.
            exclude_pending: If True, exclude UTXOs locked for pending transactions.

        Returns:
            A list of unspent UTXO dictionaries.
        """
        with self._lock:
            utxos = self._store.get_utxos_for_address(address)

            if exclude_pending:
                # Filter out pending UTXOs
                self._cleanup_expired_pending()
                utxos = [
                    utxo for utxo in utxos
                    if (utxo["txid"], utxo["vout"]) not in self._pending_utxos
                ]

            return utxos

    def get_balance(self, address: str) -> float:
        """
        Calculates the total balance for a given address from its UTXOs.

        Args:
            address: The address to calculate the balance for.

        Returns:
            The total balance as a float.
        """
        # Use store's efficient balance calculation, then adjust for pending
        with self._lock:
            self._cleanup_expired_pending()
            # Get UTXOs excluding pending for accurate balance
            utxos = self.get_utxos_for_address(address, exclude_pending=True)
            return sum(utxo["amount"] for utxo in utxos)

    def process_transaction_outputs(self, transaction: "Transaction") -> None:
        """
        Adds new UTXOs created by a transaction's outputs.
        Each output in the transaction creates a new UTXO.

        Args:
            transaction: The transaction whose outputs are to be added as UTXOs.
        """
        # Note: add_utxo already has lock, RLock allows reentrant locking
        for vout, output in enumerate(transaction.outputs):
            self.add_utxo(
                output["address"],
                transaction.txid,
                vout,
                output["amount"],
                f"P2PKH {output['address']}",
            )
        txid_display = transaction.txid[:10] if transaction.txid else "<unsigned>"
        self.logger.info(
            f"Processed outputs for transaction {txid_display}...", txid=transaction.txid
        )

    def process_transaction_inputs(self, transaction: "Transaction") -> bool:
        """
        Marks UTXOs consumed by a transaction's inputs as spent.

        Security: Validates that no duplicate inputs exist within the same transaction
        to prevent inflation attacks where the same UTXO is spent multiple times.

        Args:
            transaction: The transaction whose inputs are to be marked as spent.

        Returns:
            True if all inputs were successfully marked as spent, False otherwise.

        Raises:
            UTXOValidationError: If duplicate inputs are detected
        """
        if transaction.sender == "COINBASE":  # Coinbase transactions don't spend inputs
            return True

        # CRITICAL SECURITY CHECK: Detect duplicate inputs within this transaction
        # An attacker could reference the same UTXO multiple times to inflate value
        seen_inputs = set()
        for input_ref in transaction.inputs:
            utxo_key = (input_ref["txid"], input_ref["vout"])
            if utxo_key in seen_inputs:
                # Security event: Duplicate input attack attempt detected
                self.logger.error(
                    "SECURITY: Duplicate UTXO input detected - inflation attack attempt",
                    extra={
                        "event": "utxo.duplicate_input_attack",
                        "txid": transaction.txid,
                        "duplicate_utxo": f"{utxo_key[0]}:{utxo_key[1]}",
                        "sender": transaction.sender,
                        "severity": "CRITICAL"
                    }
                )
                raise UTXOValidationError(
                    f"Duplicate input detected: {utxo_key[0]}:{utxo_key[1]}. "
                    f"Same UTXO cannot be spent multiple times in a single transaction."
                )
            seen_inputs.add(utxo_key)

        # Process each unique input - mark UTXOs as spent
        # Note: mark_utxo_spent already has lock, RLock allows reentrant locking
        for input_utxo_ref in transaction.inputs:
            txid = input_utxo_ref["txid"]
            vout = input_utxo_ref["vout"]
            if not self.mark_utxo_spent(transaction.sender, txid, vout):
                self.logger.error(
                    f"Failed to mark UTXO {txid}:{vout} as spent for sender {transaction.sender}.",
                    txid=txid,
                    vout=vout,
                    sender=transaction.sender,
                )
                return False
        txid_display = transaction.txid[:10] if transaction.txid else "<unsigned>"
        self.logger.info(
            f"Processed inputs for transaction {txid_display}...", txid=transaction.txid
        )
        return True

    def get_unspent_output(self, txid: str, vout: int, exclude_pending: bool = True) -> dict[str, Any] | None:
        """
        Retrieves a specific unspent UTXO by its transaction ID and output index.

        Performance: O(1) operation using hash-based indexing (storage handles internally).

        Args:
            txid: The transaction ID of the UTXO.
            vout: The output index of the UTXO within the transaction.
            exclude_pending: If True, return None if UTXO is locked for pending transaction.

        Returns:
            The UTXO dictionary if found and unspent, otherwise None.
        """
        with self._lock:
            # Check if UTXO is pending
            if exclude_pending:
                self._cleanup_expired_pending()
                if (txid, vout) in self._pending_utxos:
                    return None

            # Delegate to storage backend for O(1) lookup
            return self._store.get_utxo(txid, vout)

    def find_spendable_utxos(self, address: str, amount: float) -> list[dict[str, Any]]:
        """
        Finds a set of unspent UTXOs for an address that sum up to at least the required amount.

        Args:
            address: The address to find UTXOs for.
            amount: The minimum amount required.

        Returns:
            A list of UTXO dictionaries that can be spent.
        """
        # get_utxos_for_address already has lock, RLock allows reentrant locking
        spendable_utxos = []
        current_sum = 0.0
        for utxo in self.get_utxos_for_address(address):
            spendable_utxos.append(utxo)
            current_sum += utxo["amount"]
            if current_sum >= amount:
                break

        if current_sum < amount:
            return []  # Not enough spendable UTXOs

        return spendable_utxos

    def lock_utxos(self, utxos: list[dict[str, Any]]) -> bool:
        """
        Lock UTXOs for a pending transaction to prevent double-spending.

        Security: This prevents TOCTOU race conditions where two threads could both
        validate transactions spending the same UTXO. By locking UTXOs when selected,
        we ensure atomic reservation.

        Args:
            utxos: List of UTXO dictionaries to lock

        Returns:
            True if all UTXOs were successfully locked, False if any were already locked
        """
        with self._lock:
            import time
            self._cleanup_expired_pending()

            # Check if any UTXOs are already locked
            for utxo in utxos:
                utxo_key = (utxo["txid"], utxo["vout"])
                if utxo_key in self._pending_utxos:
                    self.logger.warn(
                        f"UTXO {utxo['txid']}:{utxo['vout']} already locked for pending transaction",
                        extra={"event": "utxo.lock_failed", "utxo": utxo_key}
                    )
                    return False

            # Lock all UTXOs
            current_time = time.time()
            for utxo in utxos:
                utxo_key = (utxo["txid"], utxo["vout"])
                self._pending_utxos[utxo_key] = current_time
                self.logger.debug(
                    f"Locked UTXO {utxo['txid']}:{utxo['vout']} for pending transaction",
                    extra={"event": "utxo.locked", "utxo": utxo_key}
                )

            return True

    def unlock_utxos(self, utxos: list[dict[str, Any]]) -> None:
        """
        Unlock UTXOs when transaction is rejected or mined.

        Args:
            utxos: List of UTXO dictionaries to unlock
        """
        with self._lock:
            for utxo in utxos:
                utxo_key = (utxo["txid"], utxo["vout"])
                if utxo_key in self._pending_utxos:
                    del self._pending_utxos[utxo_key]
                    self.logger.debug(
                        f"Unlocked UTXO {utxo['txid']}:{utxo['vout']}",
                        extra={"event": "utxo.unlocked", "utxo": utxo_key}
                    )

    def unlock_utxos_by_keys(self, utxo_keys: list[tuple]) -> None:
        """
        Unlock UTXOs by their (txid, vout) keys.

        Args:
            utxo_keys: List of (txid, vout) tuples to unlock
        """
        with self._lock:
            for utxo_key in utxo_keys:
                if utxo_key in self._pending_utxos:
                    del self._pending_utxos[utxo_key]
                    self.logger.debug(
                        f"Unlocked UTXO {utxo_key[0]}:{utxo_key[1]}",
                        extra={"event": "utxo.unlocked", "utxo": utxo_key}
                    )

    def _cleanup_expired_pending(self) -> None:
        """
        Remove expired pending UTXO locks.

        Called internally to clean up locks that have timed out, preventing
        UTXOs from being locked indefinitely if a transaction fails to be
        processed or rejected.
        """
        import time
        current_time = time.time()
        expired = [
            utxo_key for utxo_key, timestamp in self._pending_utxos.items()
            if current_time - timestamp > self._pending_timeout
        ]

        for utxo_key in expired:
            del self._pending_utxos[utxo_key]
            self.logger.info(
                f"Released expired pending lock on UTXO {utxo_key[0]}:{utxo_key[1]}",
                extra={"event": "utxo.lock_expired", "utxo": utxo_key, "age": current_time - self._pending_utxos.get(utxo_key, current_time)}
            )

    def get_pending_utxo_count(self) -> int:
        """
        Get the count of currently locked pending UTXOs.

        Returns:
            Number of UTXOs locked for pending transactions
        """
        with self._lock:
            self._cleanup_expired_pending()
            return len(self._pending_utxos)

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the UTXO set to a dictionary for serialization.
        Delegated to storage backend.
        """
        with self._lock:
            return self._store.to_dict()

    def get_utxo_set(self) -> dict[str, Any]:
        """
        Get a copy of the current UTXO set.

        Returns:
            A dictionary representation of the UTXO set.
        """
        return self.to_dict()

    def load_utxo_set(self, utxo_set_data: dict[str, Any]) -> None:
        """
        Loads the UTXO set from a dictionary via storage backend.

        Performance: Storage backend handles O(1) lookup index.
        """
        with self._lock:
            self._store.load_from_dict(utxo_set_data)
            stats = self._store.get_stats()
            self.logger.info(f"UTXO set loaded with {stats['total_utxos']} unspent UTXOs.")

    def get_total_unspent_value(self) -> float:
        """
        Returns the total value of all unspent UTXOs in the system.
        """
        with self._lock:
            return self._store.get_stats()["total_value"]

    def get_unique_addresses_count(self) -> int:
        """
        Returns the count of unique addresses that have unspent UTXOs.
        """
        with self._lock:
            utxo_data = self._store.to_dict()
            return len([addr for addr in utxo_data.keys() if self.get_balance(addr) > 0])

    def get_stats(self) -> dict[str, Any]:
        """
        Returns statistics about the current UTXO set.
        """
        with self._lock:
            store_stats = self._store.get_stats()
            utxo_data = self._store.to_dict()
            return {
                "total_utxos": store_stats["total_utxos"],
                "total_unspent_value": store_stats["total_value"],
                "unique_addresses_with_utxos": len(utxo_data),
                "backend": store_stats.get("backend", "unknown"),
            }

    def reset(self) -> None:
        """
        Resets the UTXO manager to its initial state.
        """
        with self._lock:
            self._store.clear()
            self._pending_utxos = {}
            self.logger.info("UTXO Manager reset.")

    def snapshot(self) -> dict[str, Any]:
        """
        Creates a complete snapshot of the current UTXO state.
        Thread-safe atomic operation for chain reorganization rollback.

        Returns:
            A deep copy of the UTXO state including totals
        """
        with self._lock:
            stats = self._store.get_stats()
            return {
                "utxo_set": self._store.to_dict(),
                "total_utxos": stats["total_utxos"],
                "total_value": stats["total_value"],
            }

    def restore(self, snapshot: dict[str, Any]) -> None:
        """
        Restores UTXO state from a snapshot via storage backend.
        Thread-safe atomic operation for chain reorganization rollback.

        Args:
            snapshot: Snapshot created by snapshot() method
        """
        with self._lock:
            # Clear and restore via storage backend
            self._store.clear()
            utxo_data = snapshot.get("utxo_set", {})
            self._store.load_from_dict(utxo_data)
            stats = self._store.get_stats()
            self.logger.info(f"UTXO state restored from snapshot with {stats['total_utxos']} UTXOs.")

    def clear(self) -> None:
        """
        Clears all UTXOs via storage backend.
        Used for chain reorganization before rebuilding.
        """
        with self._lock:
            self._store.clear()
            self._pending_utxos = {}

    def compact_utxo_set(self) -> int:
        """
        Compact the UTXO set by removing spent UTXOs from memory.

        For LevelDB backend, this is largely a no-op as spent UTXOs are already
        removed from the index. For memory backend, this cleans up the list-based
        storage structure.

        Returns:
            Number of spent UTXOs removed from memory
        """
        with self._lock:
            # Storage backends handle spent UTXOs differently
            # For now, this is primarily for memory backend cleanup
            # LevelDB already removes spent from index immediately
            stats_before = self._store.get_stats()
            current_data = self._store.to_dict()

            # Count and filter spent UTXOs
            removed_count = 0
            compact_data: dict[str, list[dict]] = {}
            for address, utxos in current_data.items():
                unspent = [utxo for utxo in utxos if not utxo.get("spent", False)]
                removed = len(utxos) - len(unspent)
                removed_count += removed
                if unspent:
                    compact_data[address] = unspent

            if removed_count > 0:
                # Reload with compacted data
                self._store.clear()
                self._store.load_from_dict(compact_data)
                self.logger.info(
                    f"Compacted UTXO set: removed {removed_count} spent UTXOs from memory",
                    removed_count=removed_count
                )

            return removed_count

    def calculate_merkle_root(self) -> str:
        """
        Calculate a Merkle root of the entire UTXO set for state verification.

        This provides a deterministic hash of the UTXO set that can be used to:
        1. Verify UTXO set consistency across nodes
        2. Create light client proofs
        3. Detect state corruption or tampering

        The calculation is deterministic by sorting UTXOs before hashing.

        Returns:
            Hex string of the Merkle root hash
        """
        with self._lock:
            # Collect all unspent UTXOs across all addresses
            all_utxos = []
            for address, utxos in self.utxo_set.items():
                for utxo in utxos:
                    if not utxo.get("spent", False):
                        # Create deterministic representation
                        utxo_key = f"{utxo['txid']}:{utxo['vout']}:{address}:{utxo['amount']}"
                        all_utxos.append(utxo_key)

            # Sort for deterministic ordering
            all_utxos.sort()

            # Handle empty UTXO set
            if not all_utxos:
                return hashlib.sha256(b"").hexdigest()

            # Build Merkle tree
            utxo_hashes = [hashlib.sha256(utxo.encode()).hexdigest() for utxo in all_utxos]

            # Repeatedly hash pairs until we get to the root
            while len(utxo_hashes) > 1:
                # If odd number, duplicate last hash
                if len(utxo_hashes) % 2 != 0:
                    utxo_hashes.append(utxo_hashes[-1])

                new_hashes = []
                for i in range(0, len(utxo_hashes), 2):
                    combined = utxo_hashes[i] + utxo_hashes[i + 1]
                    new_hash = hashlib.sha256(combined.encode()).hexdigest()
                    new_hashes.append(new_hash)

                utxo_hashes = new_hashes

            return utxo_hashes[0]

    def verify_utxo_consistency(self) -> dict[str, Any]:
        """
        Verify internal consistency of the UTXO set.

        Checks:
        1. Total UTXO count matches actual count
        2. Total value matches sum of all unspent UTXOs
        3. No duplicate UTXOs exist

        Returns:
            Dictionary with verification results and any discrepancies found
        """
        with self._lock:
            actual_count = 0
            actual_value = 0.0
            seen_utxos = set()
            duplicates = []

            for address, utxos in self.utxo_set.items():
                for utxo in utxos:
                    if not utxo.get("spent", False):
                        actual_count += 1
                        actual_value += utxo["amount"]

                        # Check for duplicates
                        utxo_id = f"{utxo['txid']}:{utxo['vout']}"
                        if utxo_id in seen_utxos:
                            duplicates.append(utxo_id)
                        seen_utxos.add(utxo_id)

            count_mismatch = self.total_utxos != actual_count
            value_mismatch = abs(self.total_value - actual_value) > 0.00000001  # Allow for floating point error

            return {
                "is_consistent": not count_mismatch and not value_mismatch and not duplicates,
                "total_utxos_stored": self.total_utxos,
                "total_utxos_actual": actual_count,
                "count_mismatch": count_mismatch,
                "total_value_stored": self.total_value,
                "total_value_actual": actual_value,
                "value_mismatch": value_mismatch,
                "duplicates_found": duplicates,
            }

# Global instance for convenience
_global_utxo_manager = None

def get_utxo_manager(logger: StructuredLogger | None = None) -> UTXOManager:
    """
    Get global UTXO manager instance.
    """
    global _global_utxo_manager
    if _global_utxo_manager is None:
        _global_utxo_manager = UTXOManager(logger)
    return _global_utxo_manager
