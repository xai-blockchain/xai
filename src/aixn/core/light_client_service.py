"""
Light client utilities for mobile and constrained devices.

Provides compact block headers, checkpoints, and simple merkle proofs so
phones can sync quickly without downloading the entire chain.
"""

import hashlib
from typing import Any, Dict, List, Optional


class LightClientService:
    """Expose lightweight proofs for mobile wallets."""

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def get_recent_headers(self, count: int = 20, start_index: Optional[int] = None) -> Dict[str, Any]:
        chain = self.blockchain.chain
        if not chain:
            return {
                'latest_height': -1,
                'headers': [],
                'range': {'start': 0, 'end': -1}
            }

        latest_height = len(chain) - 1
        count = max(1, min(count, 200))

        if start_index is None:
            start_index = max(0, latest_height - count + 1)

        start_index = max(0, min(start_index, latest_height))
        end_index = min(latest_height, start_index + count - 1)

        headers = [
            self._serialize_header(chain[i])
            for i in range(start_index, end_index + 1)
        ]

        return {
            'latest_height': latest_height,
            'headers': headers,
            'range': {'start': start_index, 'end': end_index}
        }

    def get_checkpoint(self) -> Dict[str, Any]:
        """Return the latest header and pending transaction count."""
        chain = self.blockchain.chain
        if not chain:
            return {
                'latest_header': None,
                'height': -1,
                'pending_transactions': 0
            }

        latest_block = chain[-1]
        return {
            'latest_header': self._serialize_header(latest_block),
            'height': latest_block.index,
            'pending_transactions': len(self.blockchain.pending_transactions)
        }

    def get_transaction_proof(self, txid: str) -> Optional[Dict[str, Any]]:
        """Return a merkle proof for a transaction, if present on-chain."""
        for block in reversed(self.blockchain.chain):
            proof = self._build_merkle_proof(block, txid)
            if proof is None:
                continue

            target_tx = next((tx for tx in block.transactions if tx.txid == txid), None)
            if not target_tx:
                continue

            return {
                'block_index': block.index,
                'block_hash': block.hash,
                'merkle_root': block.merkle_root,
                'header': self._serialize_header(block),
                'transaction': target_tx.to_dict(),
                'proof': proof
            }

        return None

    def _serialize_header(self, block) -> Dict[str, Any]:
        """Return the compact header for a block object."""
        # Some historical blocks may not have hash precomputed.
        block_hash = block.hash or block.calculate_hash()
        return {
            'index': block.index,
            'hash': block_hash,
            'previous_hash': block.previous_hash,
            'merkle_root': block.merkle_root,
            'timestamp': block.timestamp,
            'difficulty': block.difficulty,
            'nonce': block.nonce,
        }

    def _build_merkle_proof(self, block, txid: str) -> Optional[List[Dict[str, str]]]:
        """Construct a merkle proof for the provided transaction ID."""
        tx_hashes = [tx.txid for tx in block.transactions]
        if txid not in tx_hashes:
            return None

        index = tx_hashes.index(txid)
        layers = self._build_merkle_layers(tx_hashes)
        proof: List[Dict[str, str]] = []

        for layer in layers[:-1]:
            working_layer = list(layer)
            if len(working_layer) % 2 != 0:
                working_layer.append(working_layer[-1])

            is_right = index % 2 == 1
            sibling_index = index - 1 if is_right else index + 1
            sibling_index = min(sibling_index, len(working_layer) - 1)

            proof.append({
                'position': 'left' if is_right else 'right',
                'hash': working_layer[sibling_index]
            })

            index //= 2

        return proof

    def _build_merkle_layers(self, tx_hashes: List[str]) -> List[List[str]]:
        layers = [tx_hashes]

        while len(layers[-1]) > 1:
            current_layer = list(layers[-1])
            if len(current_layer) % 2 != 0:
                current_layer.append(current_layer[-1])

            next_layer = []
            for i in range(0, len(current_layer), 2):
                combined = current_layer[i] + current_layer[i + 1]
                next_layer.append(hashlib.sha256(combined.encode()).hexdigest())

            layers.append(next_layer)

        return layers
