"""
Unit tests for PrecompileRegistry.

Coverage targets:
- Registration deduplication
- Case-insensitive lookup
- Clear behavior
"""

import pytest

from xai.core.vm.precompiles import PrecompileRegistry, ExecutionMessage, ExecutionResult
from xai.core.vm.exceptions import VMExecutionError


def test_register_and_get_precompile():
    """Registry stores and retrieves handlers case-insensitively."""
    registry = PrecompileRegistry()

    def handler(msg: ExecutionMessage) -> ExecutionResult:
        return ExecutionResult(success=True, gas_used=0, return_data=b"ok")

    registry.register("0x01", handler, "identity")
    precomp = registry.get("0x01")
    assert precomp is not None
    assert precomp.handler is handler
    assert precomp.description == "identity"

    assert registry.get("0x01".upper()) is precomp


def test_register_duplicate_raises():
    """Duplicate registration raises VMExecutionError."""
    registry = PrecompileRegistry()
    registry.register("0x02", lambda m: m, "dummy")
    with pytest.raises(VMExecutionError):
        registry.register("0x02", lambda m: m, "duplicate")


def test_clear_registry():
    """Clear removes all entries."""
    registry = PrecompileRegistry()
    registry.register("0x03", lambda m: m, "dummy")
    registry.clear()
    assert registry.get("0x03") is None
