from __future__ import annotations

"""
Restored delegatecall-specific regression tests.

Downstream CI jobs still invoke pytest on tests/xai_tests/unit/test_evm_delegatecall.py.
The test logic was previously folded into other suites, so these cases reintroduce a
dedicated module while keeping meaningful delegatecall coverage.
"""

from unittest.mock import MagicMock

from xai.core.vm.evm.context import BlockContext, CallContext, CallType, ExecutionContext
from xai.core.vm.evm.interpreter import EVMInterpreter
from xai.core.vm.evm.opcodes import Opcode

def _make_block() -> BlockContext:
    return BlockContext(
        number=1,
        timestamp=67890,
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

def _make_call(code: bytes, *, address: str | None = None) -> CallContext:
    return CallContext(
        call_type=CallType.CALL,
        depth=0,
        address=address or ("0x" + "D" * 40),
        caller="0x" + "C" * 40,
        origin="0x" + "B" * 40,
        value=0,
        gas=5_000_000,
        code=code,
        calldata=b"",
        static=False,
    )

def test_delegatecall_writes_through_proxy_storage():
    impl_address = "0x" + "1" * 40
    proxy_address = "0x" + "2" * 40

    set_value = 0x1234
    impl_code = bytes(
        [
            Opcode.PUSH1,
            0x00,
            Opcode.CALLDATALOAD,
            Opcode.PUSH1,
            0x00,
            Opcode.SSTORE,
            Opcode.PUSH1,
            0x00,
            Opcode.PUSH1,
            0x00,
            Opcode.RETURN,
        ]
    )

    argument_bytes = set_value.to_bytes(32, "big")
    proxy_code = bytes(
        [
            Opcode.PUSH32,
            *argument_bytes,
            Opcode.PUSH1,
            0x20,
            Opcode.MSTORE,
            Opcode.PUSH1,
            0x20,  # retSize
            Opcode.PUSH1,
            0x00,  # retOffset
            Opcode.PUSH1,
            0x20,  # argsSize
            Opcode.PUSH1,
            0x20,  # argsOffset
            Opcode.PUSH20,
            *bytes.fromhex(impl_address[2:]),
            Opcode.PUSH4,
            0x00,
            0x01,
            0x00,
            0x00,
            Opcode.DELEGATECALL,
            Opcode.STOP,
        ]
    )

    blockchain = MagicMock()
    blockchain.contracts = {
        impl_address.upper(): {"code": impl_code.hex(), "storage": {}},
        proxy_address.upper(): {"code": proxy_code.hex(), "storage": {}},
    }
    blockchain.get_balance = MagicMock(return_value=10**9)

    context = _make_context(blockchain)
    context.warm_address(impl_address)

    call = _make_call(proxy_code, address=proxy_address)
    interpreter = EVMInterpreter(context)
    context.push_call(call)
    interpreter.execute(call)

    assert call.stack.pop() == 1

    proxy_storage = context.get_storage(proxy_address)
    assert proxy_storage.get_raw(0) == set_value

def test_delegatecall_failure_bubbles_without_touching_storage():
    impl_address = "0x" + "3" * 40
    proxy_address = "0x" + "4" * 40

    # Implementation always reverts
    impl_code = bytes([Opcode.PUSH1, 0x00, Opcode.PUSH1, 0x00, Opcode.REVERT])

    proxy_code = bytes(
        [
            Opcode.PUSH1,
            0x20,  # retSize
            Opcode.PUSH1,
            0x00,  # retOffset
            Opcode.PUSH1,
            0x00,  # argsSize
            Opcode.PUSH1,
            0x00,  # argsOffset
            Opcode.PUSH20,
            *bytes.fromhex(impl_address[2:]),
            Opcode.PUSH4,
            0x00,
            0x01,
            0x00,
            0x00,
            Opcode.DELEGATECALL,
            Opcode.STOP,
        ]
    )

    blockchain = MagicMock()
    blockchain.contracts = {
        impl_address.upper(): {"code": impl_code.hex(), "storage": {}},
        proxy_address.upper(): {"code": proxy_code.hex(), "storage": {}},
    }
    blockchain.get_balance = MagicMock(return_value=10**9)

    context = _make_context(blockchain)
    context.warm_address(impl_address)

    call = _make_call(proxy_code, address=proxy_address)
    interpreter = EVMInterpreter(context)
    context.push_call(call)

    interpreter.execute(call)

    assert call.stack.pop() == 0  # delegatecall failed
    proxy_storage = blockchain.contracts[proxy_address.upper()]["storage"]
    assert proxy_storage == {}
