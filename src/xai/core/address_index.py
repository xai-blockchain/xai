"""
Address Transaction Index - O(log n) transaction history lookups

Provides SQLite-based address indexing for efficient transaction history queries.
Without indexing, get_transaction_history_window() performs O(n²) scan: O(n blocks) × O(m txs per block).
With indexing, lookups are O(log n) via SQLite B-tree indexes.

Security considerations:
- Read-only queries prevent SQL injection via parameterized statements
- Index is append-only during normal operation (no deletes except reorg)
- Crash-safe via SQLite's built-in ACID guarantees
- Chain reorganizations handled via transaction rollback
"""

import sqlite3
import threading
from typing import List, Tuple, Optional, Any
from pathlib import Path

from xai.core.transaction import Transaction
from xai.core.structured_logger import get_structured_logger


class AddressTransactionIndex:
    """
    SQLite-based address transaction index for O(log n) lookups.

    Maintains a mapping from addresses to their transaction history with efficient
    pagination support. Index is updated atomically during block addition and
    supports rollback during chain reorganizations.

    Schema:
        address_txs (address, block_index, tx_index, txid, is_sender, amount, timestamp)
        - Composite PRIMARY KEY ensures no duplicates
        - B-tree index on 'address' enables O(log n) lookups
        - Index on 'txid' supports transaction lookup by hash

    Thread Safety:
        All operations are protected by a reentrant lock to prevent concurrent
        modification during reorgs and normal block addition.
    """

    def __init__(self, db_path: str):
        """
        Initialize address index with SQLite database.

        Args:
            db_path: Path to SQLite database file. Created if doesn't exist.

        Raises:
            sqlite3.Error: If database initialization fails
        """
        self.db_path = db_path
        self.logger = get_structured_logger()

        # SQLite connection is not thread-safe by default
        # Use check_same_thread=False with explicit locking
        self._lock = threading.RLock()

        try:
            self.db = sqlite3.connect(
                db_path,
                check_same_thread=False,
                isolation_level="DEFERRED"  # Explicit transaction control
            )
            self.db.row_factory = sqlite3.Row  # Enable column access by name
            self._init_schema()
            self.logger.info("Address index initialized", db_path=db_path)
        except sqlite3.Error as e:
            self.logger.error("Failed to initialize address index", error=str(e), db_path=db_path)
            raise

    def _init_schema(self) -> None:
        """
        Create index schema if it doesn't exist.

        Schema design:
        - Composite PRIMARY KEY (address, block_index, tx_index) prevents duplicates
        - Index on address enables fast lookups by address
        - Index on txid enables fast transaction deduplication checks
        - timestamp allows sorting by time without loading full transactions

        Performance characteristics:
        - INSERT: O(log n) due to B-tree index maintenance
        - SELECT by address: O(log n + k) where k is result set size
        - DELETE by block range: O(log n + m) where m is deleted rows
        """
        with self._lock:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS address_txs (
                    address TEXT NOT NULL,
                    block_index INTEGER NOT NULL,
                    tx_index INTEGER NOT NULL,
                    txid TEXT NOT NULL,
                    is_sender BOOLEAN NOT NULL,
                    amount INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    PRIMARY KEY (address, block_index, tx_index)
                )
            """)

            # B-tree index for O(log n) address lookups
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_address ON address_txs(address)"
            )

            # Index for transaction hash lookups (deduplication, explorer queries)
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_txid ON address_txs(txid)"
            )

            # Composite index for efficient block-range deletion during reorg
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_block_range ON address_txs(block_index, tx_index)"
            )

            self.db.commit()

    def index_transaction(
        self,
        tx: Transaction,
        block_index: int,
        tx_index: int,
        timestamp: float
    ) -> None:
        """
        Index a transaction for both sender and recipient addresses.

        Creates two index entries per transaction:
        1. Sender entry: negative amount (outgoing)
        2. Recipient entry: positive amount (incoming)

        This allows efficient balance calculation and history queries.

        Args:
            tx: Transaction to index
            block_index: Block height containing this transaction
            tx_index: Position of transaction within the block
            timestamp: Block timestamp for chronological ordering

        Thread Safety:
            Protected by lock, safe to call concurrently with other operations.

        Note:
            Uses INSERT OR REPLACE to handle reindexing during recovery.
            Idempotent: reindexing same transaction multiple times is safe.
        """
        if not tx.txid:
            # Calculate txid if missing (shouldn't happen in production)
            tx.txid = tx.calculate_hash()

        entries = []

        # Index sender (outgoing transaction, negative amount)
        if tx.sender:
            entries.append((
                tx.sender,
                block_index,
                tx_index,
                tx.txid,
                True,  # is_sender
                -int(tx.amount),  # Negative for outgoing
                timestamp
            ))

        # Index recipient (incoming transaction, positive amount)
        if tx.recipient:
            entries.append((
                tx.recipient,
                block_index,
                tx_index,
                tx.txid,
                False,  # is_sender
                int(tx.amount),
                timestamp
            ))

        with self._lock:
            try:
                self.db.executemany(
                    """INSERT OR REPLACE INTO address_txs
                       (address, block_index, tx_index, txid, is_sender, amount, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    entries
                )
                # Don't commit here - let caller control transaction boundaries
            except sqlite3.Error as e:
                self.logger.error(
                    "Failed to index transaction",
                    txid=tx.txid,
                    block_index=block_index,
                    error=str(e)
                )
                raise

    def get_transactions(
        self,
        address: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Tuple[int, int, str, bool, int, float]]:
        """
        Retrieve transaction history for an address with pagination.

        Returns transactions in reverse chronological order (newest first).

        Args:
            address: Address to query
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of tuples: (block_index, tx_index, txid, is_sender, amount, timestamp)

        Performance:
            O(log n + k) where n is total indexed transactions, k is result set size.
            The B-tree index on 'address' enables log(n) seek, then k results are scanned.

        Security:
            Uses parameterized query to prevent SQL injection.
        """
        with self._lock:
            try:
                cursor = self.db.execute(
                    """SELECT block_index, tx_index, txid, is_sender, amount, timestamp
                       FROM address_txs
                       WHERE address = ?
                       ORDER BY block_index DESC, tx_index DESC
                       LIMIT ? OFFSET ?""",
                    (address, limit, offset)
                )
                return cursor.fetchall()
            except sqlite3.Error as e:
                self.logger.error(
                    "Failed to query address transactions",
                    address=address,
                    error=str(e)
                )
                return []

    def get_transaction_count(self, address: str) -> int:
        """
        Count total transactions for an address.

        Args:
            address: Address to count transactions for

        Returns:
            Total number of transactions (both sent and received)

        Performance:
            O(log n) using index-only scan, no table access required.
        """
        with self._lock:
            try:
                cursor = self.db.execute(
                    "SELECT COUNT(*) FROM address_txs WHERE address = ?",
                    (address,)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
            except sqlite3.Error as e:
                self.logger.error(
                    "Failed to count address transactions",
                    address=address,
                    error=str(e)
                )
                return 0

    def get_balance_changes(self, address: str) -> int:
        """
        Calculate net balance from indexed transactions.

        WARNING: This is a convenience method but does NOT replace proper UTXO-based
        balance calculation. Use UTXOManager.get_balance() for authoritative balance.

        This method is useful for:
        - Quick balance estimates
        - Detecting balance changes
        - Auditing and reconciliation

        Args:
            address: Address to calculate balance for

        Returns:
            Net balance change from all indexed transactions

        Performance:
            O(n) where n is number of transactions for this address.
            SQLite SUM() optimization makes this faster than manual iteration.
        """
        with self._lock:
            try:
                cursor = self.db.execute(
                    "SELECT SUM(amount) FROM address_txs WHERE address = ?",
                    (address,)
                )
                result = cursor.fetchone()
                return result[0] if result and result[0] is not None else 0
            except sqlite3.Error as e:
                self.logger.error(
                    "Failed to calculate balance changes",
                    address=address,
                    error=str(e)
                )
                return 0

    def rollback_to_block(self, block_index: int) -> None:
        """
        Remove all indexed transactions from blocks >= block_index.

        Used during chain reorganizations to revert index to a specific point.

        Args:
            block_index: Keep all transactions in blocks < block_index, remove rest

        Example:
            If chain reorganizes from height 100 back to 95:
            rollback_to_block(95) removes all transactions from blocks 95-99

        Thread Safety:
            Protected by lock, safe to call during concurrent operations.
        """
        with self._lock:
            try:
                cursor = self.db.execute(
                    "DELETE FROM address_txs WHERE block_index >= ?",
                    (block_index,)
                )
                deleted_count = cursor.rowcount
                self.logger.info(
                    "Rolled back address index",
                    to_block=block_index,
                    deleted_rows=deleted_count
                )
            except sqlite3.Error as e:
                self.logger.error(
                    "Failed to rollback address index",
                    to_block=block_index,
                    error=str(e)
                )
                raise

    def commit(self) -> None:
        """
        Commit pending index updates to disk.

        Should be called after successful block addition to persist index changes.
        If not called, changes will be rolled back on next connection.
        """
        with self._lock:
            try:
                self.db.commit()
            except sqlite3.Error as e:
                self.logger.error("Failed to commit address index", error=str(e))
                raise

    def rollback(self) -> None:
        """
        Rollback uncommitted index changes.

        Used when block addition fails to revert index to last committed state.
        """
        with self._lock:
            try:
                self.db.rollback()
            except sqlite3.Error as e:
                self.logger.error("Failed to rollback address index", error=str(e))
                raise

    def rebuild_from_chain(self, blockchain: Any) -> None:
        """
        Rebuild entire index from blockchain.

        Used for:
        - Initial index creation on existing chains
        - Recovery from index corruption
        - Migration from old index format

        Args:
            blockchain: Blockchain instance to index

        Performance:
            O(n * m) where n is number of blocks, m is avg transactions per block.
            This is acceptable since it's a one-time operation.

        Note:
            Clears existing index before rebuilding.
        """
        self.logger.info("Rebuilding address index from chain", chain_length=len(blockchain.chain))

        with self._lock:
            try:
                # Clear existing index
                self.db.execute("DELETE FROM address_txs")

                # Index all blocks
                indexed_txs = 0
                for block_index in range(len(blockchain.chain)):
                    block = blockchain.storage.load_block_from_disk(block_index)
                    if not block:
                        continue

                    for tx_index, tx in enumerate(block.transactions):
                        self.index_transaction(
                            tx,
                            block_index,
                            tx_index,
                            block.timestamp
                        )
                        indexed_txs += 1

                    # Commit periodically to avoid large transactions
                    if (block_index + 1) % 1000 == 0:
                        self.db.commit()
                        self.logger.info(
                            "Index rebuild progress",
                            blocks=block_index + 1,
                            transactions=indexed_txs
                        )

                self.db.commit()
                self.logger.info(
                    "Address index rebuild complete",
                    blocks=len(blockchain.chain),
                    transactions=indexed_txs
                )
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                self.db.rollback()
                self.logger.error("Failed to rebuild address index", error=str(e))
                raise

    def close(self) -> None:
        """Close database connection and release resources."""
        with self._lock:
            try:
                self.db.close()
                self.logger.info("Address index closed")
            except sqlite3.Error as e:
                self.logger.error("Error closing address index", error=str(e))

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
