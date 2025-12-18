"""
Light Client API Routes

Provides REST API endpoints for cross-chain light client verification.
Supports EVM and Cosmos chain verification with proof validation.

Endpoints:
- GET /api/v1/light/chains - List registered chains
- GET /api/v1/light/evm/{chain}/header/{height} - Get EVM header
- GET /api/v1/light/cosmos/{chain}/header/{height} - Get Cosmos header
- POST /api/v1/light/verify-proof - Verify cross-chain proof
- GET /api/v1/light/status/{chain_type}/{chain} - Get chain status
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, Tuple

from flask import jsonify, request
import logging
import base64

from xai.core.light_clients.manager import (
    LightClientManager,
    ChainType,
)
from xai.core.light_clients.evm_light_client import (
    EVMBlockHeader,
    EVMStateProof,
)
from xai.core.light_clients.cosmos_light_client import (
    CosmosBlockHeader,
    CosmosValidatorSet,
    CosmosProof,
    CosmosCommit,
)

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPI

logger = logging.getLogger(__name__)


def register_light_client_routes(node_api: 'NodeAPI') -> None:
    """
    Register light client API routes.

    Args:
        node_api: NodeAPI instance
    """
    # Initialize light client manager if not already present
    if not hasattr(node_api.node, 'light_client_manager'):
        node_api.node.light_client_manager = LightClientManager()
        logger.info("Light client manager initialized")

    @node_api.app.route("/api/v1/light/chains", methods=["GET"])
    def list_chains() -> Tuple[Dict[str, Any], int]:
        """
        List all registered light client chains.

        Returns:
            JSON response with EVM and Cosmos chain lists
        """
        try:
            manager: LightClientManager = node_api.node.light_client_manager
            chains = manager.list_registered_chains()

            return jsonify({
                'success': True,
                'chains': chains,
            }), 200

        except Exception as e:
            logger.error(f"Error listing chains: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500

    @node_api.app.route("/api/v1/light/evm/<chain_id>/header/<int:height>", methods=["GET"])
    def get_evm_header(chain_id: str, height: int) -> Tuple[Dict[str, Any], int]:
        """
        Get EVM block header at specific height.

        Args:
            chain_id: EVM chain ID
            height: Block height

        Returns:
            JSON response with header data
        """
        try:
            manager: LightClientManager = node_api.node.light_client_manager
            client = manager.get_evm_client(chain_id)

            if not client:
                return jsonify({
                    'success': False,
                    'error': f'Chain {chain_id} not registered',
                }), 404

            header = client.get_header(height)
            if not header:
                return jsonify({
                    'success': False,
                    'error': f'Header not found at height {height}',
                }), 404

            return jsonify({
                'success': True,
                'header': header.to_dict(),
                'confirmations': client.get_confirmations(height),
                'finalized': client.is_finalized(height),
            }), 200

        except Exception as e:
            logger.error(f"Error getting EVM header: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500

    @node_api.app.route("/api/v1/light/cosmos/<chain_id>/header/<int:height>", methods=["GET"])
    def get_cosmos_header(chain_id: str, height: int) -> Tuple[Dict[str, Any], int]:
        """
        Get Cosmos block header at specific height.

        Args:
            chain_id: Cosmos chain ID
            height: Block height

        Returns:
            JSON response with header data
        """
        try:
            manager: LightClientManager = node_api.node.light_client_manager
            client = manager.get_cosmos_client(chain_id)

            if not client:
                return jsonify({
                    'success': False,
                    'error': f'Chain {chain_id} not registered',
                }), 404

            trusted_state = client.get_trusted_state(height)
            if not trusted_state:
                return jsonify({
                    'success': False,
                    'error': f'No trusted state at height {height}',
                }), 404

            return jsonify({
                'success': True,
                'header': trusted_state.header.to_dict(),
                'validator_set': trusted_state.validator_set.to_dict(),
                'next_validator_set': trusted_state.next_validator_set.to_dict(),
                'trusted_at': trusted_state.trusted_at,
                'within_trust_period': trusted_state.is_within_trust_period(
                    client.trust_period_seconds
                ),
            }), 200

        except Exception as e:
            logger.error(f"Error getting Cosmos header: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500

    @node_api.app.route("/api/v1/light/verify-proof", methods=["POST"])
    def verify_proof() -> Tuple[Dict[str, Any], int]:
        """
        Verify a cross-chain proof.

        Request body:
        {
            "chain_type": "evm" | "cosmos",
            "chain_id": "1" | "cosmoshub-4",
            "proof_type": "header" | "state" | "ibc",
            "height": 12345,
            "proof_data": { ... }
        }

        Returns:
            JSON response with verification result
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No JSON data provided',
                }), 400

            # Extract parameters
            chain_type_str = data.get('chain_type', '').lower()
            chain_id = str(data.get('chain_id', ''))
            proof_type = data.get('proof_type', '').lower()
            height = data.get('height', 0)
            proof_data = data.get('proof_data', {})

            # Validate parameters
            if not chain_id:
                return jsonify({
                    'success': False,
                    'error': 'chain_id is required',
                }), 400

            if not height:
                return jsonify({
                    'success': False,
                    'error': 'height is required',
                }), 400

            manager: LightClientManager = node_api.node.light_client_manager

            # EVM proof verification
            if chain_type_str == 'evm':
                if proof_type == 'header':
                    # Reconstruct header from proof data
                    header = _parse_evm_header(proof_data)
                    result = manager.verify_evm_header(chain_id, header)

                elif proof_type == 'state':
                    # Reconstruct state proof
                    proof = _parse_evm_state_proof(proof_data)
                    result = manager.verify_evm_state_proof(chain_id, height, proof)

                else:
                    return jsonify({
                        'success': False,
                        'error': f'Unknown EVM proof type: {proof_type}',
                    }), 400

            # Cosmos proof verification
            elif chain_type_str == 'cosmos':
                if proof_type == 'header':
                    # Reconstruct header and validator sets
                    header = _parse_cosmos_header(proof_data.get('header', {}))
                    validator_set = _parse_cosmos_validator_set(
                        proof_data.get('validator_set', {})
                    )
                    next_validator_set = _parse_cosmos_validator_set(
                        proof_data.get('next_validator_set', {})
                    )
                    commit = _parse_cosmos_commit(proof_data.get('commit', {}))

                    result = manager.verify_cosmos_header(
                        chain_id, header, validator_set, next_validator_set, commit
                    )

                elif proof_type == 'ibc':
                    # Reconstruct IBC proof
                    proof = _parse_cosmos_proof(proof_data)
                    result = manager.verify_cosmos_ibc_proof(chain_id, height, proof)

                else:
                    return jsonify({
                        'success': False,
                        'error': f'Unknown Cosmos proof type: {proof_type}',
                    }), 400

            else:
                return jsonify({
                    'success': False,
                    'error': f'Unknown chain type: {chain_type_str}',
                }), 400

            # Return verification result
            return jsonify({
                'success': True,
                'verification': result.to_dict(),
            }), 200

        except Exception as e:
            logger.error(f"Error verifying proof: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500

    @node_api.app.route("/api/v1/light/status/<chain_type>/<chain_id>", methods=["GET"])
    def get_chain_status(chain_type: str, chain_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Get status of a registered chain.

        Args:
            chain_type: "evm" or "cosmos"
            chain_id: Chain identifier

        Returns:
            JSON response with chain status
        """
        try:
            manager: LightClientManager = node_api.node.light_client_manager

            # Parse chain type
            if chain_type.lower() == 'evm':
                chain_type_enum = ChainType.EVM
            elif chain_type.lower() == 'cosmos':
                chain_type_enum = ChainType.COSMOS
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unknown chain type: {chain_type}',
                }), 400

            status = manager.get_chain_status(chain_id, chain_type_enum)

            if not status.get('registered', False):
                return jsonify({
                    'success': False,
                    'error': f'Chain {chain_id} not registered',
                }), 404

            return jsonify({
                'success': True,
                'status': status,
            }), 200

        except Exception as e:
            logger.error(f"Error getting chain status: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500

    @node_api.app.route("/api/v1/light/cache/stats", methods=["GET"])
    def get_cache_stats() -> Tuple[Dict[str, Any], int]:
        """Get verification cache statistics."""
        try:
            manager: LightClientManager = node_api.node.light_client_manager
            stats = manager.get_cache_stats()

            return jsonify({
                'success': True,
                'cache': stats,
            }), 200

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500

    @node_api.app.route("/api/v1/light/cache/clear", methods=["POST"])
    def clear_cache() -> Tuple[Dict[str, Any], int]:
        """Clear verification cache."""
        try:
            manager: LightClientManager = node_api.node.light_client_manager
            manager.clear_cache()

            return jsonify({
                'success': True,
                'message': 'Cache cleared',
            }), 200

        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
            }), 500

    logger.info("Light client API routes registered")


# Helper functions for parsing proof data

def _parse_evm_header(data: Dict[str, Any]) -> EVMBlockHeader:
    """Parse EVM header from JSON data"""
    from eth_utils import to_bytes

    return EVMBlockHeader(
        parent_hash=to_bytes(hexstr=data['parent_hash']),
        uncle_hash=to_bytes(hexstr=data['uncle_hash']),
        coinbase=to_bytes(hexstr=data['coinbase']),
        state_root=to_bytes(hexstr=data['state_root']),
        transactions_root=to_bytes(hexstr=data['transactions_root']),
        receipts_root=to_bytes(hexstr=data['receipts_root']),
        logs_bloom=to_bytes(hexstr=data['logs_bloom']),
        difficulty=int(data['difficulty']),
        number=int(data['number']),
        gas_limit=int(data['gas_limit']),
        gas_used=int(data['gas_used']),
        timestamp=int(data['timestamp']),
        extra_data=to_bytes(hexstr=data['extra_data']),
        mix_hash=to_bytes(hexstr=data['mix_hash']),
        nonce=to_bytes(hexstr=data['nonce']),
        base_fee_per_gas=int(data['base_fee_per_gas']) if 'base_fee_per_gas' in data else None,
    )


def _parse_evm_state_proof(data: Dict[str, Any]) -> EVMStateProof:
    """Parse EVM state proof from JSON data"""
    from eth_utils import to_bytes

    storage_proofs = {}
    for key_hex, proof_list in data.get('storage_proofs', {}).items():
        storage_proofs[to_bytes(hexstr=key_hex)] = [
            to_bytes(hexstr=node) for node in proof_list
        ]

    return EVMStateProof(
        address=to_bytes(hexstr=data['address']),
        balance=int(data['balance']),
        nonce=int(data['nonce']),
        code_hash=to_bytes(hexstr=data['code_hash']),
        storage_hash=to_bytes(hexstr=data['storage_hash']),
        account_proof=[to_bytes(hexstr=node) for node in data['account_proof']],
        storage_proofs=storage_proofs,
    )


def _parse_cosmos_header(data: Dict[str, Any]) -> CosmosBlockHeader:
    """Parse Cosmos header from JSON data"""
    return CosmosBlockHeader.from_dict(data)


def _parse_cosmos_validator_set(data: Dict[str, Any]) -> CosmosValidatorSet:
    """Parse Cosmos validator set from JSON data"""
    return CosmosValidatorSet.from_dict(data)


def _parse_cosmos_commit(data: Dict[str, Any]) -> CosmosCommit:
    """Parse Cosmos commit from JSON data"""
    signatures = [
        (
            base64.b64decode(sig['address']),
            base64.b64decode(sig['signature']),
        )
        for sig in data.get('signatures', [])
    ]

    return CosmosCommit(
        height=data['height'],
        round=data['round'],
        block_id=base64.b64decode(data['block_id']),
        signatures=signatures,
        timestamp=data['timestamp'],
    )


def _parse_cosmos_proof(data: Dict[str, Any]) -> CosmosProof:
    """Parse Cosmos IBC proof from JSON data"""
    return CosmosProof(
        key=base64.b64decode(data['key']),
        value=base64.b64decode(data['value']),
        proof_ops=data.get('proof_ops', []),
        height=data['height'],
    )
