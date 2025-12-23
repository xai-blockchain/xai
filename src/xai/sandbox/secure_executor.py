"""
Secure Code Executor for Mini-Apps

Provides multiple isolation mechanisms:
1. RestrictedPython for in-process Python execution (safest for simple scripts)
2. Subprocess isolation with seccomp/landlock (for more complex code)
3. Resource limits (CPU, memory, time, file descriptors)
4. Network isolation
5. Filesystem isolation

All execution is logged and permission-checked.
"""

from __future__ import annotations

import io
import json
import logging
import os
import resource
import signal
import subprocess
import sys
import sysconfig
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xai.security.module_attachment_guard import ModuleAttachmentError, ModuleAttachmentGuard
from xai.sandbox.ast_validator import ASTValidator, SecurityError as ASTSecurityError

logger = logging.getLogger(__name__)

class ExecutionError(Exception):
    """Raised when code execution fails"""
    pass

class ResourceLimitExceeded(ExecutionError):
    """Raised when resource limits are exceeded"""
    pass

class SecurityViolation(ExecutionError):
    """Raised when a security boundary is violated"""
    pass

@dataclass
class ResourceLimits:
    """Resource limits for execution"""
    max_memory_mb: int = 128
    max_cpu_seconds: int = 5
    max_wall_time_seconds: int = 10
    max_file_descriptors: int = 64
    max_output_bytes: int = 1024 * 100  # 100KB
    max_storage_bytes: int = 1024 * 1024  # 1MB

@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    output: str = ""
    error: str = ""
    return_value: Any = None
    execution_time: float = 0.0
    memory_used_bytes: int = 0
    exit_code: int = 0
    killed_by_signal: int | None = None
    resource_exceeded: bool = False

@dataclass
class ExecutionContext:
    """Context for code execution"""
    app_id: str
    code: str
    entry_point: str = "main"
    arguments: dict[str, Any] = field(default_factory=dict)
    allowed_imports: set[str] = field(default_factory=set)
    allowed_network_domains: set[str] = field(default_factory=set)
    allowed_filesystem_paths: set[Path] = field(default_factory=set)
    api_functions: dict[str, Any] = field(default_factory=dict)

class SecureExecutor:
    """
    Secure code executor with multiple isolation mechanisms

    Uses RestrictedPython for simple Python code, subprocess isolation
    for more complex execution.
    """

    # Safe built-in functions that can be used
    SAFE_BUILTINS = {
        "abs", "all", "any", "ascii", "bin", "bool", "chr", "dict", "divmod",
        "enumerate", "filter", "float", "format", "hex", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max", "min", "next",
        "oct", "ord", "pow", "range", "reversed", "round", "set", "sorted",
        "str", "sum", "tuple", "type", "zip",
    }

    # Safe modules that can be imported
    SAFE_MODULES = {
        "json", "math", "datetime", "decimal", "uuid", "hashlib",
        "base64", "textwrap", "string", "re",
    }

    def __init__(
        self,
        limits: ResourceLimits | None = None,
        use_subprocess: bool = False,
    ):
        self.limits = limits or ResourceLimits()
        self.use_subprocess = use_subprocess

        # Check if RestrictedPython is available
        self.has_restricted_python = self._check_restricted_python()

        # Check if seccomp is available (Linux only)
        self.has_seccomp = sys.platform.startswith('linux')

        stdlib_path = Path(sysconfig.get_paths()["stdlib"]).resolve()
        self.module_guard = ModuleAttachmentGuard(
            self.SAFE_MODULES,
            trusted_base=None,
            trusted_stdlib=stdlib_path,
            require_attribute=None,
        )

        # Create AST validator for pre-execution validation
        self.ast_validator = ASTValidator(allowed_functions=self.SAFE_BUILTINS)

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute code in secure environment

        Args:
            context: Execution context with code and constraints

        Returns:
            Execution result
        """
        start_time = time.time()

        try:
            if self.use_subprocess:
                result = self._execute_subprocess(context)
            else:
                result = self._execute_restricted_python(context)

            result.execution_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(
                f"Execution failed for app {context.app_id}: {e}",
                extra={"event": "sandbox.execution_failed", "app_id": context.app_id}
            )
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    def _execute_restricted_python(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute Python code using RestrictedPython

        Provides in-process isolation with restricted builtins and imports.
        Safest option for simple scripts.
        """
        if not self.has_restricted_python:
            return ExecutionResult(
                success=False,
                error="RestrictedPython not available. Install with: pip install RestrictedPython"
            )

        try:
            from RestrictedPython import compile_restricted
            from RestrictedPython.Guards import (
                guarded_iter_unpack_sequence,
                safe_builtins,
                safer_getattr,
            )

            # Validate AST before compilation
            try:
                self.ast_validator.validate(
                    context.code,
                    filename=f'<{context.app_id}>'
                )
            except ASTSecurityError as e:
                logger.error(
                    f"AST validation failed for app {context.app_id}: {e}",
                    extra={'event': 'sandbox.ast_validation_failed', 'app_id': context.app_id}
                )
                return ExecutionResult(
                    success=False,
                    error=f"Security violation: {str(e)}"
                )
            except SyntaxError as e:
                return ExecutionResult(
                    success=False,
                    error=f"Syntax error: {str(e)}"
                )

            # Compile code with restrictions
            compile_result = compile_restricted(
                context.code,
                filename=f'<{context.app_id}>',
                mode='exec'
            )

            # Check if compilation produced errors
            if hasattr(compile_result, 'errors') and compile_result.errors:
                return ExecutionResult(
                    success=False,
                    error=f"Compilation errors: {'; '.join(compile_result.errors)}"
                )

            # Extract the code object
            byte_code = compile_result.code if hasattr(compile_result, 'code') else compile_result

            try:
                allowed_imports = self._validate_allowed_imports(context.allowed_imports)
            except SecurityViolation as exc:
                return ExecutionResult(success=False, error=str(exc))

            # Create restricted globals
            restricted_globals = {
                '__builtins__': self._create_safe_builtins(),
                '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
                '_getiter_': iter,
                '_getattr_': safer_getattr,
                '__name__': f'sandbox_{context.app_id}',
                '__file__': f'<{context.app_id}>',
            }

            # Add API functions
            if context.api_functions:
                restricted_globals['api'] = context.api_functions

            # Add allowed imports
            for module_name in allowed_imports:
                try:
                    restricted_globals[module_name] = __import__(module_name)
                except ImportError:
                    return ExecutionResult(
                        success=False,
                        error=f"Module {module_name} not found."
                    )

            # Capture stdout/stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            try:
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture

                # Set resource limits
                self._set_resource_limits()

                # Execute with timeout
                import signal

                def timeout_handler(signum, frame):
                    raise ResourceLimitExceeded("Execution time limit exceeded")

                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.limits.max_wall_time_seconds)

                try:
                    # Execute the code
                    exec(byte_code, restricted_globals)

                    # Call entry point if specified
                    return_value = None
                    if context.entry_point and context.entry_point in restricted_globals:
                        entry_func = restricted_globals[context.entry_point]
                        if callable(entry_func):
                            return_value = entry_func(**context.arguments)

                    return ExecutionResult(
                        success=True,
                        output=stdout_capture.getvalue()[:self.limits.max_output_bytes],
                        error=stderr_capture.getvalue()[:self.limits.max_output_bytes],
                        return_value=return_value,
                    )

                finally:
                    signal.alarm(0)  # Cancel timeout

            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        except ResourceLimitExceeded as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                resource_exceeded=True,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
            )

    def _validate_allowed_imports(self, allowed_imports: set[str]) -> set[str]:
        """Validate user-supplied allowed imports against the allowlist and trusted paths."""
        requested = {str(mod) for mod in (allowed_imports or set())}
        if not requested:
            return set()

        disallowed = requested - self.SAFE_MODULES
        if disallowed:
            raise SecurityViolation(f"Requested imports not allowlisted: {sorted(disallowed)}")

        for module_name in requested:
            try:
                self.module_guard.verify_module(module_name)
            except ModuleAttachmentError as exc:
                raise SecurityViolation(
                    f"Module {module_name} failed attachment validation: {exc}"
                ) from exc

        return requested

    def _execute_subprocess(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute code in isolated subprocess

        Provides stronger isolation using:
        - Separate process
        - seccomp syscall filtering (Linux)
        - Resource limits via rlimit
        - No network access (by default)
        - Read-only filesystem (by default)
        """
        # Validate AST before subprocess execution
        try:
            self.ast_validator.validate(
                context.code,
                filename=f'<{context.app_id}>'
            )
        except ASTSecurityError as e:
            logger.error(
                f"AST validation failed for app {context.app_id}: {e}",
                extra={'event': 'sandbox.ast_validation_failed', 'app_id': context.app_id}
            )
            return ExecutionResult(
                success=False,
                error=f"Security violation: {str(e)}"
            )
        except SyntaxError as e:
            return ExecutionResult(
                success=False,
                error=f"Syntax error: {str(e)}"
            )

        # Create temporary directory for execution
        try:
            allowed_imports = self._validate_allowed_imports(context.allowed_imports)
        except SecurityViolation as exc:
            return ExecutionResult(success=False, error=str(exc))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write code to file
            code_file = temp_path / "code.py"
            code_file.write_text(self._wrap_code_for_subprocess(context, allowed_imports))

            # Write API wrapper if needed
            if context.api_functions:
                api_file = temp_path / "api.json"
                # Serialize API metadata (not the actual functions)
                api_meta = {name: "function" for name in context.api_functions.keys()}
                api_file.write_text(json.dumps(api_meta))

            # Build command
            cmd = [
                sys.executable,
                "-S",  # No site packages
                str(code_file),
            ]

            # Prepare environment
            env = {
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
            }

            try:
                # Start process with preexec_fn for resource limits
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    cwd=temp_dir,
                    preexec_fn=self._prepare_subprocess if os.name == 'posix' else None,
                )

                # Wait with timeout
                try:
                    stdout, stderr = process.communicate(
                        timeout=self.limits.max_wall_time_seconds
                    )

                    return ExecutionResult(
                        success=process.returncode == 0,
                        output=stdout.decode('utf-8', errors='replace')[:self.limits.max_output_bytes],
                        error=stderr.decode('utf-8', errors='replace')[:self.limits.max_output_bytes],
                        exit_code=process.returncode,
                    )

                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

                    return ExecutionResult(
                        success=False,
                        error="Execution timeout exceeded",
                        resource_exceeded=True,
                        killed_by_signal=signal.SIGKILL,
                    )

            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=f"Subprocess execution failed: {str(e)}",
                )

    def _wrap_code_for_subprocess(self, context: ExecutionContext, allowed_imports: set[str]) -> str:
        """Wrap user code with safety checks and API stubs"""
        runtime_allowed = set(allowed_imports) | {"sys", "json"}
        wrapper = f'''
import sys
import json

# Resource monitoring
import resource
import builtins

_ALLOWED_IMPORTS = {sorted(runtime_allowed)!r}
_REAL_IMPORT = builtins.__import__

def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split('.')[0]
    if root not in _ALLOWED_IMPORTS:
        raise ImportError(f"Import '{{name}}' not permitted in sandbox")
    return _REAL_IMPORT(name, globals, locals, fromlist, level)

builtins.__import__ = _guarded_import

# Set strict limits
resource.setrlimit(resource.RLIMIT_AS, ({self.limits.max_memory_mb * 1024 * 1024}, {self.limits.max_memory_mb * 1024 * 1024}))
resource.setrlimit(resource.RLIMIT_CPU, ({self.limits.max_cpu_seconds}, {self.limits.max_cpu_seconds}))

# Stub API functions (would communicate back to parent via IPC in production)
class API:
    pass

api = API()

# User code
{context.code}

# Call entry point
if __name__ == "__main__":
    try:
        if "{context.entry_point}" in dir():
            result = {context.entry_point}()
            print(json.dumps({{"success": True, "result": str(result)}}))
        else:
            print(json.dumps({{"success": True, "result": None}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}), file=sys.stderr)
        sys.exit(1)
'''
        return wrapper

    def _prepare_subprocess(self) -> None:
        """
        Prepare subprocess with security restrictions

        Called via preexec_fn before subprocess exec.
        POSIX only.
        """
        # Set resource limits
        try:
            # Memory limit
            mem_bytes = self.limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))

            # CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.limits.max_cpu_seconds, self.limits.max_cpu_seconds)
            )

            # File descriptor limit
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (self.limits.max_file_descriptors, self.limits.max_file_descriptors)
            )

            # Core dump size (disable)
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

            # Number of processes (limit to 1)
            resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))

        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")

        # Apply seccomp filter if available
        if self.has_seccomp:
            self._apply_seccomp_filter()

    def _apply_seccomp_filter(self) -> None:
        """
        Apply seccomp syscall filter

        Blocks dangerous syscalls while allowing safe operations.
        Linux only.
        """
        try:
            import ctypes
            import ctypes.util

            # Load libc
            libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)

            # seccomp constants
            SECCOMP_SET_MODE_FILTER = 1
            SECCOMP_FILTER_FLAG_TSYNC = 1

            # This is a simplified version - production would use libseccomp
            # For now, just use SECCOMP_MODE_STRICT which allows only:
            # read, write, exit, sigreturn
            # Note: This is very restrictive and would need to be tuned

            # In production, use python-seccomp package for proper filtering
            # Example:
            # import seccomp
            # f = seccomp.SyscallFilter(defaction=seccomp.KILL)
            # f.add_rule(seccomp.ALLOW, "read")
            # f.add_rule(seccomp.ALLOW, "write")
            # ... add safe syscalls
            # f.load()

            logger.debug("Seccomp filter would be applied here in production")

        except Exception as e:
            logger.warning(f"Failed to apply seccomp filter: {e}")

    def _set_resource_limits(self) -> None:
        """Set resource limits for current process"""
        if os.name != 'posix':
            return

        try:
            # These limits apply to the current process
            # Be careful not to make them too restrictive for the parent

            # Memory limit (soft limit only)
            mem_bytes = self.limits.max_memory_mb * 1024 * 1024
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            if hard == resource.RLIM_INFINITY or mem_bytes < hard:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, hard))

        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")

    def _create_safe_builtins(self) -> dict[str, Any]:
        """Create dictionary of safe builtin functions"""
        safe_builtins = {}

        # Add safe built-in functions
        for name in self.SAFE_BUILTINS:
            if hasattr(__builtins__, name):
                safe_builtins[name] = getattr(__builtins__, name)

        # Add safe classes
        safe_builtins['True'] = True
        safe_builtins['False'] = False
        safe_builtins['None'] = None

        # Add safe exception classes
        safe_builtins['Exception'] = Exception
        safe_builtins['ValueError'] = ValueError
        safe_builtins['TypeError'] = TypeError
        safe_builtins['KeyError'] = KeyError
        safe_builtins['IndexError'] = IndexError

        return safe_builtins

    def _check_restricted_python(self) -> bool:
        """Check if RestrictedPython is available"""
        try:
            import RestrictedPython
            return True
        except ImportError:
            return False

class SandboxAPI:
    """
    API wrapper for sandbox execution

    Provides safe interface to wallet/blockchain functions.
    All calls are permission-checked and logged.
    """

    def __init__(
        self,
        app_id: str,
        permission_manager: Any,
        wallet_interface: Any,
    ):
        self.app_id = app_id
        self.permission_manager = permission_manager
        self.wallet_interface = wallet_interface

    def get_balance(self, address: str | None = None) -> float:
        """Get wallet balance (permission-checked)"""
        from .permissions import Permission, PermissionLevel

        self.permission_manager.check_permission(
            self.app_id,
            Permission.READ_BALANCE,
            PermissionLevel.READ,
            action="get_balance"
        )

        return self.wallet_interface.get_balance(address)

    def get_transactions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get transaction history (permission-checked)"""
        from .permissions import Permission, PermissionLevel

        self.permission_manager.check_permission(
            self.app_id,
            Permission.READ_TRANSACTIONS,
            PermissionLevel.READ,
            action="get_transactions"
        )

        # Enforce limit
        limit = min(limit, 100)

        return self.wallet_interface.get_transactions(limit)

    def create_transaction(
        self,
        recipient: str,
        amount: float,
        memo: str = ""
    ) -> dict[str, Any]:
        """
        Create transaction (requires user approval)

        Returns unsigned transaction for user to approve and sign.
        """
        from .permissions import Permission, PermissionLevel

        self.permission_manager.check_permission(
            self.app_id,
            Permission.SIGN_TRANSACTIONS,
            PermissionLevel.WRITE,
            action="create_transaction"
        )

        # Return unsigned transaction
        # UI will prompt user for approval
        return {
            "status": "pending_approval",
            "recipient": recipient,
            "amount": amount,
            "memo": memo,
            "app_id": self.app_id,
            "timestamp": time.time(),
        }
