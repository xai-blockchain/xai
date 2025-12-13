"""
AXN Blockchain Core - Production Implementation
Real cryptocurrency blockchain with transactions, mining, and consensus
"""

from __future__ import annotations

import hashlib
import json
import time
import os
import copy
from typing import List, Dict, Optional, Tuple, Any, Union
from datetime import datetime
import base58
from xai.core.config import Config
from xai.core.gamification import (
    AirdropManager,
    StreakTracker,
    TreasureHuntManager,
    FeeRefundCalculator,
    TimeCapsuleManager,
)
from xai.core.nonce_tracker import NonceTracker
from xai.core.wallet_trade_manager_impl import WalletTradeManager
from xai.core.trading import SwapOrderType
from xai.core.blockchain_storage import BlockchainStorage
from xai.core.transaction_validator import TransactionValidator
from xai.core.utxo_manager import UTXOManager
from xai.core.crypto_utils import sign_message_hex, verify_signature_hex
from xai.core.vm.manager import SmartContractManager
from xai.core.governance_execution import GovernanceExecutionEngine
from xai.core.governance_transactions import GovernanceState, GovernanceTxType, GovernanceTransaction
from xai.core.checkpoints import CheckpointManager
from collections import defaultdict
from xai.core.structured_logger import StructuredLogger, get_structured_logger


def canonical_json(data: Dict[str, Any]) -> str:
    """Produce deterministic JSON string for consensus-critical hashing.

    Uses canonical serialization to ensure identical hashes across all nodes:
    - sort_keys=True: Consistent key ordering
    - separators=(',', ':'): No whitespace variations
    - ensure_ascii=True: No unicode encoding variations

    Args:
        data: Dictionary to serialize

    Returns:
        Canonical JSON string suitable for hashing
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True
    )


class BlockHeader:
    """
    Represents the header of a block.
    """

    def __init__(
        self,
        index: int,
        previous_hash: str,
        merkle_root: str,
        timestamp: float,
        difficulty: int,
        nonce: int,
        signature: Optional[str] = None,
        miner_pubkey: Optional[str] = None,
        version: Optional[int] = None,
    ) -> None:
        # Validate and coerce index
        if index is None:
            raise ValueError("Block index cannot be None")
        try:
            # Coerce float to int
            coerced_index = int(index)
            if isinstance(index, float) and index != coerced_index:
                # Truncate float to int (1.5 -> 1)
                self.index = coerced_index
            else:
                self.index = coerced_index
        except (ValueError, TypeError) as e:
            raise TypeError(f"Block index must be a valid integer: {e}") from e

        # Validate index range
        if self.index < 0:
            raise ValueError("Block index cannot be negative")

        # Validate previous_hash
        if previous_hash is None:
            raise ValueError("Previous hash cannot be None")
        if not isinstance(previous_hash, str):
            raise TypeError("Previous hash must be a string")
        if len(previous_hash) == 0:
            raise ValueError("Previous hash cannot be empty")
        # Validate hash format (must be hex and proper length)
        if len(previous_hash) != 64:
            raise ValueError(f"Previous hash must be 64 characters (got {len(previous_hash)})")
        # Validate hex characters only
        try:
            int(previous_hash, 16)
        except ValueError as e:
            raise ValueError(f"Previous hash must be a valid hexadecimal string: {e}") from e
        # Check for null bytes
        if '\x00' in previous_hash:
            raise ValueError("Previous hash cannot contain null bytes")
        # Check for non-ASCII characters
        if not previous_hash.isascii():
            raise ValueError("Previous hash must contain only ASCII characters")
        self.previous_hash = previous_hash

        # Validate merkle_root
        if merkle_root is None:
            raise ValueError("Merkle root cannot be None")
        if not isinstance(merkle_root, str):
            raise TypeError("Merkle root must be a string")
        if len(merkle_root) != 64:
            raise ValueError(f"Merkle root must be 64 characters (got {len(merkle_root)})")
        # Validate hex format
        try:
            int(merkle_root, 16)
        except ValueError as e:
            raise ValueError(f"Merkle root must be a valid hexadecimal string: {e}") from e
        # Check for null bytes
        if '\x00' in merkle_root:
            raise ValueError("Merkle root cannot contain null bytes")
        # Check for non-ASCII characters
        if not merkle_root.isascii():
            raise ValueError("Merkle root must contain only ASCII characters")
        self.merkle_root = merkle_root

        # Validate timestamp
        if timestamp is None:
            raise ValueError("Timestamp cannot be None")
        try:
            self.timestamp = float(timestamp)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Timestamp must be a valid float: {e}") from e

        # Validate timestamp is not NaN
        if self.timestamp != self.timestamp:  # NaN != NaN is True
            raise ValueError("Timestamp cannot be NaN")

        # Validate timestamp is not infinity
        if self.timestamp == float('inf') or self.timestamp == float('-inf'):
            raise ValueError("Timestamp cannot be infinity")

        # Validate timestamp doesn't cause overflow when converting to time_t
        # Maximum safe timestamp is around 253402300799 (year 9999)
        # We'll use a more conservative limit that works across platforms
        MAX_SAFE_TIMESTAMP = 253402300799.0  # 9999-12-31 23:59:59 UTC
        if self.timestamp > MAX_SAFE_TIMESTAMP:
            raise OverflowError(f"Timestamp {self.timestamp} exceeds maximum safe value {MAX_SAFE_TIMESTAMP}")

        # Validate timestamp is not negative (except 0 is allowed for edge cases)
        # Note: We don't enforce > 0 here because blockchain validation will handle it
        # This allows BlockHeader construction for testing purposes

        # Validate and coerce difficulty
        if difficulty is None:
            raise ValueError("Difficulty cannot be None")
        try:
            self.difficulty = int(difficulty)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Difficulty must be a valid integer: {e}") from e
        if self.difficulty < 0:
            raise ValueError("Difficulty cannot be negative")

        # Validate and coerce nonce
        if nonce is None:
            raise ValueError("Nonce cannot be None")
        try:
            self.nonce = int(nonce)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Nonce must be a valid integer: {e}") from e
        if self.nonce < 0:
            raise ValueError("Nonce cannot be negative")

        self.signature = signature
        self.miner_pubkey = miner_pubkey
        if version is None:
            self.version = Config.BLOCK_HEADER_VERSION
            self._hash_includes_version = False
        else:
            self.version = int(version)
            self._hash_includes_version = True
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate block hash using canonical JSON serialization"""
        header_data = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
        }
        if self._hash_includes_version:
            header_data["version"] = self.version
        header_string = canonical_json(header_data)
        return hashlib.sha256(header_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        payload = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "signature": self.signature,
            "miner_pubkey": self.miner_pubkey,
            "hash": self.hash,
        }
        if self._hash_includes_version:
            payload["version"] = self.version
        return payload
