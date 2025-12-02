"""
Tests for consensus edge cases.
"""

import pytest
from xai.core.blockchain import Blockchain
from xai.core.crypto_utils import deterministic_keypair_from_seed

def test_halving_threshold(tmp_path):
    """
    Test that the block reward is halved at the halving threshold.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    bc = Blockchain(data_dir=str(data_dir))
    bc.halving_interval = 10
    miner_priv, miner_pub = deterministic_keypair_from_seed(b"halving-threshold-seed")

    # Mine blocks up to just before the halving threshold
    for _ in range(bc.halving_interval - 2):
        bc.mine_pending_transactions("miner1", {"private_key": miner_priv, "public_key": miner_pub})

    # At height halving_interval - 1, reward should be pre-halving
    block = bc.mine_pending_transactions("miner1", {"private_key": miner_priv, "public_key": miner_pub})
    assert bc.get_block_reward(block.index) == bc.initial_block_reward

    # The next block should have the halved reward
    block = bc.mine_pending_transactions("miner1", {"private_key": miner_priv, "public_key": miner_pub})
    assert bc.get_block_reward(block.index) == bc.initial_block_reward / 2
