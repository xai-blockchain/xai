from typing import Dict, Any, List, Tuple
from src.aixn.blockchain.merkle import MerkleTree # Import MerkleTree

class StateRootVerifier:
    def __init__(self):
        # In a real system, these would be fetched from a light client or a trusted oracle
        # and would be updated regularly. For this mock, we'll pre-populate some.
        # Format: {chain_id: {block_number: state_root_hash}}
        self.trusted_state_roots: Dict[str, Dict[int, str]] = {
            "SourceChainA": {
                100: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
                101: "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b3",
                102: "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b4",
            },
            "SourceChainB": {
                50: "x1y2z3w4e5r6t7y8u9i0o1p2a3s4d5f6g7h8j9k0l1z2x3c4v5b6n7m8q9w0e1",
                51: "y2z3w4e5r6t7y8u9i0o1p2a3s4d5f6g7h8j9k0l1z2x3c4v5b6n7m8q9w0e2",
            }
        }

    def add_trusted_state_root(self, chain_id: str, block_number: int, state_root: str):
        """Adds a new trusted state root for a given chain and block number."""
        if chain_id not in self.trusted_state_roots:
            self.trusted_state_roots[chain_id] = {}
        self.trusted_state_roots[chain_id][block_number] = state_root
        print(f"Added trusted state root for {chain_id} at block {block_number}: {state_root[:10]}...")

    def get_state_root(self, chain_id: str, block_number: int) -> str:
        """Retrieves a trusted state root for a given chain and block number."""
        chain_roots = self.trusted_state_roots.get(chain_id)
        if not chain_roots:
            raise ValueError(f"No trusted state roots found for chain ID: {chain_id}")
        state_root = chain_roots.get(block_number)
        if not state_root:
            raise ValueError(f"No trusted state root found for {chain_id} at block {block_number}")
        return state_root

    def verify_inclusion(self, data: Any, merkle_proof: List[Tuple[str, str]],
                         chain_id: str, block_number: int) -> bool:
        """
        Verifies that a piece of data is included in the state of a source chain
        at a specific block number, using a Merkle proof and a trusted state root.
        """
        try:
            trusted_root = self.get_state_root(chain_id, block_number)
        except ValueError as e:
            print(f"Verification failed: {e}")
            return False

        is_included = MerkleTree.verify_merkle_proof(data, trusted_root, merkle_proof)

        if is_included:
            print(f"Data successfully verified for inclusion in {chain_id} at block {block_number}.")
        else:
            print(f"Data FAILED verification for inclusion in {chain_id} at block {block_number}.")
        
        return is_included

# Example Usage (for testing purposes)
if __name__ == "__main__":
    verifier = StateRootVerifier()

    # Simulate some data on SourceChainA at block 101
    transaction_data = {"from": "Alice", "to": "Bob", "amount": 50, "asset": "TokenX"}
    
    # To generate a Merkle proof, we need a Merkle tree from the source chain's state
    # For this example, let's assume the state root at block 101 was built from these leaves:
    mock_source_chain_leaves = [
        {"from": "Charlie", "to": "David", "amount": 100, "asset": "TokenY"},
        transaction_data, # Our transaction is included here
        {"from": "Eve", "to": "Frank", "amount": 20, "asset": "TokenZ"},
    ]
    mock_merkle_tree = MerkleTree(mock_source_chain_leaves)
    
    # Ensure the mock_merkle_tree's root matches the trusted_state_roots for block 101
    # In a real system, this would be a critical check.
    if mock_merkle_tree.get_root() != verifier.get_state_root("SourceChainA", 101):
        print("Warning: Mock Merkle tree root does not match trusted state root. Adjusting for example.")
        # For the example to work, we'll update the trusted root to match our mock tree
        verifier.add_trusted_state_root("SourceChainA", 101, mock_merkle_tree.get_root())

    merkle_proof_for_tx = mock_merkle_tree.generate_merkle_proof(transaction_data)

    print("\n--- Verifying a valid transaction ---")
    is_valid_tx = verifier.verify_inclusion(
        data=transaction_data,
        merkle_proof=merkle_proof_for_tx,
        chain_id="SourceChainA",
        block_number=101
    )
    print(f"Is transaction validly included? {is_valid_tx}")

    print("\n--- Verifying a tampered transaction ---")
    tampered_transaction_data = {"from": "Alice", "to": "Bob", "amount": 51, "asset": "TokenX"} # Tampered amount
    is_tampered_tx_valid = verifier.verify_inclusion(
        data=tampered_transaction_data,
        merkle_proof=merkle_proof_for_tx, # Same proof, but data is different
        chain_id="SourceChainA",
        block_number=101
    )
    print(f"Is tampered transaction validly included? {is_tampered_tx_valid}")

    print("\n--- Verifying with an unknown state root ---")
    unknown_data = {"some": "data"}
    try:
        verifier.verify_inclusion(
            data=unknown_data,
            merkle_proof=[],
            chain_id="SourceChainA",
            block_number=999 # Unknown block
        )
    except ValueError as e:
        print(f"Error (expected): {e}")
