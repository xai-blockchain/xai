"""
XAI Mini-App Secure Sandbox

Provides secure execution environments for untrusted mini-app code:
- RestrictedPython for Python execution
- WebAssembly for compiled code
- Capability-based permission system
- Resource limits and isolation
- AST validation for pre-execution security checks
"""

from .ast_validator import ASTValidator
from .ast_validator import SecurityError as ASTSecurityError
from .ast_validator import validate_code
from .permissions import (
    AuditLog,
    Permission,
    PermissionDeniedError,
    PermissionLevel,
    PermissionManager,
)
from .secure_executor import (
    ExecutionError,
    ExecutionResult,
    ResourceLimitExceeded,
    SecureExecutor,
)
from .wasm_executor import (
    WasmExecutionError,
    WasmExecutor,
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
    "ASTValidator",
    "ASTSecurityError",
    "validate_code",
]
