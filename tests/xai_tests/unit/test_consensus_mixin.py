"""
Unit tests for BlockchainConsensusMixin.

Coverage targets:
- Block reward halving and supply cap enforcement
- Coinbase reward validation with fees and tolerance
- Difficulty adjustment defaults when chain empty
"""

from types import SimpleNamespace

import pytest

from xai.core.blockchain_components.consensus_mixin import BlockchainConsensusMixin


class _Tx:
    def __init__(self, sender, amount, fee=0.0, tx_type="payment"):
        self.sender = sender
        self.amount = amount
        self.fee = fee
        self.tx_type = tx_type


class DummyConsensus(BlockchainConsensusMixin):
    def __init__(self):
        self.chain = []
        self.difficulty = 1
        self.initial_block_reward = 12.0
        self.halving_interval = 2
        self.max_supply = 50.0
        self.target_block_time = 60
        self.difficulty_adjustment_interval = 1
        self.max_difficulty_change = 4
        self.logger = SimpleNamespace(warn=lambda *a, **k: None, debug=lambda *a, **k: None)
        self.fast_mining_enabled = False
        self.max_test_mining_difficulty = 1

    def get_circulating_supply(self):
        return sum(getattr(b, "supply", 0) for b in self.chain)


def test_block_reward_halving_and_cap():
    dc = DummyConsensus()
    assert dc.get_block_reward(0) == 12.0
    assert dc.get_block_reward(2) == 6.0  # halved after interval
    dc.chain.append(SimpleNamespace(supply=50.0))
    assert dc.get_block_reward(10) == 0.0  # supply cap hit


def test_validate_coinbase_reward_with_fees_and_tolerance():
    dc = DummyConsensus()
    block = SimpleNamespace(
        index=0,
        hash="h",
        transactions=[
            _Tx("COINBASE", amount=12.000000005, tx_type="coinbase"),
            _Tx("S", amount=1, fee=1.0),
        ],
    )
    valid, err = dc.validate_coinbase_reward(block)
    assert valid is True
    assert err is None

    block.transactions[0].amount = 14.0  # exceeds reward + fee
    valid, err = dc.validate_coinbase_reward(block)
    assert valid is False
    assert "exceeds maximum" in err


def test_calculate_next_difficulty_defaults_empty_chain():
    dc = DummyConsensus()
    new_diff = dc.calculate_next_difficulty(chain=[], current_difficulty=None, emit_log=False)
    assert new_diff >= 1
