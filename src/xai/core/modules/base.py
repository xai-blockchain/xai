"""
Base interfaces for governance-controlled modules.

These abstractions provide a consistent lifecycle for every module that plugs
into transaction validation, block processing, security monitoring, or external
interop.  The concrete implementations already present in `src/xai/blockchain`
can adopt these interfaces incrementally without refactors across the entire
node.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
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


class TransactionModule(ModuleLifecycle, ABC):
    @abstractmethod
    def pre_validate(self, context: TransactionContext) -> None:
        """Perform stateless validation before execution."""

    @abstractmethod
    def apply(self, context: TransactionContext) -> None:
        """Apply state changes after validation."""


class BlockModule(ModuleLifecycle, ABC):
    @abstractmethod
    def pre_apply(self, context: BlockContext) -> None:
        """Inspect a block before it mutates chain state."""

    @abstractmethod
    def post_apply(self, context: BlockContext) -> None:
        """Run hooks after a block has been committed."""


class ConsensusModule(ModuleLifecycle, ABC):
    @abstractmethod
    def validate_block(self, context: BlockContext) -> None:
        """Perform consensus checks on a block candidate."""

    @abstractmethod
    def validate_transaction(self, context: TransactionContext) -> None:
        """Validate transaction against consensus-specific rules."""


class DataModule(ModuleLifecycle, ABC):
    @abstractmethod
    def refresh(self, context: ModuleContext) -> None:
        """Refresh cached state or external feeds."""

    @abstractmethod
    def validate_feed(self, payload: Dict[str, Any]) -> bool:
        """Validate an external data feed payload."""


class ObserverModule(ModuleLifecycle, ABC):
    @abstractmethod
    def publish(self, context: ModuleContext, payload: Dict[str, Any]) -> None:
        """Publish telemetry or events downstream."""


class InteropModule(ModuleLifecycle, ABC):
    @abstractmethod
    def verify_proof(self, payload: Dict[str, Any]) -> bool:
        """Verify interoperability proof payloads."""

    @abstractmethod
    def submit_fraud_evidence(self, payload: Dict[str, Any]) -> None:
        """Submit fraud evidence back to governance."""


class ServiceModule(ModuleLifecycle, ABC):
    @abstractmethod
    def start(self) -> None:
        """Start long-running service loops."""

    @abstractmethod
    def stop(self) -> None:
        """Stop long-running service loops."""
