"""Bridge between blockchain transactions and the VM executors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .executor import BaseExecutor, ExecutionMessage, ExecutionResult, ProductionContractExecutor
from .state import EVMState

if TYPE_CHECKING:  # pragma: no cover - import heavy types only for hints
    from xai.core.blockchain import Block, Blockchain, Transaction

@dataclass
class ProcessorConfig:
    max_call_depth: int = 1024
    default_gas_limit: int = 15_000_000

class ContractTransactionProcessor:
    """
    Entry point used by `Blockchain` when it encounters smart-contract transactions.

    The processor is intentionally stateless; it wires the transaction, state view,
    and executor together and returns an execution result that higher layers can
    convert into receipts or errors.
    """

    def __init__(self, blockchain: "Blockchain", executor: BaseExecutor | None = None) -> None:
        self.blockchain = blockchain
        # Use production executor by default with full security controls
        self.executor = executor or ProductionContractExecutor(blockchain)
        self.config = ProcessorConfig()

    def process(
        self,
        tx: "Transaction",
        block: "Block",
        *,
        static: bool = False,
    ) -> ExecutionResult:
        message = self._build_message(tx)
        state = EVMState(blockchain=self.blockchain, block=block)
        # Future iterations will attach `state` to the executor; for now we pass via
        # global singletons.  The dummy executor ignores it entirely.
        return self._execute(message, static=static)

    def _execute(self, message: ExecutionMessage, *, static: bool) -> ExecutionResult:
        if static:
            return self.executor.call_static(message)
        return self.executor.execute(message)

    def _build_message(self, tx: "Transaction") -> ExecutionMessage:
        data = tx.metadata.get("data", b"") if isinstance(tx.metadata, dict) else b""
        if isinstance(data, str):
            data = bytes.fromhex(data)
        return ExecutionMessage(
            sender=tx.sender,
            to=tx.recipient if tx.tx_type != "contract_deploy" else None,
            value=int(tx.amount),
            gas_limit=int(tx.metadata.get("gas_limit", self.config.default_gas_limit))
            if isinstance(tx.metadata, dict)
            else self.config.default_gas_limit,
            data=data,
            nonce=tx.nonce or 0,
        )
