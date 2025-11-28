"""
Tests for consensus edge cases.
"""

import pytest
from xai.core.blockchain import Blockchain, Block, Transaction

import time

def test_halving_threshold(tmp_path):
    """
    Test that the block reward is halved at the halving threshold.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    bc = Blockchain(data_dir=str(data_dir))
    bc.halving_interval = 10
    
    # Mine blocks up to the halving threshold
    for i in range(9):
        bc.mine_pending_transactions("miner1", {"private_key": "priv1", "public_key": "pub1"})
        
    # The next block should have the original reward
    block = bc.mine_pending_transactions("miner1", {"private_key": "priv1", "public_key": "pub1"})
    assert bc.get_block_reward(block.index) == 12.0
    
    # The next block should have the halved reward
    block = bc.mine_pending_transactions("miner1", {"private_key": "priv1", "public_key": "pub1"})
    assert bc.get_block_reward(block.index) == 6.0
