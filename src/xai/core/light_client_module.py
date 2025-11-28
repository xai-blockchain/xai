"""
Light Client Module Exports
Task 177: Light client SPV proof verification

Re-export light client functionality from core module.
"""

from xai.core.light_client import (
    LightClient,
    SPVProof,
    BlockHeader,
    MerkleProofGenerator,
    SPVServerInterface
)

__all__ = [
    "LightClient",
    "SPVProof",
    "BlockHeader",
    "MerkleProofGenerator",
    "SPVServerInterface"
]
