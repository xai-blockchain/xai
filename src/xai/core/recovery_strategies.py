from __future__ import annotations

"""
XAI Blockchain - Recovery Strategies and Backup Management

Comprehensive recovery mechanisms:
- Blockchain backup and restoration
- State rollback strategies
- Transaction preservation
- Corruption recovery
- Network partition handling
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime
from typing import Any

class BlockchainBackup:
    """
    Blockchain backup and restoration manager.

    Handles creating, storing, and restoring blockchain backups
    with integrity validation and cleanup.
    """

    def __init__(self, backup_dir: str = "data/backups") -> None:
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory for storing backups
        """
        self.backup_dir: str = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

        self.logger: logging.Logger = logging.getLogger("blockchain_backup")
        self.logger.setLevel(logging.INFO)

    def create_backup(self, blockchain: Any, name: str | None = None) -> str:
        """
        Create comprehensive blockchain backup.

        Args:
            blockchain: Blockchain instance to backup
            name: Optional backup name (timestamp used if not provided)

        Returns:
            Path to created backup file
        """
        if name is None:
            name = f"backup_{int(time.time())}"

        backup_path = os.path.join(self.backup_dir, f"{name}.json")

        # Create backup data structure
        backup_data = {
            "timestamp": time.time(),
            "chain_height": len(blockchain.chain),
            "chain": [block.to_dict() for block in blockchain.chain],
            "pending_transactions": [tx.to_dict() for tx in blockchain.pending_transactions],
            "utxo_set": blockchain.utxo_set,
            "difficulty": blockchain.difficulty,
            "metadata": {
                "latest_hash": blockchain.get_latest_block().hash,
                "total_supply": (
                    blockchain.get_total_circulating_supply()
                    if hasattr(blockchain, "get_total_circulating_supply")
                    else 0
                ),
            },
        }

        # Write backup to file
        with open(backup_path, "w") as f:
            json.dump(backup_data, f, indent=2)

        self.logger.info(f"Backup created: {backup_path} (chain height: {len(blockchain.chain)})")
        return backup_path

    def restore_backup(self, backup_path: str) -> tuple[bool, Dict | None, str | None]:
        """
        Load backup data from file.

        Args:
            backup_path: Path to backup file

        Returns:
            Tuple of (success, backup_data, error_message)
        """
        try:
            with open(backup_path, "r") as f:
                backup_data = json.load(f)

            self.logger.info(f"Backup loaded: {backup_path}")
            return True, backup_data, None
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to load backup: {e}")
            return False, None, str(e)

    def list_backups(self) -> list[dict[str, Any]]:
        """
        List all available backups with metadata.

        Returns:
            List of backup information dictionaries
        """
        backups: list[dict[str, Any]] = []

        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.backup_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)

                    backups.append(
                        {
                            "name": filename,
                            "path": filepath,
                            "timestamp": data.get("timestamp"),
                            "chain_height": data.get("chain_height"),
                            "size": os.path.getsize(filepath),
                        }
                    )
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    self.logger.warning(f"Could not read backup {filename}: {e}")

        # Sort by timestamp, newest first
        backups.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return backups

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Remove old backups, keeping only the most recent.

        Args:
            keep_count: Number of backups to keep

        Returns:
            Number of backups removed
        """
        backups = self.list_backups()
        removed_count = 0

        # Remove old backups
        for backup in backups[keep_count:]:
            try:
                os.remove(backup["path"])
                removed_count += 1
                self.logger.info(f"Removed old backup: {backup['name']}")
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                self.logger.warning(f"Failed to remove backup {backup['name']}: {e}")

        return removed_count

    def validate_backup(self, backup_data: Dict) -> tuple[bool, list[str]]:
        """
        Validate backup data integrity before restoration.

        Args:
            backup_data: Backup data to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors: list[str] = []

        # Check required fields
        required_fields = ["chain", "utxo_set", "timestamp"]
        for field in required_fields:
            if field not in backup_data:
                errors.append(f"Missing required field: {field}")

        # Check chain is not empty
        if "chain" in backup_data and len(backup_data["chain"]) == 0:
            errors.append("Backup contains empty chain")

        # Check timestamp is reasonable (not from future)
        if "timestamp" in backup_data:
            backup_time = backup_data["timestamp"]
            if backup_time > time.time() + 300:  # 5 minutes tolerance
                errors.append("Backup timestamp is from the future")

        return len(errors) == 0, errors

class StateRecovery:
    """
    State recovery and rollback mechanisms.

    Handles applying backups to blockchain state and
    preserving/restoring pending transactions.
    """

    def __init__(self) -> None:
        """Initialize state recovery manager."""
        self.logger: logging.Logger = logging.getLogger("state_recovery")
        self.logger.setLevel(logging.INFO)

    def apply_backup(self, blockchain: Any, backup_data: Dict) -> tuple[bool, str | None]:
        """
        Apply backup data to blockchain.

        Args:
            blockchain: Blockchain instance to restore
            backup_data: Validated backup data

        Returns:
            Tuple of (success, error_message)
        """
        try:
            from xai.core.blockchain import Block, Transaction

            # Rebuild chain from backup
            new_chain: list[Any] = []
            for block_data in backup_data["chain"]:
                # Recreate transactions
                transactions: list[Any] = []
                for tx_data in block_data["transactions"]:
                    tx = Transaction(
                        tx_data["sender"], tx_data["recipient"], tx_data["amount"], tx_data["fee"]
                    )
                    tx.txid = tx_data["txid"]
                    tx.signature = tx_data.get("signature")
                    tx.public_key = tx_data.get("public_key")
                    tx.timestamp = tx_data["timestamp"]
                    tx.tx_type = tx_data.get("tx_type", "normal")
                    tx.nonce = tx_data.get("nonce")
                    transactions.append(tx)

                # Recreate block
                block = Block(
                    block_data["index"],
                    transactions,
                    block_data["previous_hash"],
                    block_data["difficulty"],
                )
                block.timestamp = block_data["timestamp"]
                block.nonce = block_data["nonce"]
                block.merkle_root = block_data["merkle_root"]
                block.hash = block_data["hash"]

                new_chain.append(block)

            # Apply new chain
            blockchain.chain = new_chain

            # Restore UTXO set
            blockchain.utxo_set = backup_data["utxo_set"]

            # Clear pending transactions (will be restored separately)
            blockchain.pending_transactions = []

            self.logger.info(f"Backup applied successfully (chain height: {len(new_chain)})")
            return True, None

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to apply backup: {e}")
            return False, str(e)

    def preserve_pending_transactions(
        self, blockchain: Any, filepath: str = "data/recovery/pending_transactions.json"
    ) -> tuple[bool, str | None]:
        """
        Preserve pending transactions to disk.

        Args:
            blockchain: Blockchain instance
            filepath: Path to save transactions

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Serialize pending transactions
            preserved_txs = [tx.to_dict() for tx in blockchain.pending_transactions]

            # Write to file
            with open(filepath, "w") as f:
                json.dump(preserved_txs, f, indent=2)

            self.logger.info(f"Preserved {len(preserved_txs)} pending transactions")
            return True, None

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to preserve transactions: {e}")
            return False, str(e)

    def restore_pending_transactions(
        self, blockchain: Any, filepath: str = "data/recovery/pending_transactions.json"
    ) -> tuple[bool, str | None]:
        """
        Restore preserved pending transactions.

        Args:
            blockchain: Blockchain instance
            filepath: Path to load transactions from

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not os.path.exists(filepath):
                self.logger.info("No preserved transactions to restore")
                return True, None

            # Load preserved transactions
            with open(filepath, "r") as f:
                preserved_txs = json.load(f)

            # Recreate transaction objects
            from xai.core.blockchain import Transaction

            restored_count = 0
            for tx_data in preserved_txs:
                tx = Transaction(
                    tx_data["sender"], tx_data["recipient"], tx_data["amount"], tx_data["fee"]
                )
                tx.txid = tx_data["txid"]
                tx.signature = tx_data["signature"]
                tx.public_key = tx_data.get("public_key")
                tx.timestamp = tx_data["timestamp"]

                # Re-validate and add
                if blockchain.validate_transaction(tx):
                    blockchain.pending_transactions.append(tx)
                    restored_count += 1

            self.logger.info(f"Restored {restored_count}/{len(preserved_txs)} pending transactions")
            return True, None

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to restore transactions: {e}")
            return False, str(e)

class CorruptionRecovery:
    """
    Specialized recovery for blockchain corruption.

    Coordinates detection, backup selection, and restoration
    when corruption is detected.
    """

    def __init__(self, backup_manager: BlockchainBackup) -> None:
        """
        Initialize corruption recovery.

        Args:
            backup_manager: BlockchainBackup instance
        """
        self.backup_manager: BlockchainBackup = backup_manager
        self.state_recovery: StateRecovery = StateRecovery()
        self.logger: logging.Logger = logging.getLogger("corruption_recovery")
        self.logger.setLevel(logging.INFO)

    def recover_from_corruption(
        self, blockchain: Any, corruption_issues: list[str]
    ) -> tuple[bool, str | None]:
        """
        Attempt to recover from blockchain corruption.

        Args:
            blockchain: Corrupted blockchain instance
            corruption_issues: List of detected corruption issues

        Returns:
            Tuple of (success, error_message)
        """
        self.logger.error(f"Recovering from corruption: {len(corruption_issues)} issues detected")

        try:
            # 1. Preserve pending transactions
            success, error = self.state_recovery.preserve_pending_transactions(blockchain)
            if not success:
                self.logger.warning(f"Could not preserve transactions: {error}")

            # 2. Find valid backups
            backups = self.backup_manager.list_backups()
            if not backups:
                return False, "No backups available for recovery"

            # 3. Try restoring backups (newest first)
            for backup in backups:
                self.logger.info(f"Attempting restore from {backup['name']}...")

                # Load backup
                success, backup_data, error = self.backup_manager.restore_backup(backup["path"])
                if not success:
                    self.logger.warning(f"Could not load backup: {error}")
                    continue

                # Validate backup
                is_valid, validation_errors = self.backup_manager.validate_backup(backup_data)
                if not is_valid:
                    self.logger.warning(f"Backup validation failed: {validation_errors}")
                    continue

                # Apply backup
                success, error = self.state_recovery.apply_backup(blockchain, backup_data)
                if not success:
                    self.logger.warning(f"Could not apply backup: {error}")
                    continue

                # Restore pending transactions
                self.state_recovery.restore_pending_transactions(blockchain)

                self.logger.info(f"Successfully recovered from backup: {backup['name']}")
                return True, None

            return False, "All backup restoration attempts failed"

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Corruption recovery failed: {e}")
            return False, str(e)

class NetworkPartitionRecovery:
    """
    Recovery strategies for network partition scenarios.

    Handles reconnection attempts and graceful degradation
    when network connectivity is lost.
    """

    def __init__(self) -> None:
        """Initialize network partition recovery."""
        self.logger: logging.Logger = logging.getLogger("network_recovery")
        self.logger.setLevel(logging.INFO)

    def attempt_reconnection(
        self, node: Any, max_attempts: int = 3, retry_delay: float = 5.0
    ) -> tuple[bool, str | None]:
        """
        Attempt to reconnect to network after partition.

        Args:
            node: Node instance
            max_attempts: Maximum reconnection attempts
            retry_delay: Delay between attempts in seconds

        Returns:
            Tuple of (success, error_message)
        """
        self.logger.info("Attempting network reconnection...")

        for attempt in range(max_attempts):
            try:
                # Try to sync with network
                if hasattr(node, "sync_with_network"):
                    node.sync_with_network()
                    self.logger.info(f"Reconnected on attempt {attempt + 1}")
                    return True, None
                else:
                    self.logger.warning("Node does not support network sync")
                    return False, "Network sync not supported"

            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                self.logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(retry_delay)

        return False, f"Reconnection failed after {max_attempts} attempts"

    def enter_degraded_mode(self, node: Any) -> tuple[bool, str | None]:
        """
        Enter degraded operation mode (offline).

        Args:
            node: Node instance

        Returns:
            Tuple of (success, error_message)
        """
        self.logger.warning("Entering degraded mode (offline operation)")

        try:
            # Disable network-dependent features
            if hasattr(node, "disable_network_features"):
                node.disable_network_features()

            self.logger.info("Now operating in degraded mode")
            return True, None

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Failed to enter degraded mode: {e}")
            return False, str(e)

class GracefulShutdown:
    """
    Graceful shutdown coordinator.

    Ensures clean shutdown with backup creation and
    transaction preservation.
    """

    def __init__(self, backup_manager: BlockchainBackup) -> None:
        """
        Initialize graceful shutdown manager.

        Args:
            backup_manager: BlockchainBackup instance
        """
        self.backup_manager: BlockchainBackup = backup_manager
        self.state_recovery: StateRecovery = StateRecovery()
        self.logger: logging.Logger = logging.getLogger("graceful_shutdown")
        self.logger.setLevel(logging.INFO)

    def shutdown(
        self, blockchain: Any, node: Any | None = None, reason: str = "manual"
    ) -> tuple[bool, str | None]:
        """
        Perform graceful shutdown.

        Args:
            blockchain: Blockchain instance
            node: Optional node instance
            reason: Shutdown reason

        Returns:
            Tuple of (success, error_message)
        """
        self.logger.info(f"Initiating graceful shutdown: {reason}")

        try:
            # 1. Stop mining if node exists
            if node and hasattr(node, "stop_mining"):
                self.logger.info("Stopping mining...")
                node.stop_mining()

            # 2. Preserve pending transactions
            self.logger.info("Preserving pending transactions...")
            self.state_recovery.preserve_pending_transactions(blockchain)

            # 3. Create final backup
            self.logger.info("Creating final backup...")
            backup_path = self.backup_manager.create_backup(
                blockchain, name=f"shutdown_{int(time.time())}"
            )
            self.logger.info(f"Backup created: {backup_path}")

            # 4. Cleanup old backups
            removed = self.backup_manager.cleanup_old_backups(keep_count=10)
            self.logger.info(f"Cleaned up {removed} old backups")

            self.logger.info("Graceful shutdown complete")
            return True, None

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            self.logger.error(f"Error during shutdown: {e}")
            return False, str(e)
