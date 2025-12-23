"""
Light Client Module Exports
Task 177: Light client SPV proof verification

Re-export light client functionality from core module.
"""

from xai.core.light_client import (
    BlockHeader,
    LightClient,
    MerkleProofGenerator,
    SPVProof,
    SPVServerInterface,
)

__all__ = [
    "LightClient",
    "SPVProof",
    "BlockHeader",
    "MerkleProofGenerator",
    "SPVServerInterface"
]
