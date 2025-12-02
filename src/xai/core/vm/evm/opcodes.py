"""
EVM Opcode Definitions.

Complete implementation of all EVM opcodes as defined in the Ethereum Yellow Paper
and subsequent EIPs up to Shanghai/Cancun.
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import Dict, Optional


class Opcode(IntEnum):
    """Complete EVM opcode enumeration."""

    # 0x00 - Stop and Arithmetic
    STOP = 0x00
    ADD = 0x01
    MUL = 0x02
    SUB = 0x03
    DIV = 0x04
    SDIV = 0x05
    MOD = 0x06
    SMOD = 0x07
    ADDMOD = 0x08
    MULMOD = 0x09
    EXP = 0x0A
    SIGNEXTEND = 0x0B

    # 0x10 - Comparison & Bitwise Logic
    LT = 0x10
    GT = 0x11
    SLT = 0x12
    SGT = 0x13
    EQ = 0x14
    ISZERO = 0x15
    AND = 0x16
    OR = 0x17
    XOR = 0x18
    NOT = 0x19
    BYTE = 0x1A
    SHL = 0x1B  # EIP-145
    SHR = 0x1C  # EIP-145
    SAR = 0x1D  # EIP-145

    # 0x20 - Keccak256
    KECCAK256 = 0x20

    # 0x30 - Environmental Information
    ADDRESS = 0x30
    BALANCE = 0x31
    ORIGIN = 0x32
    CALLER = 0x33
    CALLVALUE = 0x34
    CALLDATALOAD = 0x35
    CALLDATASIZE = 0x36
    CALLDATACOPY = 0x37
    CODESIZE = 0x38
    CODECOPY = 0x39
    GASPRICE = 0x3A
    EXTCODESIZE = 0x3B
    EXTCODECOPY = 0x3C
    RETURNDATASIZE = 0x3D  # EIP-211
    RETURNDATACOPY = 0x3E  # EIP-211
    EXTCODEHASH = 0x3F  # EIP-1052

    # 0x40 - Block Information
    BLOCKHASH = 0x40
    COINBASE = 0x41
    TIMESTAMP = 0x42
    NUMBER = 0x43
    PREVRANDAO = 0x44  # Was DIFFICULTY before The Merge (EIP-4399)
    GASLIMIT = 0x45
    CHAINID = 0x46  # EIP-1344
    SELFBALANCE = 0x47  # EIP-1884
    BASEFEE = 0x48  # EIP-3198
    BLOBHASH = 0x49  # EIP-4844
    BLOBBASEFEE = 0x4A  # EIP-7516

    # 0x50 - Stack, Memory, Storage and Flow Operations
    POP = 0x50
    MLOAD = 0x51
    MSTORE = 0x52
    MSTORE8 = 0x53
    SLOAD = 0x54
    SSTORE = 0x55
    JUMP = 0x56
    JUMPI = 0x57
    PC = 0x58
    MSIZE = 0x59
    GAS = 0x5A
    JUMPDEST = 0x5B
    TLOAD = 0x5C  # EIP-1153 (transient storage)
    TSTORE = 0x5D  # EIP-1153 (transient storage)
    MCOPY = 0x5E  # EIP-5656
    PUSH0 = 0x5F  # EIP-3855

    # 0x60-0x7F - Push Operations
    PUSH1 = 0x60
    PUSH2 = 0x61
    PUSH3 = 0x62
    PUSH4 = 0x63
    PUSH5 = 0x64
    PUSH6 = 0x65
    PUSH7 = 0x66
    PUSH8 = 0x67
    PUSH9 = 0x68
    PUSH10 = 0x69
    PUSH11 = 0x6A
    PUSH12 = 0x6B
    PUSH13 = 0x6C
    PUSH14 = 0x6D
    PUSH15 = 0x6E
    PUSH16 = 0x6F
    PUSH17 = 0x70
    PUSH18 = 0x71
    PUSH19 = 0x72
    PUSH20 = 0x73
    PUSH21 = 0x74
    PUSH22 = 0x75
    PUSH23 = 0x76
    PUSH24 = 0x77
    PUSH25 = 0x78
    PUSH26 = 0x79
    PUSH27 = 0x7A
    PUSH28 = 0x7B
    PUSH29 = 0x7C
    PUSH30 = 0x7D
    PUSH31 = 0x7E
    PUSH32 = 0x7F

    # 0x80-0x8F - Duplication Operations
    DUP1 = 0x80
    DUP2 = 0x81
    DUP3 = 0x82
    DUP4 = 0x83
    DUP5 = 0x84
    DUP6 = 0x85
    DUP7 = 0x86
    DUP8 = 0x87
    DUP9 = 0x88
    DUP10 = 0x89
    DUP11 = 0x8A
    DUP12 = 0x8B
    DUP13 = 0x8C
    DUP14 = 0x8D
    DUP15 = 0x8E
    DUP16 = 0x8F

    # 0x90-0x9F - Exchange Operations
    SWAP1 = 0x90
    SWAP2 = 0x91
    SWAP3 = 0x92
    SWAP4 = 0x93
    SWAP5 = 0x94
    SWAP6 = 0x95
    SWAP7 = 0x96
    SWAP8 = 0x97
    SWAP9 = 0x98
    SWAP10 = 0x99
    SWAP11 = 0x9A
    SWAP12 = 0x9B
    SWAP13 = 0x9C
    SWAP14 = 0x9D
    SWAP15 = 0x9E
    SWAP16 = 0x9F

    # 0xA0-0xA4 - Logging Operations
    LOG0 = 0xA0
    LOG1 = 0xA1
    LOG2 = 0xA2
    LOG3 = 0xA3
    LOG4 = 0xA4

    # 0xF0-0xFF - System Operations
    CREATE = 0xF0
    CALL = 0xF1
    CALLCODE = 0xF2
    RETURN = 0xF3
    DELEGATECALL = 0xF4  # EIP-7
    CREATE2 = 0xF5  # EIP-1014
    STATICCALL = 0xFA  # EIP-214
    REVERT = 0xFD  # EIP-140
    INVALID = 0xFE
    SELFDESTRUCT = 0xFF


@dataclass
class OpcodeInfo:
    """Metadata for an opcode including gas costs and stack effects."""

    opcode: int
    name: str
    stack_input: int  # Number of items popped from stack
    stack_output: int  # Number of items pushed to stack
    gas_cost: int  # Static gas cost (dynamic costs computed separately)
    description: str

    @property
    def stack_delta(self) -> int:
        """Net change in stack size."""
        return self.stack_output - self.stack_input


# Complete opcode information table
OPCODE_INFO: Dict[int, OpcodeInfo] = {
    # Stop and Arithmetic
    0x00: OpcodeInfo(0x00, "STOP", 0, 0, 0, "Halts execution"),
    0x01: OpcodeInfo(0x01, "ADD", 2, 1, 3, "Addition operation"),
    0x02: OpcodeInfo(0x02, "MUL", 2, 1, 5, "Multiplication operation"),
    0x03: OpcodeInfo(0x03, "SUB", 2, 1, 3, "Subtraction operation"),
    0x04: OpcodeInfo(0x04, "DIV", 2, 1, 5, "Integer division operation"),
    0x05: OpcodeInfo(0x05, "SDIV", 2, 1, 5, "Signed integer division operation"),
    0x06: OpcodeInfo(0x06, "MOD", 2, 1, 5, "Modulo operation"),
    0x07: OpcodeInfo(0x07, "SMOD", 2, 1, 5, "Signed modulo operation"),
    0x08: OpcodeInfo(0x08, "ADDMOD", 3, 1, 8, "Modulo addition operation"),
    0x09: OpcodeInfo(0x09, "MULMOD", 3, 1, 8, "Modulo multiplication operation"),
    0x0A: OpcodeInfo(0x0A, "EXP", 2, 1, 10, "Exponential operation"),
    0x0B: OpcodeInfo(0x0B, "SIGNEXTEND", 2, 1, 5, "Sign extension operation"),

    # Comparison & Bitwise Logic
    0x10: OpcodeInfo(0x10, "LT", 2, 1, 3, "Less-than comparison"),
    0x11: OpcodeInfo(0x11, "GT", 2, 1, 3, "Greater-than comparison"),
    0x12: OpcodeInfo(0x12, "SLT", 2, 1, 3, "Signed less-than comparison"),
    0x13: OpcodeInfo(0x13, "SGT", 2, 1, 3, "Signed greater-than comparison"),
    0x14: OpcodeInfo(0x14, "EQ", 2, 1, 3, "Equality comparison"),
    0x15: OpcodeInfo(0x15, "ISZERO", 1, 1, 3, "Simple not operator"),
    0x16: OpcodeInfo(0x16, "AND", 2, 1, 3, "Bitwise AND operation"),
    0x17: OpcodeInfo(0x17, "OR", 2, 1, 3, "Bitwise OR operation"),
    0x18: OpcodeInfo(0x18, "XOR", 2, 1, 3, "Bitwise XOR operation"),
    0x19: OpcodeInfo(0x19, "NOT", 1, 1, 3, "Bitwise NOT operation"),
    0x1A: OpcodeInfo(0x1A, "BYTE", 2, 1, 3, "Retrieve single byte from word"),
    0x1B: OpcodeInfo(0x1B, "SHL", 2, 1, 3, "Shift left"),
    0x1C: OpcodeInfo(0x1C, "SHR", 2, 1, 3, "Logical shift right"),
    0x1D: OpcodeInfo(0x1D, "SAR", 2, 1, 3, "Arithmetic shift right"),

    # Keccak256
    0x20: OpcodeInfo(0x20, "KECCAK256", 2, 1, 30, "Compute Keccak-256 hash"),

    # Environmental Information
    0x30: OpcodeInfo(0x30, "ADDRESS", 0, 1, 2, "Get address of executing account"),
    0x31: OpcodeInfo(0x31, "BALANCE", 1, 1, 100, "Get balance of account"),  # EIP-2929 warm/cold
    0x32: OpcodeInfo(0x32, "ORIGIN", 0, 1, 2, "Get execution origination address"),
    0x33: OpcodeInfo(0x33, "CALLER", 0, 1, 2, "Get caller address"),
    0x34: OpcodeInfo(0x34, "CALLVALUE", 0, 1, 2, "Get deposited value"),
    0x35: OpcodeInfo(0x35, "CALLDATALOAD", 1, 1, 3, "Get input data"),
    0x36: OpcodeInfo(0x36, "CALLDATASIZE", 0, 1, 2, "Get size of input data"),
    0x37: OpcodeInfo(0x37, "CALLDATACOPY", 3, 0, 3, "Copy input data to memory"),
    0x38: OpcodeInfo(0x38, "CODESIZE", 0, 1, 2, "Get size of code"),
    0x39: OpcodeInfo(0x39, "CODECOPY", 3, 0, 3, "Copy code to memory"),
    0x3A: OpcodeInfo(0x3A, "GASPRICE", 0, 1, 2, "Get price of gas"),
    0x3B: OpcodeInfo(0x3B, "EXTCODESIZE", 1, 1, 100, "Get size of external code"),
    0x3C: OpcodeInfo(0x3C, "EXTCODECOPY", 4, 0, 100, "Copy external code to memory"),
    0x3D: OpcodeInfo(0x3D, "RETURNDATASIZE", 0, 1, 2, "Get size of return data"),
    0x3E: OpcodeInfo(0x3E, "RETURNDATACOPY", 3, 0, 3, "Copy return data to memory"),
    0x3F: OpcodeInfo(0x3F, "EXTCODEHASH", 1, 1, 100, "Get hash of external code"),

    # Block Information
    0x40: OpcodeInfo(0x40, "BLOCKHASH", 1, 1, 20, "Get hash of recent block"),
    0x41: OpcodeInfo(0x41, "COINBASE", 0, 1, 2, "Get block's beneficiary address"),
    0x42: OpcodeInfo(0x42, "TIMESTAMP", 0, 1, 2, "Get block's timestamp"),
    0x43: OpcodeInfo(0x43, "NUMBER", 0, 1, 2, "Get block's number"),
    0x44: OpcodeInfo(0x44, "PREVRANDAO", 0, 1, 2, "Get block's prevrandao value"),
    0x45: OpcodeInfo(0x45, "GASLIMIT", 0, 1, 2, "Get block's gas limit"),
    0x46: OpcodeInfo(0x46, "CHAINID", 0, 1, 2, "Get chain ID"),
    0x47: OpcodeInfo(0x47, "SELFBALANCE", 0, 1, 5, "Get balance of current contract"),
    0x48: OpcodeInfo(0x48, "BASEFEE", 0, 1, 2, "Get block's base fee"),
    0x49: OpcodeInfo(0x49, "BLOBHASH", 1, 1, 3, "Get blob hash"),
    0x4A: OpcodeInfo(0x4A, "BLOBBASEFEE", 0, 1, 2, "Get blob base fee"),

    # Stack, Memory, Storage and Flow Operations
    0x50: OpcodeInfo(0x50, "POP", 1, 0, 2, "Remove item from stack"),
    0x51: OpcodeInfo(0x51, "MLOAD", 1, 1, 3, "Load word from memory"),
    0x52: OpcodeInfo(0x52, "MSTORE", 2, 0, 3, "Save word to memory"),
    0x53: OpcodeInfo(0x53, "MSTORE8", 2, 0, 3, "Save byte to memory"),
    0x54: OpcodeInfo(0x54, "SLOAD", 1, 1, 100, "Load word from storage"),  # EIP-2929
    0x55: OpcodeInfo(0x55, "SSTORE", 2, 0, 100, "Save word to storage"),  # Complex pricing
    0x56: OpcodeInfo(0x56, "JUMP", 1, 0, 8, "Alter program counter"),
    0x57: OpcodeInfo(0x57, "JUMPI", 2, 0, 10, "Conditionally alter program counter"),
    0x58: OpcodeInfo(0x58, "PC", 0, 1, 2, "Get program counter"),
    0x59: OpcodeInfo(0x59, "MSIZE", 0, 1, 2, "Get size of active memory"),
    0x5A: OpcodeInfo(0x5A, "GAS", 0, 1, 2, "Get remaining gas"),
    0x5B: OpcodeInfo(0x5B, "JUMPDEST", 0, 0, 1, "Mark valid jump destination"),
    0x5C: OpcodeInfo(0x5C, "TLOAD", 1, 1, 100, "Load word from transient storage"),
    0x5D: OpcodeInfo(0x5D, "TSTORE", 2, 0, 100, "Save word to transient storage"),
    0x5E: OpcodeInfo(0x5E, "MCOPY", 3, 0, 3, "Copy memory"),
    0x5F: OpcodeInfo(0x5F, "PUSH0", 0, 1, 2, "Push 0 onto stack"),

    # Logging Operations
    0xA0: OpcodeInfo(0xA0, "LOG0", 2, 0, 375, "Append log record with no topics"),
    0xA1: OpcodeInfo(0xA1, "LOG1", 3, 0, 750, "Append log record with 1 topic"),
    0xA2: OpcodeInfo(0xA2, "LOG2", 4, 0, 1125, "Append log record with 2 topics"),
    0xA3: OpcodeInfo(0xA3, "LOG3", 5, 0, 1500, "Append log record with 3 topics"),
    0xA4: OpcodeInfo(0xA4, "LOG4", 6, 0, 1875, "Append log record with 4 topics"),

    # System Operations
    0xF0: OpcodeInfo(0xF0, "CREATE", 3, 1, 32000, "Create new account with code"),
    0xF1: OpcodeInfo(0xF1, "CALL", 7, 1, 100, "Message-call into account"),
    0xF2: OpcodeInfo(0xF2, "CALLCODE", 7, 1, 100, "Message-call with alternative code"),
    0xF3: OpcodeInfo(0xF3, "RETURN", 2, 0, 0, "Halt execution returning output data"),
    0xF4: OpcodeInfo(0xF4, "DELEGATECALL", 6, 1, 100, "Message-call with caller's context"),
    0xF5: OpcodeInfo(0xF5, "CREATE2", 4, 1, 32000, "Create with deterministic address"),
    0xFA: OpcodeInfo(0xFA, "STATICCALL", 6, 1, 100, "Static message-call"),
    0xFD: OpcodeInfo(0xFD, "REVERT", 2, 0, 0, "Halt execution reverting state"),
    0xFE: OpcodeInfo(0xFE, "INVALID", 0, 0, 0, "Invalid instruction"),
    0xFF: OpcodeInfo(0xFF, "SELFDESTRUCT", 1, 0, 5000, "Halt and mark for deletion"),
}

# Add PUSH1-PUSH32 opcodes
for i in range(1, 33):
    opcode = 0x5F + i  # PUSH1 = 0x60
    OPCODE_INFO[opcode] = OpcodeInfo(
        opcode, f"PUSH{i}", 0, 1, 3, f"Push {i} byte(s) onto stack"
    )

# Add DUP1-DUP16 opcodes
for i in range(1, 17):
    opcode = 0x7F + i  # DUP1 = 0x80
    OPCODE_INFO[opcode] = OpcodeInfo(
        opcode, f"DUP{i}", i, i + 1, 3, f"Duplicate {i}th stack item"
    )

# Add SWAP1-SWAP16 opcodes
for i in range(1, 17):
    opcode = 0x8F + i  # SWAP1 = 0x90
    OPCODE_INFO[opcode] = OpcodeInfo(
        opcode, f"SWAP{i}", i + 1, i + 1, 3, f"Exchange 1st and {i + 1}th stack items"
    )


def get_push_size(opcode: int) -> int:
    """Get number of bytes to read for PUSH opcodes."""
    if 0x60 <= opcode <= 0x7F:
        return opcode - 0x5F
    return 0


def is_push(opcode: int) -> bool:
    """Check if opcode is a PUSH instruction."""
    return 0x5F <= opcode <= 0x7F


def is_dup(opcode: int) -> bool:
    """Check if opcode is a DUP instruction."""
    return 0x80 <= opcode <= 0x8F


def is_swap(opcode: int) -> bool:
    """Check if opcode is a SWAP instruction."""
    return 0x90 <= opcode <= 0x9F


def is_log(opcode: int) -> bool:
    """Check if opcode is a LOG instruction."""
    return 0xA0 <= opcode <= 0xA4


def get_log_topic_count(opcode: int) -> int:
    """Get number of topics for LOG opcodes."""
    if 0xA0 <= opcode <= 0xA4:
        return opcode - 0xA0
    return 0


def is_jump(opcode: int) -> bool:
    """Check if opcode is a jump instruction."""
    return opcode in (0x56, 0x57)  # JUMP, JUMPI


def is_terminating(opcode: int) -> bool:
    """Check if opcode terminates execution."""
    return opcode in (
        0x00,  # STOP
        0xF3,  # RETURN
        0xFD,  # REVERT
        0xFE,  # INVALID
        0xFF,  # SELFDESTRUCT
    )
