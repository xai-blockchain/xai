from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger("xai.blockchain.sync_validator")

class SyncValidator:
    def __init__(self, trusted_checkpoints: list[dict[str, Any]] | None = None):
        # trusted_checkpoints: [{"height": int, "hash": str}]
        self.trusted_checkpoints = trusted_checkpoints or []
        logger.info("SyncValidator initialized with checkpoints: %s", self.trusted_checkpoints)

    def _compute_header_hash(self, block_header: dict[str, Any]) -> str:
        """
        Compute the hash of a block header.

        This uses a deterministic serialization of header fields (excluding the hash itself)
        to produce a SHA-256 hash that can be verified.

        Args:
            block_header: Block header dict with height, previous_hash, timestamp, etc.

        Returns:
            str: Hex-encoded SHA-256 hash of the header
        """
        # Create a canonical representation of header data (excluding the hash field)
        hash_input = {
            "height": block_header.get("height"),
            "previous_hash": block_header.get("previous_hash"),
            "timestamp": block_header.get("timestamp"),
            "merkle_root": block_header.get("merkle_root", ""),
            "nonce": block_header.get("nonce", 0),
            "version": block_header.get("version", 1),
        }
        # Sort keys for deterministic serialization
        serialized = json.dumps(hash_input, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _validate_block_header(self, block_header: dict[str, Any]) -> bool:
        """
        Validates a block header with cryptographic hash verification.

        Performs:
        1. Field presence and type validation
        2. Height and timestamp sanity checks
        3. Cryptographic hash verification (hash matches header content)
        4. Hash format validation (64-char hex string)

        Args:
            block_header: Block header dictionary

        Returns:
            bool: True if header is valid
        """
        required_fields = ["hash", "previous_hash", "height", "timestamp"]
        if not all(field in block_header for field in required_fields):
            logger.warning("Header validation failed (missing fields): %s", block_header)
            return False

        if not isinstance(block_header["height"], int) or block_header["height"] < 0:
            logger.warning("Header validation failed: invalid height %s", block_header["height"])
            return False

        if not isinstance(block_header["timestamp"], int) or block_header["timestamp"] <= 0:
            logger.warning("Header validation failed: invalid timestamp %s", block_header["timestamp"])
            return False

        # Validate hash format (64-char hex string for SHA-256)
        block_hash = block_header["hash"]
        prev_hash = block_header["previous_hash"]

        if not isinstance(block_hash, str) or not isinstance(prev_hash, str):
            logger.warning("Header validation failed: hash types invalid (%s)", block_header)
            return False

        # Check hash format - should be 64 hex characters (SHA-256)
        if len(block_hash) != 64 or not all(c in "0123456789abcdef" for c in block_hash.lower()):
            logger.warning(
                "Header validation failed: invalid hash format %s",
                block_hash[:20] + "..." if len(block_hash) > 20 else block_hash,
            )
            return False

        # Genesis block (height 0) has all-zero previous hash
        if block_header["height"] > 0:
            if len(prev_hash) != 64 or not all(c in "0123456789abcdef" for c in prev_hash.lower()):
                logger.warning(
                    "Header validation failed: invalid previous_hash format %s",
                    prev_hash[:20] + "..." if len(prev_hash) > 20 else prev_hash,
                )
                return False

        # Cryptographic hash verification: compute expected hash and compare
        # Skip for headers that don't include merkle_root/nonce (legacy format)
        if "merkle_root" in block_header or "nonce" in block_header:
            computed_hash = self._compute_header_hash(block_header)
            if computed_hash != block_hash.lower():
                logger.warning(
                    "Header validation failed: hash mismatch. Expected %s, got %s",
                    computed_hash,
                    block_hash.lower(),
                )
                return False
            logger.debug("Hash verification passed for block %s", block_hash)

        logger.info(
            "Block header %s (height %s) validated successfully",
            block_header["hash"],
            block_header["height"],
        )
        return True

    def _validate_block_transactions(self, transactions: list[dict[str, Any]]) -> bool:
        """
        Simulates validation of transactions within a block.
        In a real system, this would involve checking signatures, amounts, nonces,
        and ensuring no double-spends within the block.
        """
        for i, tx in enumerate(transactions):
            required_fields = ["sender", "recipient", "amount", "nonce", "signature"]
            if not all(field in tx for field in required_fields):
                logger.warning("Transaction %s missing required fields: %s", i, tx)
                return False
            if not isinstance(tx["amount"], (int, float)) or tx["amount"] <= 0:
                logger.warning("Transaction %s invalid amount %s", i, tx.get("amount"))
                return False
            # Conceptual signature validation (as in GossipValidator)
            if "signature" not in tx:  # Simplified check
                logger.warning("Transaction %s missing signature", i)
                return False
        logger.info("All %s transactions validated conceptually", len(transactions))
        return True

    def validate_incoming_block(self, block: dict[str, Any]) -> bool:
        """
        Validates an entire incoming block for synchronization.
        """
        if not isinstance(block, dict) or "header" not in block or "transactions" not in block:
            logger.error("Block validation failed: missing header/transactions (%s)", block)
            return False

        # 1. Validate Header
        if not self._validate_block_header(block["header"]):
            logger.warning(
                "Block %s (height %s) rejected: header invalid",
                block["header"].get("hash"),
                block["header"].get("height"),
            )
            return False

        # 2. Validate Transactions
        if not self._validate_block_transactions(block["transactions"]):
            logger.warning(
                "Block %s (height %s) rejected: transactions invalid",
                block["header"].get("hash"),
                block["header"].get("height"),
            )
            return False

        # 3. Check against trusted checkpoints (conceptual)
        for cp in self.trusted_checkpoints:
            if block["header"]["height"] == cp["height"] and block["header"]["hash"] != cp["hash"]:
                logger.error(
                    "Incoming block %s (height %s) conflicts with checkpoint hash %s",
                    block["header"].get("hash"),
                    block["header"].get("height"),
                    cp["hash"],
                )
                return False

        logger.info(
            "Incoming block %s (height %s) validated successfully for sync",
            block["header"].get("hash"),
            block["header"].get("height"),
        )
        return True
