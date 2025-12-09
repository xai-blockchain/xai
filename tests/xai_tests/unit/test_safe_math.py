"""
Unit tests for SafeMath utilities.

Coverage targets:
- Basic arithmetic overflow/underflow checks
- Fixed-point wad/ray operations with rounding
- Percentage and invariant assertions
"""

import pytest

from xai.core.defi.safe_math import (
    SafeMath,
    MAX_UINT256,
    WAD,
    RAY,
    assert_supply_debt_invariant,
    assert_utilization_in_bounds,
    assert_health_factor_valid,
)
from xai.core.vm.exceptions import VMExecutionError


def test_safe_add_sub_mul_div():
    assert SafeMath.safe_add(1, 2, 10) == 3
    with pytest.raises(VMExecutionError):
        SafeMath.safe_add(5, 6, 10)
    assert SafeMath.safe_sub(5, 3) == 2
    with pytest.raises(VMExecutionError):
        SafeMath.safe_sub(1, 2)
    assert SafeMath.safe_mul(2, 3) == 6
    with pytest.raises(VMExecutionError):
        SafeMath.safe_mul(MAX_UINT256, 2)
    assert SafeMath.safe_div(6, 3) == 2
    with pytest.raises(VMExecutionError):
        SafeMath.safe_div(1, 0)


def test_wad_and_ray_operations_rounding():
    assert SafeMath.wad_mul(WAD, 2) == 2
    assert SafeMath.wad_mul(WAD, 1, round_up=True) == 1
    assert SafeMath.wad_div(2, 2) == WAD  # (2 * WAD) / 2
    assert SafeMath.ray_mul(RAY, 2) == 2
    assert SafeMath.ray_div(2, 2) == RAY  # (2 * RAY) / 2
    with pytest.raises(VMExecutionError):
        SafeMath.wad_div(1, 0)


def test_percentage_and_bounds():
    assert SafeMath.percentage(10000, 5000) == 5000
    with pytest.raises(VMExecutionError):
        SafeMath.percentage(100, 20000)
    with pytest.raises(VMExecutionError):
        SafeMath.require_positive(0)
    with pytest.raises(VMExecutionError):
        SafeMath.require_in_range(5, 10, 20)
    with pytest.raises(VMExecutionError):
        SafeMath.require_lte(5, 1)
    with pytest.raises(VMExecutionError):
        SafeMath.require_gte(1, 5)


def test_invariants_and_health_factor():
    assert_supply_debt_invariant(10, 5)
    with pytest.raises(VMExecutionError):
        assert_supply_debt_invariant(5, 10)
    assert_utilization_in_bounds(10, 5)
    with pytest.raises(VMExecutionError):
        assert_utilization_in_bounds(0, 1)
    assert_health_factor_valid(RAY)
    with pytest.raises(VMExecutionError):
        assert_health_factor_valid(-1)
    with pytest.raises(VMExecutionError):
        assert_health_factor_valid(RAY * 20_000_000)
