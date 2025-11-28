"""
Base interfaces for governance-controlled modules.

These abstractions provide a consistent lifecycle for every module that plugs
into transaction validation, block processing, security monitoring, or external
interop.  The concrete implementations already present in `src/xai/blockchain`
can adopt these interfaces incrementally without refactors across the entire
node.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from xai.core.blockchain import Blockchain, Block, Transaction


@dataclass
class ModuleMetadata:
    name: str
    version: str
    owner: str
    description: str
    governance_controls: Dict[str, Any] = field(default_factory=dict)
    docs_path: Optional[str] = None


@dataclass
class ModuleContext:
    blockchain: "Blockchain"
    config: Any
    metrics: Any


@dataclass
class TransactionContext(ModuleContext):
    transaction: "Transaction"
    sender_balance: Optional[float] = None


@dataclass
class BlockContext(ModuleContext):
    block: "Block"
    height: int


class ModuleLifecycle(Protocol):
    """Shared lifecycle hooks surfaced to governance tooling."""

    metadata: ModuleMetadata

    def configure(self, context: ModuleContext) -> None:
        """Load configs or dependencies once the module is attached."""

    def rollback(self, context: ModuleContext) -> None:
        """Provide a safe rollback path if activation fails post-deploy."""


class TransactionModule(ModuleLifecycle):
    def pre_validate(self, context: TransactionContext) -> None:
        raise NotImplementedError

    def apply(self, context: TransactionContext) -> None:
        raise NotImplementedError


class BlockModule(ModuleLifecycle):
    def pre_apply(self, context: BlockContext) -> None:
        raise NotImplementedError

    def post_apply(self, context: BlockContext) -> None:
        raise NotImplementedError


class ConsensusModule(ModuleLifecycle):
    def validate_block(self, context: BlockContext) -> None:
        raise NotImplementedError

    def validate_transaction(self, context: TransactionContext) -> None:
        raise NotImplementedError


class DataModule(ModuleLifecycle):
    def refresh(self, context: ModuleContext) -> None:
        raise NotImplementedError

    def validate_feed(self, payload: Dict[str, Any]) -> bool:
        raise NotImplementedError


class ObserverModule(ModuleLifecycle):
    def publish(self, context: ModuleContext, payload: Dict[str, Any]) -> None:
        raise NotImplementedError


class InteropModule(ModuleLifecycle):
    def verify_proof(self, payload: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def submit_fraud_evidence(self, payload: Dict[str, Any]) -> None:
        raise NotImplementedError


class ServiceModule(ModuleLifecycle):
    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError
