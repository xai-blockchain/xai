"""
Tests for EVM Bytecode Interpreter.

Comprehensive tests for the EVM implementation including:
- Stack operations
- Memory operations
- Arithmetic operations
- Control flow
- Storage operations
- Contract calls
"""

import pytest
from unittest.mock import MagicMock, patch

from xai.core.vm.evm.stack import EVMStack, to_signed, to_unsigned, sign_extend, UINT256_MAX
from xai.core.vm.evm.memory import EVMMemory
from xai.core.vm.evm.storage import EVMStorage, TransientStorage
from xai.core.vm.evm.opcodes import Opcode, OPCODE_INFO, get_push_size, is_push
from xai.core.vm.evm.context import ExecutionContext, CallContext, CallType, BlockContext, Log
from xai.core.vm.evm.interpreter import EVMInterpreter
from xai.core.vm.evm.executor import EVMBytecodeExecutor
from xai.core.vm.exceptions import VMExecutionError


class TestEVMStack:
    """Tests for EVMStack implementation."""

    def test_push_pop(self):
        """Test basic push and pop operations."""
        stack = EVMStack()
        stack.push(42)
        assert stack.pop() == 42

    def test_push_multiple(self):
        """Test pushing multiple values."""
        stack = EVMStack()
        stack.push(1)
        stack.push(2)
        stack.push(3)
        assert stack.pop() == 3
        assert stack.pop() == 2
        assert stack.pop() == 1

    def test_stack_overflow(self):
        """Test stack overflow detection."""
        stack = EVMStack(max_depth=10)
        for i in range(10):
            stack.push(i)
        with pytest.raises(VMExecutionError, match="overflow"):
            stack.push(100)

    def test_stack_underflow(self):
        """Test stack underflow detection."""
        stack = EVMStack()
        with pytest.raises(VMExecutionError, match="underflow"):
            stack.pop()

    def test_peek(self):
        """Test peek operation."""
        stack = EVMStack()
        stack.push(1)
        stack.push(2)
        stack.push(3)
        assert stack.peek(0) == 3
        assert stack.peek(1) == 2
        assert stack.peek(2) == 1

    def test_dup(self):
        """Test DUP operations."""
        stack = EVMStack()
        stack.push(10)
        stack.push(20)
        stack.push(30)
        stack.dup(2)  # DUP2 - duplicate 2nd item
        assert stack.pop() == 20
        assert stack.pop() == 30

    def test_swap(self):
        """Test SWAP operations."""
        stack = EVMStack()
        stack.push(10)
        stack.push(20)
        stack.push(30)
        stack.swap(1)  # SWAP1 - swap top with 2nd
        assert stack.pop() == 20
        assert stack.pop() == 30

    def test_uint256_bounds(self):
        """Test 256-bit value bounding."""
        stack = EVMStack()
        stack.push(UINT256_MAX + 1)  # Should wrap to 0
        assert stack.pop() == 0

        stack.push(-1)  # Should become UINT256_MAX
        assert stack.pop() == UINT256_MAX


class TestSignedOperations:
    """Tests for signed integer operations."""

    def test_to_signed_positive(self):
        """Test converting small positive values."""
        assert to_signed(100) == 100

    def test_to_signed_negative(self):
        """Test converting large values to negative."""
        # UINT256_MAX should be -1 when signed
        assert to_signed(UINT256_MAX) == -1

    def test_to_unsigned_negative(self):
        """Test converting negative to unsigned."""
        assert to_unsigned(-1) == UINT256_MAX

    def test_sign_extend(self):
        """Test sign extension."""
        # 0xFF in 1 byte should become -1 when sign extended
        result = sign_extend(0xFF, 0)  # 1-byte value
        assert result == UINT256_MAX  # All 1s (represents -1)


class TestEVMMemory:
    """Tests for EVMMemory implementation."""

    def test_store_load_word(self):
        """Test storing and loading 32-byte words."""
        mem = EVMMemory()
        mem.store(0, 0x1234567890ABCDEF)
        assert mem.load(0) == 0x1234567890ABCDEF

    def test_store_load_byte(self):
        """Test storing and loading single bytes."""
        mem = EVMMemory()
        mem.store_byte(10, 0x42)
        assert mem.load_byte(10) == 0x42

    def test_memory_expansion(self):
        """Test memory expands automatically."""
        mem = EVMMemory()
        mem.store(100, 42)
        assert mem.size >= 132  # 100 + 32 bytes

    def test_memory_gas_cost(self):
        """Test memory expansion gas calculation."""
        mem = EVMMemory()
        # First expansion
        cost1 = mem.expansion_cost(0, 32)
        assert cost1 > 0

        # Same area should be free
        mem.load(0)
        cost2 = mem.expansion_cost(0, 32)
        assert cost2 == 0

    def test_memory_copy(self):
        """Test MCOPY operation."""
        mem = EVMMemory()
        mem.store(0, 0xDEADBEEF)
        mem.copy(32, 0, 32)
        assert mem.load(32) == mem.load(0)

    def test_memory_limit(self):
        """Test memory size limit."""
        mem = EVMMemory(max_size=1024)
        with pytest.raises(VMExecutionError, match="out of bounds"):
            mem.store(2000, 42)


class TestExpOpcode:
    """Ensure EXP gas metering follows exponent byte length rules."""

    def _make_call(self, gas: int = 5000) -> tuple[EVMInterpreter, CallContext]:
        block = BlockContext(
            number=1,
            timestamp=1000,
            gas_limit=1_000_000,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=0,
            chain_id=1,
        )
        context = ExecutionContext(
            block=block,
            tx_origin="0x" + "1" * 40,
            tx_gas_price=1,
            tx_gas_limit=1_000_000,
            tx_value=0,
        )
        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address="0x" + "2" * 40,
            caller="0x" + "1" * 40,
            origin="0x" + "1" * 40,
            value=0,
            gas=gas,
            code=b"",
            calldata=b"",
        )
        interpreter = EVMInterpreter(context)
        context.push_call(call)
        return interpreter, call

    def _run_exp(self, exponent: int, expected_dynamic_gas: int) -> None:
        interpreter, call = self._make_call()
        # Push exponent first, base second (LIFO stack)
        call.stack.push(exponent)
        call.stack.push(2)
        starting_gas = call.gas

        interpreter._op_exp(call)

        assert starting_gas - call.gas == expected_dynamic_gas

    def test_exp_zero_exponent_costs_zero_dynamic_gas(self):
        self._run_exp(0, expected_dynamic_gas=0)

    def test_exp_single_byte_exponent_costs_50(self):
        self._run_exp(0x7F, expected_dynamic_gas=50)

    def test_exp_two_byte_exponent_costs_100(self):
        self._run_exp(0x0100, expected_dynamic_gas=100)

    def test_exp_full_word_exponent_costs_1600(self):
        full_word = int.from_bytes(b"\x01" + b"\x00" * 31, "big")
        self._run_exp(full_word, expected_dynamic_gas=32 * 50)


class TestEVMStorage:
    """Tests for EVMStorage implementation."""

    def test_store_load(self):
        """Test basic storage operations."""
        storage = EVMStorage(address="0x1234")
        storage.store(0, 42)
        value, _ = storage.load(0)
        assert value == 42

    def test_cold_warm_access(self):
        """Test EIP-2929 warm/cold access gas."""
        storage = EVMStorage(address="0x1234")
        # Use set_raw to initialize without marking warm
        storage.set_raw(0, 100)
        storage.commit()  # Reset warm status

        # First load is cold
        _, gas1 = storage.load(0)
        assert gas1 == 2100  # Cold access

        # Second access is warm
        _, gas2 = storage.load(0)
        assert gas2 == 100  # Warm access

    def test_sstore_gas(self):
        """Test SSTORE gas pricing."""
        storage = EVMStorage(address="0x1234")

        # Set from zero to non-zero
        gas1, _ = storage.store(0, 100)
        assert gas1 >= 20000  # SSTORE_SET

        # Change non-zero to non-zero
        gas2, _ = storage.store(0, 200)
        assert gas2 < 20000  # Should be cheaper

    def test_storage_refund(self):
        """Test SSTORE refund on clearing."""
        storage = EVMStorage(address="0x1234")
        storage.set_raw(0, 100)  # Initialize
        storage.commit()  # Make it original value

        # Clear storage
        _, refund = storage.store(0, 0)
        assert refund > 0  # Should get refund


class TestTransientStorage:
    """Tests for EIP-1153 Transient Storage."""

    def test_tload_tstore(self):
        """Test transient load/store."""
        tstorage = TransientStorage()
        tstorage.store("0x1234", 0, 42)
        value, _ = tstorage.load("0x1234", 0)
        assert value == 42

    def test_transient_clear(self):
        """Test transient storage clears."""
        tstorage = TransientStorage()
        tstorage.store("0x1234", 0, 42)
        tstorage.clear()
        value, _ = tstorage.load("0x1234", 0)
        assert value == 0


class TestOpcodes:
    """Tests for opcode definitions."""

    def test_opcode_info_complete(self):
        """Test all opcodes have info."""
        for opcode in [0x00, 0x01, 0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0xF0]:
            assert opcode in OPCODE_INFO

    def test_push_size(self):
        """Test PUSH size calculation."""
        assert get_push_size(0x60) == 1  # PUSH1
        assert get_push_size(0x7F) == 32  # PUSH32
        assert get_push_size(0x00) == 0  # Not a PUSH

    def test_is_push(self):
        """Test PUSH detection."""
        assert is_push(0x5F)  # PUSH0
        assert is_push(0x60)  # PUSH1
        assert is_push(0x7F)  # PUSH32
        assert not is_push(0x00)  # STOP


class TestEVMInterpreter:
    """Tests for EVM interpreter execution."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock execution context."""
        block = BlockContext(
            number=1000,
            timestamp=1234567890,
            gas_limit=15_000_000,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=1000000000,
            chain_id=1,
        )
        return ExecutionContext(
            block=block,
            tx_origin="0x" + "1" * 40,
            tx_gas_price=1000000000,
            tx_gas_limit=1000000,
            tx_value=0,
        )

    @pytest.fixture
    def call_context(self, mock_context):
        """Create a call context for testing."""
        return CallContext(
            call_type=CallType.CALL,
            depth=0,
            address="0x" + "2" * 40,
            caller="0x" + "1" * 40,
            origin="0x" + "1" * 40,
            value=0,
            gas=100000,
            code=b"",
            calldata=b"",
        )

    def test_stop(self, mock_context, call_context):
        """Test STOP opcode."""
        call_context.code = bytes([Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.halted

    def test_add(self, mock_context, call_context):
        """Test ADD opcode."""
        # PUSH1 10, PUSH1 20, ADD
        call_context.code = bytes([0x60, 10, 0x60, 20, Opcode.ADD, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 30

    def test_sub(self, mock_context, call_context):
        """Test SUB opcode."""
        # PUSH1 20, PUSH1 30, SUB (30 - 20 = 10)
        call_context.code = bytes([0x60, 20, 0x60, 30, Opcode.SUB, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 10

    def test_mul(self, mock_context, call_context):
        """Test MUL opcode."""
        # PUSH1 5, PUSH1 7, MUL
        call_context.code = bytes([0x60, 5, 0x60, 7, Opcode.MUL, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 35

    def test_div(self, mock_context, call_context):
        """Test DIV opcode."""
        # PUSH1 3, PUSH1 21, DIV (21 / 3 = 7)
        call_context.code = bytes([0x60, 3, 0x60, 21, Opcode.DIV, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 7

    def test_div_by_zero(self, mock_context, call_context):
        """Test DIV by zero returns 0."""
        # PUSH1 0, PUSH1 10, DIV
        call_context.code = bytes([0x60, 0, 0x60, 10, Opcode.DIV, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 0

    def test_comparison_lt(self, mock_context, call_context):
        """Test LT opcode."""
        # PUSH1 20, PUSH1 10, LT (10 < 20 = 1)
        call_context.code = bytes([0x60, 20, 0x60, 10, Opcode.LT, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 1

    def test_comparison_eq(self, mock_context, call_context):
        """Test EQ opcode."""
        # PUSH1 42, PUSH1 42, EQ
        call_context.code = bytes([0x60, 42, 0x60, 42, Opcode.EQ, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 1

    def test_bitwise_and(self, mock_context, call_context):
        """Test AND opcode."""
        # PUSH1 0x0F, PUSH1 0xFF, AND
        call_context.code = bytes([0x60, 0x0F, 0x60, 0xFF, Opcode.AND, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 0x0F

    def test_jump(self, mock_context, call_context):
        """Test JUMP opcode."""
        # PUSH1 5, JUMP, INVALID, INVALID, INVALID, JUMPDEST, PUSH1 42, STOP
        call_context.code = bytes([
            0x60, 5,          # PUSH1 5
            Opcode.JUMP,      # JUMP to offset 5
            Opcode.INVALID,   # offset 3
            Opcode.INVALID,   # offset 4
            Opcode.JUMPDEST,  # offset 5 - valid destination
            0x60, 42,         # PUSH1 42
            Opcode.STOP
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 42

    def test_jumpi_taken(self, mock_context, call_context):
        """Test JUMPI when condition is true."""
        # PUSH1 1 (true), PUSH1 6, JUMPI, INVALID, INVALID, JUMPDEST, PUSH1 99, STOP
        call_context.code = bytes([
            0x60, 1,          # PUSH1 1 (condition)
            0x60, 7,          # PUSH1 7 (destination)
            Opcode.JUMPI,     # JUMPI
            Opcode.INVALID,   # offset 5
            Opcode.INVALID,   # offset 6
            Opcode.JUMPDEST,  # offset 7
            0x60, 99,         # PUSH1 99
            Opcode.STOP
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 99

    def test_memory_operations(self, mock_context, call_context):
        """Test MSTORE and MLOAD."""
        # PUSH1 42, PUSH1 0, MSTORE, PUSH1 0, MLOAD
        call_context.code = bytes([
            0x60, 42,         # PUSH1 42
            0x60, 0,          # PUSH1 0 (offset)
            Opcode.MSTORE,    # MSTORE
            0x60, 0,          # PUSH1 0
            Opcode.MLOAD,     # MLOAD
            Opcode.STOP
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 42

    def test_calldataload(self, mock_context, call_context):
        """Test CALLDATALOAD."""
        call_context.calldata = bytes([0x12, 0x34, 0x56, 0x78] + [0] * 28)
        call_context.code = bytes([
            0x60, 0,              # PUSH1 0
            Opcode.CALLDATALOAD,  # CALLDATALOAD
            Opcode.STOP
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        result = call_context.stack.pop()
        assert (result >> 224) == 0x12345678

    def test_return(self, mock_context, call_context):
        """Test RETURN opcode."""
        # Store value in memory and return it
        call_context.code = bytes([
            0x60, 0xAB,       # PUSH1 0xAB
            0x60, 0,          # PUSH1 0
            Opcode.MSTORE8,   # MSTORE8
            0x60, 1,          # PUSH1 1 (size)
            0x60, 0,          # PUSH1 0 (offset)
            Opcode.RETURN     # RETURN
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.halted
        assert call_context.output == bytes([0xAB])

    def test_revert(self, mock_context, call_context):
        """Test REVERT opcode."""
        call_context.code = bytes([
            0x60, 0,          # PUSH1 0 (size)
            0x60, 0,          # PUSH1 0 (offset)
            Opcode.REVERT     # REVERT
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.halted
        assert call_context.reverted

    def test_push0(self, mock_context, call_context):
        """Test PUSH0 opcode (EIP-3855)."""
        call_context.code = bytes([Opcode.PUSH0, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 0

    def test_dup_operations(self, mock_context, call_context):
        """Test DUP1-DUP16."""
        # PUSH1 1, PUSH1 2, PUSH1 3, DUP2
        call_context.code = bytes([
            0x60, 1,          # PUSH1 1
            0x60, 2,          # PUSH1 2
            0x60, 3,          # PUSH1 3
            Opcode.DUP2,      # DUP2
            Opcode.STOP
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 2  # Duplicated value

    def test_swap_operations(self, mock_context, call_context):
        """Test SWAP1-SWAP16."""
        # PUSH1 1, PUSH1 2, SWAP1
        call_context.code = bytes([
            0x60, 1,          # PUSH1 1
            0x60, 2,          # PUSH1 2
            Opcode.SWAP1,     # SWAP1
            Opcode.STOP
        ])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.stack.pop() == 1
        assert call_context.stack.pop() == 2

    def test_gas_consumption(self, mock_context, call_context):
        """Test gas is consumed correctly."""
        initial_gas = call_context.gas
        call_context.code = bytes([0x60, 1, 0x60, 2, Opcode.ADD, Opcode.STOP])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        interp.execute(call_context)
        assert call_context.gas < initial_gas

    def test_out_of_gas(self, mock_context, call_context):
        """Test out of gas error."""
        call_context.gas = 1  # Very low gas
        call_context.code = bytes([0x60, 1, 0x60, 2, Opcode.ADD])
        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call_context)
        with pytest.raises(VMExecutionError, match="[Oo]ut of gas"):
            interp.execute(call_context)


class TestEVMExecutor:
    """Tests for EVM executor integration."""

    @pytest.fixture
    def mock_blockchain(self):
        """Create a mock blockchain."""
        blockchain = MagicMock()
        blockchain.chain = []
        blockchain.contracts = {}
        blockchain.get_balance.return_value = 1000000
        blockchain.nonce_tracker.get_nonce.return_value = 0
        return blockchain

    def test_executor_init(self, mock_blockchain):
        """Test executor initialization."""
        executor = EVMBytecodeExecutor(mock_blockchain)
        assert executor.chain_id == 0x584149  # XAI

    def test_deploy_simple_contract(self, mock_blockchain):
        """Test deploying a simple contract."""
        executor = EVMBytecodeExecutor(mock_blockchain)

        # Simple contract that returns 42
        # PUSH1 42, PUSH1 0, MSTORE, PUSH1 32, PUSH1 0, RETURN
        init_code = bytes([
            0x60, 42,         # PUSH1 42
            0x60, 0,          # PUSH1 0
            0x52,             # MSTORE
            0x60, 32,         # PUSH1 32 (size)
            0x60, 0,          # PUSH1 0 (offset)
            0xF3              # RETURN
        ])

        from xai.core.vm.executor import ExecutionMessage
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to=None,
            value=0,
            gas_limit=100000,
            data=init_code,
            nonce=0,
        )

        result = executor.execute(message)
        assert result.success
        assert result.gas_used > 0

    def test_estimate_gas(self, mock_blockchain):
        """Test gas estimation."""
        executor = EVMBytecodeExecutor(mock_blockchain)

        from xai.core.vm.executor import ExecutionMessage
        message = ExecutionMessage(
            sender="0x" + "1" * 40,
            to=None,
            value=0,
            gas_limit=100000,
            data=bytes([0x60, 42, 0x00]),  # PUSH1 42, STOP
            nonce=0,
        )

        gas = executor.estimate_gas(message)
        assert gas > 21000  # At least base transaction cost


class TestKeccak256:
    """Tests for KECCAK256 opcode."""

    @pytest.fixture
    def mock_context(self):
        block = BlockContext(
            number=1000,
            timestamp=1234567890,
            gas_limit=15_000_000,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=1000000000,
            chain_id=1,
        )
        return ExecutionContext(
            block=block,
            tx_origin="0x" + "1" * 40,
            tx_gas_price=1000000000,
            tx_gas_limit=1000000,
            tx_value=0,
        )

    def test_keccak256_empty(self, mock_context):
        """Test KECCAK256 of empty data."""
        import hashlib

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address="0x" + "2" * 40,
            caller="0x" + "1" * 40,
            origin="0x" + "1" * 40,
            value=0,
            gas=100000,
            code=bytes([
                0x60, 0,          # PUSH1 0 (size)
                0x60, 0,          # PUSH1 0 (offset)
                Opcode.KECCAK256,
                Opcode.STOP
            ]),
            calldata=b"",
        )

        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call)
        interp.execute(call)

        result = call.stack.pop()
        expected = int.from_bytes(hashlib.sha3_256(b"").digest(), "big")
        assert result == expected


class TestLogs:
    """Tests for LOG opcodes."""

    @pytest.fixture
    def mock_context(self):
        block = BlockContext(
            number=1000,
            timestamp=1234567890,
            gas_limit=15_000_000,
            coinbase="0x" + "0" * 40,
            prevrandao=0,
            base_fee=1000000000,
            chain_id=1,
        )
        return ExecutionContext(
            block=block,
            tx_origin="0x" + "1" * 40,
            tx_gas_price=1000000000,
            tx_gas_limit=1000000,
            tx_value=0,
        )

    def test_log0(self, mock_context):
        """Test LOG0 opcode."""
        address = "0x" + "2" * 40
        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=address,
            caller="0x" + "1" * 40,
            origin="0x" + "1" * 40,
            value=0,
            gas=100000,
            code=bytes([
                0x60, 0xAB,       # PUSH1 0xAB (data)
                0x60, 0,          # PUSH1 0
                Opcode.MSTORE8,   # Store data
                0x60, 1,          # PUSH1 1 (size)
                0x60, 0,          # PUSH1 0 (offset)
                Opcode.LOG0,
                Opcode.STOP
            ]),
            calldata=b"",
        )

        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call)
        interp.execute(call)

        assert len(mock_context.logs) == 1
        assert mock_context.logs[0].address == address
        assert len(mock_context.logs[0].topics) == 0
        assert mock_context.logs[0].data == bytes([0xAB])

    def test_log_in_static_call_fails(self, mock_context):
        """Test LOG fails in static context."""
        call = CallContext(
            call_type=CallType.STATICCALL,
            depth=0,
            address="0x" + "2" * 40,
            caller="0x" + "1" * 40,
            origin="0x" + "1" * 40,
            value=0,
            gas=100000,
            code=bytes([
                0x60, 0,          # PUSH1 0 (size)
                0x60, 0,          # PUSH1 0 (offset)
                Opcode.LOG0,
                Opcode.STOP
            ]),
            calldata=b"",
            static=True,
        )

        interp = EVMInterpreter(mock_context)
        mock_context.push_call(call)
        with pytest.raises(VMExecutionError, match="static"):
            interp.execute(call)
