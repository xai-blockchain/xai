import json
import pytest

from xai.core.vm.evm.memory import EVMMemory, MAX_MEMORY_SIZE, WORD_SIZE
from xai.core.vm.evm.opcodes import (
    Opcode,
    OPCODE_INFO,
    get_log_topic_count,
    get_push_size,
    is_dup,
    is_jump,
    is_log,
    is_push,
    is_swap,
    is_terminating,
)
from xai.core.vm.evm.stack import (
    EVMStack,
    INT256_MAX,
    UINT256_MAX,
    sign_extend,
    to_signed,
    to_unsigned,
)
from xai.core.vm.evm.storage import (
    ACCESS_LIST_STORAGE_KEY,
    EVMStorage,
    SLOAD_COLD,
    SLOAD_WARM,
    SSTORE_CLEAR_REFUND,
    SSTORE_RESET,
    SSTORE_SET,
    TransientStorage,
)
from xai.core.vm.exceptions import VMExecutionError


def test_memory_store_load_and_copy_handles_overlap_and_bounds():
    memory = EVMMemory(max_size=128)

    # Store and load a full word
    memory.store(0, 0xDEADBEEF)
    assert memory.load(0) == 0xDEADBEEF

    # Copy overlapping regions (MCOPY semantics)
    memory.store_range(32, b"hello-world")
    memory.copy(dest_offset=33, src_offset=32, size=5)
    assert memory.load_range(33, 5) == b"hello"

    # Expansion cost only charges when growing paid region
    zero_cost = memory.expansion_cost(0, WORD_SIZE)
    assert zero_cost == 0
    additional_cost = memory.expansion_cost(64, 2)
    assert additional_cost > 0

    with pytest.raises(VMExecutionError):
        memory.store(MAX_MEMORY_SIZE + 1, 1)


def test_stack_push_pop_dup_swap_and_bounds():
    stack = EVMStack(max_depth=3)

    stack.push(1)
    stack.push(UINT256_MAX + 10)
    assert stack.pop() == 9  # Values wrap mod 2**256
    stack.push(2)

    stack.dup(1)
    assert stack.pop() == 2
    stack.swap(1)
    assert stack.pop() == 1

    overflow_stack = EVMStack(max_depth=1)
    overflow_stack.push(0)
    with pytest.raises(VMExecutionError):
        overflow_stack.push(1)

    with pytest.raises(VMExecutionError):
        stack.pop_n(5)
    with pytest.raises(VMExecutionError):
        stack.peek(5)


def test_stack_signed_conversions_and_sign_extend():
    negative = to_signed(UINT256_MAX)
    assert negative == -1
    assert to_unsigned(-1) == UINT256_MAX

    # Sign-extend preserves negative sign bit across sizes
    value = 0x80  # 0b1000_0000 (negative when sign bit)
    extended = sign_extend(value, byte_size=0)
    assert extended >> 255 == 1  # high bit set after extension

    # Positive value remains unchanged
    assert sign_extend(0x7F, byte_size=0) == 0x7F

    # Clamp when byte_size >= 32
    assert sign_extend(123, byte_size=32) == 123


def test_opcode_metadata_and_classification():
    add_info = OPCODE_INFO[Opcode.ADD]
    assert add_info.name == "ADD"
    assert add_info.stack_input == 2
    assert add_info.stack_output == 1
    assert add_info.stack_delta == -1

    assert get_push_size(Opcode.PUSH32) == 32
    assert get_push_size(Opcode.ADD) == 0
    assert is_push(Opcode.PUSH1)
    assert is_dup(Opcode.DUP16)
    assert is_swap(Opcode.SWAP4)
    assert is_log(Opcode.LOG3)
    assert is_jump(Opcode.JUMP)
    assert is_terminating(Opcode.RETURN)
    assert get_log_topic_count(Opcode.LOG4) == 4


def test_storage_gas_paths_and_size_tracking():
    storage = EVMStorage(address="0xABC", max_size=64)

    # Cold load then warm load
    value, gas_cost = storage.load(1)
    assert value == 0
    assert gas_cost == SLOAD_COLD
    value, gas_cost = storage.load(1)
    assert gas_cost == SLOAD_WARM

    # First write 0 -> non-zero
    gas_cost, refund = storage.store(1, 123)
    assert gas_cost == SSTORE_SET  # already warm from prior SLOAD
    assert refund == 0
    assert storage.size == 32

    # Clearing slot triggers refund and shrinks size
    gas_cost, refund = storage.store(1, 0)
    assert gas_cost == SLOAD_WARM  # subsequent writes are warm-priced
    assert refund >= SSTORE_CLEAR_REFUND
    assert storage.size == 0
    assert storage.get_refund() >= SSTORE_CLEAR_REFUND

    # Exceeding storage limit raises (max_size less than one slot)
    tiny_storage = EVMStorage(address="0xTINY", max_size=16)
    with pytest.raises(VMExecutionError):
        tiny_storage.store(0, 1)


def test_transient_storage_is_isolated_and_clearable():
    transient = TransientStorage()
    gas = transient.store("0xA", 1, 5)
    assert gas == transient.TSTORE_GAS
    value, load_gas = transient.load("0xA", 1)
    assert value == 5
    assert load_gas == transient.TLOAD_GAS

    transient.clear_contract("0xA")
    value, _ = transient.load("0xA", 1)
    assert value == 0

    transient.store("0xB", 2, 7)
    transient.clear()
    value, _ = transient.load("0xB", 2)
    assert value == 0


def test_access_list_warms_storage_and_costs_once():
    storage = EVMStorage(address="0xDEF")
    warm_cost = storage.warm_slot(99)
    assert warm_cost == ACCESS_LIST_STORAGE_KEY
    # Subsequent warm has zero cost and SLOAD is warm-priced
    warm_cost_again = storage.warm_slot(99)
    assert warm_cost_again == 0
    _, gas_cost = storage.load(99)
    assert gas_cost == SLOAD_WARM
