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

from .context import CallContext, ExecutionContext
from .executor import EVMBytecodeExecutor
from .interpreter import EVMInterpreter
from .memory import EVMMemory
from .opcodes import OPCODE_INFO, Opcode
from .stack import EVMStack
from .storage import EVMStorage

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
