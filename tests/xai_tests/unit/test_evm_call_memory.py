"""
Regression tests dedicated to CALL argument/return memory handling.

Historically these lived in their own module that downstream test runners
invoked directly (e.g. pytest tests/.../test_evm_call_memory.py).  The
coverage was folded into test_evm_call_execution.py during refactors,
which broke automation that still references the legacy filenames.  These
tests ensure the legacy path is restored while also keeping focused
coverage on calldata/return buffer copying semantics.
"""

from typing import Optional
from unittest.mock import MagicMock

from xai.core.vm.evm.context import BlockContext, CallContext, CallType, ExecutionContext
from xai.core.vm.evm.interpreter import EVMInterpreter
from xai.core.vm.evm.opcodes import Opcode


def _make_block() -> BlockContext:
    return BlockContext(
        number=1,
        timestamp=12345,
        gas_limit=10_000_000,
        coinbase="0x" + "0" * 40,
        prevrandao=0,
        base_fee=0,
        chain_id=1,
    )


def _make_context(blockchain: MagicMock) -> ExecutionContext:
    return ExecutionContext(
        block=_make_block(),
        tx_origin="0x" + "1" * 40,
        tx_gas_price=1,
        tx_gas_limit=5_000_000,
        tx_value=0,
        blockchain=blockchain,
    )


def _make_call(code: bytes, *, address: Optional[str] = None) -> CallContext:
    return CallContext(
        call_type=CallType.CALL,
        depth=0,
        address=address or ("0x" + "C" * 40),
        caller="0x" + "B" * 40,
        origin="0x" + "A" * 40,
        value=0,
        gas=5_000_000,
        code=code,
        calldata=b"",
        static=False,
    )


def test_call_argument_buffer_is_copied_into_target_calldata():
    """Ensure CALL copies the specified args buffer into the callee's calldata."""

    argument = 0xDEADBEEFCAFEBABE
    argument_bytes = argument.to_bytes(32, "big")

    target_code = bytes(
        [
            Opcode.PUSH1,
            0x00,  # calldata offset
            Opcode.CALLDATALOAD,  # load first 32 bytes of calldata
            Opcode.DUP1,  # duplicate value for return buffer
            Opcode.PUSH1,
            0x00,  # return offset
            Opcode.MSTORE,  # store duplicated value to memory[0:32]
            Opcode.DUP1,
            Opcode.PUSH1,
            0x01,  # storage slot 1 records the calldata seen by callee
            Opcode.SSTORE,
            Opcode.PUSH1,
            0x20,  # return size
            Opcode.PUSH1,
            0x00,  # return offset
            Opcode.RETURN,
        ]
    )

    target_address = "0x" + "2" * 40
    blockchain = MagicMock()
    blockchain.contracts = {
        target_address.upper(): {"code": target_code.hex(), "storage": {}},
    }
    blockchain.get_balance = MagicMock(return_value=10**9)

    context = _make_context(blockchain)
    context.warm_address(target_address)

    caller_code = bytes(
        [
            Opcode.PUSH32,
            *argument_bytes,
            Opcode.PUSH1,
            0x00,
            Opcode.MSTORE,  # write argument to memory[0:32]
            Opcode.PUSH1,
            0x20,  # retSize
            Opcode.PUSH1,
            0x00,  # retOffset
            Opcode.PUSH1,
            0x20,  # argsSize
            Opcode.PUSH1,
            0x00,  # argsOffset
            Opcode.PUSH1,
            0x00,  # value
            Opcode.PUSH20,
            *bytes.fromhex(target_address[2:]),
            Opcode.PUSH4,
            0x00,
            0x01,
            0x00,
            0x00,  # gas forwarded
            Opcode.CALL,
            Opcode.STOP,
        ]
    )

    call = _make_call(caller_code, address="0x" + "C" * 40)
    interpreter = EVMInterpreter(context)
    context.push_call(call)
    interpreter.execute(call)

    # Verify CALL succeeded and returned the same word we sent
    assert call.stack.pop() == 1
    assert call.memory.load(0) == argument

    # The callee should have persisted the calldata it observed
    callee_storage = context.get_storage(target_address)
    assert callee_storage.get_raw(1) == argument


def test_call_return_buffer_respects_offsets_and_sizes():
    """Return data must land exactly at the caller-provided offset."""

    argument = 0xAA
    target_return = (argument + 1) & ((1 << 256) - 1)

    target_code = bytes(
        [
            Opcode.PUSH1,
            0x00,
            Opcode.CALLDATALOAD,  # load calldata word
            Opcode.DUP1,
            Opcode.PUSH1,
            0x00,
            Opcode.SSTORE,  # slot 0 = original calldata
            Opcode.PUSH1,
            0x01,
            Opcode.ADD,  # increment value for return buffer
            Opcode.PUSH1,
            0x10,
            Opcode.MSTORE,  # store at memory offset 0x10
            Opcode.PUSH1,
            0x20,
            Opcode.PUSH1,
            0x10,  # return data originates at offset 0x10
            Opcode.RETURN,
        ]
    )

    target_address = "0x" + "3" * 40
    blockchain = MagicMock()
    blockchain.contracts = {
        target_address.upper(): {"code": target_code.hex(), "storage": {}},
    }
    blockchain.get_balance = MagicMock(return_value=10**9)

    context = _make_context(blockchain)
    context.warm_address(target_address)

    caller_code = bytes(
        [
            Opcode.PUSH32,
            *argument.to_bytes(32, "big"),
            Opcode.PUSH1,
            0x40,
            Opcode.MSTORE,  # write calldata at offset 0x40
            Opcode.PUSH1,
            0x20,  # retSize
            Opcode.PUSH1,
            0x00,  # retOffset = 0
            Opcode.PUSH1,
            0x20,  # argsSize
            Opcode.PUSH1,
            0x40,  # argsOffset = 0x40
            Opcode.PUSH1,
            0x00,  # value
            Opcode.PUSH20,
            *bytes.fromhex(target_address[2:]),
            Opcode.PUSH4,
            0x00,
            0x01,
            0x00,
            0x00,
            Opcode.CALL,
            Opcode.STOP,
        ]
    )

    call = _make_call(caller_code, address="0x" + "C" * 40)
    interpreter = EVMInterpreter(context)
    context.push_call(call)
    interpreter.execute(call)

    assert call.stack.pop() == 1
    assert call.memory.load(0) == target_return
    assert call.memory.load(0x20) == 0  # untouched region

    callee_storage = context.get_storage(target_address)
    assert callee_storage.get_raw(0) == argument
