"""
XAI Blockchain - Block Pruning Manager

Implements configurable block retention and pruning policies to manage disk space
while maintaining chain integrity and security.

Features:
- Configurable retention by block count or age
- Prune old block bodies while keeping headers
- Archive mode with compression before deletion
- Disk space threshold triggers
- Safe pruning with finality checks
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import shutil
import time
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain

logger = logging.getLogger(__name__)

class PruneMode(Enum):
    """Pruning mode configuration"""
    NONE = "none"  # No pruning (archival node)
    BLOCKS = "blocks"  # Keep N recent blocks
    DAYS = "days"  # Keep blocks from last N days
    BOTH = "both"  # Keep whichever is more restrictive
    SPACE = "space"  # Prune when disk usage exceeds threshold

@dataclass
class PruningStats:
    """Statistics about pruning operations"""
    total_blocks: int
    pruned_blocks: int
    archived_blocks: int
    headers_only_blocks: int
    disk_space_saved: int  # bytes
    last_prune_time: float
    retention_blocks: int
    retention_days: int
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class PruningPolicy:
    """Pruning policy configuration"""
    mode: PruneMode
    retain_blocks: int  # Number of recent blocks to keep
    retain_days: int  # Number of days to retain
    archive_before_delete: bool  # Compress blocks before deletion
    archive_path: str  # Where to store archived blocks
    disk_threshold_gb: float  # Prune when disk usage exceeds this
    min_finalized_depth: int  # Never prune blocks younger than this
    keep_headers_only: bool  # Keep headers for pruned blocks

    @classmethod
    def from_config(cls, config: Any = None) -> PruningPolicy:
        """Create policy from config object or environment"""
        # Always read from environment first for tests, fall back to config module
        mode_str = os.getenv("XAI_PRUNE_MODE")

        if mode_str is None and config is None:
            try:
                from xai.core import config as xai_config
                mode_str = getattr(xai_config, "PRUNE_MODE", "none")
            except ImportError:
                mode_str = "none"
        elif mode_str is None:
            mode_str = getattr(config, "PRUNE_MODE", "none")

        # Parse prune mode
        try:
            mode = PruneMode(mode_str.lower())
        except ValueError:
            logger.warning("Invalid prune mode %s, defaulting to none", mode_str)
            mode = PruneMode.NONE

        # Get retention settings - environment takes precedence
        retain_blocks = int(os.getenv("XAI_PRUNE_KEEP_BLOCKS", "1000"))
        retain_days = int(os.getenv("XAI_PRUNE_KEEP_DAYS", "30"))

        # Archive settings
        archive_mode = os.getenv("XAI_PRUNE_ARCHIVE", "true").lower() == "true"
        archive_path = os.getenv("XAI_PRUNE_ARCHIVE_PATH", "data/archive")

        # Disk threshold
        disk_threshold = float(os.getenv("XAI_PRUNE_DISK_THRESHOLD_GB", "50.0"))

        # Safety settings
        min_finalized = int(os.getenv("XAI_PRUNE_MIN_FINALIZED_DEPTH", "100"))
        keep_headers = os.getenv("XAI_PRUNE_KEEP_HEADERS", "true").lower() == "true"

        return cls(
            mode=mode,
            retain_blocks=retain_blocks,
            retain_days=retain_days,
            archive_before_delete=archive_mode,
            archive_path=archive_path,
            disk_threshold_gb=disk_threshold,
            min_finalized_depth=min_finalized,
            keep_headers_only=keep_headers,
        )

class BlockPruningManager:
    """
    Manages block pruning operations for the blockchain.

    Supports multiple retention policies:
    - Block count: Keep last N blocks
    - Time-based: Keep blocks from last N days
    - Disk space: Prune when threshold exceeded
    - Archive mode: Compress before deletion
    """

    def __init__(
        self,
        blockchain: Blockchain,
        policy: PruningPolicy | None = None,
        data_dir: str = "data"
    ):
        """
        Initialize pruning manager.

        Args:
            blockchain: Blockchain instance to manage
            policy: Pruning policy (defaults from config if None)
            data_dir: Data directory for blockchain storage
        """
        self.blockchain = blockchain
        self.policy = policy or PruningPolicy.from_config()
        self.data_dir = Path(data_dir)
        self.archive_dir = Path(self.policy.archive_path)

        # Create archive directory if archiving enabled
        if self.policy.archive_before_delete:
            self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = PruningStats(
            total_blocks=0,
            pruned_blocks=0,
            archived_blocks=0,
            headers_only_blocks=0,
            disk_space_saved=0,
            last_prune_time=0,
            retention_blocks=self.policy.retain_blocks,
            retention_days=self.policy.retain_days,
            mode=self.policy.mode.value,
        )

        # Track pruned block heights
        self.pruned_heights: set[int] = set()
        self.headers_only_heights: set[int] = set()

        logger.info(
            "BlockPruningManager initialized with mode=%s, retain_blocks=%d, retain_days=%d",
            self.policy.mode.value,
            self.policy.retain_blocks,
            self.policy.retain_days,
            extra={
                "event": "pruning.init",
                "mode": self.policy.mode.value,
                "policy": asdict(self.policy),
            }
        )

    def should_prune(self) -> bool:
        """
        Check if pruning should run based on policy.

        Returns:
            True if pruning criteria are met
        """
        if self.policy.mode == PruneMode.NONE:
            return False

        chain_length = len(self.blockchain.chain)

        # Check block count threshold
        if self.policy.mode in (PruneMode.BLOCKS, PruneMode.BOTH):
            if chain_length > self.policy.retain_blocks + self.policy.min_finalized_depth:
                return True

        # Check time threshold
        if self.policy.mode in (PruneMode.DAYS, PruneMode.BOTH):
            cutoff_time = time.time() - (self.policy.retain_days * 86400)
            if self._has_blocks_older_than(cutoff_time):
                return True

        # Check disk space threshold
        if self.policy.mode == PruneMode.SPACE:
            disk_usage_gb = self._get_disk_usage_gb()
            if disk_usage_gb > self.policy.disk_threshold_gb:
                return True

        return False

    def _has_blocks_older_than(self, timestamp: float) -> bool:
        """Check if chain has blocks older than timestamp"""
        if len(self.blockchain.chain) < self.policy.min_finalized_depth:
            return False

        # Check blocks that would be eligible for pruning
        for block in self.blockchain.chain[:len(self.blockchain.chain) - self.policy.min_finalized_depth]:
            if block.timestamp < timestamp:
                return True
        return False

    def _get_disk_usage_gb(self) -> float:
        """Calculate disk usage in GB for blockchain data"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.data_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
        return total_size / (1024 ** 3)

    def calculate_prune_height(self) -> int:
        """
        Calculate the highest block height that can be pruned.

        Returns:
            Height up to which blocks can be pruned (inclusive)
        """
        chain_length = len(self.blockchain.chain)

        if chain_length <= self.policy.min_finalized_depth:
            return -1

        prune_height = -1

        # Calculate based on block count
        if self.policy.mode in (PruneMode.BLOCKS, PruneMode.BOTH):
            block_prune_height = chain_length - self.policy.retain_blocks - 1
            prune_height = max(prune_height, block_prune_height)

        # Calculate based on time
        if self.policy.mode in (PruneMode.DAYS, PruneMode.BOTH):
            cutoff_time = time.time() - (self.policy.retain_days * 86400)
            time_prune_height = self._find_cutoff_height(cutoff_time)
            if self.policy.mode == PruneMode.BOTH:
                # More restrictive: keep whichever keeps more blocks
                prune_height = min(prune_height, time_prune_height)
            else:
                prune_height = max(prune_height, time_prune_height)

        # Calculate based on disk space
        if self.policy.mode == PruneMode.SPACE:
            disk_usage = self._get_disk_usage_gb()
            if disk_usage > self.policy.disk_threshold_gb:
                # Prune enough blocks to get under threshold
                prune_height = self._calculate_space_prune_height()

        # Never prune within finalized depth
        max_prune = chain_length - self.policy.min_finalized_depth - 1
        prune_height = min(prune_height, max_prune)

        # Never prune genesis
        prune_height = max(prune_height, 0)

        return prune_height

    def _find_cutoff_height(self, cutoff_time: float) -> int:
        """Find the highest block height older than cutoff time"""
        for i in range(len(self.blockchain.chain) - 1, -1, -1):
            if self.blockchain.chain[i].timestamp < cutoff_time:
                return i
        return -1

    def _calculate_space_prune_height(self) -> int:
        """Calculate prune height to meet disk space threshold"""
        # Simple heuristic: estimate blocks to prune based on average block size
        disk_usage = self._get_disk_usage_gb()
        overage_gb = disk_usage - self.policy.disk_threshold_gb

        if overage_gb <= 0:
            return -1

        # Estimate average block size
        chain_length = len(self.blockchain.chain)
        if chain_length == 0:
            return -1

        avg_block_size = (disk_usage * 1024 ** 3) / chain_length
        blocks_to_prune = int((overage_gb * 1024 ** 3) / avg_block_size)

        # Add 10% safety margin
        blocks_to_prune = int(blocks_to_prune * 1.1)

        return blocks_to_prune

    def prune_blocks(self, up_to_height: int | None = None, dry_run: bool = False) -> dict[str, Any]:
        """
        Prune blocks up to specified height.

        Args:
            up_to_height: Height to prune up to (None = auto-calculate)
            dry_run: If True, only calculate what would be pruned

        Returns:
            Dictionary with pruning results
        """
        if up_to_height is None:
            up_to_height = self.calculate_prune_height()

        if up_to_height < 0:
            return {
                "pruned": 0,
                "archived": 0,
                "space_saved": 0,
                "reason": "No blocks eligible for pruning"
            }

        pruned_count = 0
        archived_count = 0
        space_saved = 0

        # Get list of blocks to prune (skip genesis at index 0)
        blocks_to_prune = []
        for i in range(1, min(up_to_height + 1, len(self.blockchain.chain))):
            if i not in self.pruned_heights:
                blocks_to_prune.append((i, self.blockchain.chain[i]))

        if dry_run:
            # Estimate space savings
            for idx, block in blocks_to_prune:
                block_size = len(json.dumps(block.to_dict()).encode())
                space_saved += block_size

            return {
                "pruned": len(blocks_to_prune),
                "archived": len(blocks_to_prune) if self.policy.archive_before_delete else 0,
                "space_saved": space_saved,
                "up_to_height": up_to_height,
                "dry_run": True
            }

        # Perform actual pruning
        logger.info(
            "Starting block pruning up to height %d (%d blocks)",
            up_to_height,
            len(blocks_to_prune),
            extra={"event": "pruning.start", "height": up_to_height, "count": len(blocks_to_prune)}
        )

        for idx, block in blocks_to_prune:
            block_size = len(json.dumps(block.to_dict()).encode())

            # Archive if enabled
            if self.policy.archive_before_delete:
                if self._archive_block(block):
                    archived_count += 1
                else:
                    logger.warning(
                        "Failed to archive block %d, skipping pruning",
                        idx,
                        extra={"event": "pruning.archive_failed", "height": idx}
                    )
                    continue

            # Prune block data
            if self._prune_block(block):
                pruned_count += 1
                space_saved += block_size
                self.pruned_heights.add(idx)

                if self.policy.keep_headers_only:
                    self.headers_only_heights.add(idx)

        # Update statistics
        self.stats.pruned_blocks += pruned_count
        self.stats.archived_blocks += archived_count
        self.stats.disk_space_saved += space_saved
        self.stats.last_prune_time = time.time()
        self.stats.total_blocks = len(self.blockchain.chain)
        self.stats.headers_only_blocks = len(self.headers_only_heights)

        logger.info(
            "Pruning complete: pruned=%d, archived=%d, space_saved=%d bytes",
            pruned_count,
            archived_count,
            space_saved,
            extra={
                "event": "pruning.complete",
                "pruned": pruned_count,
                "archived": archived_count,
                "space_saved": space_saved
            }
        )

        return {
            "pruned": pruned_count,
            "archived": archived_count,
            "space_saved": space_saved,
            "up_to_height": up_to_height,
            "dry_run": False
        }

    def _archive_block(self, block: Block) -> bool:
        """
        Archive a block to compressed storage.

        Args:
            block: Block to archive

        Returns:
            True if archived successfully
        """
        try:
            # Create archive filename
            archive_file = self.archive_dir / f"block_{block.index}.json.gz"

            # Serialize and compress
            block_data = json.dumps(block.to_dict(), separators=(',', ':')).encode()
            compressed_data = gzip.compress(block_data, compresslevel=9)

            # Write to archive
            with open(archive_file, 'wb') as f:
                f.write(compressed_data)

            logger.debug(
                "Archived block %d: %d -> %d bytes (%.1f%% compression)",
                block.index,
                len(block_data),
                len(compressed_data),
                100 * (1 - len(compressed_data) / len(block_data)),
                extra={
                    "event": "pruning.archived",
                    "height": block.index,
                    "original_size": len(block_data),
                    "compressed_size": len(compressed_data)
                }
            )

            return True

        except (OSError, IOError) as e:
            # File system errors during archiving
            logger.error(
                "File system error archiving block %d: %s",
                block.index,
                str(e),
                extra={"event": "pruning.archive_fs_error", "height": block.index, "error": str(e)}
            )
            return False
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # Serialization errors
            logger.error(
                "Serialization error archiving block %d: %s",
                block.index,
                str(e),
                extra={"event": "pruning.archive_serialize_error", "height": block.index, "error": str(e)}
            )
            return False
        except Exception as e:
            # Unexpected errors - log with full traceback for debugging
            logger.error(
                "Unexpected error archiving block %d: %s",
                block.index,
                str(e),
                extra={"event": "pruning.archive_error", "height": block.index, "error": str(e), "error_type": type(e).__name__},
                exc_info=True
            )
            return False

    def _prune_block(self, block: Block) -> bool:
        """
        Prune block data while optionally keeping header.

        Args:
            block: Block to prune

        Returns:
            True if pruned successfully
        """
        try:
            if self.policy.keep_headers_only:
                # Keep only header, remove transactions
                block.transactions = []
                logger.debug(
                    "Pruned block %d transactions, kept header",
                    block.index,
                    extra={"event": "pruning.header_only", "height": block.index}
                )
            else:
                # This is a more aggressive prune - would need blockchain support
                # For now, just mark it as pruned but keep in memory
                logger.debug(
                    "Marked block %d as pruned",
                    block.index,
                    extra={"event": "pruning.marked", "height": block.index}
                )

            return True

        except AttributeError as e:
            # Block missing expected attributes
            logger.error(
                "Block %d missing expected attributes during prune: %s",
                block.index,
                str(e),
                extra={"event": "pruning.prune_attr_error", "height": block.index, "error": str(e)}
            )
            return False
        except Exception as e:
            # Unexpected errors - log with full traceback for debugging
            logger.error(
                "Unexpected error pruning block %d: %s",
                block.index,
                str(e),
                extra={"event": "pruning.prune_error", "height": block.index, "error": str(e), "error_type": type(e).__name__},
                exc_info=True
            )
            return False

    def restore_block(self, height: int) -> Block | None:
        """
        Restore an archived block.

        Args:
            height: Block height to restore

        Returns:
            Restored block or None if not found
        """
        archive_file = self.archive_dir / f"block_{height}.json.gz"

        if not archive_file.exists():
            logger.warning(
                "Archive file not found for block %d",
                height,
                extra={"event": "pruning.restore_not_found", "height": height}
            )
            return None

        try:
            # Read and decompress
            with open(archive_file, 'rb') as f:
                compressed_data = f.read()

            block_data = gzip.decompress(compressed_data)
            block_dict = json.loads(block_data)

            # Reconstruct proper Block object from dictionary
            from xai.core.chain.block_header import BlockHeader
            from xai.core.blockchain_components.block import Block
            from xai.core.transaction import Transaction

            # Support both nested header format and flattened format
            if "header" in block_dict and block_dict["header"]:
                header_data = block_dict["header"]
            else:
                header_data = block_dict

            header = BlockHeader(
                index=header_data.get("index", 0),
                previous_hash=header_data.get("previous_hash", "0"),
                merkle_root=header_data.get("merkle_root", "0"),
                timestamp=header_data.get("timestamp", time.time()),
                difficulty=header_data.get("difficulty", 4),
                nonce=header_data.get("nonce", 0),
                signature=header_data.get("signature"),
                miner_pubkey=header_data.get("miner_pubkey"),
                version=header_data.get("version"),
            )

            # Preserve hash if available
            if "hash" in header_data:
                header.hash = header_data["hash"]

            # Reconstruct transactions
            transactions = []
            for tx_data in block_dict.get("transactions", []):
                tx = Transaction(
                    tx_data.get("sender", ""),
                    tx_data.get("recipient", ""),
                    tx_data.get("amount", 0),
                    tx_data.get("fee", 0),
                    tx_data.get("public_key", ""),
                    tx_data.get("tx_type", "transfer"),
                    tx_data.get("nonce"),
                    tx_data.get("inputs", []),
                    tx_data.get("outputs", []),
                )
                tx.timestamp = tx_data.get("timestamp", 0)
                tx.signature = tx_data.get("signature", "")
                tx.txid = tx_data.get("txid", "")
                tx.metadata = tx_data.get("metadata", {})
                transactions.append(tx)

            block = Block(header, transactions)
            if block_dict.get("miner"):
                block.miner = block_dict["miner"]

            logger.info(
                "Restored block %d from archive",
                height,
                extra={"event": "pruning.restored", "height": height}
            )

            return block

        except (OSError, IOError) as e:
            # File system errors during restore
            logger.error(
                "File system error restoring block %d: %s",
                height,
                str(e),
                extra={"event": "pruning.restore_fs_error", "height": height, "error": str(e)}
            )
            return None
        except (gzip.BadGzipFile, zlib.error) as e:
            # Decompression errors - possibly corrupted archive
            logger.error(
                "Decompression error restoring block %d (possibly corrupted): %s",
                height,
                str(e),
                extra={"event": "pruning.restore_decompress_error", "height": height, "error": str(e)}
            )
            return None
        except json.JSONDecodeError as e:
            # JSON parsing errors
            logger.error(
                "JSON decode error restoring block %d: %s",
                height,
                str(e),
                extra={"event": "pruning.restore_json_error", "height": height, "error": str(e)}
            )
            return None
        except Exception as e:
            # Unexpected errors - log with full traceback for debugging
            logger.error(
                "Unexpected error restoring block %d: %s",
                height,
                str(e),
                extra={"event": "pruning.restore_error", "height": height, "error": str(e), "error_type": type(e).__name__},
                exc_info=True
            )
            return None

    def get_status(self) -> dict[str, Any]:
        """
        Get current pruning status.

        Returns:
            Status information dictionary
        """
        chain_length = len(self.blockchain.chain)
        prune_height = self.calculate_prune_height()
        eligible_blocks = max(0, prune_height + 1 - len(self.pruned_heights))

        return {
            "mode": self.policy.mode.value,
            "enabled": self.policy.mode != PruneMode.NONE,
            "policy": {
                "retain_blocks": self.policy.retain_blocks,
                "retain_days": self.policy.retain_days,
                "archive_enabled": self.policy.archive_before_delete,
                "disk_threshold_gb": self.policy.disk_threshold_gb,
                "min_finalized_depth": self.policy.min_finalized_depth,
                "keep_headers": self.policy.keep_headers_only,
            },
            "stats": self.stats.to_dict(),
            "chain": {
                "total_blocks": chain_length,
                "prunable_height": prune_height,
                "eligible_blocks": eligible_blocks,
                "disk_usage_gb": self._get_disk_usage_gb(),
            },
            "would_prune": self.should_prune(),
        }

    def get_stats(self) -> PruningStats:
        """Get pruning statistics"""
        self.stats.total_blocks = len(self.blockchain.chain)
        return self.stats

    def is_block_pruned(self, height: int) -> bool:
        """Check if a block has been pruned"""
        return height in self.pruned_heights

    def has_full_block(self, height: int) -> bool:
        """Check if full block data is available (not just header)"""
        if height in self.pruned_heights and height not in self.headers_only_heights:
            return False
        if height in self.headers_only_heights:
            return False
        return True

    def set_policy(self, policy: PruningPolicy) -> None:
        """Update pruning policy at runtime"""
        old_mode = self.policy.mode
        self.policy = policy
        self.stats.mode = policy.mode.value
        self.stats.retention_blocks = policy.retain_blocks
        self.stats.retention_days = policy.retain_days

        logger.info(
            "Pruning policy updated: %s -> %s",
            old_mode.value,
            policy.mode.value,
            extra={"event": "pruning.policy_updated", "old_mode": old_mode.value, "new_mode": policy.mode.value}
        )
