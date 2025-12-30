"""
Blockchain Write-Ahead Log (WAL) - Production Implementation

Manages Write-Ahead Logging for chain reorganizations to enable crash recovery.
If a node crashes mid-reorg, the WAL allows detection and recovery on restart.
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Any

from xai.utils.secure_io import SECURE_FILE_MODE

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain


class BlockchainWAL:
    """
    Write-Ahead Log manager for blockchain reorganizations.

    Provides crash recovery for chain reorganizations by recording reorg
    operations to disk before they're applied. If the node crashes mid-reorg,
    the WAL enables detection and recovery on restart.
    """

    def __init__(self, blockchain: Blockchain) -> None:
        """
        Initialize the WAL manager.

        Args:
            blockchain: The parent Blockchain instance
        """
        self.blockchain = blockchain

    def write_reorg_wal(
        self,
        old_tip: str | None,
        new_tip: str | None,
        fork_point: int | None
    ) -> dict[str, Any]:
        """
        Write a WAL entry recording the start of a chain reorganization.

        This enables crash recovery: if the node crashes mid-reorg, on restart
        we can detect the incomplete reorg and either complete it or roll back.

        Args:
            old_tip: Hash of the old chain tip
            new_tip: Hash of the new chain tip
            fork_point: Block height where chains diverged

        Returns:
            WAL entry dictionary
        """
        wal_entry = {
            "type": "REORG_BEGIN",
            "old_tip": old_tip,
            "new_tip": new_tip,
            "fork_point": fork_point,
            "timestamp": time.time(),
            "status": "in_progress",
        }

        try:
            # SECURITY: Use explicit permissions to prevent data leakage
            fd = os.open(self.blockchain.reorg_wal_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SECURE_FILE_MODE)
            with os.fdopen(fd, "w") as f:
                json.dump(wal_entry, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            self.blockchain.logger.info(
                "WAL: Recorded reorg begin",
                extra={
                    "event": "wal.reorg_begin",
                    "old_tip": old_tip,
                    "new_tip": new_tip,
                    "fork_point": fork_point,
                }
            )
        except (OSError, IOError, ValueError) as e:
            self.blockchain.logger.error(
                "WAL: Failed to write reorg entry",
                extra={"event": "wal.write_failed", "error": str(e), "error_type": type(e).__name__}
            )

        return wal_entry

    def commit_reorg_wal(self, wal_entry: dict[str, Any]) -> None:
        """
        Mark a WAL entry as committed (reorg completed successfully).

        Args:
            wal_entry: The WAL entry to commit
        """
        try:
            wal_entry["status"] = "committed"
            wal_entry["commit_timestamp"] = time.time()

            # SECURITY: Use explicit permissions to prevent data leakage
            fd = os.open(self.blockchain.reorg_wal_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SECURE_FILE_MODE)
            with os.fdopen(fd, "w") as f:
                json.dump(wal_entry, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # After successful commit, remove the WAL file
            # (No recovery needed - reorg completed successfully)
            if os.path.exists(self.blockchain.reorg_wal_path):
                os.remove(self.blockchain.reorg_wal_path)

            self.blockchain.logger.info(
                "WAL: Reorg committed and WAL cleared",
                extra={"event": "wal.reorg_committed"}
            )
        except (OSError, IOError, ValueError) as e:
            self.blockchain.logger.error(
                "WAL: Failed to commit reorg",
                extra={"event": "wal.commit_failed", "error": str(e), "error_type": type(e).__name__}
            )

    def rollback_reorg_wal(self, wal_entry: dict[str, Any]) -> None:
        """
        Mark a WAL entry as rolled back (reorg failed and was reverted).

        Args:
            wal_entry: The WAL entry to roll back
        """
        try:
            wal_entry["status"] = "rolled_back"
            wal_entry["rollback_timestamp"] = time.time()

            # SECURITY: Use explicit permissions to prevent data leakage
            fd = os.open(self.blockchain.reorg_wal_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SECURE_FILE_MODE)
            with os.fdopen(fd, "w") as f:
                json.dump(wal_entry, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # After successful rollback, remove the WAL file
            # (State has been restored to pre-reorg)
            if os.path.exists(self.blockchain.reorg_wal_path):
                os.remove(self.blockchain.reorg_wal_path)

            self.blockchain.logger.info(
                "WAL: Reorg rolled back and WAL cleared",
                extra={"event": "wal.reorg_rolled_back"}
            )
        except (OSError, IOError, ValueError) as e:
            self.blockchain.logger.error(
                "WAL: Failed to record rollback",
                extra={"event": "wal.rollback_failed", "error": str(e), "error_type": type(e).__name__}
            )

    def recover_from_incomplete_reorg(self) -> None:
        """
        Check for incomplete reorg on node startup and recover.

        If a reorg WAL entry exists with status "in_progress", the node
        crashed mid-reorg. We don't know if the reorg was partially applied,
        so the safest approach is to rebuild all state from disk.

        This is called during Blockchain.__init__() to ensure recovery
        happens before any operations begin.
        """
        if not os.path.exists(self.blockchain.reorg_wal_path):
            # No incomplete reorg - normal startup
            return

        try:
            with open(self.blockchain.reorg_wal_path, "r") as f:
                wal_entry = json.load(f)

            if wal_entry.get("status") == "in_progress":
                self.blockchain.logger.warning(
                    "Detected incomplete chain reorganization from previous session. "
                    "Node may have crashed mid-reorg. Blockchain state will be rebuilt from disk.",
                    extra={
                        "event": "wal.incomplete_reorg_detected",
                        "old_tip": wal_entry.get("old_tip"),
                        "new_tip": wal_entry.get("new_tip"),
                        "fork_point": wal_entry.get("fork_point"),
                        "timestamp": wal_entry.get("timestamp"),
                    }
                )

                # Clear the WAL file - we'll rebuild state from disk
                os.remove(self.blockchain.reorg_wal_path)

                # Log the recovery action
                self.blockchain.logger.info(
                    "WAL: Cleared incomplete reorg entry. State will be rebuilt from persistent storage.",
                    extra={"event": "wal.recovery_initiated"}
                )
            else:
                # WAL entry is committed or rolled back - safe to remove
                os.remove(self.blockchain.reorg_wal_path)
                self.blockchain.logger.debug("WAL: Removed stale reorg entry")

        except (OSError, IOError, ValueError, KeyError) as e:
            self.blockchain.logger.error(
                "WAL: Failed to recover from incomplete reorg - manual intervention may be required",
                extra={"event": "wal.recovery_failed", "error": str(e), "error_type": type(e).__name__}
            )
