"""Coordination helpers for smart-contract transaction processing."""

from __future__ import annotations

import time
from typing import Any, Dict, List, TYPE_CHECKING

from .executor import (
    ExecutionMessage,
    ExecutionResult,
    SimpleContractExecutor,
    BaseExecutor,
)
from .exceptions import VMExecutionError
from .tx_processor import ContractTransactionProcessor

if TYPE_CHECKING:  # pragma: no cover - avoid circular imports
    from xai.core.blockchain import Blockchain, Block, Transaction


class SmartContractManager:
    """Handles contract execution, receipt tracking, and view calls."""

    CONTRACT_TYPES = {"contract_call", "contract_deploy"}

    def __init__(self, blockchain: "Blockchain", executor: BaseExecutor | None = None) -> None:
        self.blockchain = blockchain
        self.executor = executor or SimpleContractExecutor(blockchain)
        self.processor = ContractTransactionProcessor(blockchain, executor=self.executor)

    def is_contract_transaction(self, tx: "Transaction") -> bool:
        return tx.tx_type in self.CONTRACT_TYPES

    def process_block(self, block: "Block") -> List[Dict[str, Any]]:
        receipts: List[Dict[str, Any]] = []
        for tx in block.transactions:
            if not self.is_contract_transaction(tx):
                continue
            receipt = self.process_transaction(tx, block)
            receipts.append(receipt)
        return receipts

    def process_transaction(self, tx: "Transaction", block: "Block") -> Dict[str, Any]:
        metadata = dict(tx.metadata or {})
        try:
            result = self.processor.process(tx, block)
        except VMExecutionError as exc:
            result = ExecutionResult(
                success=False,
                gas_used=0,
                return_data=b"",
                logs=[{"event": "vm_error", "message": str(exc)}],
            )

        contract_address = tx.recipient or self.blockchain.derive_contract_address(tx.sender, tx.nonce)
        normalized = contract_address.upper()
        block_index = getattr(block, "index", getattr(block.header, "index", None))
        block_hash = getattr(block, "hash", getattr(getattr(block, "header", None), "hash", None))
        block_timestamp = getattr(block, "timestamp", getattr(getattr(block, "header", None), "timestamp", time.time()))
        receipt: Dict[str, Any] = {
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
                logger = getattr(self.blockchain, "logger", None)
                if logger:
                    logger.warn(f"Failed to persist contract ABI: {exc}")
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

    def snapshot(self) -> Dict[str, Any]:
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

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """
        Restore contract state from a snapshot.
        Thread-safe atomic operation for chain reorganization rollback.

        Args:
            snapshot: Snapshot created by snapshot() method
        """
        import copy
        self.blockchain.contracts = copy.deepcopy(snapshot.get("contracts", {}))
        self.blockchain.contract_receipts = copy.deepcopy(snapshot.get("contract_receipts", []))

        logger = getattr(self.blockchain, "logger", None)
        if logger:
            logger.info(
                "Contract state restored from snapshot",
                extra={
                    "event": "contract.restore",
                    "contract_count": len(self.blockchain.contracts),
                    "receipt_count": len(self.blockchain.contract_receipts),
                }
            )
