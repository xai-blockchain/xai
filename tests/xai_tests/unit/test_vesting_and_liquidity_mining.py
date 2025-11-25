import pytest

from xai.blockchain.vesting_manager import VestingManager
from xai.blockchain.liquidity_mining_manager import LiquidityMiningManager


class ManualClock:
    def __init__(self, start_time: int):
        self.current_time = start_time

    def now(self) -> int:
        return self.current_time

    def advance(self, seconds: int):
        self.current_time += seconds


def test_vesting_schedule_claim_flow():
    manager = VestingManager()
    start = 1_700_000_000
    end = start + 30
    cliff = 10

    schedule_id = manager.create_vesting_schedule("0xuser", 1000.0, start, end, cliff)

    assert manager.get_vested_amount(schedule_id, start) == 0.0

    mid_time = start + 15  # 5 seconds into vesting window
    vested_mid = manager.get_vested_amount(schedule_id, mid_time)
    assert vested_mid == pytest.approx(250.0)
    claimed_mid = manager.claim_vested_tokens(schedule_id, mid_time)
    assert claimed_mid == pytest.approx(250.0)
    assert manager.get_vested_amount(schedule_id, mid_time) == 0.0

    final_time = end + 5
    claimed_final = manager.claim_vested_tokens(schedule_id, final_time)
    assert claimed_final == pytest.approx(750.0)
    assert manager.vesting_schedules[schedule_id]["claimed_amount"] == pytest.approx(1000.0)


def test_vesting_schedule_validation_errors():
    manager = VestingManager()
    now = 1_700_000_000
    with pytest.raises(ValueError):
        manager.create_vesting_schedule("", 100.0, now, now + 10, 0)
    with pytest.raises(ValueError):
        manager.create_vesting_schedule("0xuser", -5, now, now + 10, 0)
    with pytest.raises(ValueError):
        manager.create_vesting_schedule("0xuser", 100.0, now + 20, now + 10, 0)
    with pytest.raises(ValueError):
        manager.get_vested_amount("unknown")
    schedule_id = manager.create_vesting_schedule("0xuser", 50.0, now, now + 10, 0)
    assert manager.claim_vested_tokens(schedule_id, now) == 0.0


def test_liquidity_mining_enforces_cap_and_resets():
    clock = ManualClock(start_time=1_700_000_000)
    manager = LiquidityMiningManager(daily_reward_cap=1_000.0, time_provider=clock.now)

    first = manager.distribute_rewards(600.0, current_time=clock.now())
    assert first == pytest.approx(600.0)
    second = manager.distribute_rewards(500.0, current_time=clock.now())
    assert second == pytest.approx(400.0)
    assert manager.get_rewards_distributed_today() == pytest.approx(1_000.0)

    third = manager.distribute_rewards(10.0, current_time=clock.now())
    assert third == 0.0

    clock.advance(24 * 3600 + 1)
    after_reset = manager.distribute_rewards(200.0, current_time=clock.now())
    assert after_reset == pytest.approx(200.0)
    assert manager.get_rewards_distributed_today() == pytest.approx(200.0)


def test_liquidity_mining_validations():
    with pytest.raises(ValueError):
        LiquidityMiningManager(0)
    manager = LiquidityMiningManager(100)
    with pytest.raises(ValueError):
        manager.distribute_rewards(0)
    with pytest.raises(ValueError):
        manager.distribute_rewards(10, current_time=1700000000.5)  # type: ignore[arg-type]
