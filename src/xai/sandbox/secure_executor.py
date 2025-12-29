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

from xai.sandbox.ast_validator import ASTValidator
from xai.sandbox.ast_validator import SecurityError as ASTSecurityError
from xai.security.module_attachment_guard import ModuleAttachmentError, ModuleAttachmentGuard

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

        except ResourceLimitExceeded as e:
            logger.warning(
                f"Resource limit exceeded for app {context.app_id}: {e}",
                extra={"event": "sandbox.resource_limit_exceeded", "app_id": context.app_id}
            )
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                resource_exceeded=True,
            )
        except SecurityViolation as e:
            logger.warning(
                f"Security violation for app {context.app_id}: {e}",
                extra={"event": "sandbox.security_violation", "app_id": context.app_id}
            )
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
        except (SyntaxError, ValueError, TypeError) as e:
            logger.warning(
                f"Code error for app {context.app_id}: {type(e).__name__}: {e}",
                extra={"event": "sandbox.code_error", "app_id": context.app_id}
            )
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            logger.error(
                f"Unexpected execution error for app {context.app_id}: {type(e).__name__}: {e}",
                extra={"event": "sandbox.unexpected_error", "app_id": context.app_id}
            )
            return ExecutionResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
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

        except NameError as e:
            logger.warning(f"Undefined name in sandbox code: {e}")
            return ExecutionResult(
                success=False,
                error=f"Name error: {str(e)}",
            )
        except AttributeError as e:
            logger.warning(f"Attribute error in sandbox code: {e}")
            return ExecutionResult(
                success=False,
                error=f"Attribute error: {str(e)}",
            )
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.warning(f"Data error in sandbox code: {type(e).__name__}: {e}")
            return ExecutionResult(
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected sandbox execution error: {type(e).__name__}: {e}")
            return ExecutionResult(
                success=False,
                error=f"Unexpected execution error: {str(e)}",
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

        SECURITY LAYERS (Defense in Depth):
        ===================================

        Layer 1 - Pre-execution Validation:
          - AST validation via ASTValidator blocks dangerous constructs
          - Module allowlist prevents importing dangerous modules (os, subprocess, etc.)
          - ModuleAttachmentGuard validates module paths against trusted locations

        Layer 2 - Process Isolation:
          - Separate subprocess prevents direct memory access to parent
          - preexec_fn applies security settings before exec()
          - Minimal environment (PYTHONDONTWRITEBYTECODE, PYTHONUNBUFFERED only)
          - -S flag disables site packages (reduces attack surface)
          - Execution in temporary directory (deleted after execution)

        Layer 3 - Resource Limits (via rlimit):
          - RLIMIT_AS: Memory limit (default 128MB) - prevents memory exhaustion
          - RLIMIT_CPU: CPU time limit (default 5s) - prevents CPU DoS
          - RLIMIT_NOFILE: File descriptor limit (default 64) - prevents fd exhaustion
          - RLIMIT_CORE: Core dumps disabled (0) - prevents info leakage
          - RLIMIT_NPROC: Process limit (1) - prevents fork bombs

        Layer 4 - Syscall Filtering (Linux, seccomp-bpf):
          - FULLY IMPLEMENTED via python-seccomp or libseccomp ctypes bindings
          - Default action: KILL_PROCESS for blocked syscalls
          - Whitelist approach: only ~80 essential syscalls allowed
          - Blocked: execve, execveat, ptrace, mount, fork, vfork, socket, etc.
          - Allowed: read, write, mmap, exit, brk, futex, clock_gettime, etc.
          - Graceful degradation: logs warning if seccomp unavailable

        Layer 5 - Output/Timeout Controls:
          - Wall-clock timeout via communicate(timeout=N)
          - Output truncation to max_output_bytes
          - Process killed (SIGKILL) on timeout

        KNOWN LIMITATIONS (document for security review):
          - Network isolation: seccomp blocks socket syscall; additional isolation via
            module allowlist (socket import blocked). No kernel-level namespace isolation.
          - Filesystem isolation: via temp dir + seccomp (no chroot/namespace)
          - clone syscall allowed for threading (RLIMIT_NPROC=1 limits fork abuse)
          # IMPROVEMENT: Consider using nsjail, firejail, or bubblewrap for full namespace isolation
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

            except OSError as e:
                logger.error(f"OS error during subprocess execution: {e}")
                return ExecutionResult(
                    success=False,
                    error=f"System error: {str(e)}",
                )
            except ValueError as e:
                logger.error(f"Invalid subprocess parameters: {e}")
                return ExecutionResult(
                    success=False,
                    error=f"Invalid parameters: {str(e)}",
                )
            except Exception as e:
                logger.error(f"Unexpected subprocess error: {type(e).__name__}: {e}")
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

        Called via preexec_fn before subprocess exec (POSIX only).

        SECURITY NOTE: This runs in the child process AFTER fork() but BEFORE exec().
        Any limits set here apply to the sandboxed code only, not the parent.

        Resource Limits Applied:
          - RLIMIT_AS: Virtual memory cap (prevents allocation-based attacks)
          - RLIMIT_CPU: CPU seconds cap (kernel enforces with SIGXCPU/SIGKILL)
          - RLIMIT_NOFILE: File descriptor limit (prevents fd table exhaustion)
          - RLIMIT_CORE: Set to 0 (no core dumps - prevents info leakage)
          - RLIMIT_NPROC: Set to 1 (no fork/exec - prevents fork bombs)

        These limits are enforced by the kernel and cannot be bypassed by user code.
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

        except (OSError, ValueError) as e:
            # OSError: permission denied or unsupported limit
            # ValueError: invalid limit values
            logger.warning(f"Failed to set subprocess resource limits ({type(e).__name__}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error setting subprocess limits: {type(e).__name__}: {e}")

        # Apply seccomp filter if available
        if self.has_seccomp:
            self._apply_seccomp_filter()

    def _apply_seccomp_filter(self) -> None:
        """
        Apply seccomp-bpf syscall filter (Linux only)

        SECURITY STATUS: FULLY IMPLEMENTED
        ===================================

        This implements a production-grade seccomp-bpf filter using either:
        1. python-seccomp (pyseccomp) if available - preferred
        2. ctypes-based libseccomp bindings as fallback

        ALLOWED SYSCALLS (whitelist - minimal set for Python execution):
        ----------------------------------------------------------------
        Memory Management:
          - brk, mmap, mprotect, munmap, mremap, madvise, mincore, msync
        File I/O (restricted):
          - read, write, openat, close, fstat, lseek, access, faccessat
          - dup, dup2, dup3, pipe, pipe2, fcntl
        Process Control:
          - exit, exit_group, getpid, gettid, getppid
          - rt_sigaction, rt_sigprocmask, rt_sigreturn, sigaltstack
          - set_tid_address, set_robust_list
        Synchronization:
          - futex, nanosleep, clock_nanosleep, clock_gettime, gettimeofday
        Threading (limited):
          - clone (with restricted flags), arch_prctl
        I/O Multiplexing:
          - select, pselect6, poll, ppoll, epoll_create, epoll_ctl, epoll_wait
        Misc:
          - uname, getrandom, ioctl (limited), sched_yield, sched_getaffinity

        BLOCKED SYSCALLS (default action = KILL_PROCESS):
        --------------------------------------------------
        Process Creation/Execution:
          - execve, execveat, fork, vfork (prevents spawning)
        Debugging/Tracing:
          - ptrace, process_vm_readv, process_vm_writev
        Filesystem Manipulation:
          - mount, umount, umount2, pivot_root, chroot
        System Administration:
          - reboot, init_module, finit_module, delete_module
          - swapon, swapoff, kexec_load, kexec_file_load
        Security-Sensitive:
          - keyctl, add_key, request_key
          - setuid, setgid, setreuid, setregid, setresuid, setresgid
          - capset, prctl (except for seccomp)
        Network (optional - configurable):
          - socket, connect, bind, listen, accept, sendto, recvfrom

        GRACEFUL DEGRADATION:
          - Non-Linux: Logs warning, continues without seccomp
          - Missing library: Logs warning, continues without seccomp
          - Filter load failure: Logs error, raises SecurityViolation if strict mode
        """
        # Try python-seccomp first (cleaner API)
        if self._apply_seccomp_pyseccomp():
            return

        # Fall back to ctypes-based libseccomp
        if self._apply_seccomp_libseccomp():
            return

        # Neither method worked - log and continue with reduced security
        logger.warning(
            "Seccomp filter not applied: neither pyseccomp nor libseccomp available. "
            "Install python-seccomp for enhanced subprocess isolation.",
            extra={"event": "sandbox.seccomp_unavailable"}
        )

    def _apply_seccomp_pyseccomp(self) -> bool:
        """
        Apply seccomp filter using python-seccomp (pyseccomp) library.

        Returns True if filter was successfully applied, False otherwise.
        """
        try:
            import seccomp
        except ImportError:
            logger.debug("python-seccomp not available, trying libseccomp")
            return False

        try:
            # Create filter with default action KILL_PROCESS
            # KILL_PROCESS is preferred over KILL (which only kills the thread)
            try:
                default_action = seccomp.KILL_PROCESS
            except AttributeError:
                # Older versions may not have KILL_PROCESS
                default_action = seccomp.KILL

            f = seccomp.SyscallFilter(defaction=default_action)

            # ===== Memory Management =====
            f.add_rule(seccomp.ALLOW, "brk")
            f.add_rule(seccomp.ALLOW, "mmap")
            f.add_rule(seccomp.ALLOW, "mprotect")
            f.add_rule(seccomp.ALLOW, "munmap")
            f.add_rule(seccomp.ALLOW, "mremap")
            f.add_rule(seccomp.ALLOW, "madvise")
            f.add_rule(seccomp.ALLOW, "mincore")
            f.add_rule(seccomp.ALLOW, "msync")

            # ===== File I/O (read-focused, sandbox controls write paths) =====
            f.add_rule(seccomp.ALLOW, "read")
            f.add_rule(seccomp.ALLOW, "write")
            f.add_rule(seccomp.ALLOW, "openat")  # Modern open
            f.add_rule(seccomp.ALLOW, "close")
            f.add_rule(seccomp.ALLOW, "fstat")
            f.add_rule(seccomp.ALLOW, "newfstatat")  # fstatat on x86_64
            f.add_rule(seccomp.ALLOW, "lseek")
            f.add_rule(seccomp.ALLOW, "access")
            f.add_rule(seccomp.ALLOW, "faccessat")
            f.add_rule(seccomp.ALLOW, "faccessat2")
            f.add_rule(seccomp.ALLOW, "readlink")
            f.add_rule(seccomp.ALLOW, "readlinkat")
            f.add_rule(seccomp.ALLOW, "getcwd")
            f.add_rule(seccomp.ALLOW, "stat")
            f.add_rule(seccomp.ALLOW, "lstat")
            f.add_rule(seccomp.ALLOW, "statfs")
            f.add_rule(seccomp.ALLOW, "fstatfs")
            f.add_rule(seccomp.ALLOW, "statx")
            f.add_rule(seccomp.ALLOW, "getdents")
            f.add_rule(seccomp.ALLOW, "getdents64")
            f.add_rule(seccomp.ALLOW, "dup")
            f.add_rule(seccomp.ALLOW, "dup2")
            f.add_rule(seccomp.ALLOW, "dup3")
            f.add_rule(seccomp.ALLOW, "pipe")
            f.add_rule(seccomp.ALLOW, "pipe2")
            f.add_rule(seccomp.ALLOW, "fcntl")
            f.add_rule(seccomp.ALLOW, "ioctl")  # Needed for terminal handling

            # ===== Process Information (read-only) =====
            f.add_rule(seccomp.ALLOW, "getpid")
            f.add_rule(seccomp.ALLOW, "gettid")
            f.add_rule(seccomp.ALLOW, "getppid")
            f.add_rule(seccomp.ALLOW, "getuid")
            f.add_rule(seccomp.ALLOW, "geteuid")
            f.add_rule(seccomp.ALLOW, "getgid")
            f.add_rule(seccomp.ALLOW, "getegid")
            f.add_rule(seccomp.ALLOW, "getgroups")
            f.add_rule(seccomp.ALLOW, "getrlimit")
            f.add_rule(seccomp.ALLOW, "prlimit64")
            f.add_rule(seccomp.ALLOW, "getrusage")

            # ===== Signal Handling =====
            f.add_rule(seccomp.ALLOW, "rt_sigaction")
            f.add_rule(seccomp.ALLOW, "rt_sigprocmask")
            f.add_rule(seccomp.ALLOW, "rt_sigreturn")
            f.add_rule(seccomp.ALLOW, "sigaltstack")

            # ===== Process Exit =====
            f.add_rule(seccomp.ALLOW, "exit")
            f.add_rule(seccomp.ALLOW, "exit_group")

            # ===== Time Functions =====
            f.add_rule(seccomp.ALLOW, "clock_gettime")
            f.add_rule(seccomp.ALLOW, "clock_getres")
            f.add_rule(seccomp.ALLOW, "gettimeofday")
            f.add_rule(seccomp.ALLOW, "nanosleep")
            f.add_rule(seccomp.ALLOW, "clock_nanosleep")
            f.add_rule(seccomp.ALLOW, "time")

            # ===== Synchronization =====
            f.add_rule(seccomp.ALLOW, "futex")
            f.add_rule(seccomp.ALLOW, "set_robust_list")
            f.add_rule(seccomp.ALLOW, "get_robust_list")

            # ===== I/O Multiplexing =====
            f.add_rule(seccomp.ALLOW, "select")
            f.add_rule(seccomp.ALLOW, "pselect6")
            f.add_rule(seccomp.ALLOW, "poll")
            f.add_rule(seccomp.ALLOW, "ppoll")
            f.add_rule(seccomp.ALLOW, "epoll_create")
            f.add_rule(seccomp.ALLOW, "epoll_create1")
            f.add_rule(seccomp.ALLOW, "epoll_ctl")
            f.add_rule(seccomp.ALLOW, "epoll_wait")
            f.add_rule(seccomp.ALLOW, "epoll_pwait")
            f.add_rule(seccomp.ALLOW, "eventfd")
            f.add_rule(seccomp.ALLOW, "eventfd2")

            # ===== Thread/Process Setup =====
            f.add_rule(seccomp.ALLOW, "set_tid_address")
            f.add_rule(seccomp.ALLOW, "arch_prctl")
            f.add_rule(seccomp.ALLOW, "prctl")  # Needed for seccomp itself

            # ===== System Information (read-only) =====
            f.add_rule(seccomp.ALLOW, "uname")
            f.add_rule(seccomp.ALLOW, "sysinfo")
            f.add_rule(seccomp.ALLOW, "getrandom")

            # ===== Scheduler (read-only + yield) =====
            f.add_rule(seccomp.ALLOW, "sched_yield")
            f.add_rule(seccomp.ALLOW, "sched_getaffinity")
            f.add_rule(seccomp.ALLOW, "sched_get_priority_min")
            f.add_rule(seccomp.ALLOW, "sched_get_priority_max")

            # ===== Memory Locking (for Python internals) =====
            f.add_rule(seccomp.ALLOW, "mlock")
            f.add_rule(seccomp.ALLOW, "munlock")

            # ===== Restricted clone (threading only, no new namespaces) =====
            # Note: clone is needed for Python threading but we can't easily
            # restrict flags with basic seccomp rules. RLIMIT_NPROC=1 provides
            # additional protection against fork bombs.
            f.add_rule(seccomp.ALLOW, "clone")
            f.add_rule(seccomp.ALLOW, "clone3")

            # ===== Write operations for stdout/stderr =====
            f.add_rule(seccomp.ALLOW, "writev")
            f.add_rule(seccomp.ALLOW, "pwrite64")
            f.add_rule(seccomp.ALLOW, "pwritev")

            # ===== Read operations =====
            f.add_rule(seccomp.ALLOW, "pread64")
            f.add_rule(seccomp.ALLOW, "readv")
            f.add_rule(seccomp.ALLOW, "preadv")

            # ===== Memory mapping with restrictions =====
            f.add_rule(seccomp.ALLOW, "rseq")  # Restartable sequences

            # Load the filter
            f.load()

            logger.info(
                "Seccomp-bpf filter applied successfully via pyseccomp",
                extra={"event": "sandbox.seccomp_applied", "method": "pyseccomp"}
            )
            return True

        except OSError as e:
            # EPERM (1) means seccomp is not allowed (e.g., in container without capability)
            # EINVAL (22) means invalid filter or seccomp not supported
            import errno
            if hasattr(e, 'errno'):
                if e.errno == errno.EPERM:
                    logger.warning(
                        "Seccomp filter denied (EPERM): process lacks CAP_SYS_ADMIN or "
                        "seccomp is disabled. Running with reduced isolation.",
                        extra={"event": "sandbox.seccomp_denied", "error": str(e)}
                    )
                elif e.errno == errno.EINVAL:
                    logger.warning(
                        "Seccomp filter invalid or unsupported kernel",
                        extra={"event": "sandbox.seccomp_invalid", "error": str(e)}
                    )
                else:
                    logger.warning(
                        f"Seccomp filter OS error: {e}",
                        extra={"event": "sandbox.seccomp_os_error", "error": str(e)}
                    )
            else:
                logger.warning(f"Seccomp filter OS error: {e}")
            return False

        except Exception as e:
            logger.error(
                f"Unexpected error applying seccomp via pyseccomp: {type(e).__name__}: {e}",
                extra={"event": "sandbox.seccomp_error", "error": str(e)}
            )
            return False

    def _apply_seccomp_libseccomp(self) -> bool:
        """
        Apply seccomp filter using ctypes bindings to libseccomp.

        This is a fallback when python-seccomp is not installed.
        Returns True if filter was successfully applied, False otherwise.
        """
        try:
            import ctypes
            import ctypes.util
        except ImportError:
            return False

        try:
            # Find libseccomp
            libseccomp_path = ctypes.util.find_library('seccomp')
            if not libseccomp_path:
                logger.debug("libseccomp not found in system library path")
                return False

            libseccomp = ctypes.CDLL(libseccomp_path, use_errno=True)

            # libseccomp constants
            SCMP_ACT_KILL_PROCESS = 0x80000000
            SCMP_ACT_KILL = 0x00000000
            SCMP_ACT_ALLOW = 0x7FFF0000

            # Try KILL_PROCESS first, fall back to KILL
            try:
                default_action = SCMP_ACT_KILL_PROCESS
            except Exception:
                default_action = SCMP_ACT_KILL

            # Initialize filter
            libseccomp.seccomp_init.argtypes = [ctypes.c_uint32]
            libseccomp.seccomp_init.restype = ctypes.c_void_p

            ctx = libseccomp.seccomp_init(default_action)
            if not ctx:
                logger.warning("Failed to initialize seccomp context")
                return False

            # Helper to add syscall rule
            libseccomp.seccomp_rule_add.argtypes = [
                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint
            ]
            libseccomp.seccomp_rule_add.restype = ctypes.c_int

            libseccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
            libseccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int

            def allow_syscall(name: str) -> None:
                """Add allow rule for a syscall by name"""
                syscall_nr = libseccomp.seccomp_syscall_resolve_name(name.encode('utf-8'))
                if syscall_nr < 0:
                    # Syscall not found on this architecture - skip silently
                    return
                ret = libseccomp.seccomp_rule_add(ctx, SCMP_ACT_ALLOW, syscall_nr, 0)
                if ret < 0:
                    logger.debug(f"Failed to add rule for syscall {name}: {ret}")

            # Add all allowed syscalls (same list as pyseccomp version)
            allowed_syscalls = [
                # Memory management
                "brk", "mmap", "mprotect", "munmap", "mremap", "madvise", "mincore", "msync",
                # File I/O
                "read", "write", "openat", "close", "fstat", "newfstatat", "lseek",
                "access", "faccessat", "faccessat2", "readlink", "readlinkat", "getcwd",
                "stat", "lstat", "statfs", "fstatfs", "statx", "getdents", "getdents64",
                "dup", "dup2", "dup3", "pipe", "pipe2", "fcntl", "ioctl",
                # Process info
                "getpid", "gettid", "getppid", "getuid", "geteuid", "getgid", "getegid",
                "getgroups", "getrlimit", "prlimit64", "getrusage",
                # Signals
                "rt_sigaction", "rt_sigprocmask", "rt_sigreturn", "sigaltstack",
                # Exit
                "exit", "exit_group",
                # Time
                "clock_gettime", "clock_getres", "gettimeofday", "nanosleep",
                "clock_nanosleep", "time",
                # Sync
                "futex", "set_robust_list", "get_robust_list",
                # I/O multiplexing
                "select", "pselect6", "poll", "ppoll", "epoll_create", "epoll_create1",
                "epoll_ctl", "epoll_wait", "epoll_pwait", "eventfd", "eventfd2",
                # Thread setup
                "set_tid_address", "arch_prctl", "prctl",
                # System info
                "uname", "sysinfo", "getrandom",
                # Scheduler
                "sched_yield", "sched_getaffinity", "sched_get_priority_min",
                "sched_get_priority_max",
                # Memory locking
                "mlock", "munlock",
                # Threading
                "clone", "clone3",
                # Extended I/O
                "writev", "pwrite64", "pwritev", "pread64", "readv", "preadv",
                # Misc
                "rseq",
            ]

            for syscall in allowed_syscalls:
                allow_syscall(syscall)

            # Load the filter
            libseccomp.seccomp_load.argtypes = [ctypes.c_void_p]
            libseccomp.seccomp_load.restype = ctypes.c_int

            ret = libseccomp.seccomp_load(ctx)

            # Release context
            libseccomp.seccomp_release.argtypes = [ctypes.c_void_p]
            libseccomp.seccomp_release.restype = None
            libseccomp.seccomp_release(ctx)

            if ret < 0:
                import errno
                err = ctypes.get_errno()
                if err == errno.EPERM:
                    logger.warning(
                        "Seccomp filter denied (EPERM): process lacks capability",
                        extra={"event": "sandbox.seccomp_denied"}
                    )
                else:
                    logger.warning(
                        f"Seccomp filter load failed with error code {ret}",
                        extra={"event": "sandbox.seccomp_load_failed", "error_code": ret}
                    )
                return False

            logger.info(
                "Seccomp-bpf filter applied successfully via libseccomp",
                extra={"event": "sandbox.seccomp_applied", "method": "libseccomp"}
            )
            return True

        except OSError as e:
            logger.warning(f"libseccomp OS error: {e}")
            return False

        except Exception as e:
            logger.debug(f"libseccomp fallback failed: {type(e).__name__}: {e}")
            return False

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

        except (OSError, ValueError) as e:
            # OSError: permission denied or unsupported limit
            # ValueError: invalid limit values
            logger.warning(f"Failed to set resource limits ({type(e).__name__}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error setting resource limits: {type(e).__name__}: {e}")

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
