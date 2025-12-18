"""
Light Client Manager

Unified interface for managing multiple chain light clients.
Provides cross-chain proof verification and state caching.

Features:
- Multi-chain support (EVM + Cosmos)
- Automatic client registration
- Cross-chain proof verification
- State caching and persistence
- Health monitoring
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Any, List
from enum import Enum

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
    CosmosCommit,
    TrustLevel,
)

logger = logging.getLogger(__name__)


class ChainType(Enum):
    """Supported blockchain types"""
    EVM = "evm"
    COSMOS = "cosmos"
    UNKNOWN = "unknown"


@dataclass
class ProofVerificationResult:
    """Result of proof verification"""
    valid: bool
    message: str
    chain_type: ChainType
    chain_id: str
    height: int
    proof_type: str
    verified_at: int = 0

    def __post_init__(self):
        """Set verified_at timestamp"""
        if self.verified_at == 0:
            self.verified_at = int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'valid': self.valid,
            'message': self.message,
            'chain_type': self.chain_type.value,
            'chain_id': self.chain_id,
            'height': self.height,
            'proof_type': self.proof_type,
            'verified_at': self.verified_at,
        }


class LightClientManager:
    """
    Manages multiple light clients for cross-chain verification

    Provides unified interface for EVM and Cosmos light clients.
    """

    def __init__(self):
        """Initialize light client manager"""
        self.evm_clients: Dict[str, EVMLightClient] = {}  # chain_id -> client
        self.cosmos_clients: Dict[str, CosmosLightClient] = {}  # chain_id -> client

        # Cache for recent verifications
        self.verification_cache: Dict[str, ProofVerificationResult] = {}
        self.cache_ttl = 300  # 5 minutes

        logger.info("Light client manager initialized")

    def register_evm_chain(
        self,
        chain_config: EVMChainConfig,
        genesis_header: Optional[EVMBlockHeader] = None,
    ) -> bool:
        """
        Register an EVM-compatible chain

        Args:
            chain_config: Chain configuration
            genesis_header: Optional genesis header to initialize with

        Returns:
            True if registration successful
        """
        chain_id = str(chain_config.chain_id)

        if chain_id in self.evm_clients:
            logger.warning(f"EVM chain {chain_id} already registered")
            return False

        # Create light client
        client = EVMLightClient(chain_config)

        # Add genesis header if provided
        if genesis_header is not None:
            if not client.add_header(genesis_header):
                logger.error(f"Failed to add genesis header for chain {chain_id}")
                return False

        self.evm_clients[chain_id] = client

        logger.info(
            f"Registered EVM chain: {chain_config.chain_name} (ID: {chain_id})",
            extra={'event': 'light_client_manager.evm_registered'}
        )

        return True

    def register_cosmos_chain(
        self,
        chain_id: str,
        trust_level: TrustLevel = TrustLevel.ONE_THIRD,
        trust_period_seconds: int = 14 * 24 * 3600,
        trusted_header: Optional[CosmosBlockHeader] = None,
        trusted_validator_set: Optional[CosmosValidatorSet] = None,
        trusted_next_validator_set: Optional[CosmosValidatorSet] = None,
    ) -> bool:
        """
        Register a Cosmos SDK chain

        Args:
            chain_id: Cosmos chain ID
            trust_level: Required validator overlap
            trust_period_seconds: Trust period duration
            trusted_header: Optional trusted header to initialize with
            trusted_validator_set: Validator set for trusted header
            trusted_next_validator_set: Next validator set

        Returns:
            True if registration successful
        """
        if chain_id in self.cosmos_clients:
            logger.warning(f"Cosmos chain {chain_id} already registered")
            return False

        # Create light client
        client = CosmosLightClient(
            chain_id=chain_id,
            trust_level=trust_level,
            trust_period_seconds=trust_period_seconds,
        )

        # Initialize trust if provided
        if all([trusted_header, trusted_validator_set, trusted_next_validator_set]):
            if not client.initialize_trust(
                trusted_header,
                trusted_validator_set,
                trusted_next_validator_set,
            ):
                logger.error(f"Failed to initialize trust for chain {chain_id}")
                return False

        self.cosmos_clients[chain_id] = client

        logger.info(
            f"Registered Cosmos chain: {chain_id}",
            extra={'event': 'light_client_manager.cosmos_registered'}
        )

        return True

    def get_evm_client(self, chain_id: str) -> Optional[EVMLightClient]:
        """Get EVM light client by chain ID"""
        return self.evm_clients.get(chain_id)

    def get_cosmos_client(self, chain_id: str) -> Optional[CosmosLightClient]:
        """Get Cosmos light client by chain ID"""
        return self.cosmos_clients.get(chain_id)

    def verify_evm_header(
        self,
        chain_id: str,
        header: EVMBlockHeader,
    ) -> ProofVerificationResult:
        """
        Verify EVM block header

        Args:
            chain_id: EVM chain ID
            header: Block header to verify

        Returns:
            Verification result
        """
        client = self.evm_clients.get(chain_id)
        if not client:
            return ProofVerificationResult(
                valid=False,
                message=f"No EVM client registered for chain {chain_id}",
                chain_type=ChainType.EVM,
                chain_id=chain_id,
                height=header.number,
                proof_type='header',
            )

        # Attempt to add header
        if client.add_header(header):
            return ProofVerificationResult(
                valid=True,
                message=f"Header verified at height {header.number}",
                chain_type=ChainType.EVM,
                chain_id=chain_id,
                height=header.number,
                proof_type='header',
            )
        else:
            return ProofVerificationResult(
                valid=False,
                message=f"Header verification failed at height {header.number}",
                chain_type=ChainType.EVM,
                chain_id=chain_id,
                height=header.number,
                proof_type='header',
            )

    def verify_evm_state_proof(
        self,
        chain_id: str,
        height: int,
        proof: EVMStateProof,
    ) -> ProofVerificationResult:
        """
        Verify EVM state proof

        Args:
            chain_id: EVM chain ID
            height: Block height
            proof: State proof to verify

        Returns:
            Verification result
        """
        client = self.evm_clients.get(chain_id)
        if not client:
            return ProofVerificationResult(
                valid=False,
                message=f"No EVM client registered for chain {chain_id}",
                chain_type=ChainType.EVM,
                chain_id=chain_id,
                height=height,
                proof_type='state',
            )

        # Get header at height
        header = client.get_header(height)
        if not header:
            return ProofVerificationResult(
                valid=False,
                message=f"No header at height {height}",
                chain_type=ChainType.EVM,
                chain_id=chain_id,
                height=height,
                proof_type='state',
            )

        # Verify proof
        if client.verify_state_proof(header.state_root, proof):
            return ProofVerificationResult(
                valid=True,
                message=f"State proof verified at height {height}",
                chain_type=ChainType.EVM,
                chain_id=chain_id,
                height=height,
                proof_type='state',
            )
        else:
            return ProofVerificationResult(
                valid=False,
                message=f"State proof verification failed at height {height}",
                chain_type=ChainType.EVM,
                chain_id=chain_id,
                height=height,
                proof_type='state',
            )

    def verify_cosmos_header(
        self,
        chain_id: str,
        header: CosmosBlockHeader,
        validator_set: CosmosValidatorSet,
        next_validator_set: CosmosValidatorSet,
        commit: CosmosCommit,
    ) -> ProofVerificationResult:
        """
        Verify Cosmos block header

        Args:
            chain_id: Cosmos chain ID
            header: Block header to verify
            validator_set: Validator set at header height
            next_validator_set: Next validator set
            commit: Commit with signatures

        Returns:
            Verification result
        """
        client = self.cosmos_clients.get(chain_id)
        if not client:
            return ProofVerificationResult(
                valid=False,
                message=f"No Cosmos client registered for chain {chain_id}",
                chain_type=ChainType.COSMOS,
                chain_id=chain_id,
                height=header.height,
                proof_type='header',
            )

        # Verify header
        if client.verify_header(header, validator_set, next_validator_set, commit):
            return ProofVerificationResult(
                valid=True,
                message=f"Header verified at height {header.height}",
                chain_type=ChainType.COSMOS,
                chain_id=chain_id,
                height=header.height,
                proof_type='header',
            )
        else:
            return ProofVerificationResult(
                valid=False,
                message=f"Header verification failed at height {header.height}",
                chain_type=ChainType.COSMOS,
                chain_id=chain_id,
                height=header.height,
                proof_type='header',
            )

    def verify_cosmos_ibc_proof(
        self,
        chain_id: str,
        height: int,
        proof: CosmosProof,
    ) -> ProofVerificationResult:
        """
        Verify Cosmos IBC proof

        Args:
            chain_id: Cosmos chain ID
            height: Block height
            proof: IBC proof to verify

        Returns:
            Verification result
        """
        client = self.cosmos_clients.get(chain_id)
        if not client:
            return ProofVerificationResult(
                valid=False,
                message=f"No Cosmos client registered for chain {chain_id}",
                chain_type=ChainType.COSMOS,
                chain_id=chain_id,
                height=height,
                proof_type='ibc',
            )

        # Verify proof
        if client.verify_ibc_proof(height, proof):
            return ProofVerificationResult(
                valid=True,
                message=f"IBC proof verified at height {height}",
                chain_type=ChainType.COSMOS,
                chain_id=chain_id,
                height=height,
                proof_type='ibc',
            )
        else:
            return ProofVerificationResult(
                valid=False,
                message=f"IBC proof verification failed at height {height}",
                chain_type=ChainType.COSMOS,
                chain_id=chain_id,
                height=height,
                proof_type='ibc',
            )

    def get_chain_status(self, chain_id: str, chain_type: ChainType) -> Dict[str, Any]:
        """
        Get status of a registered chain

        Args:
            chain_id: Chain ID
            chain_type: Type of chain

        Returns:
            Status dictionary
        """
        if chain_type == ChainType.EVM:
            client = self.evm_clients.get(chain_id)
            if not client:
                return {'registered': False}

            latest = client.get_latest_header()
            return {
                'registered': True,
                'chain_type': 'evm',
                'chain_id': chain_id,
                'chain_name': client.config.chain_name,
                'latest_height': client.latest_verified_height,
                'finalized_height': client.finalized_height,
                'consensus_type': client.config.consensus_type.value,
                'headers_count': len(client.headers),
                'latest_header': latest.to_dict() if latest else None,
            }

        elif chain_type == ChainType.COSMOS:
            client = self.cosmos_clients.get(chain_id)
            if not client:
                return {'registered': False}

            latest = client.get_latest_trusted_state()
            return {
                'registered': True,
                'chain_type': 'cosmos',
                'chain_id': chain_id,
                'latest_height': client.latest_trusted_height,
                'trust_level': client.trust_level.name,
                'trust_period': client.trust_period_seconds,
                'trusted_states_count': len(client.trusted_states),
                'latest_header': latest.header.to_dict() if latest else None,
            }

        return {'registered': False}

    def list_registered_chains(self) -> Dict[str, Any]:
        """
        List all registered chains

        Returns:
            Dictionary with EVM and Cosmos chain lists
        """
        return {
            'evm_chains': [
                {
                    'chain_id': chain_id,
                    'chain_name': client.config.chain_name,
                    'latest_height': client.latest_verified_height,
                }
                for chain_id, client in self.evm_clients.items()
            ],
            'cosmos_chains': [
                {
                    'chain_id': chain_id,
                    'latest_height': client.latest_trusted_height,
                }
                for chain_id, client in self.cosmos_clients.items()
            ],
        }

    def export_state(self) -> Dict[str, Any]:
        """
        Export state of all light clients for persistence

        Returns:
            Serializable state dictionary
        """
        return {
            'evm_chains': {
                chain_id: {
                    'config': {
                        'chain_id': client.config.chain_id,
                        'chain_name': client.config.chain_name,
                        'consensus_type': client.config.consensus_type.value,
                    },
                    'headers': client.export_headers(),
                    'latest_height': client.latest_verified_height,
                    'finalized_height': client.finalized_height,
                }
                for chain_id, client in self.evm_clients.items()
            },
            'cosmos_chains': {
                chain_id: {
                    'chain_id': client.chain_id,
                    'trust_level': client.trust_level.name,
                    'trusted_states': client.export_trusted_states(),
                    'latest_height': client.latest_trusted_height,
                }
                for chain_id, client in self.cosmos_clients.items()
            },
        }

    def clear_cache(self) -> None:
        """Clear verification cache"""
        self.verification_cache.clear()
        logger.info("Verification cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = int(time.time())
        valid_entries = sum(
            1 for result in self.verification_cache.values()
            if now - result.verified_at < self.cache_ttl
        )

        return {
            'total_entries': len(self.verification_cache),
            'valid_entries': valid_entries,
            'ttl_seconds': self.cache_ttl,
        }
