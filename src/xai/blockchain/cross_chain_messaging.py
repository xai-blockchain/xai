from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from xai.blockchain.merkle import MerkleTree

logger = logging.getLogger("xai.blockchain.cross_chain_messaging")

class CrossChainMessage:
    def __init__(
        self,
        origin_chain_id: str,
        destination_chain_id: str,
        sender_address: str,
        recipient_address: str,
        payload: dict[str, Any],
        sequence_number: int,
        merkle_proof: list[tuple[str, str]] | None = None,
    ):
        if not origin_chain_id or not destination_chain_id:
            raise ValueError("Origin and destination chain IDs cannot be empty.")
        if not sender_address or not recipient_address:
            raise ValueError("Sender and recipient addresses cannot be empty.")
        if not payload:
            raise ValueError("Message payload cannot be empty.")
        if not isinstance(sequence_number, int) or sequence_number <= 0:
            raise ValueError("Sequence number must be a positive integer.")

        self.origin_chain_id = origin_chain_id
        self.destination_chain_id = destination_chain_id
        self.sender_address = sender_address
        self.recipient_address = recipient_address
        self.payload = payload
        self.sequence_number = sequence_number
        self.merkle_proof = merkle_proof  # Proof of inclusion on origin chain

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_chain_id": self.origin_chain_id,
            "destination_chain_id": self.destination_chain_id,
            "sender_address": self.sender_address,
            "recipient_address": self.recipient_address,
            "payload": self.payload,
            "sequence_number": self.sequence_number,
            # Merkle proof is not part of the message content for hashing, but attached for verification
        }

    def get_message_hash(self) -> str:
        """Generates a consistent hash of the message content for Merkle tree inclusion."""
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()

    def __repr__(self):
        return (
            f"CrossChainMessage(from='{self.origin_chain_id}', to='{self.destination_chain_id}', "
            f"seq={self.sequence_number}, payload={self.payload})"
        )

class CrossChainMessageVerifier:
    def __init__(self):
        self.logger = logger

    def verify_message(self, message: CrossChainMessage, origin_chain_merkle_root: str) -> bool:
        """
        Verifies a cross-chain message using its attached Merkle proof against the
        known Merkle root of the origin chain.
        """
        if not origin_chain_merkle_root:
            raise ValueError("Origin chain Merkle root is required for verification.")

        if not message.merkle_proof:
            self.logger.error(
                "Cross-chain message %s on %s has no Merkle proof attached.",
                message.sequence_number,
                message.origin_chain_id,
            )
            return False

        is_valid = MerkleTree.verify_merkle_proof(
            message.to_dict(), origin_chain_merkle_root, message.merkle_proof
        )

        if is_valid:
            self.logger.info(
                "Cross-chain message %s from %s verified against root %s",
                message.sequence_number,
                message.origin_chain_id,
                origin_chain_merkle_root,
            )
        else:
            self.logger.warning(
                "Cross-chain message %s from %s failed verification",
                message.sequence_number,
                message.origin_chain_id,
            )

        return is_valid
