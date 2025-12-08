"""
XAI Blockchain - Blockchain Storage Manager

Handles all disk I/O operations for the blockchain, including saving and loading
blocks, the UTXO set, and pending transactions.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import time
from typing import List, Dict, Optional, TYPE_CHECKING, Any
from xai.core.block_index import BlockIndex

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Transaction
    from xai.core.block_header import BlockHeader


MAX_BLOCK_FILE_SIZE = 16 * 1024 * 1024  # 16 MB
COMPRESSION_THRESHOLD = 1000  # Compress blocks older than this many blocks from tip

class BlockchainStorage:
    """
    Manages the persistence of blockchain data to disk.
    """

    def __init__(self, data_dir: str = "data", compact_on_startup: bool = False, enable_index: bool = True) -> None:
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.blocks_dir = os.path.join(self.data_dir, "blocks")
        os.makedirs(self.blocks_dir, exist_ok=True)
        self.utxo_file = os.path.join(self.data_dir, "utxo_set.json")
        self.pending_tx_file = os.path.join(self.data_dir, "pending_transactions.json")
        self.contracts_file = os.path.join(self.data_dir, "contracts_state.json")
        self.receipts_file = os.path.join(self.data_dir, "contract_receipts.json")
        self.journal_file = os.path.join(self.data_dir, "journal.log")
        self.block_file_index = 0
        self._set_block_file_index()

        # Initialize block index for O(1) lookups
        self.enable_index = enable_index
        if enable_index:
            index_db_path = os.path.join(self.data_dir, "block_index.db")
            self.block_index = BlockIndex(db_path=index_db_path, cache_size=256)
            # Check if we need to build index for existing blocks
            self._ensure_index_built()
        else:
            self.block_index = None

        if compact_on_startup:
            self.compact()

    def _set_block_file_index(self) -> None:
        """Sets the block file index to the latest one."""
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("blocks_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )
        if block_files:
            self.block_file_index = int(block_files[-1].split("_")[1].split(".")[0])

    def _get_latest_block_index(self) -> int:
        """
        Get the highest block index in the chain.

        Returns:
            Highest block index, or -1 if chain is empty
        """
        if self.block_index:
            max_height = self.block_index.get_max_indexed_height()
            if max_height is not None:
                return max_height

        # Fallback: scan all block files
        latest_block = self.get_latest_block_from_disk()
        if latest_block:
            return latest_block.header.index
        return -1

    def _ensure_index_built(self) -> None:
        """
        Ensure block index is built for all existing blocks.

        This runs on startup to index any blocks that were written before
        the index was enabled. Uses efficient streaming to handle large chains.
        """
        if not self.block_index:
            return

        # Check if index needs building
        max_indexed = self.block_index.get_max_indexed_height()
        if max_indexed is not None:
            # Index exists, check if it's up to date
            logger.info(
                "Block index loaded",
                extra={
                    "event": "storage.index_loaded",
                    "max_height": max_indexed,
                    "total_blocks": self.block_index.get_index_count(),
                }
            )
            return

        # Index is empty, need to build it
        logger.info("Building block index for existing chain...")
        start_time = time.time()

        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("blocks_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        blocks_indexed = 0
        for block_file in block_files:
            file_path = os.path.join(self.blocks_dir, block_file)
            relative_path = os.path.join("blocks", block_file)

            with open(file_path, "r", encoding="utf-8") as f:
                file_offset = 0
                for line in f:
                    line_size = len(line.encode("utf-8"))
                    try:
                        block_data = json.loads(line)
                        # Support both nested and flattened block formats
                        if "header" in block_data and block_data["header"]:
                            header_data = block_data["header"]
                        else:
                            header_data = block_data
                        block_index = header_data.get("index", 0)

                        # Calculate block hash for integrity
                        # Use the stored hash if available, otherwise calculate
                        block_hash = header_data.get("hash", "")
                        if not block_hash:
                            # Fallback: hash the entire block data
                            block_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()

                        # Index this block
                        self.block_index.index_block(
                            block_index=block_index,
                            block_hash=block_hash,
                            file_path=relative_path,
                            file_offset=file_offset,
                            file_size=line_size,
                        )
                        blocks_indexed += 1

                        if blocks_indexed % 1000 == 0:
                            logger.info(f"Indexed {blocks_indexed} blocks...")

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(
                            f"Skipping corrupt block at offset {file_offset} in {block_file}: {e}"
                        )

                    file_offset += line_size

        elapsed = time.time() - start_time
        logger.info(
            "Block index built successfully",
            extra={
                "event": "storage.index_built",
                "blocks_indexed": blocks_indexed,
                "elapsed_seconds": f"{elapsed:.2f}",
                "blocks_per_second": int(blocks_indexed / elapsed) if elapsed > 0 else 0,
            }
        )

    def compact(self) -> None:
        """Compacts all block files into a single file with durable writes."""
        compacted_file = os.path.join(self.blocks_dir, "blockchain.json")
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("blocks_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        with open(compacted_file, "w", encoding="utf-8") as f:
            for block_file in block_files:
                with open(os.path.join(self.blocks_dir, block_file), "r", encoding="utf-8") as bf:
                    for line in bf:
                        f.write(line)
            f.flush()
            os.fsync(f.fileno())

        for block_file in block_files:
            os.remove(os.path.join(self.blocks_dir, block_file))

        self.block_file_index = 0
        os.rename(compacted_file, os.path.join(self.blocks_dir, "blocks_0.json"))


    def _should_compress_block(self, block_index: int) -> bool:
        """
        Determine if a block should be compressed based on its age.

        Blocks older than COMPRESSION_THRESHOLD from the chain tip are compressed
        to save ~70% disk space. Recent blocks are kept uncompressed for fast access.

        Args:
            block_index: Height of block to check

        Returns:
            True if block should be compressed, False otherwise
        """
        latest_index = self._get_latest_block_index()
        if latest_index < 0:
            return False  # Empty chain, don't compress

        # Compress blocks older than threshold
        return (latest_index - block_index) >= COMPRESSION_THRESHOLD

    def _get_block_file_path(self, block_index: int, compressed: bool = False) -> str:
        """
        Get the file path for a block, checking both compressed and uncompressed versions.

        Args:
            block_index: Block height
            compressed: If True, return compressed path; if False, check both

        Returns:
            Path to block file (may not exist)
        """
        # For individual block files (new compression scheme)
        compressed_path = os.path.join(self.blocks_dir, f"block_{block_index}.json.gz")
        uncompressed_path = os.path.join(self.blocks_dir, f"block_{block_index}.json")

        if compressed:
            return compressed_path

        # Check which file exists
        if os.path.exists(compressed_path):
            return compressed_path
        elif os.path.exists(uncompressed_path):
            return uncompressed_path

        # Default to uncompressed for new blocks
        return uncompressed_path

    def _save_block_to_disk(self, block: Block) -> None:
        """Save a single block to its file with durable append.

        Uses fsync after write to ensure block data is persisted to disk
        before the function returns. This prevents data loss on power failure
        or system crash.

        Also updates the block index for O(1) lookups.
        """
        block_file = os.path.join(self.blocks_dir, f"blocks_{self.block_file_index}.json")

        if os.path.exists(block_file) and os.path.getsize(block_file) > MAX_BLOCK_FILE_SIZE:
            self.block_file_index += 1
            block_file = os.path.join(self.blocks_dir, f"blocks_{self.block_file_index}.json")

        # Get file offset before write
        file_offset = os.path.getsize(block_file) if os.path.exists(block_file) else 0

        block_dict = block.to_dict()
        block_json = json.dumps(block_dict) + "\n"
        block_size = len(block_json.encode("utf-8"))

        with open(block_file, "a", encoding="utf-8") as f:
            f.write(block_json)
            f.flush()
            os.fsync(f.fileno())

        # Update index after successful write
        if self.block_index:
            relative_path = os.path.join("blocks", f"blocks_{self.block_file_index}.json")
            # Support both nested and flattened block formats
            if "header" in block_dict and block_dict["header"]:
                header_data = block_dict["header"]
            else:
                header_data = block_dict
            block_hash = header_data.get("hash", "")
            if not block_hash:
                # Fallback: use block header hash
                block_hash = block.header.calculate_hash() if hasattr(block, "header") else ""

            self.block_index.index_block(
                block_index=block.header.index if hasattr(block, "header") else header_data.get("index", 0),
                block_hash=block_hash,
                file_path=relative_path,
                file_offset=file_offset,
                file_size=block_size,
            )

    def compress_old_blocks(self, force: bool = False) -> int:
        """
        Compress old blocks to save disk space.

        This method scans all block files and compresses blocks that are older than
        COMPRESSION_THRESHOLD blocks from the current chain tip. Compressed blocks
        use gzip and save approximately 70% disk space.

        Args:
            force: If True, compress all blocks regardless of age

        Returns:
            Number of blocks compressed
        """
        latest_index = self._get_latest_block_index()
        if latest_index < 0:
            return 0  # Empty chain

        blocks_compressed = 0
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("blocks_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        for block_file in block_files:
            file_path = os.path.join(self.blocks_dir, block_file)

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                try:
                    block_data = json.loads(line.strip())
                    block_index = block_data["header"]["index"]

                    # Check if block should be compressed
                    if force or self._should_compress_block(block_index):
                        # Create individual compressed block file
                        compressed_path = os.path.join(
                            self.blocks_dir, f"block_{block_index}.json.gz"
                        )

                        # Skip if already compressed
                        if os.path.exists(compressed_path):
                            continue

                        # Write compressed block
                        block_json = json.dumps(block_data)
                        with gzip.open(compressed_path, 'wt', encoding='utf-8') as gz_f:
                            gz_f.write(block_json)

                        blocks_compressed += 1

                        if blocks_compressed % 100 == 0:
                            logger.info(f"Compressed {blocks_compressed} blocks...")

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to compress block: {e}")
                    continue

        if blocks_compressed > 0:
            logger.info(
                "Block compression completed",
                extra={
                    "event": "storage.compression_completed",
                    "blocks_compressed": blocks_compressed,
                    "latest_index": latest_index,
                }
            )

        return blocks_compressed
    
    def save_state_to_disk(
        self,
        utxo_manager: Any,
        pending_transactions: List[Transaction],
        contracts: Optional[Dict[str, Dict[str, Any]]] = None,
        receipts: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Save the blockchain state (UTXO set and pending transactions) to disk."""
        # Save UTXO set (atomic)
        self._atomic_write_json(self.utxo_file, utxo_manager.to_dict())

        # Save pending transactions
        pending_tx_data = [tx.to_dict() for tx in pending_transactions]
        self._atomic_write_json(self.pending_tx_file, pending_tx_data)

        contracts_payload = {}
        if contracts:
            for address, contract in contracts.items():
                contracts_payload[address] = {
                    "creator": contract.get("creator"),
                    "code": contract.get("code").hex() if isinstance(contract.get("code"), (bytes, bytearray)) else contract.get("code"),
                    "storage": contract.get("storage", {}),
                    "gas_limit": contract.get("gas_limit"),
                    "balance": contract.get("balance"),
                    "created_at": contract.get("created_at"),
                }
        self._atomic_write_json(self.contracts_file, contracts_payload)

        self._atomic_write_json(self.receipts_file, receipts or [])

        # Update checksums
        checksums = {
            os.path.basename(self.utxo_file): self._calculate_checksum(self.utxo_file),
            os.path.basename(self.pending_tx_file): self._calculate_checksum(self.pending_tx_file),
            os.path.basename(self.contracts_file): self._calculate_checksum(self.contracts_file),
            os.path.basename(self.receipts_file): self._calculate_checksum(self.receipts_file),
        }
        for block_file in os.listdir(self.blocks_dir):
            if block_file.startswith("blocks_") and block_file.endswith(".json"):
                checksums[os.path.join("blocks", block_file)] = self._calculate_checksum(os.path.join(self.blocks_dir, block_file))
        
        checksum_file = os.path.join(self.data_dir, "checksum.json")
        self._atomic_write_json(checksum_file, checksums)

    def verify_integrity(self) -> bool:
        """Verify the integrity of all blockchain data files."""
        checksum_file = os.path.join(self.data_dir, "checksum.json")
        if not os.path.exists(checksum_file):
            return True  # No checksum to verify against

        with open(checksum_file, "r") as f:
            stored_checksums = json.load(f)

        for filename, stored_checksum in stored_checksums.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                return False  # File is missing
            current_checksum = self._calculate_checksum(filepath)
            if current_checksum != stored_checksum:
                return False  # Checksum mismatch

        return True

    def _calculate_checksum(self, filepath: str) -> str:
        """Calculate the SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _atomic_write_json(self, path: str, payload: Any) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"

        # Write to journal first
        with open(self.journal_file, "a", encoding="utf-8") as jf:
            jf.write(f"{path}\n")
            jf.flush()
            os.fsync(jf.fileno())

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

        # Clear journal after successful write
        with open(self.journal_file, "w", encoding="utf-8") as jf:
            jf.truncate(0)

    def load_block_from_disk(self, block_index: int) -> Optional[Block]:
        """
        Load a single block from disk using O(1) index lookup.

        This method uses the block index for fast lookups. If the index
        is not available, it falls back to sequential scanning (legacy mode).

        Args:
            block_index: Block height to load

        Returns:
            Block object or None if not found
        """
        from xai.core.blockchain import Block, Transaction
        from xai.core.block_header import BlockHeader

        # Try index lookup first (O(1))
        if self.block_index:
            # Check cache first
            cached_block = self.block_index.cache.get(block_index)
            if cached_block:
                return cached_block

            # Look up in index
            location = self.block_index.get_block_location(block_index)
            if location:
                file_path, file_offset, file_size = location
                full_path = os.path.join(self.data_dir, file_path)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        # Seek to exact position
                        f.seek(file_offset)
                        # Read exact size
                        line = f.read(file_size)
                        block_data = json.loads(line.strip())

                        # Parse block
                        block = self._parse_block_data(block_data)

                        # Cache the parsed block
                        if block:
                            self.block_index.cache.put(block_index, block)

                        return block

                except (IOError, json.JSONDecodeError, KeyError) as e:
                    logger.error(
                        "Failed to load block from index",
                        extra={
                            "event": "storage.index_load_failed",
                            "block_index": block_index,
                            "error": str(e),
                            "file_path": file_path,
                        }
                    )
                    # Fall through to sequential scan as fallback
            else:
                # Block not in index, fall through to sequential scan
                pass

        # Fallback: sequential scan (legacy mode or index miss)
        return self._load_block_fallback(block_index)

    def _parse_block_data(self, block_data: Dict[str, Any]) -> Optional[Block]:
        """
        Parse block data dictionary into Block object.

        Supports both nested format (header: {index: ...}) and flattened format
        where header fields are at the top level for backward compatibility.

        Args:
            block_data: Block dictionary from JSON

        Returns:
            Block object or None on parse error
        """
        from xai.core.blockchain import Block, Transaction
        from xai.core.block_header import BlockHeader

        try:
            # Support both nested header format and flattened format
            # If "header" key exists and has content, use nested format
            # Otherwise, read header fields from top level (flattened format)
            if "header" in block_data and block_data["header"]:
                header_data = block_data["header"]
            else:
                # Flattened format: header fields are at the top level
                header_data = block_data

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

            transactions = []
            for tx_data in block_data["transactions"]:
                tx = Transaction(
                    tx_data["sender"],
                    tx_data["recipient"],
                    tx_data["amount"],
                    tx_data["fee"],
                    tx_data["public_key"],
                    tx_data["tx_type"],
                    tx_data.get("nonce"),
                    tx_data.get("inputs", []),
                    tx_data.get("outputs", []),
                )
                tx.timestamp = tx_data["timestamp"]
                tx.signature = tx_data["signature"]
                tx.txid = tx_data["txid"]
                tx.metadata = tx_data.get("metadata", {})
                transactions.append(tx)

            block = Block(header, transactions)
            if block_data.get("miner"):
                block.miner = block_data.get("miner")

            return block

        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "Failed to parse block data",
                extra={
                    "event": "storage.block_parse_failed",
                    "error": str(e),
                }
            )
            return None

    def _load_block_fallback(self, block_index: int) -> Optional[Block]:
        """
        Legacy sequential scan fallback for loading blocks.

        Used when index is disabled or lookup fails.
        This is the original O(n) implementation.
        Supports transparent decompression of gzip-compressed blocks.

        Args:
            block_index: Block height to load

        Returns:
            Block object or None if not found
        """
        from xai.core.blockchain import Block, Transaction
        from xai.core.block_header import BlockHeader

        # First, check for individual compressed block file (fast path for old blocks)
        compressed_path = os.path.join(self.blocks_dir, f"block_{block_index}.json.gz")
        if os.path.exists(compressed_path):
            try:
                with gzip.open(compressed_path, 'rt', encoding='utf-8') as f:
                    block_data = json.loads(f.read())
                    return self._parse_block_data(block_data)
            except (IOError, json.JSONDecodeError, KeyError) as e:
                logger.error(
                    "Failed to load compressed block %d: %s",
                    block_index,
                    type(e).__name__,
                    extra={
                        "event": "storage.compressed_block_load_failed",
                        "block_index": block_index,
                        "error": str(e),
                    }
                )
                # Fall through to regular files

        # Check for individual uncompressed block file
        uncompressed_path = os.path.join(self.blocks_dir, f"block_{block_index}.json")
        if os.path.exists(uncompressed_path):
            try:
                with open(uncompressed_path, 'r', encoding='utf-8') as f:
                    block_data = json.loads(f.read())
                    return self._parse_block_data(block_data)
            except (IOError, json.JSONDecodeError, KeyError) as e:
                logger.error(
                    "Failed to load uncompressed block %d: %s",
                    block_index,
                    type(e).__name__,
                    extra={
                        "event": "storage.uncompressed_block_load_failed",
                        "block_index": block_index,
                        "error": str(e),
                    }
                )

        # Fall back to scanning multi-block files
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("blocks_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        found_block: Optional[Block] = None
        for block_file in block_files:
            with open(os.path.join(self.blocks_dir, block_file), "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        block_data = json.loads(line)
                        # Support both nested and flattened block formats
                        if "header" in block_data and block_data["header"]:
                            data_index = block_data["header"].get("index")
                        else:
                            data_index = block_data.get("index")
                        if data_index == block_index:
                            block = self._parse_block_data(block_data)
                            if block:
                                found_block = block  # keep last occurrence to honor reorg writes
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(
                            "Failed to load block %d from disk: %s",
                            block_index,
                            type(e).__name__,
                            extra={
                                "event": "storage.block_load_failed",
                                "block_index": block_index,
                                "error": str(e),
                            }
                        )
                        continue  # Try next line instead of returning None

        return found_block

    # Legacy alias for tests that reference the previous private API name
    def _load_block_from_disk(self, block_index: int) -> Optional[Block]:
        return self.load_block_from_disk(block_index)

    def load_chain_from_disk(self) -> List[Block]:
        """Load the entire blockchain (all blocks) from disk."""
        from xai.core.blockchain import Block, Transaction
        from xai.core.block_header import BlockHeader
        
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("blocks_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        chain_map: Dict[int, Block] = {}
        for block_file in block_files:
            with open(os.path.join(self.blocks_dir, block_file), "r") as f:
                for line in f:
                    try:
                        block_data = json.loads(line)
                        # Support both nested and flattened block formats
                        if "header" in block_data and block_data["header"]:
                            header_data = block_data["header"]
                        else:
                            header_data = block_data
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
                        if "hash" in header_data:
                            header.hash = header_data["hash"]
                        transactions = []
                        for tx_data in block_data["transactions"]:
                            tx = Transaction(
                                tx_data["sender"],
                                tx_data["recipient"],
                                tx_data["amount"],
                                tx_data["fee"],
                                tx_data["public_key"],
                                tx_data["tx_type"],
                                tx_data.get("nonce"),
                                tx_data.get("inputs", []),
                                tx_data.get("outputs", []),
                            )
                            tx.timestamp = tx_data["timestamp"]
                            tx.signature = tx_data["signature"]
                            tx.txid = tx_data["txid"]
                            tx.metadata = tx_data.get("metadata", {})
                            transactions.append(tx)

                        block = Block(header, transactions)
                        if block_data.get("miner"):
                            block.miner = block_data.get("miner")
                        chain_map[header.index] = block  # overwrite with latest at height
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(
                            "Failed to load chain from disk: %s",
                            type(e).__name__,
                            extra={"event": "storage.chain_load_failed", "error": str(e)}
                        )
                        return []
        return [chain_map[idx] for idx in sorted(chain_map.keys())]

    def get_latest_block_from_disk(self) -> Optional[Block]:
        """Get the last block in the chain by loading it from disk."""
        from xai.core.blockchain import Block, Transaction
        from xai.core.block_header import BlockHeader
        
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("blocks_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
            reverse=True,
        )
        if not block_files:
            return None
        
        latest_block_file = os.path.join(self.blocks_dir, block_files[0])
        with open(latest_block_file, "r") as f:
            lines = f.readlines()
        
        if not lines:
            return None
            
        latest_block_data = json.loads(lines[-1])

        # Support both nested and flattened block formats
        if "header" in latest_block_data and latest_block_data["header"]:
            header_data = latest_block_data["header"]
        else:
            header_data = latest_block_data
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
        if "hash" in header_data:
            header.hash = header_data["hash"]
        
        transactions = []
        for tx_data in latest_block_data["transactions"]:
            tx = Transaction(
                tx_data["sender"],
                tx_data["recipient"],
                tx_data["amount"],
                tx_data["fee"],
                tx_data["public_key"],
                tx_data["tx_type"],
                tx_data.get("nonce"),
                tx_data.get("inputs", []),
                tx_data.get("outputs", []),
            )
            tx.timestamp = tx_data["timestamp"]
            tx.signature = tx_data["signature"]
            tx.txid = tx_data["txid"]
            tx.metadata = tx_data.get("metadata", {})
            transactions.append(tx)

        block = Block(header, transactions)
        return block
    
    def load_state_from_disk(self) -> Dict[str, Any]:
        """Load the blockchain state (UTXO set and pending transactions) from disk."""
        from xai.core.blockchain import Transaction

        utxo_set = {}
        pending_transactions = []

        # Load UTXO set
        if os.path.exists(self.utxo_file):
            try:
                with open(self.utxo_file, "r") as f:
                    utxo_set = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(
                    "Failed to load UTXO set from %s: %s - starting fresh",
                    self.utxo_file,
                    type(e).__name__,
                    extra={"event": "storage.utxo_load_failed", "error": str(e)}
                )
                utxo_set = {}

        # Load pending transactions
        if os.path.exists(self.pending_tx_file):
            try:
                with open(self.pending_tx_file, "r") as f:
                    pending_tx_data = json.load(f)
                    for tx_data in pending_tx_data:
                        tx = Transaction(
                            tx_data["sender"],
                            tx_data["recipient"],
                            tx_data["amount"],
                            tx_data["fee"],
                            tx_data["public_key"],
                            tx_data["tx_type"],
                            tx_data.get("nonce"),
                            tx_data.get("inputs", []),
                            tx_data.get("outputs", []),
                        )
                        tx.timestamp = tx_data["timestamp"]
                        tx.signature = tx_data["signature"]
                        tx.txid = tx_data["txid"]
                        tx.metadata = tx_data.get("metadata", {})
                        pending_transactions.append(tx)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(
                    "Failed to load pending transactions from %s: %s - starting fresh",
                    self.pending_tx_file,
                    type(e).__name__,
                    extra={"event": "storage.pending_tx_load_failed", "error": str(e)}
                )
                pending_transactions = []

        contracts_state = {}
        if os.path.exists(self.contracts_file):
            try:
                with open(self.contracts_file, "r") as f:
                    raw_contracts = json.load(f)
                    for address, entry in raw_contracts.items():
                        code = entry.get("code", "")
                        if isinstance(code, str):
                            try:
                                code_bytes = bytes.fromhex(code)
                            except ValueError:
                                code_bytes = code.encode("utf-8")
                        else:
                            code_bytes = code
                        contracts_state[address] = {
                            "creator": entry.get("creator"),
                            "code": code_bytes,
                            "storage": entry.get("storage", {}),
                            "gas_limit": entry.get("gas_limit"),
                            "balance": entry.get("balance"),
                            "created_at": entry.get("created_at"),
                        }
            except (json.JSONDecodeError, KeyError):
                contracts_state = {}

        receipts: List[Dict[str, Any]] = []
        if os.path.exists(self.receipts_file):
            try:
                with open(self.receipts_file, "r") as f:
                    receipts = json.load(f)
            except (json.JSONDecodeError, KeyError):
                receipts = []

        return {
            "utxo_set": utxo_set,
            "pending_transactions": pending_transactions,
            "contracts": contracts_state,
            "receipts": receipts,
        }

    def handle_reorg(self, fork_point: int) -> None:
        """
        Handle blockchain reorganization by invalidating index entries.

        Called when a reorg occurs to ensure index consistency.
        Removes all blocks from fork_point onwards from the index.

        Args:
            fork_point: Block height where the fork occurred
        """
        if self.block_index:
            removed = self.block_index.remove_blocks_from(fork_point)
            logger.info(
                "Index updated for reorg",
                extra={
                    "event": "storage.reorg_handled",
                    "fork_point": fork_point,
                    "blocks_removed": removed,
                }
            )

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get block index statistics.

        Returns:
            Dictionary with index statistics or empty dict if index disabled
        """
        if self.block_index:
            return self.block_index.get_stats()
        return {"enabled": False}

    def close(self) -> None:
        """
        Clean shutdown of storage subsystem.

        Closes database connections and flushes caches.
        """
        if self.block_index:
            self.block_index.close()
            logger.info("Block index closed", extra={"event": "storage.closed"})
