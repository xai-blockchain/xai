import pytest

from xai.blockchain.merkle import MerkleTree
from xai.blockchain.state_root_verifier import StateRootVerifier


def test_merkle_tree_and_proof_verification():
    leaves = [
        {"tx": "A"},
        {"tx": "B"},
        {"tx": "C"},
    ]
    tree = MerkleTree(leaves)
    root = tree.get_root()
    proof = tree.generate_merkle_proof({"tx": "B"})
    assert MerkleTree.verify_merkle_proof({"tx": "B"}, root, proof) is True
    assert MerkleTree.verify_merkle_proof({"tx": "X"}, root, proof) is False


def test_state_root_verifier_add_and_verify():
    verifier = StateRootVerifier()
    leaves = [{"tx": "1"}, {"tx": "2"}]
    tree = MerkleTree(leaves)
    root = tree.get_root()
    verifier.add_trusted_state_root("chainA", 1, root)
    proof = tree.generate_merkle_proof({"tx": "1"})
    assert verifier.verify_inclusion({"tx": "1"}, proof, "chainA", 1) is True
    assert verifier.verify_inclusion({"tx": "X"}, proof, "chainA", 1) is False
    with pytest.raises(ValueError):
        verifier.get_state_root("chainA", 999)
