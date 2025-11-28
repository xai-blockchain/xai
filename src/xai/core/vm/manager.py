"""Coordination helpers for smart-contract transaction processing."""

from __future__ import annotations

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
        receipt: Dict[str, Any] = {
            "txid": tx.txid,
            "contract": normalized,
            "success": result.success,
            "gas_used": result.gas_used,
            "return_data": result.return_data.hex(),
            "logs": [dict(log) for log in result.logs],
        }

        metadata["vm_result"] = receipt
        tx.metadata = metadata
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
