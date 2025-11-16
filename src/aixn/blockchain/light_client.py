from typing import Dict, Any, List, Tuple
import hashlib
import json
from src.aixn.blockchain.merkle import MerkleTree  # Import MerkleTree


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
            print(
                f"Warning: Header for block {header.block_number} is older or same as latest. Not syncing."
            )
            return

        self.trusted_headers[header.block_number] = header
        self.latest_block_number = header.block_number
        print(f"Light client for {self.chain_id} synced header for block {header.block_number}.")

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
            print(f"Verification failed: {e}")
            return False

        # In this simplified model, we assume the Merkle proof is against the transactions_root.
        # In a more complex system, it could be against a state_root for state changes.
        is_included = MerkleTree.verify_merkle_proof(
            transaction_data, header.transactions_root, merkle_proof
        )

        if is_included:
            print(
                f"Transaction successfully verified for inclusion in {self.chain_id} at block {block_number}."
            )
        else:
            print(
                f"Transaction FAILED verification for inclusion in {self.chain_id} at block {block_number}."
            )

        return is_included


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Initialize a light client for "SourceChainA"
    light_client_a = LightClient("SourceChainA")

    # Simulate some transactions for a block on SourceChainA
    tx1 = {"from": "Alice", "to": "Bob", "amount": 10}
    tx2 = {"from": "Bob", "to": "Charlie", "amount": 5}
    tx3 = {"from": "Charlie", "to": "Alice", "amount": 12}

    block_transactions = [tx1, tx2, tx3]
    transactions_merkle_tree = MerkleTree(block_transactions)
    transactions_root = transactions_merkle_tree.get_root()

    # Simulate a block header for block 100
    header_100 = BlockHeader(
        block_number=100,
        prev_block_hash="0xprevhash99",
        state_root="0xstateroot100",
        transactions_root=transactions_root,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
    )
    light_client_a.sync_header(header_100)

    # Simulate another block header for block 101
    header_101 = BlockHeader(
        block_number=101,
        prev_block_hash=header_100.block_hash,
        state_root="0xstateroot101",
        transactions_root="0xtxroot101",  # Different transactions root for this block
        timestamp=int(datetime.now(timezone.utc).timestamp()) + 60,
    )
    light_client_a.sync_header(header_101)

    # Generate a Merkle proof for tx1 from block 100
    proof_for_tx1 = transactions_merkle_tree.generate_merkle_proof(tx1)

    print("\n--- Verifying transaction inclusion in block 100 ---")
    is_tx1_included = light_client_a.verify_transaction_inclusion(tx1, proof_for_tx1, 100)
    print(f"Is tx1 included in block 100? {is_tx1_included}")

    print("\n--- Verifying a tampered transaction ---")
    tampered_tx1 = {"from": "Alice", "to": "Bob", "amount": 11}  # Tampered amount
    is_tampered_tx1_included = light_client_a.verify_transaction_inclusion(
        tampered_tx1, proof_for_tx1, 100
    )
    print(f"Is tampered tx1 included in block 100? {is_tampered_tx1_included}")

    print("\n--- Verifying transaction inclusion in a different block (should fail) ---")
    is_tx1_included_in_101 = light_client_a.verify_transaction_inclusion(tx1, proof_for_tx1, 101)
    print(f"Is tx1 included in block 101? {is_tx1_included_in_101}")

    print("\n--- Verifying with an unknown block number ---")
    is_tx1_included_in_99 = light_client_a.verify_transaction_inclusion(tx1, proof_for_tx1, 99)
    print(f"Is tx1 included in block 99? {is_tx1_included_in_99}")
