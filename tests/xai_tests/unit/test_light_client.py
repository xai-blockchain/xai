import time

from xai.blockchain.light_client import LightClient, BlockHeader
from xai.blockchain.merkle import MerkleTree


def test_light_client_verification():
    client = LightClient("chainA")
    leaves = [{"tx": 1}, {"tx": 2}, {"tx": 3}]
    tree = MerkleTree(leaves)
    header = BlockHeader(
        block_number=1,
        prev_block_hash="0" * 64,
        state_root="state",
        transactions_root=tree.get_root(),
        timestamp=int(time.time()),
    )
    client.sync_header(header)
    proof = tree.generate_merkle_proof({"tx": 1})
    assert client.verify_transaction_inclusion({"tx": 1}, proof, 1) is True
    assert client.verify_transaction_inclusion({"tx": 999}, proof, 1) is False
