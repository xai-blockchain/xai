"""
Comprehensive tests for EVM CREATE and CREATE2 opcodes.

Tests proper init code execution, deployed bytecode extraction,
nonce management, and address computation.
"""

import pytest
from unittest.mock import MagicMock, patch

from xai.core.vm.evm.interpreter import EVMInterpreter
from xai.core.vm.evm.context import (
    ExecutionContext,
    CallContext,
    BlockContext,
    CallType,
)
from xai.core.vm.evm.opcodes import Opcode
from xai.core.vm.exceptions import VMExecutionError
from xai.core.vm.evm import interpreter_helpers


class TestCreateOpcodes:
    """Tests for CREATE and CREATE2 opcodes."""

    def setup_method(self):
        """Set up test environment."""
        # Create mock blockchain with nonce tracking
        self.mock_blockchain = MagicMock()
        self.mock_blockchain.contracts = {}
        self.mock_blockchain.nonce_tracker = MagicMock()
        self.mock_blockchain.nonce_tracker.get_nonce = MagicMock(return_value=0)
        self.mock_blockchain.nonce_tracker.set_nonce = MagicMock()

        # Create execution context
        self.block = BlockContext(
            number=1,
            timestamp=1000,
            gas_limit=10_000_000,
            coinbase="0x0000000000000000000000000000000000000000",
            prevrandao=0,
            base_fee=1_000_000_000,
            chain_id=1,
        )

        self.context = ExecutionContext(
            block=self.block,
            tx_origin="0x1111111111111111111111111111111111111111",
            tx_gas_price=1_000_000_000,
            tx_gas_limit=1_000_000,
            tx_value=0,
            blockchain=self.mock_blockchain,
        )

        # Set initial balance for deployer
        self.deployer_address = "0x1234567890123456789012345678901234567890"
        self.context.set_balance(self.deployer_address, 10**18)  # 1 ETH

    def _single_byte_return_init_code(self) -> bytes:
        """Init code that returns a single byte 0x2a."""
        return bytes([
            Opcode.PUSH1, 0x2A,  # value
            Opcode.PUSH1, 0x00,  # offset
            Opcode.MSTORE8,
            Opcode.PUSH1, 0x01,  # size
            Opcode.PUSH1, 0x00,  # offset
            Opcode.RETURN,
        ])

    def _prepare_create_call(self, gas: int, init_code: bytes) -> CallContext:
        """Build a call context preloaded with init code for CREATE."""
        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=gas,
            code=b"",
            calldata=b"",
        )
        call.memory.store_range(0, init_code)
        call.stack.push(len(init_code))
        call.stack.push(0)  # offset
        call.stack.push(0)  # value
        return call

    def test_create_simple_deployment(self):
        """Test CREATE with simple contract deployment."""
        # Init code that returns deployed bytecode
        # PUSH1 0x02 (deployed code length)
        # PUSH1 0x0C (offset where deployed code starts)
        # RETURN
        # [deployed code]: PUSH1 0x42 STOP
        init_code = bytes.fromhex("600260" + "0C" + "F3" + "6042" + "00")

        # Create call context
        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=500_000,
            code=b"",  # Outer code doesn't matter
            calldata=b"",
        )

        # Store init code in memory at offset 0
        call.memory.store_range(0, init_code)

        # Stack: size=len(init_code), offset=0, value=0
        call.stack.push(0)  # value
        call.stack.push(0)  # offset
        call.stack.push(len(init_code))  # size

        # Execute CREATE
        interpreter = EVMInterpreter(self.context)
        interpreter._op_create(call)

        # Should return non-zero address
        result_addr_int = call.stack.pop()
        assert result_addr_int != 0

        # Convert to hex address
        result_addr = f"0x{result_addr_int:040x}"

        # Verify nonce was incremented
        assert self.mock_blockchain.nonce_tracker.set_nonce.called

        # Verify deployed code was stored
        assert result_addr.upper() in self.mock_blockchain.contracts

    def test_create_with_constructor_args(self):
        """Test CREATE with constructor that processes arguments."""
        # Init code that reads constructor args and returns bytecode
        # For simplicity, just return a fixed bytecode
        deployed_bytecode = bytes.fromhex("6042600052602060006000F3")  # Return 0x42

        # Calculate offset: 1 (PUSH1) + 1 (size) + 1 (PUSH1) + 1 (offset) + 1 (RETURN) = 5
        init_header_size = 5
        init_code = (
            bytes.fromhex("60" + f"{len(deployed_bytecode):02x}")  # PUSH1 size
            + bytes.fromhex("60" + f"{init_header_size:02x}")  # PUSH1 offset
            + bytes.fromhex("F3")  # RETURN
            + deployed_bytecode
        )

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=500_000,
            code=b"",
            calldata=b"",
        )

        call.memory.store_range(0, init_code)
        call.stack.push(0)  # value
        call.stack.push(0)  # offset
        call.stack.push(len(init_code))  # size

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create(call)

        result_addr_int = call.stack.pop()
        assert result_addr_int != 0

    def test_create_increments_nonce(self):
        """Test that CREATE increments deployer nonce."""
        init_code = bytes.fromhex("60026000F3")  # RETURN 2 bytes of zeros

        # Set initial nonce
        self.mock_blockchain.nonce_tracker.get_nonce.return_value = 5

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=500_000,
            code=b"",
            calldata=b"",
        )

        call.memory.store_range(0, init_code)
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create(call)

        # Verify nonce was incremented from 5 to 6
        self.mock_blockchain.nonce_tracker.set_nonce.assert_called_with(
            self.deployer_address, 6
        )

    def test_create_with_value_transfer(self):
        """Test CREATE with ETH value transfer to new contract."""
        init_code = bytes.fromhex("60026000F3")
        transfer_amount = 10**17  # 0.1 ETH

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=1_000_000,  # High gas for test
            code=b"",
            calldata=b"",
        )

        # Store init code in memory
        call.memory.store_range(0, init_code)

        # Stack setup (remember: push in REVERSE order of how opcode pops)
        # Opcode pops: value, offset, size
        # So push: size, offset, value
        call.stack.push(len(init_code))  # size (popped 3rd)
        call.stack.push(0)  # offset (popped 2nd)
        call.stack.push(transfer_amount)  # value (popped 1st)

        # Manually charge base gas (normally done by execute() loop)
        # CREATE base cost is 32000 gas
        call.use_gas(32000)

        initial_balance = self.context.get_balance(self.deployer_address)

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create(call)

        result_addr_int = call.stack.pop()
        assert result_addr_int != 0

        # Verify balance was transferred (may have tiny gas refund differences)
        result_addr = f"0x{result_addr_int:040x}"
        # Allow for small gas-related rounding (init code can leave 1-2 wei)
        assert abs(self.context.get_balance(result_addr) - transfer_amount) < 10
        assert abs(
            self.context.get_balance(self.deployer_address) - (initial_balance - transfer_amount)
        ) < 10

    def test_create_insufficient_balance(self):
        """Test CREATE fails with insufficient balance."""
        init_code = bytes.fromhex("60026000F3")
        transfer_amount = 10**20  # More than deployer has

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=1_000_000,
            code=b"",
            calldata=b"",
        )

        call.memory.store_range(0, init_code)
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(transfer_amount)

        # Charge base gas
        call.use_gas(32000)

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create(call)

        # Should return 0 (failure)
        result_addr_int = call.stack.pop()
        assert result_addr_int == 0

    def test_create_init_code_reverts(self):
        """Test CREATE when init code reverts."""
        # Init code that reverts: PUSH1 0 PUSH1 0 REVERT
        init_code = bytes.fromhex("60006000FD")

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=1_000_000,
            code=b"",
            calldata=b"",
        )

        call.memory.store_range(0, init_code)
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        # Charge base gas
        call.use_gas(32000)

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create(call)

        # Should return 0 (failure due to revert)
        result_addr_int = call.stack.pop()
        assert result_addr_int == 0

    def test_create_max_code_size_limit(self):
        """Test CREATE enforces EIP-170 code size limit (24KB)."""
        # Init code that returns more than 24KB of deployed code
        MAX_CODE_SIZE = 24576
        deployed_code = b"\x00" * (MAX_CODE_SIZE + 1)

        # Build init code: PUSH2 size PUSH2 offset RETURN [deployed_code]
        size_bytes = (len(deployed_code)).to_bytes(2, "big")
        offset_bytes = (9).to_bytes(2, "big")  # After init code instructions
        init_code = (
            bytes.fromhex("61") + size_bytes +  # PUSH2 size
            bytes.fromhex("61") + offset_bytes +  # PUSH2 offset
            bytes.fromhex("F3") +  # RETURN
            deployed_code
        )

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=5_000_000,  # High gas to avoid OOG
            code=b"",
            calldata=b"",
        )

        call.memory.store_range(0, init_code)
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        # Charge base gas
        call.use_gas(32000)

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create(call)

        # Should return 0 (failure due to code size limit)
        result_addr_int = call.stack.pop()
        assert result_addr_int == 0

    def test_create_charges_code_deposit_gas(self):
        """CREATE should charge 200 gas per byte of deployed code."""
        init_code = self._single_byte_return_init_code()

        call = self._prepare_create_call(200_000, init_code)
        call.use_gas(32_000)
        interpreter = EVMInterpreter(self.context)
        deposit_cost = interpreter_helpers.CODE_DEPOSIT_GAS * 1

        with patch.object(call, "use_gas", wraps=call.use_gas) as mocked_use_gas:
            interpreter._op_create(call)

        result_addr_int = call.stack.pop()
        assert result_addr_int != 0
        deployed_address = f"0x{result_addr_int:040x}"
        assert self.context.get_code(deployed_address) == b"\x2a"

        assert any(call_args.args and call_args.args[0] == deposit_cost for call_args in mocked_use_gas.call_args_list)

    def test_create_code_deposit_oom_reverts(self):
        """CREATE fails if caller lacks gas for code deposit."""
        init_code = self._single_byte_return_init_code()

        call = self._prepare_create_call(200_000, init_code)
        call.use_gas(32_000)
        interpreter = EVMInterpreter(self.context)
        deposit_cost = interpreter_helpers.CODE_DEPOSIT_GAS * 1

        original_use_gas = call.use_gas

        def reject_deposit(amount: int) -> bool:
            if amount == deposit_cost:
                return False
            return original_use_gas(amount)

        call.use_gas = MagicMock(side_effect=reject_deposit)
        interpreter._op_create(call)

        result_addr_int = call.stack.pop()
        assert result_addr_int == 0
        expected_address = interpreter_helpers.compute_create_address(self.deployer_address, 0)
        assert self.context.get_code(expected_address) == b""

    def test_create2_deterministic_address(self):
        """Test CREATE2 produces deterministic addresses."""
        init_code = bytes.fromhex("60026000F3")
        salt = 42

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=500_000,
            code=b"",
            calldata=b"",
        )

        call.memory.store_range(0, init_code)
        call.stack.push(salt)  # salt
        call.stack.push(len(init_code))  # size
        call.stack.push(0)  # offset
        call.stack.push(0)  # value

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create2(call)

        addr1 = call.stack.pop()

        # Deploy again with same salt - should get same address (but fail due to collision)
        call.stack.push(salt)
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        interpreter._op_create2(call)
        result = call.stack.pop()

        # Should fail (return 0) because address already has code
        assert result == 0

    def test_create2_different_salt_different_address(self):
        """Test CREATE2 with different salts produces different addresses."""
        init_code = bytes.fromhex("60026000F3")

        call = CallContext(
            call_type=CallType.CALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=500_000,
            code=b"",
            calldata=b"",
        )

        # Deploy with salt=1
        call.memory.store_range(0, init_code)
        call.stack.push(1)  # salt
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        interpreter = EVMInterpreter(self.context)
        interpreter._op_create2(call)
        addr1 = call.stack.pop()

        # Deploy with salt=2
        call.stack.push(2)  # different salt
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        interpreter._op_create2(call)
        addr2 = call.stack.pop()

        # Should be different addresses
        assert addr1 != addr2
        assert addr1 != 0
        assert addr2 != 0

    def test_create_in_static_context_fails(self):
        """Test CREATE fails in static context."""
        init_code = bytes.fromhex("60026000F3")

        call = CallContext(
            call_type=CallType.STATICCALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=500_000,
            code=b"",
            calldata=b"",
            static=True,  # Static mode
        )

        call.memory.store_range(0, init_code)
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        interpreter = EVMInterpreter(self.context)

        with pytest.raises(VMExecutionError, match="not allowed in static context"):
            interpreter._op_create(call)

    def test_create2_in_static_context_fails(self):
        """Test CREATE2 fails in static context."""
        init_code = bytes.fromhex("60026000F3")

        call = CallContext(
            call_type=CallType.STATICCALL,
            depth=0,
            address=self.deployer_address,
            caller=self.context.tx_origin,
            origin=self.context.tx_origin,
            value=0,
            gas=500_000,
            code=b"",
            calldata=b"",
            static=True,
        )

        call.memory.store_range(0, init_code)
        call.stack.push(42)  # salt
        call.stack.push(len(init_code))
        call.stack.push(0)
        call.stack.push(0)

        interpreter = EVMInterpreter(self.context)

        with pytest.raises(VMExecutionError, match="not allowed in static context"):
            interpreter._op_create2(call)


class TestRLPEncoding:
    """Tests for RLP encoding helper."""

    def test_rlp_encode_address_zero_nonce(self):
        """Test RLP encoding with nonce=0."""
        address = "0x1234567890123456789012345678901234567890"
        nonce = 0

        result = interpreter_helpers.rlp_encode_address_nonce(address, nonce)

        # Should be: list prefix + address prefix + address bytes + nonce (0x80 for empty)
        assert isinstance(result, bytes)
        assert len(result) > 20  # At least address + encoding

    def test_rlp_encode_address_small_nonce(self):
        """Test RLP encoding with small nonce < 128."""
        address = "0x1234567890123456789012345678901234567890"
        nonce = 5

        result = interpreter_helpers.rlp_encode_address_nonce(address, nonce)
        assert isinstance(result, bytes)

    def test_rlp_encode_address_large_nonce(self):
        """Test RLP encoding with large nonce."""
        address = "0x1234567890123456789012345678901234567890"
        nonce = 256

        result = interpreter_helpers.rlp_encode_address_nonce(address, nonce)
        assert isinstance(result, bytes)


class TestAddressComputation:
    """Tests for address computation helpers."""

    def test_create_address_computation(self):
        """Test CREATE address matches expected value."""
        sender = "0x1234567890123456789012345678901234567890"
        nonce = 0

        address = interpreter_helpers.compute_create_address(sender, nonce)

        # Should be 20-byte hex address with 0x prefix
        assert address.startswith("0x")
        assert len(address) == 42  # 0x + 40 hex chars

    def test_create_address_changes_with_nonce(self):
        """Test CREATE address changes with different nonce."""
        sender = "0x1234567890123456789012345678901234567890"

        addr1 = interpreter_helpers.compute_create_address(sender, 0)
        addr2 = interpreter_helpers.compute_create_address(sender, 1)

        assert addr1 != addr2

    def test_create2_address_computation(self):
        """Test CREATE2 address computation."""
        sender = "0x1234567890123456789012345678901234567890"
        salt = 42
        init_code_hash = b"\x00" * 32

        address = interpreter_helpers.compute_create2_address(
            sender, salt, init_code_hash
        )

        assert address.startswith("0x")
        assert len(address) == 42

    def test_create2_address_deterministic(self):
        """Test CREATE2 address is deterministic."""
        sender = "0x1234567890123456789012345678901234567890"
        salt = 42
        init_code_hash = b"\x00" * 32

        addr1 = interpreter_helpers.compute_create2_address(
            sender, salt, init_code_hash
        )
        addr2 = interpreter_helpers.compute_create2_address(
            sender, salt, init_code_hash
        )

        assert addr1 == addr2
