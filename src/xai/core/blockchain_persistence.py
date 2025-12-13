"""
XAI Blockchain - Persistent Storage System

Provides secure, reliable blockchain persistence with:
- Atomic writes (temp file + rename)
- Checksum verification
- Auto-recovery from corruption
- Automated backups
- Checkpoint system every 1000 blocks
"""

import json
import hashlib
import os
import time
import shutil
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from threading import Lock

from .blockchain_exceptions import (
    DatabaseError,
    StorageError,
    CorruptedDataError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class BlockchainStorageConfig:
    """Configuration for blockchain storage"""

    # Data directory
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    # Storage files
    BLOCKCHAIN_FILE = os.path.join(DATA_DIR, "blockchain.json")
    BACKUP_DIR = os.path.join(DATA_DIR, "backups")
    CHECKPOINT_DIR = os.path.join(DATA_DIR, "checkpoints")

    # Checkpoint interval (blocks)
    CHECKPOINT_INTERVAL = 1000

    # Max backup files to keep
    MAX_BACKUPS = 10

    # Auto-save interval (blocks)
    AUTO_SAVE_INTERVAL = 1


class BlockchainStorage:
    """
    Blockchain persistent storage with data integrity and recovery

    Features:
    - Atomic writes (write to temp, then rename)
    - SHA-256 checksums for data integrity
    - Automatic backups on save
    - Recovery from corrupted data
    - Checkpoint system every 1000 blocks
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize blockchain storage

        Args:
            data_dir: Custom data directory (uses default if None)
        """
        # Setup directories
        if data_dir:
            self.data_dir = data_dir
            self.blockchain_file = os.path.join(data_dir, "blockchain.json")
            self.backup_dir = os.path.join(data_dir, "backups")
            self.checkpoint_dir = os.path.join(data_dir, "checkpoints")
        else:
            self.data_dir = BlockchainStorageConfig.DATA_DIR
            self.blockchain_file = BlockchainStorageConfig.BLOCKCHAIN_FILE
            self.backup_dir = BlockchainStorageConfig.BACKUP_DIR
            self.checkpoint_dir = BlockchainStorageConfig.CHECKPOINT_DIR

        # Create directories
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        # Thread safety
        self.lock = Lock()

        # Metadata file
        self.metadata_file = os.path.join(self.data_dir, "blockchain_metadata.json")

    def _calculate_checksum(self, data: str) -> str:
        """
        Calculate SHA-256 checksum of data

        Args:
            data: Data string to checksum

        Returns:
            str: Hex checksum
        """
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _verify_checksum(self, data: str, expected_checksum: str) -> bool:
        """
        Verify data checksum

        Args:
            data: Data to verify
            expected_checksum: Expected checksum

        Returns:
            bool: True if checksum matches
        """
        actual_checksum = self._calculate_checksum(data)
        return actual_checksum == expected_checksum

    def save_to_disk(self, blockchain_data: dict, create_backup: bool = True) -> Tuple[bool, str]:
        """
        Save blockchain to disk with atomic write

        Uses temp file + rename for atomicity.
        Creates backup before overwriting.

        Args:
            blockchain_data: Blockchain dictionary to save
            create_backup: Whether to create backup

        Returns:
            tuple: (success: bool, message: str)
        """
        with self.lock:
            try:
                # Serialize blockchain data
                json_data = json.dumps(blockchain_data, indent=2, sort_keys=True)

                # Calculate checksum
                checksum = self._calculate_checksum(json_data)

                # Create metadata
                metadata = {
                    "timestamp": time.time(),
                    "block_height": len(blockchain_data.get("chain", [])),
                    "checksum": checksum,
                    "version": "1.0",
                }

                # Package data with metadata
                package = {"metadata": metadata, "blockchain": blockchain_data}

                package_json = json.dumps(package, indent=2, sort_keys=True)

                # Create backup if requested and file exists
                if create_backup and os.path.exists(self.blockchain_file):
                    self._create_backup()

                # Atomic write: write to temp file, then rename
                temp_file = self.blockchain_file + ".tmp"

                # Write to temp file
                with open(temp_file, "w") as f:
                    f.write(package_json)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk

                # Atomic rename
                if os.path.exists(self.blockchain_file):
                    os.replace(temp_file, self.blockchain_file)
                else:
                    os.rename(temp_file, self.blockchain_file)

                # Save metadata separately for quick access
                with open(self.metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)

                # Create checkpoint if needed
                block_height = metadata["block_height"]
                if block_height % BlockchainStorageConfig.CHECKPOINT_INTERVAL == 0:
                    self._create_checkpoint(blockchain_data, block_height)

                return (
                    True,
                    f"Blockchain saved successfully (height: {block_height}, checksum: {checksum[:8]}...)",
                )

            except (DatabaseError, StorageError, OSError, IOError, PermissionError) as e:
                logger.error(
                    "Failed to save blockchain to disk",
                    operation="save_to_disk",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return False, f"Failed to save blockchain: {str(e)}"

    def load_from_disk(self) -> Tuple[bool, Optional[dict], str]:
        """
        Load blockchain from disk with integrity checks

        Attempts recovery if corruption detected.

        Returns:
            tuple: (success: bool, blockchain_data: dict or None, message: str)
        """
        with self.lock:
            # Check if blockchain file exists
            if not os.path.exists(self.blockchain_file):
                return False, None, "No blockchain file found"

            try:
                # Read file
                with open(self.blockchain_file, "r") as f:
                    package = json.load(f)

                # Extract metadata and blockchain
                metadata = package.get("metadata", {})
                blockchain_data = package.get("blockchain", {})

                # Verify checksum
                blockchain_json = json.dumps(blockchain_data, indent=2, sort_keys=True)
                expected_checksum = metadata.get("checksum")

                if expected_checksum:
                    if not self._verify_checksum(blockchain_json, expected_checksum):
                        # Checksum failed - attempt recovery
                        print("WARNING: Checksum verification failed. Attempting recovery...")
                        return self._attempt_recovery()

                block_height = len(blockchain_data.get("chain", []))

                return (
                    True,
                    blockchain_data,
                    f"Blockchain loaded successfully (height: {block_height})",
                )

            except json.JSONDecodeError as e:
                # Corrupted JSON - attempt recovery
                logger.warning(
                    "JSON decode error during blockchain load",
                    error=str(e),
                    error_type="JSONDecodeError",
                )
                print(f"WARNING: JSON decode error: {e}. Attempting recovery...")
                return self._attempt_recovery()

            except (DatabaseError, StorageError, CorruptedDataError, OSError, IOError) as e:
                logger.error(
                    "Failed to load blockchain from disk",
                    operation="load_from_disk",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return False, None, f"Failed to load blockchain: {str(e)}"

    def _create_backup(self) -> bool:
        """
        Create timestamped backup of current blockchain

        Returns:
            bool: Success
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"blockchain_backup_{timestamp}.json")

            # Copy current blockchain to backup
            shutil.copy2(self.blockchain_file, backup_file)

            # Clean old backups
            self._cleanup_old_backups()

            return True

        except (OSError, IOError, PermissionError, shutil.Error) as e:
            logger.warning(
                "Failed to create blockchain backup",
                operation="_create_backup",
                error=str(e),
                error_type=type(e).__name__,
            )
            print(f"Warning: Failed to create backup: {e}")
            return False

    def _cleanup_old_backups(self):
        """Remove old backups, keeping only MAX_BACKUPS most recent"""
        try:
            # Get all backup files
            backups = [
                os.path.join(self.backup_dir, f)
                for f in os.listdir(self.backup_dir)
                if f.startswith("blockchain_backup_") and f.endswith(".json")
            ]

            # Sort by modification time
            backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            # Remove old backups
            for backup in backups[BlockchainStorageConfig.MAX_BACKUPS :]:
                os.remove(backup)

        except (OSError, IOError, PermissionError) as e:
            logger.warning(
                "Failed to cleanup old backups",
                operation="_cleanup_old_backups",
                error=str(e),
                error_type=type(e).__name__,
            )
            print(f"Warning: Failed to cleanup old backups: {e}")

    def _create_checkpoint(self, blockchain_data: dict, block_height: int):
        """
        Create checkpoint file for blockchain state

        Args:
            blockchain_data: Blockchain data to checkpoint
            block_height: Current block height
        """
        try:
            checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{block_height}.json")

            # Calculate checksum
            json_data = json.dumps(blockchain_data, indent=2, sort_keys=True)
            checksum = self._calculate_checksum(json_data)

            # Create checkpoint package
            checkpoint = {
                "block_height": block_height,
                "timestamp": time.time(),
                "checksum": checksum,
                "blockchain": blockchain_data,
            }

            # Write checkpoint
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint, f, indent=2)

            print(f"Checkpoint created at block {block_height}")

        except Exception as e:
            print(f"Warning: Failed to create checkpoint: {e}")

    def _attempt_recovery(self) -> Tuple[bool, Optional[dict], str]:
        """
        Attempt to recover blockchain from backups or checkpoints

        Recovery priority:
        1. Most recent backup
        2. Most recent checkpoint
        3. Genesis block only

        Returns:
            tuple: (success: bool, blockchain_data: dict or None, message: str)
        """
        print("Attempting blockchain recovery...")

        # Try backups first
        recovery_data = self._recover_from_backup()
        if recovery_data:
            return True, recovery_data, "Recovered from backup"

        # Try checkpoints
        recovery_data = self._recover_from_checkpoint()
        if recovery_data:
            return True, recovery_data, "Recovered from checkpoint"

        # All recovery attempts failed
        return False, None, "Recovery failed - no valid backup or checkpoint found"

    def _recover_from_backup(self) -> Optional[dict]:
        """
        Recover from most recent valid backup

        Returns:
            dict or None: Blockchain data if successful
        """
        try:
            # Get all backups sorted by time (newest first)
            backups = [
                os.path.join(self.backup_dir, f)
                for f in os.listdir(self.backup_dir)
                if f.startswith("blockchain_backup_") and f.endswith(".json")
            ]
            backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            # Try each backup
            for backup_file in backups:
                try:
                    with open(backup_file, "r") as f:
                        package = json.load(f)

                    # Check format
                    if "metadata" in package and "blockchain" in package:
                        # New format
                        blockchain_data = package.get("blockchain", {})
                        metadata = package.get("metadata", {})

                        # Verify checksum if available
                        blockchain_json = json.dumps(blockchain_data, indent=2, sort_keys=True)
                        expected_checksum = metadata.get("checksum")

                        if expected_checksum and self._verify_checksum(
                            blockchain_json, expected_checksum
                        ):
                            print(f"Recovered from backup: {os.path.basename(backup_file)}")
                            return blockchain_data
                        elif not expected_checksum:
                            # No checksum, accept anyway
                            print(
                                f"Recovered from backup (no checksum): {os.path.basename(backup_file)}"
                            )
                            return blockchain_data
                    else:
                        # Old format - direct blockchain data
                        blockchain_data = package
                        print(
                            f"Recovered from backup (old format): {os.path.basename(backup_file)}"
                        )
                        return blockchain_data

                except Exception as e:
                    print(f"Backup {os.path.basename(backup_file)} is invalid: {e}")
                    continue

            return None

        except Exception as e:
            print(f"Failed to recover from backups: {e}")
            return None

    def _recover_from_checkpoint(self) -> Optional[dict]:
        """
        Recover from most recent valid checkpoint

        Returns:
            dict or None: Blockchain data if successful
        """
        try:
            # Get all checkpoints sorted by block height (highest first)
            checkpoints = [
                os.path.join(self.checkpoint_dir, f)
                for f in os.listdir(self.checkpoint_dir)
                if f.startswith("checkpoint_") and f.endswith(".json")
            ]

            # Extract block heights and sort
            checkpoint_data = []
            for cp_file in checkpoints:
                try:
                    height = int(
                        os.path.basename(cp_file).replace("checkpoint_", "").replace(".json", "")
                    )
                    checkpoint_data.append((height, cp_file))
                except ValueError:
                    continue

            checkpoint_data.sort(reverse=True)

            # Try each checkpoint
            for height, checkpoint_file in checkpoint_data:
                try:
                    with open(checkpoint_file, "r") as f:
                        checkpoint = json.load(f)

                    blockchain_data = checkpoint.get("blockchain", {})
                    expected_checksum = checkpoint.get("checksum")

                    # Verify checksum
                    blockchain_json = json.dumps(blockchain_data, indent=2, sort_keys=True)

                    if expected_checksum and self._verify_checksum(
                        blockchain_json, expected_checksum
                    ):
                        print(f"Recovered from checkpoint at block {height}")
                        return blockchain_data

                except Exception as e:
                    print(f"Checkpoint {height} is invalid: {e}")
                    continue

            return None

        except Exception as e:
            print(f"Failed to recover from checkpoints: {e}")
            return None

    def restore_from_backup(self, backup_filename: str) -> Tuple[bool, Optional[dict], str]:
        """
        Manually restore from specific backup file

        Args:
            backup_filename: Name of backup file

        Returns:
            tuple: (success: bool, blockchain_data: dict or None, message: str)
        """
        with self.lock:
            backup_path = os.path.join(self.backup_dir, backup_filename)

            if not os.path.exists(backup_path):
                return False, None, f"Backup file not found: {backup_filename}"

            try:
                with open(backup_path, "r") as f:
                    package = json.load(f)

                # Check if this is the new format (with metadata) or old format
                if "metadata" in package and "blockchain" in package:
                    # New format
                    blockchain_data = package.get("blockchain", {})
                    metadata = package.get("metadata", {})

                    # Verify checksum if available
                    blockchain_json = json.dumps(blockchain_data, indent=2, sort_keys=True)
                    expected_checksum = metadata.get("checksum")

                    if expected_checksum and not self._verify_checksum(
                        blockchain_json, expected_checksum
                    ):
                        print(
                            f"Warning: Checksum mismatch for {backup_filename}, but continuing with restore"
                        )
                        # Don't fail on checksum mismatch for backups - they may be from recovery
                else:
                    # Old format - direct blockchain data
                    blockchain_data = package

                return True, blockchain_data, f"Restored from backup: {backup_filename}"

            except Exception as e:
                return False, None, f"Failed to restore from backup: {str(e)}"

    def list_backups(self) -> List[dict]:
        """
        List all available backups

        Returns:
            list: Backup information
        """
        try:
            backups = [
                f
                for f in os.listdir(self.backup_dir)
                if f.startswith("blockchain_backup_") and f.endswith(".json")
            ]

            backup_info = []
            for backup in backups:
                backup_path = os.path.join(self.backup_dir, backup)
                stat = os.stat(backup_path)

                # Try to get block height from metadata
                try:
                    with open(backup_path, "r") as f:
                        package = json.load(f)
                    block_height = package.get("metadata", {}).get("block_height", "unknown")
                except (IOError, json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Could not read backup metadata: {e}")
                    block_height = "unknown"

                backup_info.append(
                    {
                        "filename": backup,
                        "timestamp": datetime.fromtimestamp(stat.st_mtime).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "size_mb": stat.st_size / (1024 * 1024),
                        "block_height": block_height,
                    }
                )

            # Sort by timestamp (newest first)
            backup_info.sort(key=lambda x: x["timestamp"], reverse=True)

            return backup_info

        except Exception as e:
            print(f"Failed to list backups: {e}")
            return []

    def list_checkpoints(self) -> List[dict]:
        """
        List all available checkpoints

        Returns:
            list: Checkpoint information
        """
        try:
            checkpoints = [
                f
                for f in os.listdir(self.checkpoint_dir)
                if f.startswith("checkpoint_") and f.endswith(".json")
            ]

            checkpoint_info = []
            for checkpoint in checkpoints:
                checkpoint_path = os.path.join(self.checkpoint_dir, checkpoint)
                stat = os.stat(checkpoint_path)

                # Extract block height
                try:
                    height = int(checkpoint.replace("checkpoint_", "").replace(".json", ""))
                except ValueError:
                    height = "unknown"

                checkpoint_info.append(
                    {
                        "filename": checkpoint,
                        "block_height": height,
                        "timestamp": datetime.fromtimestamp(stat.st_mtime).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "size_mb": stat.st_size / (1024 * 1024),
                    }
                )

            # Sort by block height (highest first)
            checkpoint_info.sort(
                key=lambda x: x["block_height"] if isinstance(x["block_height"], int) else 0,
                reverse=True,
            )

            return checkpoint_info

        except Exception as e:
            print(f"Failed to list checkpoints: {e}")
            return []

    def get_metadata(self) -> Optional[dict]:
        """
        Get blockchain metadata

        Returns:
            dict or None: Metadata
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Failed to read metadata: {e}")
            return None

    def verify_integrity(self) -> Tuple[bool, str]:
        """
        Verify blockchain file integrity

        Returns:
            tuple: (valid: bool, message: str)
        """
        try:
            if not os.path.exists(self.blockchain_file):
                return False, "Blockchain file not found"

            # Load and verify
            with open(self.blockchain_file, "r") as f:
                package = json.load(f)

            metadata = package.get("metadata", {})
            blockchain_data = package.get("blockchain", {})

            # Verify checksum
            blockchain_json = json.dumps(blockchain_data, indent=2, sort_keys=True)
            expected_checksum = metadata.get("checksum")

            if not expected_checksum:
                return False, "No checksum found in metadata"

            if not self._verify_checksum(blockchain_json, expected_checksum):
                return False, "Checksum verification failed"

            block_height = len(blockchain_data.get("chain", []))

            return (
                True,
                f"Integrity verified (height: {block_height}, checksum: {expected_checksum[:8]}...)",
            )

        except Exception as e:
            return False, f"Integrity check failed: {str(e)}"
