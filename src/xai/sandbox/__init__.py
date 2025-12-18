"""
XAI Mini-App Secure Sandbox

Provides secure execution environments for untrusted mini-app code:
- RestrictedPython for Python execution
- WebAssembly for compiled code
- Capability-based permission system
- Resource limits and isolation
"""

from .permissions import (
    Permission,
    PermissionLevel,
    PermissionManager,
    PermissionDeniedError,
    AuditLog,
)
from .secure_executor import (
    SecureExecutor,
    ExecutionResult,
    ExecutionError,
    ResourceLimitExceeded,
)
from .wasm_executor import (
    WasmExecutor,
    WasmExecutionError,
)

__all__ = [
    "Permission",
    "PermissionLevel",
    "PermissionManager",
    "PermissionDeniedError",
    "AuditLog",
    "SecureExecutor",
    "ExecutionResult",
    "ExecutionError",
    "ResourceLimitExceeded",
    "WasmExecutor",
    "WasmExecutionError",
]
