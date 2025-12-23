"""Registry for EVM-style precompiled contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .exceptions import VMExecutionError
from .executor import ExecutionMessage, ExecutionResult

PrecompileHandler = Callable[[ExecutionMessage], ExecutionResult]

@dataclass
class Precompile:
    address: str
    handler: PrecompileHandler
    description: str

class PrecompileRegistry:
    """Simple in-memory registry so executors can look up native handlers."""

    def __init__(self) -> None:
        self._registry: dict[str, Precompile] = {}

    def register(self, address: str, handler: PrecompileHandler, description: str) -> None:
        key = address.lower()
        if key in self._registry:
            raise VMExecutionError(f"Precompile already registered for {address}")
        self._registry[key] = Precompile(address=address, handler=handler, description=description)

    def get(self, address: str) -> Precompile | None:
        return self._registry.get(address.lower())

    def clear(self) -> None:
        self._registry.clear()
