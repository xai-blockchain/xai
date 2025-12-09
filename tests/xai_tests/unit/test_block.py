"""
Unit tests for Block construction and properties.

Coverage targets:
- Legacy vs header-based construction validation
- Merkle root calculation and hash recalculation on mutable fields
- Miner resolution order
"""

import pytest

from xai.core.block_header import BlockHeader
from xai.core.blockchain_components.block import Block


class _Tx:
    def __init__(self, txid="id", sender="S", recipient="R"):
        self.txid = txid
        self.sender = sender
        self.recipient = recipient

    def calculate_hash(self):
        return self.txid

    def to_dict(self):
        return {}


def test_legacy_construction_requires_args():
    header = BlockHeader(index=0, previous_hash="0", merkle_root="root", timestamp=1, difficulty=1, nonce=0, signature=None, miner_pubkey=None, version=1)
    b = Block(header, [])
    assert b.index == 0
    with pytest.raises(ValueError):
        Block(None, [])
    with pytest.raises(ValueError):
        Block(1, previous_hash=None, transactions=[])


def test_merkle_root_and_hash_updates():
    txs = [_Tx(txid="a"), _Tx(txid="b")]
    block = Block(1, transactions=txs, previous_hash="0", difficulty=1)
    root_before = block.merkle_root
    old_hash = block.hash
    block.nonce = block.nonce + 1
    assert block.hash != old_hash
    assert root_before == block.merkle_root


def test_miner_resolution_precedence():
    # Miner from coinbase when no miner_pubkey set
    coinbase = _Tx(sender="COINBASE", recipient="M")
    b = Block(1, transactions=[coinbase], previous_hash="0", difficulty=1)
    assert b.miner == "M"

    # Miner from header pubkey
    header = BlockHeader(index=2, previous_hash="0", merkle_root="r", timestamp=1, difficulty=1, nonce=0, signature=None, miner_pubkey="PUB", version=1)
    b2 = Block(header, [])
    assert b2.miner == "PUB"

    # Explicit miner override
    b2._miner = "EXPL"
    assert b2.miner == "EXPL"
