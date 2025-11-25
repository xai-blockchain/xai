import pytest

from xai.blockchain.impermanent_loss_protection import (
    ImpermanentLossCalculator,
    ILProtectionManager,
)


class ManualClock:
    def __init__(self, start_time: int):
        self.current_time = start_time

    def now(self) -> int:
        return self.current_time

    def advance(self, seconds: int):
        self.current_time += seconds


def test_il_calculator_basic_cases():
    calc = ImpermanentLossCalculator()
    assert calc.calculate_il(1.0, 1.0) == pytest.approx(0.0)
    assert calc.calculate_il(1.0, 2.0) < 0  # Impermanent loss for doubling price


def test_il_protection_requires_lock_period():
    calc = ImpermanentLossCalculator()
    clock = ManualClock(start_time=1_700_000_000)
    manager = ILProtectionManager(
        calc,
        protection_percentage=50.0,
        min_lock_duration_days=1,
        time_provider=clock.now,
    )

    manager.record_lp_deposit("0xLP", 10_000, 1.0)
    protection = manager.calculate_protected_il("0xLP", 9_000, 2.0)
    assert protection == 0.0

    clock.advance(2 * 24 * 3600)
    protection = manager.calculate_protected_il("0xLP", 9_000, 2.0)
    assert protection > 0


def test_il_protection_handles_missing_lp():
    calc = ImpermanentLossCalculator()
    manager = ILProtectionManager(calc)
    with pytest.raises(ValueError):
        manager.calculate_protected_il("unknown", 9000, 2.0)
