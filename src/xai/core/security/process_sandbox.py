from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

def _get_logger(logger: Any) -> logging.Logger:
    if isinstance(logger, logging.Logger):
        return logger
    return logging.getLogger(__name__)

def apply_process_limits(
    max_mem_mb: int = 2048,
    cpu_seconds: int = 7200,
    open_files: int = 2048,
    logger: Any = None,
) -> dict[str, tuple[int, int]]:
    """
    Apply best-effort resource limits to the current process.

    Returns a mapping of resource name -> (soft_limit, hard_limit) for visibility.
    """
    log = _get_logger(logger)
    if os.name != "posix":
        log.info("Process sandbox skipped: non-posix platform", extra={"event": "sandbox.skipped"})
        return {}

    import resource

    limits = {}

    def _bounded(target: int, current_hard: int) -> tuple[int, int]:
        if current_hard == resource.RLIM_INFINITY or current_hard < 0:
            return target, target
        bounded = min(target, int(current_hard))
        return bounded, bounded

    try:
        # Address space (approx memory) in bytes
        mem_bytes = int(max_mem_mb) * 1024 * 1024
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        new_soft, new_hard = _bounded(mem_bytes, hard)
        resource.setrlimit(resource.RLIMIT_AS, (new_soft, new_hard))
        limits["address_space_bytes"] = (new_soft, new_hard)
    except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:  # pragma: no cover - platform specific
        logger.error(
            "Exception in _bounded",
            extra={
                "error_type": "Exception",
                "error": str(exc),
                "function": "_bounded"
            }
        )
        log.warning("Failed to set memory limit: %s", exc, extra={"event": "sandbox.mem_fail"})

    try:
        cpu_target = int(cpu_seconds)
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        new_soft, new_hard = _bounded(cpu_target, hard)
        resource.setrlimit(resource.RLIMIT_CPU, (new_soft, new_hard))
        limits["cpu_seconds"] = (new_soft, new_hard)
    except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:  # pragma: no cover - platform specific
        logger.error(
            "Exception in _bounded",
            extra={
                "error_type": "Exception",
                "error": str(exc),
                "function": "_bounded"
            }
        )
        log.warning("Failed to set CPU limit: %s", exc, extra={"event": "sandbox.cpu_fail"})

    try:
        open_target = int(open_files)
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_soft, new_hard = _bounded(open_target, hard)
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, new_hard))
        limits["open_files"] = (new_soft, new_hard)
    except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:  # pragma: no cover - platform specific
        logger.error(
            "Exception in _bounded",
            extra={
                "error_type": "Exception",
                "error": str(exc),
                "function": "_bounded"
            }
        )
        log.warning("Failed to set file descriptor limit: %s", exc, extra={"event": "sandbox.fd_fail"})

    log.info("Process sandbox limits applied", extra={"event": "sandbox.applied", "limits": limits})
    return limits

def maybe_enable_process_sandbox(logger: Any = None) -> dict[str, tuple[int, int]] | bool:
    """
    Enable process sandboxing based on environment variables.

    Environment:
        XAI_ENABLE_PROCESS_SANDBOX: set to "1"/"true" to enable
        XAI_SANDBOX_MAX_MEM_MB: memory cap in MB (default 2048)
        XAI_SANDBOX_MAX_CPU_SECONDS: CPU seconds cap (default 7200)
        XAI_SANDBOX_MAX_OPEN_FILES: file descriptor cap (default 2048)
    """
    enabled = os.getenv("XAI_ENABLE_PROCESS_SANDBOX", "false").lower() in {"1", "true", "yes"}
    log = _get_logger(logger)

    if not enabled:
        log.debug("Process sandbox disabled by environment", extra={"event": "sandbox.disabled"})
        return False

    max_mem_mb = int(os.getenv("XAI_SANDBOX_MAX_MEM_MB", "2048"))
    cpu_seconds = int(os.getenv("XAI_SANDBOX_MAX_CPU_SECONDS", "7200"))
    open_files = int(os.getenv("XAI_SANDBOX_MAX_OPEN_FILES", "2048"))
    return apply_process_limits(max_mem_mb=max_mem_mb, cpu_seconds=cpu_seconds, open_files=open_files, logger=log)
