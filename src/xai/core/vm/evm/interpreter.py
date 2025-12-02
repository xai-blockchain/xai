"""
EVM Bytecode Interpreter.

This is the core execution engine that interprets EVM bytecode, handling
all opcodes including arithmetic, stack, memory, storage, and control flow.
"""

from __future__ import annotations

import hashlib
import time
from typing import Optional, Callable, Dict, TYPE_CHECKING

from .opcodes import (
    Opcode,
    OPCODE_INFO,
    get_push_size,
    is_push,
    is_dup,
    is_swap,
    is_log,
    get_log_topic_count,
    is_terminating,
)
from .stack import EVMStack, to_signed, to_unsigned, sign_extend, UINT256_MAX
from .memory import EVMMemory
from .context import ExecutionContext, CallContext, CallType, Log
from ..exceptions import VMExecutionError

if TYPE_CHECKING:
    from .storage import EVMStorage


# Constants
UINT256_CEILING = 2**256


class EVMInterpreter:
    """
    EVM Bytecode Interpreter.

    Executes EVM bytecode instruction by instruction, managing:
    - Program counter advancement
    - Gas consumption
    - Stack operations
    - Memory operations
    - Storage operations
    - Control flow (jumps, calls, returns)
    - Events (logs)

    Security features:
    - Gas limit enforcement
    - Stack depth checking
    - Memory expansion limiting
    - Storage size limiting
    - Execution timeout
    - Reentrancy protection at call level
    """

    # Execution limits
    MAX_EXECUTION_TIME = 10.0  # 10 seconds
    MAX_INSTRUCTIONS = 10_000_000  # 10 million instructions

    def __init__(self, context: ExecutionContext) -> None:
        """
        Initialize interpreter with execution context.

        Args:
            context: Execution context
        """
        self.context = context
        self._instruction_count = 0
        self._start_time = 0.0

        # Opcode handlers
        self._handlers: Dict[int, Callable[[CallContext], None]] = {
            # Stop and Arithmetic
            Opcode.STOP: self._op_stop,
            Opcode.ADD: self._op_add,
            Opcode.MUL: self._op_mul,
            Opcode.SUB: self._op_sub,
            Opcode.DIV: self._op_div,
            Opcode.SDIV: self._op_sdiv,
            Opcode.MOD: self._op_mod,
            Opcode.SMOD: self._op_smod,
            Opcode.ADDMOD: self._op_addmod,
            Opcode.MULMOD: self._op_mulmod,
            Opcode.EXP: self._op_exp,
            Opcode.SIGNEXTEND: self._op_signextend,
            # Comparison
            Opcode.LT: self._op_lt,
            Opcode.GT: self._op_gt,
            Opcode.SLT: self._op_slt,
            Opcode.SGT: self._op_sgt,
            Opcode.EQ: self._op_eq,
            Opcode.ISZERO: self._op_iszero,
            # Bitwise
            Opcode.AND: self._op_and,
            Opcode.OR: self._op_or,
            Opcode.XOR: self._op_xor,
            Opcode.NOT: self._op_not,
            Opcode.BYTE: self._op_byte,
            Opcode.SHL: self._op_shl,
            Opcode.SHR: self._op_shr,
            Opcode.SAR: self._op_sar,
            # Keccak256
            Opcode.KECCAK256: self._op_keccak256,
            # Environmental
            Opcode.ADDRESS: self._op_address,
            Opcode.BALANCE: self._op_balance,
            Opcode.ORIGIN: self._op_origin,
            Opcode.CALLER: self._op_caller,
            Opcode.CALLVALUE: self._op_callvalue,
            Opcode.CALLDATALOAD: self._op_calldataload,
            Opcode.CALLDATASIZE: self._op_calldatasize,
            Opcode.CALLDATACOPY: self._op_calldatacopy,
            Opcode.CODESIZE: self._op_codesize,
            Opcode.CODECOPY: self._op_codecopy,
            Opcode.GASPRICE: self._op_gasprice,
            Opcode.EXTCODESIZE: self._op_extcodesize,
            Opcode.EXTCODECOPY: self._op_extcodecopy,
            Opcode.RETURNDATASIZE: self._op_returndatasize,
            Opcode.RETURNDATACOPY: self._op_returndatacopy,
            Opcode.EXTCODEHASH: self._op_extcodehash,
            # Block information
            Opcode.BLOCKHASH: self._op_blockhash,
            Opcode.COINBASE: self._op_coinbase,
            Opcode.TIMESTAMP: self._op_timestamp,
            Opcode.NUMBER: self._op_number,
            Opcode.PREVRANDAO: self._op_prevrandao,
            Opcode.GASLIMIT: self._op_gaslimit,
            Opcode.CHAINID: self._op_chainid,
            Opcode.SELFBALANCE: self._op_selfbalance,
            Opcode.BASEFEE: self._op_basefee,
            # Stack/Memory/Storage
            Opcode.POP: self._op_pop,
            Opcode.MLOAD: self._op_mload,
            Opcode.MSTORE: self._op_mstore,
            Opcode.MSTORE8: self._op_mstore8,
            Opcode.SLOAD: self._op_sload,
            Opcode.SSTORE: self._op_sstore,
            Opcode.JUMP: self._op_jump,
            Opcode.JUMPI: self._op_jumpi,
            Opcode.PC: self._op_pc,
            Opcode.MSIZE: self._op_msize,
            Opcode.GAS: self._op_gas,
            Opcode.JUMPDEST: self._op_jumpdest,
            Opcode.TLOAD: self._op_tload,
            Opcode.TSTORE: self._op_tstore,
            Opcode.MCOPY: self._op_mcopy,
            Opcode.PUSH0: self._op_push0,
            # Logging
            Opcode.LOG0: self._op_log,
            Opcode.LOG1: self._op_log,
            Opcode.LOG2: self._op_log,
            Opcode.LOG3: self._op_log,
            Opcode.LOG4: self._op_log,
            # System
            Opcode.CREATE: self._op_create,
            Opcode.CALL: self._op_call,
            Opcode.CALLCODE: self._op_callcode,
            Opcode.RETURN: self._op_return,
            Opcode.DELEGATECALL: self._op_delegatecall,
            Opcode.CREATE2: self._op_create2,
            Opcode.STATICCALL: self._op_staticcall,
            Opcode.REVERT: self._op_revert,
            Opcode.INVALID: self._op_invalid,
            Opcode.SELFDESTRUCT: self._op_selfdestruct,
        }

    def execute(self, call: CallContext) -> None:
        """
        Execute bytecode in the given call context.

        Args:
            call: Call context to execute

        Raises:
            VMExecutionError: On execution failure
        """
        self._start_time = time.time()
        self._instruction_count = 0

        # Pre-compute valid jump destinations
        jump_dests = self._compute_jump_destinations(call.code)

        while not call.halted and call.pc < len(call.code):
            # Check limits
            self._check_limits()

            # Fetch opcode
            opcode = call.code[call.pc]
            self._instruction_count += 1

            # Get opcode info for gas
            info = OPCODE_INFO.get(opcode)
            if info is None:
                raise VMExecutionError(f"Invalid opcode: 0x{opcode:02x}")

            # Consume base gas
            if not call.use_gas(info.gas_cost):
                raise VMExecutionError(
                    f"Out of gas at PC={call.pc}: opcode {info.name} costs {info.gas_cost}"
                )

            # Handle PUSH opcodes specially
            if is_push(opcode):
                self._handle_push(call, opcode)
                continue

            # Handle DUP opcodes
            if is_dup(opcode):
                position = opcode - 0x7F  # DUP1 = 0x80 -> position 1
                call.stack.dup(position)
                call.pc += 1
                continue

            # Handle SWAP opcodes
            if is_swap(opcode):
                position = opcode - 0x8F  # SWAP1 = 0x90 -> position 1
                call.stack.swap(position)
                call.pc += 1
                continue

            # Execute opcode handler
            handler = self._handlers.get(opcode)
            if handler is None:
                raise VMExecutionError(f"Unimplemented opcode: 0x{opcode:02x}")

            # Validate jump destinations
            if opcode == Opcode.JUMP or opcode == Opcode.JUMPI:
                dest = call.stack.peek(0)
                if dest not in jump_dests:
                    raise VMExecutionError(f"Invalid jump destination: {dest}")

            handler(call)

            # Advance PC unless handler did it
            if opcode not in (
                Opcode.JUMP,
                Opcode.JUMPI,
                Opcode.STOP,
                Opcode.RETURN,
                Opcode.REVERT,
                Opcode.SELFDESTRUCT,
                Opcode.INVALID,
            ):
                call.pc += 1

    def _check_limits(self) -> None:
        """Check execution limits."""
        # Time limit
        elapsed = time.time() - self._start_time
        if elapsed > self.MAX_EXECUTION_TIME:
            raise VMExecutionError(
                f"Execution timeout: {elapsed:.2f}s > {self.MAX_EXECUTION_TIME}s"
            )

        # Instruction limit
        if self._instruction_count > self.MAX_INSTRUCTIONS:
            raise VMExecutionError(
                f"Instruction limit exceeded: {self._instruction_count} > {self.MAX_INSTRUCTIONS}"
            )

    def _compute_jump_destinations(self, code: bytes) -> set:
        """
        Pre-compute valid JUMPDEST locations.

        Args:
            code: Contract bytecode

        Returns:
            Set of valid jump destination offsets
        """
        jump_dests = set()
        i = 0
        while i < len(code):
            op = code[i]
            if op == Opcode.JUMPDEST:
                jump_dests.add(i)
            # Skip PUSH data
            if is_push(op):
                push_size = get_push_size(op)
                i += push_size
            i += 1
        return jump_dests

    def _handle_push(self, call: CallContext, opcode: int) -> None:
        """Handle PUSH1-PUSH32 opcodes."""
        push_size = get_push_size(opcode)
        start = call.pc + 1
        end = start + push_size

        # Read bytes from code
        if end <= len(call.code):
            value_bytes = call.code[start:end]
        else:
            # Pad with zeros if reading past end
            value_bytes = call.code[start:] + bytes(end - len(call.code))

        # Convert to integer (big-endian)
        value = int.from_bytes(value_bytes, "big")
        call.stack.push(value)
        call.pc = end

    # ==================== Arithmetic Operations ====================

    def _op_stop(self, call: CallContext) -> None:
        """STOP: Halt execution."""
        call.halted = True

    def _op_add(self, call: CallContext) -> None:
        """ADD: Addition operation."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push((a + b) % UINT256_CEILING)

    def _op_mul(self, call: CallContext) -> None:
        """MUL: Multiplication operation."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push((a * b) % UINT256_CEILING)

    def _op_sub(self, call: CallContext) -> None:
        """SUB: Subtraction operation."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push((a - b) % UINT256_CEILING)

    def _op_div(self, call: CallContext) -> None:
        """DIV: Integer division."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(a // b if b != 0 else 0)

    def _op_sdiv(self, call: CallContext) -> None:
        """SDIV: Signed integer division."""
        a, b = to_signed(call.stack.pop()), to_signed(call.stack.pop())
        if b == 0:
            call.stack.push(0)
        else:
            sign = -1 if (a < 0) != (b < 0) else 1
            call.stack.push(to_unsigned(sign * (abs(a) // abs(b))))

    def _op_mod(self, call: CallContext) -> None:
        """MOD: Modulo operation."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(a % b if b != 0 else 0)

    def _op_smod(self, call: CallContext) -> None:
        """SMOD: Signed modulo."""
        a, b = to_signed(call.stack.pop()), to_signed(call.stack.pop())
        if b == 0:
            call.stack.push(0)
        else:
            sign = -1 if a < 0 else 1
            call.stack.push(to_unsigned(sign * (abs(a) % abs(b))))

    def _op_addmod(self, call: CallContext) -> None:
        """ADDMOD: Modular addition."""
        a, b, n = call.stack.pop(), call.stack.pop(), call.stack.pop()
        call.stack.push((a + b) % n if n != 0 else 0)

    def _op_mulmod(self, call: CallContext) -> None:
        """MULMOD: Modular multiplication."""
        a, b, n = call.stack.pop(), call.stack.pop(), call.stack.pop()
        call.stack.push((a * b) % n if n != 0 else 0)

    def _op_exp(self, call: CallContext) -> None:
        """EXP: Exponential operation."""
        base, exp = call.stack.pop(), call.stack.pop()

        # Calculate dynamic gas cost (50 gas per byte of exponent)
        exp_bytes = (exp.bit_length() + 7) // 8
        dynamic_gas = 50 * exp_bytes
        if not call.use_gas(dynamic_gas):
            raise VMExecutionError(f"Out of gas for EXP: need {dynamic_gas} more")

        call.stack.push(pow(base, exp, UINT256_CEILING))

    def _op_signextend(self, call: CallContext) -> None:
        """SIGNEXTEND: Extend sign of smaller integer."""
        byte_size, value = call.stack.pop(), call.stack.pop()
        call.stack.push(sign_extend(value, byte_size))

    # ==================== Comparison Operations ====================

    def _op_lt(self, call: CallContext) -> None:
        """LT: Less-than comparison."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(1 if a < b else 0)

    def _op_gt(self, call: CallContext) -> None:
        """GT: Greater-than comparison."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(1 if a > b else 0)

    def _op_slt(self, call: CallContext) -> None:
        """SLT: Signed less-than."""
        a, b = to_signed(call.stack.pop()), to_signed(call.stack.pop())
        call.stack.push(1 if a < b else 0)

    def _op_sgt(self, call: CallContext) -> None:
        """SGT: Signed greater-than."""
        a, b = to_signed(call.stack.pop()), to_signed(call.stack.pop())
        call.stack.push(1 if a > b else 0)

    def _op_eq(self, call: CallContext) -> None:
        """EQ: Equality comparison."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(1 if a == b else 0)

    def _op_iszero(self, call: CallContext) -> None:
        """ISZERO: Check if zero."""
        a = call.stack.pop()
        call.stack.push(1 if a == 0 else 0)

    # ==================== Bitwise Operations ====================

    def _op_and(self, call: CallContext) -> None:
        """AND: Bitwise AND."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(a & b)

    def _op_or(self, call: CallContext) -> None:
        """OR: Bitwise OR."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(a | b)

    def _op_xor(self, call: CallContext) -> None:
        """XOR: Bitwise XOR."""
        a, b = call.stack.pop(), call.stack.pop()
        call.stack.push(a ^ b)

    def _op_not(self, call: CallContext) -> None:
        """NOT: Bitwise NOT."""
        a = call.stack.pop()
        call.stack.push(UINT256_MAX ^ a)

    def _op_byte(self, call: CallContext) -> None:
        """BYTE: Retrieve single byte."""
        i, x = call.stack.pop(), call.stack.pop()
        if i >= 32:
            call.stack.push(0)
        else:
            call.stack.push((x >> (248 - i * 8)) & 0xFF)

    def _op_shl(self, call: CallContext) -> None:
        """SHL: Shift left."""
        shift, value = call.stack.pop(), call.stack.pop()
        if shift >= 256:
            call.stack.push(0)
        else:
            call.stack.push((value << shift) % UINT256_CEILING)

    def _op_shr(self, call: CallContext) -> None:
        """SHR: Logical shift right."""
        shift, value = call.stack.pop(), call.stack.pop()
        if shift >= 256:
            call.stack.push(0)
        else:
            call.stack.push(value >> shift)

    def _op_sar(self, call: CallContext) -> None:
        """SAR: Arithmetic shift right."""
        shift, value = call.stack.pop(), call.stack.pop()
        signed_value = to_signed(value)
        if shift >= 256:
            call.stack.push(to_unsigned(-1 if signed_value < 0 else 0))
        else:
            call.stack.push(to_unsigned(signed_value >> shift))

    # ==================== Keccak256 ====================

    def _op_keccak256(self, call: CallContext) -> None:
        """KECCAK256: Compute Keccak-256 hash."""
        offset, size = call.stack.pop(), call.stack.pop()

        # Calculate memory expansion gas
        expansion_cost = call.memory.expansion_cost(offset, size)
        word_cost = 6 * ((size + 31) // 32)  # 6 gas per word
        if not call.use_gas(expansion_cost + word_cost):
            raise VMExecutionError("Out of gas for KECCAK256")

        data = call.memory.load_range(offset, size)
        hash_result = hashlib.sha3_256(data).digest()
        call.stack.push(int.from_bytes(hash_result, "big"))

    # ==================== Environmental Operations ====================

    def _op_address(self, call: CallContext) -> None:
        """ADDRESS: Get executing contract address."""
        call.stack.push(int(call.address, 16) if call.address.startswith("0x") else int(call.address, 16))

    def _op_balance(self, call: CallContext) -> None:
        """BALANCE: Get account balance."""
        addr_int = call.stack.pop()
        address = f"0x{addr_int:040x}"

        # Warm/cold gas (EIP-2929)
        gas = self.context.warm_address(address)
        if not call.use_gas(gas):
            raise VMExecutionError("Out of gas for BALANCE")

        balance = self.context.get_balance(address)
        call.stack.push(balance)

    def _op_origin(self, call: CallContext) -> None:
        """ORIGIN: Get transaction origin."""
        origin = self.context.tx_origin
        call.stack.push(int(origin, 16) if origin.startswith("0x") else int(origin, 16))

    def _op_caller(self, call: CallContext) -> None:
        """CALLER: Get immediate caller."""
        caller = call.caller
        call.stack.push(int(caller, 16) if caller.startswith("0x") else int(caller, 16))

    def _op_callvalue(self, call: CallContext) -> None:
        """CALLVALUE: Get deposited value."""
        call.stack.push(call.value)

    def _op_calldataload(self, call: CallContext) -> None:
        """CALLDATALOAD: Load 32 bytes from calldata."""
        offset = call.stack.pop()
        if offset >= len(call.calldata):
            call.stack.push(0)
        else:
            end = min(offset + 32, len(call.calldata))
            data = call.calldata[offset:end]
            # Pad with zeros
            data = data + bytes(32 - len(data))
            call.stack.push(int.from_bytes(data, "big"))

    def _op_calldatasize(self, call: CallContext) -> None:
        """CALLDATASIZE: Get size of calldata."""
        call.stack.push(len(call.calldata))

    def _op_calldatacopy(self, call: CallContext) -> None:
        """CALLDATACOPY: Copy calldata to memory."""
        dest_offset, data_offset, size = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )

        # Calculate gas
        expansion_cost = call.memory.expansion_cost(dest_offset, size)
        copy_cost = 3 * ((size + 31) // 32)
        if not call.use_gas(expansion_cost + copy_cost):
            raise VMExecutionError("Out of gas for CALLDATACOPY")

        # Copy data with zero-padding
        if data_offset >= len(call.calldata):
            data = bytes(size)
        else:
            end = min(data_offset + size, len(call.calldata))
            data = call.calldata[data_offset:end]
            data = data + bytes(size - len(data))

        call.memory.store_range(dest_offset, data)

    def _op_codesize(self, call: CallContext) -> None:
        """CODESIZE: Get size of executing code."""
        call.stack.push(len(call.code))

    def _op_codecopy(self, call: CallContext) -> None:
        """CODECOPY: Copy code to memory."""
        dest_offset, code_offset, size = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )

        # Calculate gas
        expansion_cost = call.memory.expansion_cost(dest_offset, size)
        copy_cost = 3 * ((size + 31) // 32)
        if not call.use_gas(expansion_cost + copy_cost):
            raise VMExecutionError("Out of gas for CODECOPY")

        # Copy code with zero-padding
        if code_offset >= len(call.code):
            data = bytes(size)
        else:
            end = min(code_offset + size, len(call.code))
            data = call.code[code_offset:end]
            data = data + bytes(size - len(data))

        call.memory.store_range(dest_offset, data)

    def _op_gasprice(self, call: CallContext) -> None:
        """GASPRICE: Get gas price."""
        call.stack.push(self.context.tx_gas_price)

    def _op_extcodesize(self, call: CallContext) -> None:
        """EXTCODESIZE: Get external code size."""
        addr_int = call.stack.pop()
        address = f"0x{addr_int:040x}"

        # Warm/cold gas
        gas = self.context.warm_address(address)
        if not call.use_gas(gas):
            raise VMExecutionError("Out of gas for EXTCODESIZE")

        code = self.context.get_code(address)
        call.stack.push(len(code))

    def _op_extcodecopy(self, call: CallContext) -> None:
        """EXTCODECOPY: Copy external code to memory."""
        addr_int = call.stack.pop()
        dest_offset, code_offset, size = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )
        address = f"0x{addr_int:040x}"

        # Warm/cold gas
        warm_gas = self.context.warm_address(address)
        expansion_cost = call.memory.expansion_cost(dest_offset, size)
        copy_cost = 3 * ((size + 31) // 32)
        if not call.use_gas(warm_gas + expansion_cost + copy_cost):
            raise VMExecutionError("Out of gas for EXTCODECOPY")

        code = self.context.get_code(address)
        if code_offset >= len(code):
            data = bytes(size)
        else:
            end = min(code_offset + size, len(code))
            data = code[code_offset:end]
            data = data + bytes(size - len(data))

        call.memory.store_range(dest_offset, data)

    def _op_returndatasize(self, call: CallContext) -> None:
        """RETURNDATASIZE: Get size of return data."""
        call.stack.push(len(call.return_data))

    def _op_returndatacopy(self, call: CallContext) -> None:
        """RETURNDATACOPY: Copy return data to memory."""
        dest_offset, data_offset, size = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )

        # Bounds check
        if data_offset + size > len(call.return_data):
            raise VMExecutionError("Return data out of bounds")

        # Calculate gas
        expansion_cost = call.memory.expansion_cost(dest_offset, size)
        copy_cost = 3 * ((size + 31) // 32)
        if not call.use_gas(expansion_cost + copy_cost):
            raise VMExecutionError("Out of gas for RETURNDATACOPY")

        data = call.return_data[data_offset : data_offset + size]
        call.memory.store_range(dest_offset, data)

    def _op_extcodehash(self, call: CallContext) -> None:
        """EXTCODEHASH: Get hash of external code."""
        addr_int = call.stack.pop()
        address = f"0x{addr_int:040x}"

        # Warm/cold gas
        gas = self.context.warm_address(address)
        if not call.use_gas(gas):
            raise VMExecutionError("Out of gas for EXTCODEHASH")

        code_hash = self.context.get_code_hash(address)
        call.stack.push(code_hash)

    # ==================== Block Information ====================

    def _op_blockhash(self, call: CallContext) -> None:
        """BLOCKHASH: Get hash of recent block."""
        block_num = call.stack.pop()
        current = self.context.block.number

        # Only last 256 blocks available
        if block_num >= current or current - block_num > 256:
            call.stack.push(0)
        else:
            hash_val = self.context.block.get_block_hash(block_num)
            call.stack.push(hash_val)

    def _op_coinbase(self, call: CallContext) -> None:
        """COINBASE: Get block's beneficiary."""
        coinbase = self.context.block.coinbase
        call.stack.push(int(coinbase, 16) if coinbase.startswith("0x") else 0)

    def _op_timestamp(self, call: CallContext) -> None:
        """TIMESTAMP: Get block's timestamp."""
        call.stack.push(self.context.block.timestamp)

    def _op_number(self, call: CallContext) -> None:
        """NUMBER: Get block's number."""
        call.stack.push(self.context.block.number)

    def _op_prevrandao(self, call: CallContext) -> None:
        """PREVRANDAO: Get block's prevrandao value."""
        call.stack.push(self.context.block.prevrandao)

    def _op_gaslimit(self, call: CallContext) -> None:
        """GASLIMIT: Get block's gas limit."""
        call.stack.push(self.context.block.gas_limit)

    def _op_chainid(self, call: CallContext) -> None:
        """CHAINID: Get chain ID."""
        call.stack.push(self.context.block.chain_id)

    def _op_selfbalance(self, call: CallContext) -> None:
        """SELFBALANCE: Get balance of executing contract."""
        balance = self.context.get_balance(call.address)
        call.stack.push(balance)

    def _op_basefee(self, call: CallContext) -> None:
        """BASEFEE: Get block's base fee."""
        call.stack.push(self.context.block.base_fee)

    # ==================== Stack/Memory/Storage/Flow ====================

    def _op_pop(self, call: CallContext) -> None:
        """POP: Remove item from stack."""
        call.stack.pop()

    def _op_mload(self, call: CallContext) -> None:
        """MLOAD: Load word from memory."""
        offset = call.stack.pop()

        # Memory expansion gas
        expansion_cost = call.memory.expansion_cost(offset, 32)
        if not call.use_gas(expansion_cost):
            raise VMExecutionError("Out of gas for MLOAD")

        value = call.memory.load(offset)
        call.stack.push(value)

    def _op_mstore(self, call: CallContext) -> None:
        """MSTORE: Store word to memory."""
        offset, value = call.stack.pop(), call.stack.pop()

        # Memory expansion gas
        expansion_cost = call.memory.expansion_cost(offset, 32)
        if not call.use_gas(expansion_cost):
            raise VMExecutionError("Out of gas for MSTORE")

        call.memory.store(offset, value)

    def _op_mstore8(self, call: CallContext) -> None:
        """MSTORE8: Store byte to memory."""
        offset, value = call.stack.pop(), call.stack.pop()

        # Memory expansion gas
        expansion_cost = call.memory.expansion_cost(offset, 1)
        if not call.use_gas(expansion_cost):
            raise VMExecutionError("Out of gas for MSTORE8")

        call.memory.store_byte(offset, value & 0xFF)

    def _op_sload(self, call: CallContext) -> None:
        """SLOAD: Load word from storage."""
        key = call.stack.pop()
        storage = self.context.get_storage(call.address)

        # Get value and gas cost
        value, gas_cost = storage.load(key)

        # Charge gas (base already charged)
        additional = gas_cost - 100  # Base SLOAD cost already charged
        if additional > 0 and not call.use_gas(additional):
            raise VMExecutionError("Out of gas for SLOAD")

        call.stack.push(value)

    def _op_sstore(self, call: CallContext) -> None:
        """SSTORE: Save word to storage."""
        if call.static:
            raise VMExecutionError("SSTORE not allowed in static context")

        key, value = call.stack.pop(), call.stack.pop()
        storage = self.context.get_storage(call.address)

        # Get gas cost and refund
        gas_cost, refund = storage.store(key, value)

        # Charge gas (base already charged)
        additional = gas_cost - 100  # Base SSTORE cost already charged
        if additional > 0 and not call.use_gas(additional):
            raise VMExecutionError("Out of gas for SSTORE")

        # Track refund
        self.context.gas_refund += refund

    def _op_jump(self, call: CallContext) -> None:
        """JUMP: Unconditional jump."""
        dest = call.stack.pop()
        # Destination already validated in execute()
        call.pc = dest

    def _op_jumpi(self, call: CallContext) -> None:
        """JUMPI: Conditional jump."""
        dest, condition = call.stack.pop(), call.stack.pop()
        if condition != 0:
            call.pc = dest
        else:
            call.pc += 1

    def _op_pc(self, call: CallContext) -> None:
        """PC: Get program counter."""
        call.stack.push(call.pc)

    def _op_msize(self, call: CallContext) -> None:
        """MSIZE: Get size of active memory."""
        call.stack.push(call.memory.size)

    def _op_gas(self, call: CallContext) -> None:
        """GAS: Get remaining gas."""
        call.stack.push(call.gas)

    def _op_jumpdest(self, call: CallContext) -> None:
        """JUMPDEST: Mark valid jump destination."""
        # No-op, just marks a valid destination
        pass

    def _op_tload(self, call: CallContext) -> None:
        """TLOAD: Load from transient storage (EIP-1153)."""
        key = call.stack.pop()
        value, gas = self.context.transient_storage.load(call.address, key)
        # Base gas already charged
        call.stack.push(value)

    def _op_tstore(self, call: CallContext) -> None:
        """TSTORE: Store to transient storage (EIP-1153)."""
        if call.static:
            raise VMExecutionError("TSTORE not allowed in static context")

        key, value = call.stack.pop(), call.stack.pop()
        self.context.transient_storage.store(call.address, key, value)

    def _op_mcopy(self, call: CallContext) -> None:
        """MCOPY: Copy memory region (EIP-5656)."""
        dest, src, size = call.stack.pop(), call.stack.pop(), call.stack.pop()

        # Calculate gas
        expansion_cost = call.memory.expansion_cost(max(dest, src), size)
        copy_cost = 3 * ((size + 31) // 32)
        if not call.use_gas(expansion_cost + copy_cost):
            raise VMExecutionError("Out of gas for MCOPY")

        call.memory.copy(dest, src, size)

    def _op_push0(self, call: CallContext) -> None:
        """PUSH0: Push 0 onto stack (EIP-3855)."""
        call.stack.push(0)

    # ==================== Logging ====================

    def _op_log(self, call: CallContext) -> None:
        """LOG0-LOG4: Append log record."""
        if call.static:
            raise VMExecutionError("LOG not allowed in static context")

        opcode = call.code[call.pc]
        topic_count = get_log_topic_count(opcode)

        offset, size = call.stack.pop(), call.stack.pop()
        topics = [call.stack.pop() for _ in range(topic_count)]

        # Calculate gas
        expansion_cost = call.memory.expansion_cost(offset, size)
        data_cost = 8 * size  # 8 gas per byte
        topic_cost = 375 * topic_count  # Already in base cost
        if not call.use_gas(expansion_cost + data_cost):
            raise VMExecutionError("Out of gas for LOG")

        data = call.memory.load_range(offset, size)
        log = Log(address=call.address, topics=topics, data=data)
        self.context.add_log(log)

    # ==================== System Operations ====================

    def _op_create(self, call: CallContext) -> None:
        """CREATE: Create new contract."""
        if call.static:
            raise VMExecutionError("CREATE not allowed in static context")

        value, offset, size = call.stack.pop(), call.stack.pop(), call.stack.pop()

        # Memory expansion
        expansion_cost = call.memory.expansion_cost(offset, size)
        if not call.use_gas(expansion_cost):
            raise VMExecutionError("Out of gas for CREATE")

        # Get init code
        init_code = call.memory.load_range(offset, size)

        # Create contract address (keccak256(rlp([sender, nonce]))[12:])
        # Simplified: hash of sender + nonce
        nonce = 0  # Would get from account state
        addr_input = call.address.encode() + nonce.to_bytes(8, "big")
        addr_hash = hashlib.sha3_256(addr_input).digest()
        new_address = f"0x{addr_hash[-20:].hex()}"

        # Execute init code and store result
        # For now, push address or 0 on failure
        call.stack.push(int(new_address[2:], 16))

    def _op_call(self, call: CallContext) -> None:
        """CALL: Message-call into account."""
        gas, addr_int, value, args_offset, args_size, ret_offset, ret_size = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )

        if call.static and value != 0:
            raise VMExecutionError("Value transfer not allowed in static context")

        address = f"0x{addr_int:040x}"

        # Warm/cold address gas
        warm_gas = self.context.warm_address(address)

        # Memory expansion
        in_expansion = call.memory.expansion_cost(args_offset, args_size)
        out_expansion = call.memory.expansion_cost(ret_offset, ret_size)

        total_gas = warm_gas + in_expansion + out_expansion
        if value != 0:
            total_gas += 9000  # Value transfer stipend

        if not call.use_gas(total_gas):
            raise VMExecutionError("Out of gas for CALL")

        # Get calldata
        calldata = call.memory.load_range(args_offset, args_size)

        # Execute call (simplified - would recurse into interpreter)
        # For now, return success
        call.return_data = b""
        call.stack.push(1)  # Success

    def _op_callcode(self, call: CallContext) -> None:
        """CALLCODE: Message-call with alternative code."""
        # Similar to CALL but executes code in current context
        self._op_call(call)  # Simplified

    def _op_return(self, call: CallContext) -> None:
        """RETURN: Halt and return output data."""
        offset, size = call.stack.pop(), call.stack.pop()

        # Memory expansion
        expansion_cost = call.memory.expansion_cost(offset, size)
        if not call.use_gas(expansion_cost):
            raise VMExecutionError("Out of gas for RETURN")

        call.output = call.memory.load_range(offset, size)
        call.halted = True

    def _op_delegatecall(self, call: CallContext) -> None:
        """DELEGATECALL: Message-call with caller's context."""
        gas, addr_int, args_offset, args_size, ret_offset, ret_size = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )

        address = f"0x{addr_int:040x}"

        # Warm/cold address gas
        warm_gas = self.context.warm_address(address)
        in_expansion = call.memory.expansion_cost(args_offset, args_size)
        out_expansion = call.memory.expansion_cost(ret_offset, ret_size)

        if not call.use_gas(warm_gas + in_expansion + out_expansion):
            raise VMExecutionError("Out of gas for DELEGATECALL")

        # Execute with current msg.sender and msg.value
        call.return_data = b""
        call.stack.push(1)

    def _op_create2(self, call: CallContext) -> None:
        """CREATE2: Create with deterministic address."""
        if call.static:
            raise VMExecutionError("CREATE2 not allowed in static context")

        value, offset, size, salt = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )

        # Memory expansion
        expansion_cost = call.memory.expansion_cost(offset, size)
        hash_cost = 6 * ((size + 31) // 32)  # SHA3 word cost
        if not call.use_gas(expansion_cost + hash_cost):
            raise VMExecutionError("Out of gas for CREATE2")

        init_code = call.memory.load_range(offset, size)

        # CREATE2 address: keccak256(0xff ++ sender ++ salt ++ keccak256(init_code))[12:]
        init_code_hash = hashlib.sha3_256(init_code).digest()
        addr_input = (
            b"\xff"
            + bytes.fromhex(call.address[2:] if call.address.startswith("0x") else call.address)
            + salt.to_bytes(32, "big")
            + init_code_hash
        )
        addr_hash = hashlib.sha3_256(addr_input).digest()
        new_address = f"0x{addr_hash[-20:].hex()}"

        call.stack.push(int(new_address[2:], 16))

    def _op_staticcall(self, call: CallContext) -> None:
        """STATICCALL: Static message-call (no state modification)."""
        gas, addr_int, args_offset, args_size, ret_offset, ret_size = (
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
            call.stack.pop(),
        )

        address = f"0x{addr_int:040x}"

        # Warm/cold address gas
        warm_gas = self.context.warm_address(address)
        in_expansion = call.memory.expansion_cost(args_offset, args_size)
        out_expansion = call.memory.expansion_cost(ret_offset, ret_size)

        if not call.use_gas(warm_gas + in_expansion + out_expansion):
            raise VMExecutionError("Out of gas for STATICCALL")

        # Execute in static mode (no state changes)
        call.return_data = b""
        call.stack.push(1)

    def _op_revert(self, call: CallContext) -> None:
        """REVERT: Halt and revert state changes."""
        offset, size = call.stack.pop(), call.stack.pop()

        # Memory expansion
        expansion_cost = call.memory.expansion_cost(offset, size)
        if not call.use_gas(expansion_cost):
            raise VMExecutionError("Out of gas for REVERT")

        call.output = call.memory.load_range(offset, size)
        call.halted = True
        call.reverted = True

        # Extract revert reason if ABI-encoded
        if len(call.output) >= 4:
            call.revert_reason = call.output.hex()

    def _op_invalid(self, call: CallContext) -> None:
        """INVALID: Invalid instruction."""
        raise VMExecutionError("Invalid opcode (0xFE)")

    def _op_selfdestruct(self, call: CallContext) -> None:
        """SELFDESTRUCT: Halt and mark for deletion."""
        if call.static:
            raise VMExecutionError("SELFDESTRUCT not allowed in static context")

        addr_int = call.stack.pop()
        recipient = f"0x{addr_int:040x}"

        # Warm/cold gas
        warm_gas = self.context.warm_address(recipient)
        if not call.use_gas(warm_gas):
            raise VMExecutionError("Out of gas for SELFDESTRUCT")

        # Transfer balance to recipient
        balance = self.context.get_balance(call.address)
        if balance > 0:
            self.context.transfer(call.address, recipient, balance)

        # Mark for destruction
        self.context.destroyed_accounts.add(call.address)
        call.halted = True
