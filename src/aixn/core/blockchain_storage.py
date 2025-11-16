"""
XAI Blockchain - Blockchain Storage Manager

Handles all disk I/O operations for the blockchain, including saving and loading
blocks, the UTXO set, and pending transactions.
"""

import hashlib
import json
import os
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aixn.core.blockchain import Block, Transaction


class BlockchainStorage:
    """
    Manages the persistence of blockchain data to disk.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.blocks_dir = os.path.join(self.data_dir, "blocks")
        os.makedirs(self.blocks_dir, exist_ok=True)
        self.utxo_file = os.path.join(self.data_dir, "utxo_set.json")
        self.pending_tx_file = os.path.join(self.data_dir, "pending_transactions.json")

    def _save_block_to_disk(self, block: "Block"):
        """Save a single block to its file."""
        block_file = os.path.join(self.blocks_dir, f"block_{block.index}.json")
        with open(block_file, "w") as f:
            json.dump(block.to_dict(), f, indent=2)

    def save_state_to_disk(self, utxo_manager, pending_transactions: List["Transaction"]):
        """Save the blockchain state (UTXO set and pending transactions) to disk."""
        # Save UTXO set
        with open(self.utxo_file, "w") as f:
            json.dump(utxo_manager.to_dict(), f, indent=2)

        # Save pending transactions
        pending_tx_data = [tx.to_dict() for tx in pending_transactions]
        with open(self.pending_tx_file, "w") as f:
            json.dump(pending_tx_data, f, indent=2)

    def _load_block_from_disk(self, block_index: int) -> Optional["Block"]:
        """Load a single block from its file."""
        from aixn.core.blockchain import Block, Transaction

        block_file = os.path.join(self.blocks_dir, f"block_{block_index}.json")
        if not os.path.exists(block_file):
            return None
        try:
            with open(block_file, "r") as f:
                block_data = json.load(f)
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
                transactions.append(tx)

            block = Block(
                block_data["index"],
                transactions,
                block_data["previous_hash"],
                block_data["difficulty"],
            )
            block.timestamp = block_data["timestamp"]
            block.nonce = block_data["nonce"]
            block.hash = block_data["hash"]
            block.merkle_root = block_data["merkle_root"]
            return block
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading block {block_index} from disk: {e}")
            return None

    def load_state_from_disk(self) -> Dict:
        """Load the blockchain state (UTXO set and pending transactions) from disk."""
        from aixn.core.blockchain import Transaction

        utxo_set = {}
        pending_transactions = []

        # Load UTXO set
        if os.path.exists(self.utxo_file):
            try:
                with open(self.utxo_file, "r") as f:
                    utxo_set = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading UTXO set: {e}. Starting fresh.")
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
                        pending_transactions.append(tx)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading pending transactions: {e}. Starting fresh.")
                pending_transactions = []

        return {"utxo_set": utxo_set, "pending_transactions": pending_transactions}

    def load_chain_from_disk(self) -> List["Block"]:
        """Load the entire blockchain (all blocks) from disk."""
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("block_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
        )

        chain = []
        for block_file in block_files:
            block_index = int(block_file.split("_")[1].split(".")[0])
            block = self._load_block_from_disk(block_index)
            if block:
                chain.append(block)
            else:
                print(f"Failed to load block {block_index}. Data might be corrupted.")
                # Depending on desired behavior, might raise an exception or return partial chain
                return []
        return chain

    def get_latest_block_from_disk(self) -> Optional["Block"]:
        """Get the last block in the chain by loading it from disk."""
        block_files = sorted(
            [
                f
                for f in os.listdir(self.blocks_dir)
                if f.startswith("block_") and f.endswith(".json")
            ],
            key=lambda x: int(x.split("_")[1].split(".")[0]),
            reverse=True,
        )
        if not block_files:
            return None
        latest_block_index = int(block_files[0].split("_")[1].split(".")[0])
        latest_block = self._load_block_from_disk(latest_block_index)
        return latest_block
