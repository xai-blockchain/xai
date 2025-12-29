import os
import pytest

from xai.core.blockchain import Blockchain
from xai.core.consensus.advanced_consensus import DynamicDifficultyAdjustment
from xai.core.wallet import Wallet
from xai.core.security import security_validation


def test_fast_mining_rejected_on_mainnet(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_NETWORK", "mainnet")
    monkeypatch.setenv("XAI_FAST_MINING", "1")
    # Ensure pytest flag present to mimic collection environment
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    dispatched = []
    monkeypatch.setattr(security_validation.SecurityEventRouter, "dispatch", lambda *args, **kwargs: dispatched.append((args, kwargs)))

    with pytest.raises(ValueError):
        Blockchain(data_dir=str(tmp_path))

    assert dispatched, "SecurityEventRouter.dispatch should be called when fast mining is rejected on mainnet"
    assert dispatched[0][0][0] == "config.fast_mining_rejected"


def test_fast_mining_caps_difficulty(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_NETWORK", "testnet")
    monkeypatch.setenv("XAI_FAST_MINING", "1")
    monkeypatch.setenv("XAI_MAX_TEST_MINING_DIFFICULTY", "2")
    dispatched = []
    monkeypatch.setattr(security_validation.SecurityEventRouter, "dispatch", lambda *args, **kwargs: dispatched.append((args, kwargs)))

    bc = Blockchain(data_dir=str(tmp_path))
    bc.difficulty = 8
    wallet = Wallet()

    block = bc.mine_pending_transactions(wallet.address)

    assert bc.difficulty == bc.max_test_mining_difficulty == 2
    assert block.header.difficulty == 2
    assert any(call[0][0] == "config.fast_mining_enabled" for call in dispatched)


def test_difficulty_timestamp_sanitization(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_NETWORK", "testnet")
    monkeypatch.setenv("XAI_FAST_MINING", "1")

    bc = Blockchain(data_dir=str(tmp_path))
    adjuster = DynamicDifficultyAdjustment(target_block_time=1)
    wallet = Wallet()

    # Mine a few blocks then force a non-monotonic timestamp regression
    for _ in range(5):
        bc.mine_pending_transactions(wallet.address)
    bc.chain[-1].timestamp = bc.chain[-2].timestamp - 5

    stats = adjuster.get_difficulty_stats(bc)
    assert stats["avg_block_time"] > 0

    new_diff = adjuster.calculate_new_difficulty(bc)
    assert adjuster.min_difficulty <= new_diff <= adjuster.max_difficulty
