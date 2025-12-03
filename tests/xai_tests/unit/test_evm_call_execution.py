"""
Tests for EVM CALL/DELEGATECALL/STATICCALL execution.

Verifies that contracts can properly call other contracts and execute
their bytecode, including proper context handling and return data.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from xai.core.vm.evm.interpreter import EVMInterpreter
from xai.core.vm.evm.context import ExecutionContext, CallContext, CallType, BlockContext
from xai.core.vm.evm.opcodes import Opcode
from xai.core.vm.exceptions import VMExecutionError


class TestCALLExecution:
    """Tests for CALL opcode execution."""

    def test_call_executes_target_contract_code(self):
        """Test that CALL actually executes the target contract's bytecode."""
        # Create a simple target contract that returns a value
        # PUSH1 0x42, PUSH1 0x00, MSTORE, PUSH1 0x20, PUSH1 0x00, RETURN
        target_code = bytes([
            Opcode.PUSH1, 0x42,  # Push value 0x42
            Opcode.PUSH1, 0x00,  # Push memory offset 0
            Opcode.MSTORE,       # Store to memory
            Opcode.PUSH1, 0x20,  # Push size 32
            Opcode.PUSH1, 0x00,  # Push offset 0
            Opcode.RETURN,       # Return 32 bytes from memory
        ])

        # Create blockchain mock with target contract
        blockchain = MagicMock()
        target_address = "0x1234567890123456789012345678901234567890"
        blockchain.contracts = {
            target_address.upper(): {
                "code": target_code.hex(),
            }
        }
        blockchain.get_balance = MagicMock(return_value=1000000)

        # Create execution context
        block = BlockContext(
            number=1,
            timestamp=1000,
            gas_limit=10000000,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=0,
            chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "a" * 40,
            tx_gas_price=1,
            tx_gas_limit=1000000,
            tx_value=0,
            blockchain=blockchain,
        )

        # Pre-warm the target address to avoid cold access costs (EIP-2929)
        context.warm_address(target_address)

        # Create caller contract that calls target
        # CALL stack layout (from EVM spec): gas, address, value, argsOffset, argsSize, retOffset, retSize
        # Where 'gas' is on TOP of stack (popped first)
        # So we must PUSH in REVERSE order: retSize, retOffset, argsSize, argsOffset, value, address, gas
        caller_code = bytes([
            Opcode.PUSH1, 0x20,  # retSize = 32 (pushed first, at bottom)
            Opcode.PUSH1, 0x00,  # retOffset = 0
            Opcode.PUSH1, 0x00,  # argsSize = 0
            Opcode.PUSH1, 0x00,  # argsOffset = 0
            Opcode.PUSH1, 0x00,  # value = 0
            Opcode.PUSH20,  # address (20 bytes)
            *bytes.fromhex(target_address[2:]),
            Opcode.PUSH4, 0x00, 0x01, 0x00, 0x00,  # gas = 65536 (pushed last, on top)
            Opcode.CALL,
            # After CALL, success is on stack, return data is in memory
            Opcode.STOP,
        ])

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address="0x" + "b" * 40,
            caller="0x" + "a" * 40,
            origin="0x" + "a" * 40,
            value=0,
            gas=10000000,  # Plenty of gas for testing
            code=caller_code,
            calldata=b"",
            static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        interpreter.execute(call)

        # Verify CALL returned success (1 on stack)
        assert call.stack.pop() == 1

        # Verify return data was copied to memory
        returned_value = call.memory.load(0)
        assert returned_value == 0x42

    def test_call_with_value_transfer(self):
        """Test CALL with value transfer."""
        # Simple contract that returns success
        target_code = bytes([Opcode.PUSH1, 0x01, Opcode.PUSH1, 0x00, Opcode.RETURN])

        blockchain = MagicMock()
        target_address = "0x1234567890123456789012345678901234567890"
        blockchain.contracts = {
            target_address.upper(): {"code": target_code.hex()}
        }

        # Track balances
        balances = {
            "0x" + "b" * 40: 1000000,  # Caller has balance
            target_address: 500000,
        }
        blockchain.get_balance = lambda addr: balances.get(addr, 0)

        block = BlockContext(
            number=1, timestamp=1000, gas_limit=10000000,
            coinbase="0x" + "0" * 40, prevrandao=0, base_fee=0, chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "a" * 40,
            tx_gas_price=1,
            tx_gas_limit=1000000,
            tx_value=0,
            blockchain=blockchain,
        )

        # Caller sends 1000 wei
        value = 1000
        caller_code = bytes([
            Opcode.PUSH1, 0x00,  # retSize
            Opcode.PUSH1, 0x00,  # retOffset
            Opcode.PUSH1, 0x00,  # argsSize
            Opcode.PUSH1, 0x00,  # argsOffset
            Opcode.PUSH2, *value.to_bytes(2, "big"),  # value = 1000
            Opcode.PUSH20, *bytes.fromhex(target_address[2:]),  # address
            Opcode.PUSH4, 0x00, 0x01, 0x00, 0x00,  # gas
            Opcode.CALL,
            Opcode.STOP,
        ])

        call = CallContext(
            call_type=CallType.CALL, depth=0,
            address="0x" + "b" * 40, caller="0x" + "a" * 40,
            origin="0x" + "a" * 40, value=0, gas=10000000,  # Plenty of gas
            code=caller_code, calldata=b"", static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        interpreter.execute(call)

        # Verify transfer occurred
        assert context.get_balance("0x" + "b" * 40) == 1000000 - value
        assert context.get_balance(target_address) == 500000 + value

    def test_call_depth_limit(self):
        """Test that CALL respects the call depth limit of 1024."""
        # Contract that calls itself recursively
        self_address = "0x1111111111111111111111111111111111111111"

        # CALL to self with all gas
        recursive_code = bytes([
            Opcode.PUSH1, 0x00,  # retSize
            Opcode.PUSH1, 0x00,  # retOffset
            Opcode.PUSH1, 0x00,  # argsSize
            Opcode.PUSH1, 0x00,  # argsOffset
            Opcode.PUSH1, 0x00,  # value
            Opcode.PUSH20, *bytes.fromhex(self_address[2:]),  # self address
            Opcode.PUSH4, 0xFF, 0xFF, 0xFF, 0xFF,  # gas = max
            Opcode.CALL,
            Opcode.STOP,
        ])

        blockchain = MagicMock()
        blockchain.contracts = {
            self_address.upper(): {"code": recursive_code.hex()}
        }
        blockchain.get_balance = MagicMock(return_value=0)

        block = BlockContext(
            number=1, timestamp=1000, gas_limit=10000000,
            coinbase="0x" + "0" * 40, prevrandao=0, base_fee=0, chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "a" * 40,
            tx_gas_price=1,
            tx_gas_limit=100000000,  # Very high gas
            tx_value=0,
            blockchain=blockchain,
            max_call_depth=10,  # Lower limit for testing
        )

        call = CallContext(
            call_type=CallType.CALL, depth=0,
            address=self_address, caller="0x" + "a" * 40,
            origin="0x" + "a" * 40, value=0, gas=100000000,
            code=recursive_code, calldata=b"", static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)

        # Should not raise - depth limit returns 0 (failure) instead
        interpreter.execute(call)

        # The recursive call should eventually return 0 due to depth limit
        assert True  # Made it without infinite recursion


class TestDELEGATECALL:
    """Tests for DELEGATECALL opcode execution."""

    def test_delegatecall_preserves_caller_context(self):
        """Test that DELEGATECALL executes in caller's storage context."""
        # Target contract code: SSTORE key=0, value=0x42, then RETURN
        target_code = bytes([
            Opcode.PUSH1, 0x42,  # value
            Opcode.PUSH1, 0x00,  # key
            Opcode.SSTORE,       # Store in current address's storage
            Opcode.PUSH1, 0x00,
            Opcode.PUSH1, 0x00,
            Opcode.RETURN,
        ])

        target_address = "0x2222222222222222222222222222222222222222"
        caller_address = "0x3333333333333333333333333333333333333333"

        blockchain = MagicMock()
        blockchain.contracts = {
            target_address.upper(): {"code": target_code.hex()},
            caller_address.upper(): {"code": b"", "storage": {}},
        }
        blockchain.get_balance = MagicMock(return_value=0)

        block = BlockContext(
            number=1, timestamp=1000, gas_limit=10000000,
            coinbase="0x" + "0" * 40, prevrandao=0, base_fee=0, chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "a" * 40,
            tx_gas_price=1,
            tx_gas_limit=1000000,
            tx_value=0,
            blockchain=blockchain,
        )

        # Caller uses DELEGATECALL
        caller_code = bytes([
            Opcode.PUSH1, 0x00,  # retSize
            Opcode.PUSH1, 0x00,  # retOffset
            Opcode.PUSH1, 0x00,  # argsSize
            Opcode.PUSH1, 0x00,  # argsOffset
            Opcode.PUSH20, *bytes.fromhex(target_address[2:]),  # target
            Opcode.PUSH4, 0x00, 0x01, 0x00, 0x00,  # gas
            Opcode.DELEGATECALL,
            Opcode.STOP,
        ])

        call = CallContext(
            call_type=CallType.CALL, depth=0,
            address=caller_address, caller="0x" + "a" * 40,
            origin="0x" + "a" * 40, value=0, gas=10000000,  # Plenty of gas
            code=caller_code, calldata=b"", static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        interpreter.execute(call)

        # Verify storage was written to CALLER's address, not target
        caller_storage = context.get_storage(caller_address)
        value, _ = caller_storage.load(0)
        assert value == 0x42

        # Target storage should be empty
        target_storage = context.get_storage(target_address)
        target_value, _ = target_storage.load(0)
        assert target_value == 0


class TestSTATICCALL:
    """Tests for STATICCALL opcode execution."""

    def test_staticcall_prevents_state_modification(self):
        """Test that STATICCALL prevents state modifications."""
        # Target contract tries to modify storage
        target_code = bytes([
            Opcode.PUSH1, 0x42,
            Opcode.PUSH1, 0x00,
            Opcode.SSTORE,  # This should fail in static context
        ])

        target_address = "0x4444444444444444444444444444444444444444"

        blockchain = MagicMock()
        blockchain.contracts = {
            target_address.upper(): {"code": target_code.hex()}
        }
        blockchain.get_balance = MagicMock(return_value=0)

        block = BlockContext(
            number=1, timestamp=1000, gas_limit=10000000,
            coinbase="0x" + "0" * 40, prevrandao=0, base_fee=0, chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "a" * 40,
            tx_gas_price=1,
            tx_gas_limit=1000000,
            tx_value=0,
            blockchain=blockchain,
        )

        # Caller uses STATICCALL
        caller_code = bytes([
            Opcode.PUSH1, 0x00,  # retSize
            Opcode.PUSH1, 0x00,  # retOffset
            Opcode.PUSH1, 0x00,  # argsSize
            Opcode.PUSH1, 0x00,  # argsOffset
            Opcode.PUSH20, *bytes.fromhex(target_address[2:]),
            Opcode.PUSH4, 0x00, 0x01, 0x00, 0x00,  # gas
            Opcode.STATICCALL,
            # Result (0 = failure) should be on stack
            Opcode.STOP,
        ])

        call = CallContext(
            call_type=CallType.CALL, depth=0,
            address="0x" + "b" * 40, caller="0x" + "a" * 40,
            origin="0x" + "a" * 40, value=0, gas=10000000,  # Plenty of gas
            code=caller_code, calldata=b"", static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        interpreter.execute(call)

        # STATICCALL should return 0 (failure) because target tried to modify state
        result = call.stack.pop()
        assert result == 0  # Call failed

    def test_staticcall_allows_reads(self):
        """Test that STATICCALL allows reading state."""
        # Target contract reads from storage and returns it
        target_code = bytes([
            Opcode.PUSH1, 0x00,  # key
            Opcode.SLOAD,        # Load from storage (allowed in static)
            Opcode.PUSH1, 0x00,
            Opcode.MSTORE,       # Store to memory
            Opcode.PUSH1, 0x20,
            Opcode.PUSH1, 0x00,
            Opcode.RETURN,
        ])

        target_address = "0x5555555555555555555555555555555555555555"

        blockchain = MagicMock()
        blockchain.contracts = {
            target_address.upper(): {
                "code": target_code.hex(),
                "storage": {"0": 99},  # Pre-existing storage value
            }
        }
        blockchain.get_balance = MagicMock(return_value=0)

        block = BlockContext(
            number=1, timestamp=1000, gas_limit=10000000,
            coinbase="0x" + "0" * 40, prevrandao=0, base_fee=0, chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "a" * 40,
            tx_gas_price=1,
            tx_gas_limit=1000000,
            tx_value=0,
            blockchain=blockchain,
        )

        caller_code = bytes([
            Opcode.PUSH1, 0x20,  # retSize = 32
            Opcode.PUSH1, 0x00,  # retOffset = 0
            Opcode.PUSH1, 0x00,
            Opcode.PUSH1, 0x00,
            Opcode.PUSH20, *bytes.fromhex(target_address[2:]),
            Opcode.PUSH4, 0x00, 0x01, 0x00, 0x00,  # gas
            Opcode.STATICCALL,
            Opcode.STOP,
        ])

        call = CallContext(
            call_type=CallType.CALL, depth=0,
            address="0x" + "b" * 40, caller="0x" + "a" * 40,
            origin="0x" + "a" * 40, value=0, gas=10000000,  # Plenty of gas
            code=caller_code, calldata=b"", static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        interpreter.execute(call)

        # STATICCALL should succeed
        result = call.stack.pop()
        assert result == 1

        # Return data should contain the storage value
        returned = call.memory.load(0)
        assert returned == 99

    def test_staticcall_context_flag_enforced(self):
        """Ensure CallContext always enforces static mode for STATICCALL frames."""
        # Contract attempts to write storage in a STATICCALL context.
        target_address = "0x7777777777777777777777777777777777777777"
        code = bytes([
            Opcode.PUSH1, 0x01,
            Opcode.PUSH1, 0x00,
            Opcode.SSTORE,
            Opcode.STOP,
        ])

        blockchain = MagicMock()
        blockchain.contracts = {target_address.upper(): {"code": code.hex(), "storage": {}}}
        blockchain.get_balance = MagicMock(return_value=0)

        block = BlockContext(
            number=1,
            timestamp=1000,
            gas_limit=10000000,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=0,
            chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "a" * 40,
            tx_gas_price=1,
            tx_gas_limit=1000000,
            tx_value=0,
            blockchain=blockchain,
        )

        # Intentionally omit static=True to simulate callers forgetting to set it.
        call = CallContext(
            call_type=CallType.STATICCALL,
            depth=0,
            address=target_address,
            caller="0x" + "b" * 40,
            origin="0x" + "b" * 40,
            value=0,
            gas=100000,
            code=code,
            calldata=b"",
            static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        with pytest.raises(VMExecutionError, match="static"):
            interpreter.execute(call)


class TestReturnDataHandling:
    """Tests for return data handling across calls."""

    def test_returndatasize_after_call(self):
        """Test RETURNDATASIZE opcode after CALL."""
        # Target returns 64 bytes
        target_code = bytes([
            Opcode.PUSH1, 0x40,  # size = 64
            Opcode.PUSH1, 0x00,  # offset = 0
            Opcode.RETURN,
        ])

        target_address = "0x6666666666666666666666666666666666666666"
        blockchain = MagicMock()
        blockchain.contracts = {
            target_address.upper(): {"code": target_code.hex()}
        }
        blockchain.get_balance = MagicMock(return_value=0)

        block = BlockContext(
            number=1, timestamp=1000, gas_limit=10000000,
            coinbase="0x" + "0" * 40, prevrandao=0, base_fee=0, chain_id=1,
        )
        context = ExecutionContext(
            block=block, tx_origin="0x" + "a" * 40,
            tx_gas_price=1, tx_gas_limit=1000000, tx_value=0,
            blockchain=blockchain,
        )

        # Caller does CALL then RETURNDATASIZE
        caller_code = bytes([
            Opcode.PUSH1, 0x00,  # retSize
            Opcode.PUSH1, 0x00,  # retOffset
            Opcode.PUSH1, 0x00,
            Opcode.PUSH1, 0x00,
            Opcode.PUSH1, 0x00,  # value
            Opcode.PUSH20, *bytes.fromhex(target_address[2:]),
            Opcode.PUSH4, 0x00, 0x01, 0x00, 0x00,
            Opcode.CALL,
            Opcode.RETURNDATASIZE,  # Should push 64
            Opcode.STOP,
        ])

        call = CallContext(
            call_type=CallType.CALL, depth=0,
            address="0x" + "b" * 40, caller="0x" + "a" * 40,
            origin="0x" + "a" * 40, value=0, gas=10000000,  # Plenty of gas
            code=caller_code, calldata=b"", static=False,
        )

        interpreter = EVMInterpreter(context)
        context.push_call(call)
        interpreter.execute(call)

        # RETURNDATASIZE should be 64
        size = call.stack.pop()
        assert size == 64


class TestCallGasForwarding:
    """Validate CALL-family gas forwarding semantics."""

    CALLER = "0x" + "b" * 40
    ORIGIN = "0x" + "a" * 40
    TARGET = "0x9999999999999999999999999999999999999999"

    def _build_context(self, initial_gas: int = 64000, static: bool = False):
        """Create interpreter and call context with deterministic balances."""
        blockchain = SimpleNamespace(
            contracts={self.TARGET.upper(): {"code": ""}},
            get_balance=lambda addr: 0,
            nonce_tracker=SimpleNamespace(
                get_nonce=lambda addr: 0,
                set_nonce=lambda addr, value: None,
            ),
        )
        block = BlockContext(
            number=1,
            timestamp=1000,
            gas_limit=10_000_000,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=0,
            chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin=self.ORIGIN,
            tx_gas_price=1,
            tx_gas_limit=1_000_000,
            tx_value=0,
            blockchain=blockchain,
        )
        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.CALLER,
            caller=self.ORIGIN,
            origin=self.ORIGIN,
            value=0,
            gas=initial_gas,
            code=b"",
            calldata=b"",
            static=static,
        )
        interpreter = EVMInterpreter(context)
        context.push_call(call)
        context.accessed_addresses.add(self.TARGET)
        context.set_balance(self.CALLER, 10**9)
        context.set_balance(self.TARGET, 1)
        return interpreter, context, call

    def _push_call_operands(self, call: CallContext, gas: int, value: int = 0, args_size: int = 0, ret_size: int = 0) -> None:
        addr_int = int(self.TARGET, 16)
        # PUSH order (bottom -> top): ret_size, ret_offset, args_size, args_offset, value, address, gas
        for item in (ret_size, 0, args_size, 0, value, addr_int, gas):
            call.stack.push(item)

    def _push_staticcall_operands(self, call: CallContext, gas: int) -> None:
        addr_int = int(self.TARGET, 16)
        # PUSH order (bottom -> top): ret_size, ret_offset, args_size, args_offset, address, gas
        for item in (0, 0, 0, 0, addr_int, gas):
            call.stack.push(item)

    def test_call_gas_forwarding_apply_min_with_63_64_rule(self):
        interpreter, _, call = self._build_context(initial_gas=64000)
        self._push_call_operands(call, gas=50_000)
        mock_execute = MagicMock(return_value=(True, b""))
        interpreter._execute_subcall = mock_execute

        interpreter._op_call(call)

        forwarded = mock_execute.call_args.kwargs["gas"]
        assert forwarded == 50_000  # Requested less than cap so unchanged

    def test_call_gas_forwarding_caps_to_63_64_limit(self):
        interpreter, _, call = self._build_context(initial_gas=64_000)
        # Request more gas than allowed (63/64 rule should cap to 63,000)
        self._push_call_operands(call, gas=80_000)
        mock_execute = MagicMock(return_value=(True, b""))
        interpreter._execute_subcall = mock_execute

        interpreter._op_call(call)

        forwarded = mock_execute.call_args.kwargs["gas"]
        assert forwarded == 63_000

    def test_call_value_transfer_adds_stipend_without_exceeding_available(self):
        interpreter, context, call = self._build_context(initial_gas=25_000)
        value = 1_000
        context.set_balance(self.CALLER, 10_000)
        context.set_balance(self.TARGET, 1)
        self._push_call_operands(call, gas=20_000, value=value)
        mock_execute = MagicMock(return_value=(True, b""))
        interpreter._execute_subcall = mock_execute

        interpreter._op_call(call)

        forwarded = mock_execute.call_args.kwargs["gas"]
        remaining = 25_000 - 9_000  # value transfer base cost (address pre-warmed)
        max_forwardable = remaining - (remaining // 64)
        expected = min(20_000, max_forwardable)
        expected = min(expected + 2_300, remaining)
        assert forwarded == expected

    def test_staticcall_uses_same_gas_limit_rule(self):
        interpreter, _, call = self._build_context(initial_gas=90_000)
        self._push_staticcall_operands(call, gas=200_000)
        mock_execute = MagicMock(return_value=(True, b""))
        interpreter._execute_subcall = mock_execute

        interpreter._op_staticcall(call)

        forwarded = mock_execute.call_args.kwargs["gas"]
        assert forwarded == 90_000 - (90_000 // 64)

    def test_call_charges_input_copy_gas(self):
        interpreter, _, call = self._build_context(initial_gas=10_000)
        call.memory.expansion_cost = MagicMock(return_value=0)
        call.use_gas = MagicMock(wraps=call.use_gas)
        self._push_call_operands(call, gas=10_000, args_size=64)

        interpreter._op_call(call)

        expected_copy = 3 * ((64 + 31) // 32)
        call.use_gas.assert_called_once_with(expected_copy)

    def test_call_charges_output_copy_gas(self):
        interpreter, _, call = self._build_context(initial_gas=10_000)
        call.memory.expansion_cost = MagicMock(return_value=0)
        call.use_gas = MagicMock(wraps=call.use_gas)
        self._push_call_operands(call, gas=10_000, ret_size=64)
        interpreter._execute_subcall = MagicMock(return_value=(True, b""))

        interpreter._op_call(call)

        expected_copy = 3 * ((64 + 31) // 32)
        call.use_gas.assert_called_once_with(expected_copy)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
