"""
XAI Blockchain - Checkpoint System

Provides checkpoint/snapshot functionality for the blockchain to:
- Prevent deep reorganizations and long-range attacks
- Enable fast recovery on startup
- Save complete blockchain state at regular intervals
- Protect against blockchain corruption

A checkpoint includes:
- Block height and hash
- Complete UTXO set snapshot
- Timestamp and difficulty
- Chain metadata
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from datetime import datetime

from xai.utils.secure_io import SECURE_FILE_MODE
from typing import TYPE_CHECKING, Any

try:
    from xai.core.security.checkpoint_encryption import (
        encrypt_utxo_snapshot,
        decrypt_utxo_snapshot,
    )
    CHECKPOINT_ENCRYPTION_AVAILABLE = True
except ImportError:
    CHECKPOINT_ENCRYPTION_AVAILABLE = False
    encrypt_utxo_snapshot = lambda x: x  # type: ignore
    decrypt_utxo_snapshot = lambda x: x  # type: ignore

if TYPE_CHECKING:
    from xai.core.blockchain import Block
    from xai.core.transactions.utxo_manager import UTXOManager

# Configure logger for checkpoints
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class Checkpoint:
    """Represents a blockchain checkpoint at a specific height"""

    def __init__(
        self,
        height: int,
        block_hash: str,
        previous_hash: str,
        utxo_snapshot: dict[str, Any],
        timestamp: float,
        difficulty: int,
        total_supply: float,
        merkle_root: str,
        nonce: int = 0,
    ):
        self.height = height
        self.block_hash = block_hash
        self.previous_hash = previous_hash
        self.utxo_snapshot = utxo_snapshot
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.total_supply = total_supply
        self.merkle_root = merkle_root
        self.nonce = nonce
        self.checkpoint_hash = self._calculate_checkpoint_hash()

    def _calculate_checkpoint_hash(self) -> str:
        """Calculate a hash of the checkpoint for integrity verification"""
        checkpoint_data = {
            "height": self.height,
            "block_hash": self.block_hash,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "total_supply": self.total_supply,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
        }
        checkpoint_string = json.dumps(checkpoint_data, sort_keys=True)
        return hashlib.sha256(checkpoint_string.encode()).hexdigest()

    def to_dict(self, encrypt: bool = True) -> dict[str, Any]:
        """Convert checkpoint to dictionary for serialization.

        Args:
            encrypt: If True, encrypt UTXO snapshot data (default: True)

        Returns:
            Serialized checkpoint dictionary
        """
        # SECURITY: Encrypt UTXO snapshot to protect address balances at rest
        utxo_data = self.utxo_snapshot
        if encrypt and CHECKPOINT_ENCRYPTION_AVAILABLE:
            utxo_data = encrypt_utxo_snapshot(self.utxo_snapshot)

        return {
            "height": self.height,
            "block_hash": self.block_hash,
            "previous_hash": self.previous_hash,
            "utxo_snapshot": utxo_data,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "total_supply": self.total_supply,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "checkpoint_hash": self.checkpoint_hash,
            "created_at": datetime.fromtimestamp(time.time()).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Create checkpoint from dictionary.

        SECURITY: Automatically decrypts encrypted UTXO data if present.
        """
        # SECURITY: Decrypt UTXO snapshot if encrypted
        utxo_data = data["utxo_snapshot"]
        if isinstance(utxo_data, dict) and utxo_data.get("_encrypted"):
            utxo_data = decrypt_utxo_snapshot(utxo_data)

        checkpoint = cls(
            height=data["height"],
            block_hash=data["block_hash"],
            previous_hash=data["previous_hash"],
            utxo_snapshot=utxo_data,
            timestamp=data["timestamp"],
            difficulty=data["difficulty"],
            total_supply=data["total_supply"],
            merkle_root=data["merkle_root"],
            nonce=data.get("nonce", 0),
        )

        # Verify checkpoint hash if present
        if "checkpoint_hash" in data:
            if checkpoint.checkpoint_hash != data["checkpoint_hash"]:
                raise ValueError(
                    f"Checkpoint hash mismatch at height {data['height']}: "
                    f"expected {data['checkpoint_hash']}, got {checkpoint.checkpoint_hash}"
                )

        return checkpoint

    def verify_integrity(self) -> bool:
        """Verify checkpoint integrity"""
        return self.checkpoint_hash == self._calculate_checkpoint_hash()

class CheckpointManager:
    """
    Manages blockchain checkpoints for fast recovery and long-range attack protection.

    Key features:
    - Automatic checkpoint creation every N blocks
    - Manual checkpoint creation
    - Atomic checkpoint writes with backup
    - Automatic cleanup of old checkpoints
    - Fast blockchain recovery on startup
    - Protection against reorganization before last checkpoint
    """

    def __init__(
        self,
        data_dir: str = "data",
        checkpoint_interval: int = 1000,
        max_checkpoints: int = 10,
    ):
        """
        Initialize checkpoint manager.

        Args:
            data_dir: Base directory for blockchain data
            checkpoint_interval: Create checkpoint every N blocks (default: 1000)
            max_checkpoints: Maximum number of checkpoints to keep (default: 10)
        """
        self.data_dir = data_dir
        self.checkpoint_interval = checkpoint_interval
        self.max_checkpoints = max_checkpoints

        # Create checkpoints directory
        self.checkpoints_dir = os.path.join(data_dir, "checkpoints")
        os.makedirs(self.checkpoints_dir, exist_ok=True)

        # Track the latest checkpoint height to prevent deep reorgs
        self.latest_checkpoint_height: int | None = None
        self._load_latest_checkpoint_height()

        logger.info(
            f"Checkpoint manager initialized: interval={checkpoint_interval}, "
            f"max_checkpoints={max_checkpoints}, dir={self.checkpoints_dir}"
        )

    def _load_latest_checkpoint_height(self) -> None:
        """Load the height of the latest checkpoint"""
        checkpoints = self.list_checkpoints()
        if checkpoints:
            self.latest_checkpoint_height = max(checkpoints)
            logger.info(f"Latest checkpoint at height {self.latest_checkpoint_height}")
        else:
            self.latest_checkpoint_height = None
            logger.info("No checkpoints found")

    def should_create_checkpoint(self, block_height: int) -> bool:
        """
        Check if a checkpoint should be created at this block height.

        Args:
            block_height: Current block height

        Returns:
            True if checkpoint should be created
        """
        # Always create checkpoint at genesis
        if block_height == 0:
            return False  # Genesis is always saved

        # Create checkpoint at regular intervals
        if block_height > 0 and block_height % self.checkpoint_interval == 0:
            return True

        return False

    def create_checkpoint(
        self, block: "Block", utxo_manager: "UTXOManager", total_supply: float
    ) -> Checkpoint | None:
        """
        Create a checkpoint from the current blockchain state.

        Args:
            block: The block to checkpoint
            utxo_manager: UTXO manager for state snapshot
            total_supply: Current total supply

        Returns:
            Checkpoint object if successful, None otherwise
        """
        try:
            logger.info(f"Creating checkpoint at height {block.index}")

            # Create UTXO snapshot (thread-safe)
            utxo_snapshot = utxo_manager.snapshot()

            # Create checkpoint object
            checkpoint = Checkpoint(
                height=block.index,
                block_hash=block.hash,
                previous_hash=block.previous_hash,
                utxo_snapshot=utxo_snapshot,
                timestamp=block.timestamp,
                difficulty=block.difficulty,
                total_supply=total_supply,
                merkle_root=block.merkle_root,
                nonce=block.nonce,
            )

            # Save checkpoint atomically
            if self._save_checkpoint_atomic(checkpoint):
                self.latest_checkpoint_height = block.index
                logger.info(
                    f"Checkpoint created successfully at height {block.index}, "
                    f"hash: {checkpoint.checkpoint_hash[:16]}..."
                )

                # Cleanup old checkpoints
                self._cleanup_old_checkpoints()

                return checkpoint
            else:
                logger.error(f"Failed to save checkpoint at height {block.index}")
                return None

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(f"Error creating checkpoint at height {block.index}: {e}")
            return None

    def _save_checkpoint_atomic(self, checkpoint: Checkpoint) -> bool:
        """
        Save checkpoint atomically to prevent corruption.

        Uses write-to-temp-and-rename pattern for atomic writes.

        Args:
            checkpoint: Checkpoint to save

        Returns:
            True if successful, False otherwise
        """
        checkpoint_file = os.path.join(
            self.checkpoints_dir, f"cp_{checkpoint.height}.json"
        )
        temp_file = checkpoint_file + ".tmp"

        try:
            # Write to temporary file with secure permissions
            # SECURITY: Checkpoints contain UTXO data - prevent data leakage
            fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SECURE_FILE_MODE)
            with os.fdopen(fd, "w") as f:
                json.dump(checkpoint.to_dict(), f, indent=2)

            # Verify the written data
            with open(temp_file, "r") as f:
                saved_data = json.load(f)
                saved_checkpoint = Checkpoint.from_dict(saved_data)
                if not saved_checkpoint.verify_integrity():
                    logger.error(
                        f"Checkpoint integrity verification failed for height {checkpoint.height}"
                    )
                    os.remove(temp_file)
                    return False

            # Atomic rename (overwrites existing checkpoint if any)
            if os.path.exists(checkpoint_file):
                # Create backup of existing checkpoint
                backup_file = checkpoint_file + ".backup"
                shutil.copy2(checkpoint_file, backup_file)

            shutil.move(temp_file, checkpoint_file)

            # Remove backup after successful write
            backup_file = checkpoint_file + ".backup"
            if os.path.exists(backup_file):
                os.remove(backup_file)

            logger.debug(f"Checkpoint saved atomically: {checkpoint_file}")
            return True

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(f"Error saving checkpoint atomically: {e}")
            # Cleanup temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError as cleanup_error:
                    logger.debug(f"Could not cleanup temp file: {cleanup_error}")
            return False

    def load_checkpoint(self, height: int) -> Checkpoint | None:
        """
        Load a checkpoint from disk.

        Args:
            height: Block height of the checkpoint to load

        Returns:
            Checkpoint object if found and valid, None otherwise
        """
        checkpoint_file = os.path.join(self.checkpoints_dir, f"cp_{height}.json")

        if not os.path.exists(checkpoint_file):
            logger.debug(f"Checkpoint not found at height {height}")
            return None

        try:
            with open(checkpoint_file, "r") as f:
                data = json.load(f)

            checkpoint = Checkpoint.from_dict(data)

            # Verify checkpoint integrity
            if not checkpoint.verify_integrity():
                logger.error(
                    f"Checkpoint integrity verification failed for height {height}"
                )
                return None

            logger.info(f"Loaded checkpoint at height {height}")
            return checkpoint

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(f"Error loading checkpoint at height {height}: {e}")
            return None

    def load_latest_checkpoint(self) -> Checkpoint | None:
        """
        Load the most recent checkpoint.

        Returns:
            Latest checkpoint if found, None otherwise
        """
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            logger.info("No checkpoints available")
            return None

        # Try loading checkpoints from newest to oldest
        for height in sorted(checkpoints, reverse=True):
            checkpoint = self.load_checkpoint(height)
            if checkpoint:
                logger.info(f"Loaded latest checkpoint at height {height}")
                return checkpoint

        logger.warn("No valid checkpoints found")
        return None

    def list_checkpoints(self) -> list[int]:
        """
        List all available checkpoint heights.

        Returns:
            Sorted list of checkpoint heights
        """
        if not os.path.exists(self.checkpoints_dir):
            return []

        checkpoints = []
        for filename in os.listdir(self.checkpoints_dir):
            if filename.startswith("cp_") and filename.endswith(".json"):
                try:
                    height = int(filename[3:-5])  # Extract height from "cp_HEIGHT.json"
                    checkpoints.append(height)
                except ValueError:
                    continue

        return sorted(checkpoints)

    def _cleanup_old_checkpoints(self) -> None:
        """
        Remove old checkpoints, keeping only the most recent max_checkpoints.
        Implements automatic pruning while maintaining security.
        """
        checkpoints = self.list_checkpoints()

        if len(checkpoints) <= self.max_checkpoints:
            return

        # Keep only the newest max_checkpoints
        checkpoints_to_keep = sorted(checkpoints, reverse=True)[: self.max_checkpoints]
        checkpoints_to_remove = [h for h in checkpoints if h not in checkpoints_to_keep]

        # Prune old checkpoints
        pruned_count = 0
        for height in checkpoints_to_remove:
            if self._should_prune_checkpoint(height):
                checkpoint_file = os.path.join(self.checkpoints_dir, f"cp_{height}.json")
                try:
                    # Create backup before deletion (optional safety measure)
                    backup_dir = os.path.join(self.checkpoints_dir, "pruned")
                    os.makedirs(backup_dir, exist_ok=True)
                    backup_file = os.path.join(backup_dir, f"cp_{height}.json")

                    if os.path.exists(checkpoint_file):
                        # Move to pruned directory instead of deleting (for recovery)
                        shutil.move(checkpoint_file, backup_file)
                        pruned_count += 1
                        logger.info(f"Pruned checkpoint at height {height} (moved to {backup_dir})")
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    logger.warning(f"Failed to prune checkpoint at height {height}: {e}")

        if pruned_count > 0:
            logger.info(f"Pruned {pruned_count} checkpoints, keeping {len(checkpoints_to_keep)}")

    def reset_all_checkpoints(self) -> None:
        """Delete every checkpoint and reset tracking metadata."""
        try:
            shutil.rmtree(self.checkpoints_dir, ignore_errors=True)
            os.makedirs(self.checkpoints_dir, exist_ok=True)
            self.latest_checkpoint_height = None
            logger.info("All checkpoints removed; ledger will rebuild from genesis.")
        except (OSError, IOError) as exc:
            logger.error("Failed to reset checkpoint directory", error=str(exc))
            raise

    def _should_prune_checkpoint(self, height: int) -> bool:
        """
        Determine if a checkpoint should be pruned

        Args:
            height: Checkpoint height to evaluate

        Returns:
            True if checkpoint can be safely pruned
        """
        # Don't prune genesis checkpoint
        if height == 0:
            return False

        # Don't prune if it's one of the keep candidates
        checkpoints = self.list_checkpoints()
        checkpoints_to_keep = sorted(checkpoints, reverse=True)[: self.max_checkpoints]

        return height not in checkpoints_to_keep

    def is_before_checkpoint(self, height: int) -> bool:
        """
        Check if a block height is before the latest checkpoint.
        Used to prevent deep reorganizations.

        Args:
            height: Block height to check

        Returns:
            True if height is before the latest checkpoint
        """
        if self.latest_checkpoint_height is None:
            return False

        return height < self.latest_checkpoint_height

    def get_checkpoint_info(self) -> dict[str, Any]:
        """
        Get information about the checkpoint system.

        Returns:
            Dictionary with checkpoint statistics
        """
        checkpoints = self.list_checkpoints()

        return {
            "total_checkpoints": len(checkpoints),
            "latest_checkpoint_height": self.latest_checkpoint_height,
            "checkpoint_interval": self.checkpoint_interval,
            "max_checkpoints": self.max_checkpoints,
            "checkpoints_dir": self.checkpoints_dir,
            "available_checkpoints": checkpoints,
        }

    def delete_checkpoint(self, height: int) -> bool:
        """
        Delete a specific checkpoint.

        Args:
            height: Height of checkpoint to delete

        Returns:
            True if successful, False otherwise
        """
        checkpoint_file = os.path.join(self.checkpoints_dir, f"cp_{height}.json")

        if not os.path.exists(checkpoint_file):
            logger.warn(f"Checkpoint at height {height} does not exist")
            return False

        try:
            os.remove(checkpoint_file)
            logger.info(f"Deleted checkpoint at height {height}")

            # Update latest checkpoint height if we deleted it
            if height == self.latest_checkpoint_height:
                self._load_latest_checkpoint_height()

            return True
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to delete checkpoint at height {height}: {e}")
            return False

    def verify_checkpoint(self, height: int) -> bool:
        """
        Verify the integrity of a checkpoint.

        Args:
            height: Height of checkpoint to verify

        Returns:
            True if checkpoint is valid, False otherwise
        """
        checkpoint = self.load_checkpoint(height)
        return checkpoint is not None and checkpoint.verify_integrity()

    def create_manual_checkpoint(
        self, block: "Block", utxo_manager: "UTXOManager", total_supply: float
    ) -> Checkpoint | None:
        """
        Manually create a checkpoint regardless of interval.

        Args:
            block: The block to checkpoint
            utxo_manager: UTXO manager for state snapshot
            total_supply: Current total supply

        Returns:
            Checkpoint object if successful, None otherwise
        """
        logger.info(f"Creating manual checkpoint at height {block.index}")
        return self.create_checkpoint(block, utxo_manager, total_supply)

    def verify_checkpoint_with_peers(
        self, height: int, peer_checkpoints: list[dict[str, Any]], min_consensus: float = 0.67
    ) -> tuple[bool, str]:
        """
        Verify checkpoint against peer consensus by comparing hashes.

        Args:
            height: Checkpoint height to verify
            peer_checkpoints: List of checkpoint data from peers
            min_consensus: Minimum percentage of peers that must agree (0.67 = 67%)

        Returns:
            tuple: (is_valid, message)
        """
        local_checkpoint = self.load_checkpoint(height)

        if not local_checkpoint:
            return False, f"No local checkpoint at height {height}"

        if not peer_checkpoints:
            return False, "No peer checkpoints provided for comparison"

        # Count hash matches
        matching_peers = 0
        total_peers = len(peer_checkpoints)

        for peer_cp in peer_checkpoints:
            peer_hash = peer_cp.get("checkpoint_hash")
            if peer_hash == local_checkpoint.checkpoint_hash:
                matching_peers += 1

        # Calculate consensus percentage
        consensus_percentage = matching_peers / total_peers if total_peers > 0 else 0

        if consensus_percentage >= min_consensus:
            logger.info(
                f"Checkpoint at height {height} verified with {consensus_percentage:.1%} "
                f"peer consensus ({matching_peers}/{total_peers})"
            )
            return True, f"Checkpoint verified with {consensus_percentage:.1%} consensus"
        else:
            logger.warning(
                f"Checkpoint at height {height} failed consensus: "
                f"{consensus_percentage:.1%} < {min_consensus:.1%} required"
            )
            return False, f"Insufficient consensus: {consensus_percentage:.1%} < {min_consensus:.1%}"

    def compare_checkpoint_with_peer(
        self, height: int, peer_checkpoint_data: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Compare local checkpoint with peer checkpoint and identify differences.

        Args:
            height: Checkpoint height
            peer_checkpoint_data: Checkpoint data from peer

        Returns:
            tuple: (matches, list_of_differences)
        """
        local_checkpoint = self.load_checkpoint(height)

        if not local_checkpoint:
            return False, ["Local checkpoint not found"]

        differences = []

        # Compare critical fields
        if local_checkpoint.block_hash != peer_checkpoint_data.get("block_hash"):
            differences.append("block_hash mismatch")

        if local_checkpoint.checkpoint_hash != peer_checkpoint_data.get("checkpoint_hash"):
            differences.append("checkpoint_hash mismatch")

        if local_checkpoint.merkle_root != peer_checkpoint_data.get("merkle_root"):
            differences.append("merkle_root mismatch")

        if local_checkpoint.total_supply != peer_checkpoint_data.get("total_supply"):
            differences.append("total_supply mismatch")

        matches = len(differences) == 0
        return matches, differences

    def request_checkpoint_from_peers(
        self, height: int, peer_list: list[str]
    ) -> list[dict[str, Any]]:
        """
        Request checkpoint data from multiple peers for consensus verification.

        Args:
            height: Checkpoint height to request
            peer_list: List of peer addresses/IDs or peer objects with send_message

        Returns:
            List of checkpoint data from responding peers
        """
        if not peer_list:
            return []

        logger.info(
            "Requesting checkpoint at height %d from %d peers",
            height,
            len(peer_list),
            extra={"event": "checkpoint.peer_request", "height": height, "peer_count": len(peer_list)}
        )

        peer_checkpoints: list[dict[str, Any]] = []
        timeout = 10.0  # seconds per peer
        max_peers = 5  # Limit concurrent requests

        for peer in peer_list[:max_peers]:
            try:
                # Create checkpoint request message
                request = {
                    "type": "checkpoint_request",
                    "height": height,
                    "timestamp": time.time(),
                }

                # If peer has send_message method, use it for network request
                if hasattr(peer, 'send_message'):
                    response = peer.send_message(request, timeout=timeout)
                    if response and self._validate_checkpoint_response(response):
                        peer_checkpoints.append(response)
                        logger.debug(
                            "Got valid checkpoint response from peer",
                            extra={"event": "checkpoint.peer_response", "height": height}
                        )
                elif hasattr(peer, 'request_checkpoint'):
                    # Alternative interface for checkpoint-specific requests
                    response = peer.request_checkpoint(height, timeout=timeout)
                    if response and self._validate_checkpoint_response(response):
                        peer_checkpoints.append(response)

            except TimeoutError:
                logger.debug(
                    "Timeout requesting checkpoint from peer",
                    extra={"event": "checkpoint.peer_timeout", "height": height}
                )
            except (ConnectionError, OSError) as e:
                logger.debug(
                    "Network error requesting checkpoint from peer: %s",
                    str(e),
                    extra={"event": "checkpoint.peer_network_error", "height": height}
                )
            except (ValueError, TypeError, RuntimeError) as e:
                logger.debug(
                    "Failed to get checkpoint from peer: %s",
                    str(e),
                    extra={"event": "checkpoint.peer_error", "height": height, "error": str(e)}
                )

        logger.info(
            "Collected %d checkpoint responses from peers",
            len(peer_checkpoints),
            extra={"event": "checkpoint.peer_responses", "height": height, "count": len(peer_checkpoints)}
        )
        return peer_checkpoints

    def _validate_checkpoint_response(self, response: dict[str, Any]) -> bool:
        """
        Validate that a checkpoint response contains required fields.

        Args:
            response: Checkpoint response dictionary from peer

        Returns:
            True if response has all required fields with valid types
        """
        required_fields = ["block_hash", "height", "state_root"]

        if not isinstance(response, dict):
            return False

        for field in required_fields:
            if field not in response:
                return False

        # Validate field types
        if not isinstance(response.get("height"), (int, float)):
            return False
        if not isinstance(response.get("block_hash"), str):
            return False
        if not isinstance(response.get("state_root"), str):
            return False

        return True
