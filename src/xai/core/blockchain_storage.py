"""
XAI Blockchain - Blockchain Storage Manager

Handles all disk I/O operations for the blockchain, including saving and loading
blocks, the UTXO set, and pending transactions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import List, Dict, Optional, TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Transaction
    from xai.core.block_header import BlockHeader


MAX_BLOCK_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

class BlockchainStorage:
    """
    Manages the persistence of blockchain data to disk.
    """

    def __init__(self, data_dir: str = "data", compact_on_startup: bool = False) -> None:
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


    def _save_block_to_disk(self, block: Block) -> None:
        """Save a single block to its file with durable append.

        Uses fsync after write to ensure block data is persisted to disk
        before the function returns. This prevents data loss on power failure
        or system crash.
        """
        block_file = os.path.join(self.blocks_dir, f"blocks_{self.block_file_index}.json")

        if os.path.exists(block_file) and os.path.getsize(block_file) > MAX_BLOCK_FILE_SIZE:
            self.block_file_index += 1
            block_file = os.path.join(self.blocks_dir, f"blocks_{self.block_file_index}.json")

        with open(block_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(block.to_dict()) + "\n")
            f.flush()
            os.fsync(f.fileno())
    
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
        """Load a single block from its file."""
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

        found_block: Optional[Block] = None
        for block_file in block_files:
            with open(os.path.join(self.blocks_dir, block_file), "r") as f:
                for line in f:
                    try:
                        block_data = json.loads(line)
                        if block_data["header"]["index"] == block_index:
                            header_data = block_data.get("header", {})
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
                            found_block = block  # keep last occurrence to honor reorg writes
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(
                            "Failed to load block %d from disk: %s",
                            block_index,
                            type(e).__name__,
                            extra={"event": "storage.block_load_failed", "block_index": block_index, "error": str(e)}
                        )
                        return None
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
                        header_data = block_data.get("header", {})
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
        
        header_data = latest_block_data.get("header", {})
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
