import pytest

from xai.blockchain.liquidity_locker import LiquidityLocker


def test_liquidity_lock_and_unlock_flow():
    locker = LiquidityLocker()
    lock_id = locker.lock_liquidity("0xUser", 100.0, lock_duration_seconds=10, current_time=100)
    assert locker.get_total_locked_liquidity() == pytest.approx(100.0)
    assert len(locker.get_locked_liquidity("0xUser")) == 1

    with pytest.raises(ValueError):
        locker.unlock_liquidity(lock_id, "0xUser", current_time=105)

    with pytest.raises(PermissionError):
        locker.unlock_liquidity(lock_id, "0xOther", current_time=200)

    unlocked = locker.unlock_liquidity(lock_id, "0xUser", current_time=120)
    assert unlocked == pytest.approx(100.0)
    assert locker.get_total_locked_liquidity() == 0.0


def test_lock_input_validation():
    locker = LiquidityLocker()
    with pytest.raises(ValueError):
        locker.lock_liquidity("", 100.0, 10, current_time=0)
    with pytest.raises(ValueError):
        locker.lock_liquidity("0xUser", -1, 10, current_time=0)
    with pytest.raises(ValueError):
        locker.lock_liquidity("0xUser", 1, 0, current_time=0)
