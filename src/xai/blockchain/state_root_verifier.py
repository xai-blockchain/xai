from __future__ import annotations

import logging
from typing import Any

from .merkle import MerkleTree  # Import MerkleTree

logger = logging.getLogger("xai.blockchain.state_root_verifier")

class StateRootVerifier:
    def __init__(self):
        # In a real system, these would be fetched from a light client or a trusted oracle
        # and would be updated regularly. For this mock, we'll pre-populate some.
        # Format: {chain_id: {block_number: state_root_hash}}
        self.trusted_state_roots: dict[str, dict[int, str]] = {
            "SourceChainA": {
                100: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
                101: "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b3",
                102: "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b4",
            },
            "SourceChainB": {
                50: "x1y2z3w4e5r6t7y8u9i0o1p2a3s4d5f6g7h8j9k0l1z2x3c4v5b6n7m8q9w0e1",
                51: "y2z3w4e5r6t7y8u9i0o1p2a3s4d5f6g7h8j9k0l1z2x3c4v5b6n7m8q9w0e2",
            },
        }

    def add_trusted_state_root(self, chain_id: str, block_number: int, state_root: str):
        """Adds a new trusted state root for a given chain and block number."""
        if chain_id not in self.trusted_state_roots:
            self.trusted_state_roots[chain_id] = {}
        self.trusted_state_roots[chain_id][block_number] = state_root
        logger.info(
            "Added trusted state root for %s at block %s: %s...",
            chain_id,
            block_number,
            state_root[:10],
        )

    def get_state_root(self, chain_id: str, block_number: int) -> str:
        """Retrieves a trusted state root for a given chain and block number."""
        chain_roots = self.trusted_state_roots.get(chain_id)
        if not chain_roots:
            raise ValueError(f"No trusted state roots found for chain ID: {chain_id}")
        state_root = chain_roots.get(block_number)
        if not state_root:
            raise ValueError(f"No trusted state root found for {chain_id} at block {block_number}")
        return state_root

    def verify_inclusion(
        self, data: Any, merkle_proof: list[tuple[str, str]], chain_id: str, block_number: int
    ) -> bool:
        """
        Verifies that a piece of data is included in the state of a source chain
        at a specific block number, using a Merkle proof and a trusted state root.
        """
        try:
            trusted_root = self.get_state_root(chain_id, block_number)
        except ValueError as e:
            logger.warning("Verification failed: %s", e)
            return False

        is_included = MerkleTree.verify_merkle_proof(data, trusted_root, merkle_proof)

        if is_included:
            logger.info(
                "Data verified for inclusion in %s at block %s.", chain_id, block_number
            )
        else:
            logger.warning(
                "Data failed verification for inclusion in %s at block %s.",
                chain_id,
                block_number,
            )

        return is_included
