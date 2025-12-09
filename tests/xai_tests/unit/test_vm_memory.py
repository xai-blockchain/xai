"""
Unit tests for EVMMemory.

Coverage targets:
- Load/store words and bytes with auto expansion
- Range operations and MCOPY overlap handling
- Memory limit enforcement
"""

import pytest

from xai.core.vm.evm.memory import EVMMemory, WORD_SIZE
from xai.core.vm.exceptions import VMExecutionError


def test_load_store_word_and_byte():
    mem = EVMMemory()
    mem.store(0, 1)
    assert mem.load(0) == 1
    mem.store_byte(1, 0xFF)
    assert mem.load_byte(1) == 0xFF


def test_load_store_range_and_expand():
    mem = EVMMemory()
    mem.store_range(10, b"abc")
    assert mem.load_range(10, 3) == b"abc"
    # load beyond stored data zero-pads
    assert mem.load_range(10, 5) == b"abc\x00\x00"


def test_copy_handles_overlap():
    mem = EVMMemory()
    mem.store_range(0, b"abcdef")
    mem.copy(2, 0, 4)  # overlap copy
    assert mem.load_range(0, 6) == b"ababcd"


def test_memory_limit_enforced():
    mem = EVMMemory(max_size=32)
    with pytest.raises(VMExecutionError):
        mem.store(16, 1)  # requires 48 bytes
