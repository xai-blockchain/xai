import time
import pytest

from xai.core.defi.circuit_breaker import (
    BreakerStatus,
    CircuitBreaker,
    ProtectionLevel,
)
from xai.core.defi.safe_math import (
    MAX_SUPPLY,
    SafeMath,
    assert_health_factor_valid,
    assert_supply_debt_invariant,
    assert_utilization_in_bounds,
)
from xai.core.vm.exceptions import VMExecutionError


def test_safe_math_hardens_overflow_and_fixed_point_paths():
    with pytest.raises(VMExecutionError):
        SafeMath.safe_add(MAX_SUPPLY, 1, MAX_SUPPLY, "supply")
    with pytest.raises(VMExecutionError):
        SafeMath.safe_sub(1, 2)
    with pytest.raises(VMExecutionError):
        SafeMath.safe_mul(2**130, 2**130, name="mul128")
    with pytest.raises(VMExecutionError):
        SafeMath.safe_div(1, 0)

    # WAD rounding down/up and RAY round half up
    wad_product = SafeMath.wad_mul(2 * 10**18, 5 * 10**17)
    wad_product_up = SafeMath.wad_mul(1, 1, round_up=True)
    assert wad_product == 1_000_000_000_000_000_000  # 1.0 in WAD
    assert wad_product_up == 1

    ray_product = SafeMath.ray_mul(5 * 10**26, 2 * 10**26)
    assert ray_product == 100_000_000_000_000_000_000_000_000  # 1e26 rounded half-up

    assert SafeMath.percentage(2000, 5000) == 1000


def test_safe_math_invariants_fail_fast_on_bad_state():
    with pytest.raises(VMExecutionError):
        assert_supply_debt_invariant(100, 101)
    with pytest.raises(VMExecutionError):
        assert_utilization_in_bounds(0, 1)
    with pytest.raises(VMExecutionError):
        assert_health_factor_valid(-1)
    with pytest.raises(VMExecutionError):
        assert_health_factor_valid(10**35)


def test_circuit_breaker_trigger_cooldown_and_recovery_paths():
    breaker = CircuitBreaker(
        name="PriceDeviation",
        target="pool-1",
        warning_threshold=90,
        trigger_threshold=100,
        protection_level=ProtectionLevel.HALT,
        cooldown_period=1,
    )

    # Warning does not change status
    assert breaker.record_metric(95) == "warn"
    assert breaker.status == BreakerStatus.ACTIVE

    # Trigger escalates and records event
    assert breaker.record_metric(150) == "trigger"
    breaker.trigger(actor="guardian", details={"delta": 150})
    assert breaker.status == BreakerStatus.TRIGGERED
    assert breaker.events[-1].actor == "guardian"

    # Cooldown restores to active once elapsed when manually recovered
    breaker.status = BreakerStatus.COOLING_DOWN
    breaker.cooldown_until = time.time() - 1
    assert breaker.record_metric(10) is None
    assert breaker.status == BreakerStatus.ACTIVE
