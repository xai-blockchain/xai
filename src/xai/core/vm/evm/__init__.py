"""
EVM (Ethereum Virtual Machine) Implementation for XAI Blockchain.

This module provides a production-grade EVM bytecode interpreter compatible
with Ethereum's execution semantics, enabling deployment and execution of
Solidity smart contracts.

Features:
- Full EVM opcode support (all 140+ opcodes)
- EIP-compliant gas metering
- Stack, memory, and storage operations
- Contract creation and calls
- Precompiled contracts
- Log/event emission
- Error handling with revert data
"""

from .opcodes import Opcode, OPCODE_INFO
from .memory import EVMMemory
from .stack import EVMStack
from .storage import EVMStorage
from .interpreter import EVMInterpreter
from .context import ExecutionContext, CallContext
from .executor import EVMBytecodeExecutor

__all__ = [
    "Opcode",
    "OPCODE_INFO",
    "EVMMemory",
    "EVMStack",
    "EVMStorage",
    "EVMInterpreter",
    "ExecutionContext",
    "CallContext",
    "EVMBytecodeExecutor",
]
