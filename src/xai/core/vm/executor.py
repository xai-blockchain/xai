"""Execution interfaces for smart-contract VMs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol, Sequence, TYPE_CHECKING

from .exceptions import VMExecutionError

if TYPE_CHECKING:  # pragma: no cover - runtime imports deferred
    from xai.core.blockchain import Blockchain


@dataclass
class ExecutionMessage:
    sender: str
    to: str | None
    value: int
    gas_limit: int
    data: bytes
    nonce: int


@dataclass
class ExecutionResult:
    success: bool
    gas_used: int
    return_data: bytes
    logs: Sequence[dict]


class BaseExecutor(Protocol):
    """
    Contract execution engine.

    Concrete executors (EVM/WASM) implement this interface so the surrounding node
    code can remain agnostic to the specific bytecode semantics.
    """

    def execute(self, message: ExecutionMessage) -> ExecutionResult:
        raise NotImplementedError

    def call_static(self, message: ExecutionMessage) -> ExecutionResult:
        raise NotImplementedError

    def estimate_gas(self, message: ExecutionMessage) -> int:
        raise NotImplementedError


class DummyExecutor(BaseExecutor):
    """
    Minimal placeholder executor used until the real VM is wired in.

    It refuses to execute anything substantial so developers do not accidentally
    ship the node without linking the real engine.
    """

    def execute(self, message: ExecutionMessage) -> ExecutionResult:  # pragma: no cover - placeholder
        raise VMExecutionError("Contract execution is not yet implemented")

    def call_static(self, message: ExecutionMessage) -> ExecutionResult:  # pragma: no cover - placeholder
        raise VMExecutionError("Static calls are not yet implemented")

    def estimate_gas(self, message: ExecutionMessage) -> int:  # pragma: no cover - placeholder
        raise VMExecutionError("Gas estimation is not yet implemented")


class SimpleContractExecutor(BaseExecutor):
    """Lightweight VM stub that stores key/value state per contract."""

    BASE_GAS = 21000

    def __init__(self, blockchain: "Blockchain") -> None:
        self.blockchain = blockchain

    def execute(self, message: ExecutionMessage) -> ExecutionResult:
        if message.to is None:
            return self._deploy_contract(message)
        return self._invoke_contract(message, mutate=True)

    def call_static(self, message: ExecutionMessage) -> ExecutionResult:
        return self._invoke_contract(message, mutate=False)

    def estimate_gas(self, message: ExecutionMessage) -> int:
        return self.BASE_GAS + len(message.data or b"")

    def _deploy_contract(self, message: ExecutionMessage) -> ExecutionResult:
        contract_address = self.blockchain.derive_contract_address(message.sender, message.nonce)
        normalized = self._normalize_address(contract_address)
        self.blockchain.register_contract(
            address=normalized,
            creator=message.sender,
            code=message.data,
            gas_limit=message.gas_limit,
            value=message.value,
        )
        gas_used = min(message.gas_limit, self.BASE_GAS + len(message.data or b""))
        logs = [{"event": "ContractDeployed", "contract": normalized}]
        return ExecutionResult(
            success=True,
            gas_used=gas_used,
            return_data=normalized.encode("utf-8"),
            logs=logs,
        )

    def _invoke_contract(
        self,
        message: ExecutionMessage,
        *,
        mutate: bool,
    ) -> ExecutionResult:
        if not message.to:
            raise VMExecutionError("Missing contract address for call")

        target = self._normalize_address(message.to)
        contract = self.blockchain.contracts.get(target)
        if not contract:
            raise VMExecutionError(f"Unknown contract {message.to}")

        payload = self._decode_payload(message.data or b"")
        op = payload.get("op", "").lower()
        gas_used = min(message.gas_limit, self.BASE_GAS + len(message.data or b""))
        storage = contract.setdefault("storage", {})
        logs: list[dict] = []

        if op == "set":
            key = payload.get("key")
            value = payload.get("value")
            if key is None:
                raise VMExecutionError("Missing key for storage.set")
            if mutate:
                storage[key] = value
            logs.append({"event": "StorageSet", "key": key})
            return ExecutionResult(success=True, gas_used=gas_used, return_data=b"OK", logs=logs)

        if op == "get":
            key = payload.get("key")
            if key is None:
                raise VMExecutionError("Missing key for storage.get")
            value = storage.get(key)
            return ExecutionResult(
                success=True,
                gas_used=gas_used,
                return_data=str(value).encode("utf-8") if value is not None else b"",
                logs=logs,
            )

        if op == "delete":
            key = payload.get("key")
            if key is None:
                raise VMExecutionError("Missing key for storage.delete")
            if mutate:
                storage.pop(key, None)
            logs.append({"event": "StorageDelete", "key": key})
            return ExecutionResult(success=True, gas_used=gas_used, return_data=b"OK", logs=logs)

        if op == "emit":
            message_payload = payload.get("message", "")
            logs.append({"event": "Log", "message": message_payload})
            return ExecutionResult(success=True, gas_used=gas_used, return_data=b"OK", logs=logs)

        raise VMExecutionError(f"Unsupported contract operation '{op}'")

    @staticmethod
    def _decode_payload(data: bytes) -> dict:
        if not data:
            return {}
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise VMExecutionError("Failed to decode contract payload") from exc
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise VMExecutionError("Contract payload must be valid JSON") from exc

    @staticmethod
    def _normalize_address(address: str) -> str:
        return address.upper()
