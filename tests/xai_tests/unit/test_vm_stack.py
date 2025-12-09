"""
Unit tests for EVM stack utilities.

Coverage targets:
- Push/pop bounds, overflow/underflow
- DUP/SWAP semantics
- Sign conversion helpers and sign extension
"""

import pytest

from xai.core.vm.evm.stack import (
    EVMStack,
    MAX_STACK_DEPTH,
    UINT256_MAX,
    to_signed,
    to_unsigned,
    sign_extend,
)
from xai.core.vm.exceptions import VMExecutionError


def test_push_pop_bounds_and_overflow():
    """Push/pop respects max depth and underflow protections."""
    stack = EVMStack(max_depth=2)
    stack.push(1)
    stack.push(2)
    with pytest.raises(VMExecutionError):
        stack.push(3)
    assert stack.pop() == 2
    assert stack.pop() == 1
    with pytest.raises(VMExecutionError):
        stack.pop()


def test_dup_and_swap():
    """DUP/SWAP operate on correct positions and enforce bounds."""
    stack = EVMStack()
    stack.push(1)
    stack.push(2)
    stack.push(3)
    stack.dup(2)  # duplicate "2"
    assert stack.pop() == 2
    stack.swap(1)
    assert stack.pop() == 2
    assert stack.pop() == 3
    assert stack.pop() == 1
    with pytest.raises(VMExecutionError):
        stack.swap(5)


def test_push_n_and_pop_n():
    """Batch push/pop enforce size constraints."""
    stack = EVMStack(max_depth=5)
    stack.push_n([1, 2, 3])
    assert stack.pop_n(2) == [3, 2]
    with pytest.raises(VMExecutionError):
        stack.pop_n(5)


def test_value_bounding_and_sign_helpers():
    """Values are bounded to uint256, and sign conversions round-trip."""
    stack = EVMStack()
    stack.push(UINT256_MAX + 1)
    assert stack.pop() == 0

    assert to_signed(UINT256_MAX) == -1
    assert to_unsigned(-1) == UINT256_MAX

    # Sign extend: 0xff (byte) to 256 bits becomes -1
    assert sign_extend(0xFF, 0) == UINT256_MAX
    # Positive value remains unchanged within byte size
    assert sign_extend(0x7F, 0) == 0x7F
