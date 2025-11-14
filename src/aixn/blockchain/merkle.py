import hashlib
import json

class MerkleTree:
    def __init__(self, data_leaves):
        if not data_leaves:
            raise ValueError("Merkle tree requires at least one data leaf.")
        self.data_leaves = [self._hash_leaf(leaf) for leaf in data_leaves]
        self.tree = self._build_tree(self.data_leaves)
        self.root = self.tree[-1][0] if self.tree else None

    def _hash_leaf(self, leaf_data):
        # Ensure consistent hashing for leaf data
        if isinstance(leaf_data, dict) or isinstance(leaf_data, list):
            return hashlib.sha256(json.dumps(leaf_data, sort_keys=True).encode()).hexdigest()
        return hashlib.sha256(str(leaf_data).encode()).hexdigest()

    def _hash_pair(self, hash1, hash2):
        # Ensure consistent ordering for hashing pairs
        if hash1 is None:
            return hash2
        if hash2 is None:
            return hash1
        
        # Sort hashes to ensure deterministic tree construction
        if hash1 > hash2:
            hash1, hash2 = hash2, hash1
        return hashlib.sha256((hash1 + hash2).encode()).hexdigest()

    def _build_tree(self, leaves):
        tree = [leaves]
        current_level = leaves
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                hash1 = current_level[i]
                hash2 = current_level[i+1] if i+1 < len(current_level) else hash1 # Duplicate last hash if odd number
                next_level.append(self._hash_pair(hash1, hash2))
            tree.append(next_level)
            current_level = next_level
        return tree

    def get_root(self):
        return self.root

    def generate_merkle_proof(self, leaf_data):
        leaf_hash = self._hash_leaf(leaf_data)
        if leaf_hash not in self.data_leaves:
            raise ValueError("Leaf data not found in the Merkle tree.")

        proof = []
        leaf_index = self.data_leaves.index(leaf_hash)

        for level in self.tree[:-1]: # Iterate through levels from leaves up to root-1
            if len(level) == 1: # If only one hash in the level, it's the root
                break
            
            is_left_node = (leaf_index % 2 == 0)
            sibling_index = leaf_index + 1 if is_left_node else leaf_index - 1

            if sibling_index < len(level):
                sibling_hash = level[sibling_index]
                proof.append((sibling_hash, "left" if not is_left_node else "right"))
            elif not is_left_node and sibling_index >= len(level): # Handle duplicated last hash
                proof.append((level[leaf_index], "left")) # Sibling is itself

            leaf_index //= 2 # Move up to the next level

        return proof

    @staticmethod
    def verify_merkle_proof(leaf_data, merkle_root, proof):
        current_hash = MerkleTree._hash_leaf(leaf_data)

        for sibling_hash, position in proof:
            if position == "left":
                current_hash = MerkleTree._hash_pair(sibling_hash, current_hash)
            else: # position == "right"
                current_hash = MerkleTree._hash_pair(current_hash, sibling_hash)
        
        return current_hash == merkle_root

# Example Usage (for testing purposes)
if __name__ == "__main__":
    transactions = [
        {"from": "A", "to": "B", "amount": 10},
        {"from": "B", "to": "C", "amount": 5},
        {"from": "C", "to": "D", "amount": 12},
        {"from": "D", "to": "A", "amount": 3},
        {"from": "E", "to": "F", "amount": 7} # Odd number of transactions
    ]

    merkle_tree = MerkleTree(transactions)
    print(f"Merkle Root: {merkle_tree.get_root()}")

    # Test a transaction
    tx_to_prove = {"from": "B", "to": "C", "amount": 5}
    proof = merkle_tree.generate_merkle_proof(tx_to_prove)
    print(f"Proof for {tx_to_prove}: {proof}")

    is_valid = MerkleTree.verify_merkle_proof(tx_to_prove, merkle_tree.get_root(), proof)
    print(f"Is proof valid? {is_valid}")

    # Test an invalid transaction
    invalid_tx = {"from": "X", "to": "Y", "amount": 100}
    try:
        merkle_tree.generate_merkle_proof(invalid_tx)
    except ValueError as e:
        print(f"Error generating proof for invalid tx: {e}")

    # Test with a tampered transaction
    tampered_tx = {"from": "B", "to": "C", "amount": 6} # Changed amount
    is_tampered_valid = MerkleTree.verify_merkle_proof(tampered_tx, merkle_tree.get_root(), proof)
    print(f"Is tampered proof valid? {is_tampered_valid}")