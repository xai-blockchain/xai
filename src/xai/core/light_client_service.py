"""
Light client utilities for mobile and constrained devices.

Provides compact block headers, checkpoints, and simple merkle proofs so
phones can sync quickly without downloading the entire chain.

SPV (Simplified Payment Verification):
    Light clients can verify transactions without downloading the full blockchain
    by checking merkle proofs against block headers. The proof demonstrates that
    a transaction is included in a block without revealing all other transactions.

Security Considerations:
    - Light clients trust that the longest chain represents the valid chain
    - They should verify multiple block confirmations before considering a tx final
    - For high-value transactions, consider using a full node for verification
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MerkleProofError(Exception):
    """Raised when merkle proof verification fails."""
    pass


def verify_merkle_proof(
    txid: str,
    merkle_root: str,
    proof: List[Dict[str, str]],
) -> bool:
    """
    Verify a merkle proof for a transaction.

    This is the core SPV verification function. Given a transaction ID,
    the expected merkle root, and a proof path, this function reconstructs
    the merkle root by hashing up the tree and compares it to the expected value.

    Args:
        txid: The transaction ID (hex string) to verify
        merkle_root: The expected merkle root from the block header
        proof: List of proof steps, each containing:
            - "hash": sibling hash at this level
            - "position": "left" or "right" indicating sibling position

    Returns:
        True if the proof is valid, False otherwise

    Example:
        >>> proof = [
        ...     {"hash": "abc...", "position": "right"},
        ...     {"hash": "def...", "position": "left"},
        ... ]
        >>> verify_merkle_proof("123...", "root_hash...", proof)
        True
    """
    if not txid:
        logger.warning("Empty txid provided for merkle verification")
        return False

    if not merkle_root:
        logger.warning("Empty merkle root provided for verification")
        return False

    # Start with the transaction hash
    current_hash = txid

    # Walk up the tree using the proof
    for step in proof:
        sibling_hash = step.get("hash", "")
        position = step.get("position", "")

        if not sibling_hash:
            logger.warning(
                "Invalid proof step: missing sibling hash",
                extra={"event": "spv.invalid_proof_step"}
            )
            return False

        # Combine current hash with sibling based on position
        if position == "left":
            # Sibling is on the left, so sibling comes first
            combined = sibling_hash + current_hash
        elif position == "right":
            # Sibling is on the right, so current comes first
            combined = current_hash + sibling_hash
        else:
            logger.warning(
                f"Invalid proof step: unknown position '{position}'",
                extra={"event": "spv.invalid_position"}
            )
            return False

        # Hash the combination to get the parent node
        current_hash = hashlib.sha256(combined.encode()).hexdigest()

    # Final hash should match the merkle root
    is_valid = current_hash == merkle_root

    if is_valid:
        logger.debug(
            "Merkle proof verified successfully",
            extra={"event": "spv.proof_verified", "txid": txid[:16] + "..."}
        )
    else:
        logger.warning(
            "Merkle proof verification failed",
            extra={
                "event": "spv.proof_failed",
                "txid": txid[:16] + "...",
                "computed_root": current_hash[:16] + "...",
                "expected_root": merkle_root[:16] + "..."
            }
        )

    return is_valid


def verify_transaction_inclusion(
    txid: str,
    block_header: Dict[str, Any],
    proof: List[Dict[str, str]],
    min_confirmations: int = 6,
    current_height: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Verify that a transaction is included in a block with sufficient confirmations.

    This is a higher-level SPV verification that checks:
    1. The merkle proof is valid
    2. The block has sufficient confirmations (if current_height provided)

    Args:
        txid: Transaction ID to verify
        block_header: Block header containing merkle_root and index
        proof: Merkle proof path
        min_confirmations: Minimum confirmations required (default 6)
        current_height: Current blockchain height for confirmation check

    Returns:
        Tuple of (is_valid, message)
        - is_valid: True if transaction is verified with sufficient confirmations
        - message: Human-readable status message
    """
    # Verify merkle proof
    merkle_root = block_header.get("merkle_root", "")
    if not verify_merkle_proof(txid, merkle_root, proof):
        return False, "Merkle proof verification failed"

    # Check confirmations if current height provided
    block_index = block_header.get("index", 0)
    if current_height is not None:
        confirmations = current_height - block_index + 1
        if confirmations < min_confirmations:
            return False, f"Insufficient confirmations: {confirmations}/{min_confirmations}"

        logger.info(
            "Transaction verified with confirmations",
            extra={
                "event": "spv.tx_verified",
                "txid": txid[:16] + "...",
                "confirmations": confirmations,
                "block_index": block_index
            }
        )
        return True, f"Verified with {confirmations} confirmations"

    return True, "Merkle proof valid (confirmation count not checked)"


class LightClientService:
    """Expose lightweight proofs for mobile wallets."""

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def get_recent_headers(
        self, count: int = 20, start_index: Optional[int] = None
    ) -> Dict[str, Any]:
        chain = self.blockchain.chain
        if not chain:
            return {"latest_height": -1, "headers": [], "range": {"start": 0, "end": -1}}

        latest_height = len(chain) - 1
        count = max(1, min(count, 200))

        if start_index is None:
            start_index = max(0, latest_height - count + 1)

        start_index = max(0, min(start_index, latest_height))
        end_index = min(latest_height, start_index + count - 1)

        headers = [self._serialize_header(chain[i]) for i in range(start_index, end_index + 1)]

        return {
            "latest_height": latest_height,
            "headers": headers,
            "range": {"start": start_index, "end": end_index},
        }

    def get_checkpoint(self) -> Dict[str, Any]:
        """Return the latest header and pending transaction count."""
        chain = self.blockchain.chain
        if not chain:
            return {"latest_header": None, "height": -1, "pending_transactions": 0}

        latest_block = chain[-1]
        return {
            "latest_header": self._serialize_header(latest_block),
            "height": latest_block.index,
            "pending_transactions": len(self.blockchain.pending_transactions),
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
                "block_index": block.index,
                "block_hash": block.hash,
                "merkle_root": block.merkle_root,
                "header": self._serialize_header(block),
                "transaction": target_tx.to_dict(),
                "proof": proof,
            }

        return None

    def verify_proof(
        self,
        txid: str,
        proof_data: Dict[str, Any],
        min_confirmations: int = 6,
    ) -> Tuple[bool, str]:
        """
        Verify a transaction proof returned by get_transaction_proof.

        This method provides SPV verification for light clients to verify
        that a transaction is included in the blockchain.

        Args:
            txid: Transaction ID to verify
            proof_data: Proof data from get_transaction_proof()
            min_confirmations: Minimum block confirmations required

        Returns:
            Tuple of (is_valid, message)
        """
        if not proof_data:
            return False, "No proof data provided"

        # Extract proof components
        block_header = proof_data.get("header", {})
        merkle_root = proof_data.get("merkle_root", "")
        proof = proof_data.get("proof", [])

        # Verify the txid matches
        tx_data = proof_data.get("transaction", {})
        if tx_data.get("txid") != txid:
            return False, f"Transaction ID mismatch in proof"

        # Verify merkle proof
        if not verify_merkle_proof(txid, merkle_root, proof):
            return False, "Merkle proof verification failed"

        # Check block is in chain
        block_index = proof_data.get("block_index", -1)
        if block_index < 0 or block_index >= len(self.blockchain.chain):
            return False, "Block index not found in chain"

        # Verify block hash matches
        chain_block = self.blockchain.chain[block_index]
        expected_hash = proof_data.get("block_hash", "")
        actual_hash = chain_block.hash or chain_block.calculate_hash()
        if expected_hash != actual_hash:
            return False, "Block hash mismatch - possible chain reorganization"

        # Check confirmations
        current_height = len(self.blockchain.chain) - 1
        confirmations = current_height - block_index + 1

        if confirmations < min_confirmations:
            return False, f"Insufficient confirmations: {confirmations}/{min_confirmations}"

        logger.info(
            "SPV verification successful",
            extra={
                "event": "spv.verification_complete",
                "txid": txid[:16] + "...",
                "block_index": block_index,
                "confirmations": confirmations
            }
        )

        return True, f"Transaction verified with {confirmations} confirmations"

    def _serialize_header(self, block) -> Dict[str, Any]:
        """Return the compact header for a block object."""
        # Some historical blocks may not have hash precomputed.
        block_hash = block.hash or block.calculate_hash()
        return {
            "index": block.index,
            "hash": block_hash,
            "previous_hash": block.previous_hash,
            "merkle_root": block.merkle_root,
            "timestamp": block.timestamp,
            "difficulty": block.difficulty,
            "nonce": block.nonce,
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

            proof.append(
                {"position": "left" if is_right else "right", "hash": working_layer[sibling_index]}
            )

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
