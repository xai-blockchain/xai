"""
XAI Light Clients Module

Cross-chain light client verification for EVM and Cosmos chains.
Enables trustless verification of external blockchain state.
"""

from xai.core.light_clients.evm_light_client import (
    EVMLightClient,
    EVMBlockHeader,
    EVMStateProof,
    EVMChainConfig,
)
from xai.core.light_clients.cosmos_light_client import (
    CosmosLightClient,
    CosmosBlockHeader,
    CosmosValidatorSet,
    CosmosProof,
)
from xai.core.light_clients.manager import (
    LightClientManager,
    ChainType,
    ProofVerificationResult,
)

__all__ = [
    "EVMLightClient",
    "EVMBlockHeader",
    "EVMStateProof",
    "EVMChainConfig",
    "CosmosLightClient",
    "CosmosBlockHeader",
    "CosmosValidatorSet",
    "CosmosProof",
    "LightClientManager",
    "ChainType",
    "ProofVerificationResult",
]
