import logging
from typing import Dict, Any, List, Tuple
import hashlib
from .merkle import MerkleTree  # Import MerkleTree

logger = logging.getLogger("xai.blockchain.light_client")


class BlockHeader:
    def __init__(
        self,
        block_number: int,
        prev_block_hash: str,
        state_root: str,
        transactions_root: str,
        timestamp: int,
    ):
        if not isinstance(block_number, int) or block_number < 0:
            raise ValueError("Block number must be a non-negative integer.")
        if not prev_block_hash or not state_root or not transactions_root:
            raise ValueError("Block hashes and roots cannot be empty.")
        if not isinstance(timestamp, int) or timestamp <= 0:
            raise ValueError("Timestamp must be a positive integer.")

        self.block_number = block_number
        self.prev_block_hash = prev_block_hash
        self.state_root = state_root
        self.transactions_root = transactions_root
        self.timestamp = timestamp
        self.block_hash = self._calculate_block_hash()

    def _calculate_block_hash(self) -> str:
        header_string = f"{self.block_number}{self.prev_block_hash}{self.state_root}{self.transactions_root}{self.timestamp}"
        return hashlib.sha256(header_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_number": self.block_number,
            "prev_block_hash": self.prev_block_hash,
            "state_root": self.state_root,
            "transactions_root": self.transactions_root,
            "timestamp": self.timestamp,
            "block_hash": self.block_hash,
        }

    def __repr__(self):
        return (
            f"BlockHeader(block={self.block_number}, hash='{self.block_hash[:8]}...', "
            f"state_root='{self.state_root[:8]}...')"
        )


class LightClient:
    def __init__(self, chain_id: str):
        self.chain_id = chain_id
        self.trusted_headers: Dict[int, BlockHeader] = {}  # {block_number: BlockHeader}
        self.latest_block_number = -1

    def sync_header(self, header: BlockHeader):
        """
        Adds a new block header to the light client's trusted chain.
        In a real light client, this would involve verifying the header's PoW/PoS
        and linking it to a previous trusted header. Here, we simply store it.
        """
        if header.block_number <= self.latest_block_number:
            logger.warning(
                "Header for block %s is older or same as latest (%s). Skipping.",
                header.block_number,
                self.latest_block_number,
            )
            return

        self.trusted_headers[header.block_number] = header
        self.latest_block_number = header.block_number
        logger.info("Light client %s synced header #%s.", self.chain_id, header.block_number)

    def get_header(self, block_number: int) -> BlockHeader:
        header = self.trusted_headers.get(block_number)
        if not header:
            raise ValueError(
                f"Header for block {block_number} not found in light client for {self.chain_id}."
            )
        return header

    def verify_transaction_inclusion(
        self, transaction_data: Any, merkle_proof: List[Tuple[str, str]], block_number: int
    ) -> bool:
        """
        Verifies that a transaction is included in a specific block of the source chain
        by checking its Merkle proof against the transactions_root in the block header.
        """
        try:
            header = self.get_header(block_number)
        except ValueError as e:
            logger.warning("Verification failed: %s", e)
            return False

        # In this simplified model, we assume the Merkle proof is against the transactions_root.
        # In a more complex system, it could be against a state_root for state changes.
        is_included = MerkleTree.verify_merkle_proof(
            transaction_data, header.transactions_root, merkle_proof
        )

        if is_included:
            logger.info(
                "Transaction verified in %s block %s.",
                self.chain_id,
                block_number,
            )
        else:
            logger.warning(
                "Transaction failed verification in %s block %s.",
                self.chain_id,
                block_number,
            )

        return is_included

