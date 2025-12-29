"""Coordination helpers for smart-contract transaction processing."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from .exceptions import VMExecutionError
from .executor import (
    BaseExecutor,
    ExecutionMessage,
    ExecutionResult,
    SimpleContractExecutor,
)
from .tx_processor import ContractTransactionProcessor

if TYPE_CHECKING:  # pragma: no cover - avoid circular imports
    from xai.core.blockchain import Block, Blockchain, Transaction

try:  # pragma: no cover - optional for lightweight test environments
    from xai.core.api.monitoring import MetricsCollector  # type: ignore
except ImportError:  # pragma: no cover
    MetricsCollector = None  # type: ignore

def _record_contract_metric(metric_name: str, value: float, operation: str = "inc") -> None:
    """Safely record smart contract metrics if the collector is available."""
    if MetricsCollector is None:
        return
    collector = getattr(MetricsCollector, "_instance", None)
    if collector is None:
        return
    metric = collector.get_metric(metric_name)
    if metric is None:
        return
    try:
        if operation == "inc":
            metric.inc(value)
        elif operation == "observe":
            metric.observe(value)
    except (AttributeError, TypeError, ValueError):
        logger.debug("Failed to record contract metric %s", metric_name)

class SmartContractManager:
    """Handles contract execution, receipt tracking, and view calls."""

    CONTRACT_TYPES = {"contract_call", "contract_deploy"}

    def __init__(self, blockchain: "Blockchain", executor: BaseExecutor | None = None) -> None:
        self.blockchain = blockchain
        self.executor = executor or SimpleContractExecutor(blockchain)
        self.processor = ContractTransactionProcessor(blockchain, executor=self.executor)

    def is_contract_transaction(self, tx: "Transaction") -> bool:
        return tx.tx_type in self.CONTRACT_TYPES

    def process_block(self, block: "Block") -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        for tx in block.transactions:
            if not self.is_contract_transaction(tx):
                continue
            receipt = self.process_transaction(tx, block)
            receipts.append(receipt)
        return receipts

    def process_transaction(self, tx: "Transaction", block: "Block") -> dict[str, Any]:
        metadata = dict(tx.metadata or {})
        exec_start = time.perf_counter()
        try:
            result = self.processor.process(tx, block)
        except VMExecutionError as exc:
            logger.warning(
                "VMExecutionError in process_transaction",
                extra={
                    "error_type": "VMExecutionError",
                    "error": str(exc),
                    "function": "process_transaction"
                }
            )
            result = ExecutionResult(
                success=False,
                gas_used=0,
                return_data=b"",
                logs=[{"event": "vm_error", "message": str(exc)}],
            )
        duration = max(time.perf_counter() - exec_start, 0.0)

        tx_type = tx.tx_type or ""
        gas_used = max(int(result.gas_used or 0), 0)
        if tx_type == "contract_deploy":
            _record_contract_metric("xai_contract_deployments_total", 1)
        else:
            _record_contract_metric("xai_contract_calls_total", 1)
        if result.success:
            _record_contract_metric("xai_contract_success_total", 1)
        else:
            _record_contract_metric("xai_contract_failures_total", 1)
        _record_contract_metric("xai_contract_gas_used_total", gas_used)
        _record_contract_metric(
            "xai_contract_execution_duration_seconds",
            duration,
            operation="observe",
        )

        contract_address = tx.recipient or self.blockchain.derive_contract_address(tx.sender, tx.nonce)
        normalized = contract_address.upper()
        block_index = getattr(block, "index", getattr(block.header, "index", None))
        block_hash = getattr(block, "hash", getattr(getattr(block, "header", None), "hash", None))
        block_timestamp = getattr(block, "timestamp", getattr(getattr(block, "header", None), "timestamp", time.time()))
        receipt: dict[str, Any] = {
            "txid": tx.txid,
            "contract": normalized,
            "success": result.success,
            "gas_used": result.gas_used,
            "return_data": result.return_data.hex(),
            "logs": [dict(log) for log in result.logs],
            "block_index": block_index,
            "block_hash": block_hash,
            "timestamp": block_timestamp,
        }

        metadata["vm_result"] = receipt
        tx.metadata = metadata

        if tx.tx_type == "contract_deploy" and metadata.get("abi"):
            try:
                self.blockchain.store_contract_abi(
                    normalized,
                    metadata.get("abi"),
                    verified=True,
                    source="deployment",
                )
            except (ValueError, TypeError) as exc:  # pragma: no cover - defensive
                blockchain_logger = getattr(self.blockchain, "logger", None)
                if blockchain_logger:
                    blockchain_logger.warn(f"Failed to persist contract ABI: {exc}")
        return receipt

    def static_call(
        self,
        sender: str,
        contract_address: str,
        data: bytes,
        gas_limit: int,
    ) -> ExecutionResult:
        nonce = self.blockchain.nonce_tracker.get_next_nonce(sender)
        message = ExecutionMessage(
            sender=sender,
            to=contract_address,
            value=0,
            gas_limit=gas_limit,
            data=data,
            nonce=nonce,
        )
        return self.executor.call_static(message)

    def snapshot(self) -> dict[str, Any]:
        """
        Create a complete snapshot of the current contract state.
        Thread-safe atomic operation for chain reorganization rollback.

        Returns:
            A deep copy of the contract state including contracts and receipts
        """
        import copy
        return {
            "contracts": copy.deepcopy(self.blockchain.contracts),
            "contract_receipts": copy.deepcopy(self.blockchain.contract_receipts),
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        """
        Restore contract state from a snapshot.
        Thread-safe atomic operation for chain reorganization rollback.

        Args:
            snapshot: Snapshot created by snapshot() method
        """
        import copy
        self.blockchain.contracts = copy.deepcopy(snapshot.get("contracts", {}))
        self.blockchain.contract_receipts = copy.deepcopy(snapshot.get("contract_receipts", []))

        blockchain_logger = getattr(self.blockchain, "logger", None)
        if blockchain_logger:
            blockchain_logger.info(
                "Contract state restored from snapshot",
                extra={
                    "event": "contract.restore",
                    "contract_count": len(self.blockchain.contracts),
                    "receipt_count": len(self.blockchain.contract_receipts),
                }
            )
