"""
Smart-contract execution scaffolding.

The VM package houses the execution engines (EVM/WASM), shared state helpers,
and transaction processors that integrate with the existing blockchain code.
Only the interfaces live here today; concrete logic will follow as the
implementation plan is executed.
"""

from .exceptions import VMExecutionError, VMConfigurationError  # noqa: F401
from .state import EVMState, AccountState  # noqa: F401
from .executor import (  # noqa: F401
    ExecutionMessage,
    ExecutionResult,
    BaseExecutor,
)
from .manager import SmartContractManager  # noqa: F401
from .tx_processor import ContractTransactionProcessor  # noqa: F401

__all__ = [
    "VMExecutionError",
    "VMConfigurationError",
    "EVMState",
    "AccountState",
    "ExecutionMessage",
    "ExecutionResult",
    "BaseExecutor",
    "SmartContractManager",
    "ContractTransactionProcessor",
]
