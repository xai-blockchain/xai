"""Exception hierarchy for the smart-contract VM."""

from __future__ import annotations


class VMError(Exception):
    """Base class for VM-specific errors."""


class VMConfigurationError(VMError):
    """Raised when the VM is misconfigured (invalid gas limits, missing precompiles, etc.)."""


class VMExecutionError(VMError):
    """
    Raised when execution fails deterministically.

    Use this for contract-level errors (stack issues, invalid opcode) so that
    upstream components can convert them into transaction reverts without
    masking bugs.
    """

    def __init__(self, message: str, *, revert_data: bytes | None = None) -> None:
        super().__init__(message)
        self.revert_data = revert_data or b""
