"""
Module infrastructure used to plug governance-controlled components into the node.

All modules must inherit from the interfaces defined in `base.py`.  Keeping this
package lightweight allows us to compose transaction/block/consensus hooks
without introducing import cycles in the existing code while we incrementally
adopt the new smart-contract plan.
"""

from .base import (  # noqa: F401
    ModuleMetadata,
    ModuleContext,
    TransactionContext,
    BlockContext,
    TransactionModule,
    BlockModule,
    ConsensusModule,
    DataModule,
    ObserverModule,
    InteropModule,
    ServiceModule,
)

__all__ = [
    "ModuleMetadata",
    "ModuleContext",
    "TransactionContext",
    "BlockContext",
    "TransactionModule",
    "BlockModule",
    "ConsensusModule",
    "DataModule",
    "ObserverModule",
    "InteropModule",
    "ServiceModule",
]
