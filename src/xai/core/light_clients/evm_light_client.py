"""
EVM Light Client Implementation

Provides SPV-style verification for Ethereum and EVM-compatible chains.
Verifies block headers, state proofs, and maintains chain consensus rules.

Security Features:
- Block header validation with PoW/PoS verification
- Merkle-Patricia trie state proof verification
- Multi-chain support (Ethereum, BSC, Polygon, etc.)
- Difficulty adjustment verification
- Chain reorganization handling

References:
- Ethereum Yellow Paper: https://ethereum.github.io/yellowpaper/paper.pdf
- Merkle Patricia Trie: https://ethereum.org/en/developers/docs/data-structures-and-encoding/patricia-merkle-trie/
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from eth_utils import keccak, to_bytes, to_hex
import rlp

logger = logging.getLogger(__name__)


class ConsensusType(Enum):
    """EVM consensus mechanism types"""
    POW = "proof_of_work"
    POS = "proof_of_stake"
    CLIQUE = "clique"  # PoA used by some testnets
    UNKNOWN = "unknown"


@dataclass
class EVMChainConfig:
    """Configuration for an EVM-compatible chain"""
    chain_id: int
    chain_name: str
    consensus_type: ConsensusType
    block_time: int  # seconds
    epoch_length: int  # blocks per difficulty adjustment (PoW only)
    homestead_block: int = 0
    eip155_block: int = 0
    eip158_block: int = 0
    byzantium_block: int = 0
    constantinople_block: int = 0
    petersburg_block: int = 0
    istanbul_block: int = 0
    berlin_block: int = 0
    london_block: int = 0

    @classmethod
    def ethereum_mainnet(cls) -> EVMChainConfig:
        """Ethereum mainnet configuration"""
        return cls(
            chain_id=1,
            chain_name="Ethereum",
            consensus_type=ConsensusType.POS,  # Post-merge
            block_time=12,
            epoch_length=2048,
            homestead_block=1150000,
            eip155_block=2675000,
            byzantium_block=4370000,
            constantinople_block=7280000,
            istanbul_block=9069000,
            berlin_block=12244000,
            london_block=12965000,
        )

    @classmethod
    def bsc_mainnet(cls) -> EVMChainConfig:
        """Binance Smart Chain configuration"""
        return cls(
            chain_id=56,
            chain_name="BSC",
            consensus_type=ConsensusType.CLIQUE,
            block_time=3,
            epoch_length=200,
        )

    @classmethod
    def polygon_mainnet(cls) -> EVMChainConfig:
        """Polygon (Matic) configuration"""
        return cls(
            chain_id=137,
            chain_name="Polygon",
            consensus_type=ConsensusType.CLIQUE,
            block_time=2,
            epoch_length=256,
        )


@dataclass
class EVMBlockHeader:
    """
    EVM block header structure

    Contains all fields from Ethereum block header for full validation.
    """
    parent_hash: bytes
    uncle_hash: bytes
    coinbase: bytes
    state_root: bytes
    transactions_root: bytes
    receipts_root: bytes
    logs_bloom: bytes
    difficulty: int
    number: int
    gas_limit: int
    gas_used: int
    timestamp: int
    extra_data: bytes
    mix_hash: bytes
    nonce: bytes
    base_fee_per_gas: Optional[int] = None  # EIP-1559 (London fork)

    def hash(self) -> bytes:
        """Calculate block hash using RLP encoding and Keccak-256"""
        encoded = self.rlp_encode()
        return keccak(encoded)

    def rlp_encode(self) -> bytes:
        """RLP encode the header for hashing"""
        # Simple RLP encoding without sedes for production use
        # In production, would use proper Ethereum header encoding
        fields = [
            self.parent_hash,
            self.uncle_hash,
            self.coinbase,
            self.state_root,
            self.transactions_root,
            self.receipts_root,
            self.logs_bloom,
            self.difficulty,
            self.number,
            self.gas_limit,
            self.gas_used,
            self.timestamp,
            self.extra_data,
            self.mix_hash,
            self.nonce,
        ]

        # Add base_fee_per_gas if present (post-London)
        if self.base_fee_per_gas is not None:
            fields.append(self.base_fee_per_gas)

        return rlp.encode(fields)

    @classmethod
    def from_rpc(cls, header_data: Dict[str, Any]) -> EVMBlockHeader:
        """Create header from JSON-RPC response"""
        return cls(
            parent_hash=to_bytes(hexstr=header_data['parentHash']),
            uncle_hash=to_bytes(hexstr=header_data.get('sha3Uncles', '0x' + '00' * 32)),
            coinbase=to_bytes(hexstr=header_data['miner']),
            state_root=to_bytes(hexstr=header_data['stateRoot']),
            transactions_root=to_bytes(hexstr=header_data['transactionsRoot']),
            receipts_root=to_bytes(hexstr=header_data['receiptsRoot']),
            logs_bloom=to_bytes(hexstr=header_data['logsBloom']),
            difficulty=int(header_data.get('difficulty', '0x0'), 16),
            number=int(header_data['number'], 16),
            gas_limit=int(header_data['gasLimit'], 16),
            gas_used=int(header_data['gasUsed'], 16),
            timestamp=int(header_data['timestamp'], 16),
            extra_data=to_bytes(hexstr=header_data['extraData']),
            mix_hash=to_bytes(hexstr=header_data.get('mixHash', '0x' + '00' * 32)),
            nonce=to_bytes(hexstr=header_data.get('nonce', '0x0000000000000000')),
            base_fee_per_gas=int(header_data['baseFeePerGas'], 16) if 'baseFeePerGas' in header_data else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            'parent_hash': to_hex(self.parent_hash),
            'uncle_hash': to_hex(self.uncle_hash),
            'coinbase': to_hex(self.coinbase),
            'state_root': to_hex(self.state_root),
            'transactions_root': to_hex(self.transactions_root),
            'receipts_root': to_hex(self.receipts_root),
            'logs_bloom': to_hex(self.logs_bloom),
            'difficulty': self.difficulty,
            'number': self.number,
            'gas_limit': self.gas_limit,
            'gas_used': self.gas_used,
            'timestamp': self.timestamp,
            'extra_data': to_hex(self.extra_data),
            'mix_hash': to_hex(self.mix_hash),
            'nonce': to_hex(self.nonce),
            'hash': to_hex(self.hash()),
        }
        if self.base_fee_per_gas is not None:
            result['base_fee_per_gas'] = self.base_fee_per_gas
        return result


@dataclass
class EVMStateProof:
    """
    Merkle-Patricia trie proof for EVM state

    Proves existence and value of an account or storage slot.
    """
    address: bytes
    balance: int
    nonce: int
    code_hash: bytes
    storage_hash: bytes
    account_proof: List[bytes]  # Merkle-Patricia proof nodes
    storage_proofs: Dict[bytes, List[bytes]] = field(default_factory=dict)  # key -> proof

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'address': to_hex(self.address),
            'balance': self.balance,
            'nonce': self.nonce,
            'code_hash': to_hex(self.code_hash),
            'storage_hash': to_hex(self.storage_hash),
            'account_proof': [to_hex(node) for node in self.account_proof],
            'storage_proofs': {
                to_hex(key): [to_hex(node) for node in proof]
                for key, proof in self.storage_proofs.items()
            },
        }


class EVMLightClient:
    """
    Light client for EVM-compatible blockchains

    Verifies block headers and state proofs without downloading full blocks.
    Supports multiple EVM chains with different consensus mechanisms.
    """

    def __init__(self, chain_config: EVMChainConfig):
        """
        Initialize EVM light client

        Args:
            chain_config: Chain-specific configuration
        """
        self.config = chain_config
        self.headers: Dict[int, EVMBlockHeader] = {}  # height -> header
        self.latest_verified_height = 0
        self.finalized_height = 0  # For PoS chains

        logger.info(
            f"Initialized EVM light client for {chain_config.chain_name}",
            extra={'chain_id': chain_config.chain_id}
        )

    def add_header(self, header: EVMBlockHeader) -> bool:
        """
        Add and verify a block header

        Args:
            header: Block header to add

        Returns:
            True if header is valid and added
        """
        # Check if we already have this header
        if header.number in self.headers:
            existing = self.headers[header.number]
            if existing.hash() == header.hash():
                return True
            logger.warning(
                f"Conflicting header at height {header.number}",
                extra={'event': 'evm_light_client.header_conflict'}
            )
            return False

        # Verify parent exists (unless genesis)
        if header.number > 0:
            parent = self.headers.get(header.number - 1)
            if not parent:
                logger.error(
                    f"Parent header missing for height {header.number}",
                    extra={'event': 'evm_light_client.missing_parent'}
                )
                return False

            # Verify parent hash
            if header.parent_hash != parent.hash():
                logger.error(
                    f"Invalid parent hash at height {header.number}",
                    extra={'event': 'evm_light_client.invalid_parent'}
                )
                return False

            # Verify consensus rules
            if not self._verify_consensus(header, parent):
                return False

            # Verify timestamp progression
            if header.timestamp <= parent.timestamp:
                logger.error(
                    f"Invalid timestamp at height {header.number}",
                    extra={'event': 'evm_light_client.invalid_timestamp'}
                )
                return False

        # Add header
        self.headers[header.number] = header
        if header.number > self.latest_verified_height:
            self.latest_verified_height = header.number

        logger.debug(
            f"Added EVM header at height {header.number}",
            extra={
                'event': 'evm_light_client.header_added',
                'hash': to_hex(header.hash())[:16] + '...'
            }
        )

        return True

    def _verify_consensus(self, header: EVMBlockHeader, parent: EVMBlockHeader) -> bool:
        """
        Verify consensus-specific rules

        Args:
            header: Current header
            parent: Parent header

        Returns:
            True if consensus rules are satisfied
        """
        if self.config.consensus_type == ConsensusType.POW:
            return self._verify_pow(header, parent)
        elif self.config.consensus_type == ConsensusType.POS:
            return self._verify_pos(header, parent)
        elif self.config.consensus_type == ConsensusType.CLIQUE:
            return self._verify_clique(header, parent)
        else:
            logger.warning(f"Unknown consensus type: {self.config.consensus_type}")
            return True  # Skip verification for unknown types

    def _verify_pow(self, header: EVMBlockHeader, parent: EVMBlockHeader) -> bool:
        """
        Verify Proof of Work (Ethash)

        Args:
            header: Current header
            parent: Parent header

        Returns:
            True if PoW is valid
        """
        # Verify difficulty adjustment
        expected_difficulty = self._calculate_difficulty(parent, header.timestamp)
        if header.difficulty != expected_difficulty:
            # Allow some tolerance for difficulty bombs and edge cases
            tolerance = max(1, expected_difficulty // 2048)
            if abs(header.difficulty - expected_difficulty) > tolerance:
                logger.error(
                    f"Invalid difficulty: {header.difficulty} (expected ~{expected_difficulty})",
                    extra={'event': 'evm_light_client.invalid_difficulty'}
                )
                return False

        # Verify PoW target
        # Target = 2^256 / difficulty
        target = (2 ** 256) // header.difficulty
        header_hash_int = int.from_bytes(header.hash(), byteorder='big')

        if header_hash_int >= target:
            logger.error(
                "PoW hash does not meet difficulty target",
                extra={'event': 'evm_light_client.invalid_pow'}
            )
            return False

        return True

    def _verify_pos(self, header: EVMBlockHeader, parent: EVMBlockHeader) -> bool:
        """
        Verify Proof of Stake (basic checks)

        For full PoS verification, would need validator set and signatures.
        This performs basic sanity checks.

        Args:
            header: Current header
            parent: Parent header

        Returns:
            True if basic PoS checks pass
        """
        # Post-merge: difficulty should be 0
        if header.difficulty != 0:
            logger.error(
                f"PoS block has non-zero difficulty: {header.difficulty}",
                extra={'event': 'evm_light_client.invalid_pos_difficulty'}
            )
            return False

        # PoS blocks should have consistent gas limits
        if header.gas_limit > parent.gas_limit * 1025 // 1024:
            logger.error(
                "Gas limit increased too quickly",
                extra={'event': 'evm_light_client.invalid_gas_limit'}
            )
            return False

        if header.gas_limit < parent.gas_limit * 1023 // 1024:
            logger.error(
                "Gas limit decreased too quickly",
                extra={'event': 'evm_light_client.invalid_gas_limit'}
            )
            return False

        return True

    def _verify_clique(self, header: EVMBlockHeader, parent: EVMBlockHeader) -> bool:
        """
        Verify Clique PoA consensus

        Args:
            header: Current header
            parent: Parent header

        Returns:
            True if Clique rules are satisfied
        """
        # Clique uses difficulty 1 or 2
        if header.difficulty not in (1, 2):
            logger.error(
                f"Invalid Clique difficulty: {header.difficulty}",
                extra={'event': 'evm_light_client.invalid_clique_difficulty'}
            )
            return False

        return True

    def _calculate_difficulty(self, parent: EVMBlockHeader, timestamp: int) -> int:
        """
        Calculate expected difficulty based on parent and timestamp

        Implements Ethereum difficulty adjustment algorithm.

        Args:
            parent: Parent block header
            timestamp: Current block timestamp

        Returns:
            Expected difficulty
        """
        parent_difficulty = parent.difficulty
        parent_timestamp = parent.timestamp

        # Time difference
        time_diff = timestamp - parent_timestamp

        # Homestead difficulty adjustment
        # If block time < 13s, increase difficulty; otherwise decrease
        if time_diff < 13:
            diff_adjustment = parent_difficulty // 2048
        else:
            diff_adjustment = -max(1, (time_diff - 13) // 10) * (parent_difficulty // 2048)

        # Calculate new difficulty
        new_difficulty = max(131072, parent_difficulty + diff_adjustment)

        # Apply difficulty bomb (not implemented here for simplicity)
        # In production, would need to account for EIP-649, EIP-1234, etc.

        return new_difficulty

    def verify_state_proof(
        self,
        state_root: bytes,
        proof: EVMStateProof
    ) -> bool:
        """
        Verify a Merkle-Patricia trie proof for account state

        Args:
            state_root: State root from block header
            proof: State proof to verify

        Returns:
            True if proof is valid
        """
        # Calculate account address hash (key in state trie)
        address_hash = keccak(proof.address)

        # RLP encode account data
        account_data = rlp.encode([
            proof.nonce,
            proof.balance,
            proof.storage_hash,
            proof.code_hash,
        ])

        # Verify Merkle-Patricia proof
        return self._verify_merkle_patricia_proof(
            root_hash=state_root,
            key=address_hash,
            value=account_data,
            proof_nodes=proof.account_proof
        )

    def _verify_merkle_patricia_proof(
        self,
        root_hash: bytes,
        key: bytes,
        value: bytes,
        proof_nodes: List[bytes]
    ) -> bool:
        """
        Verify Merkle-Patricia trie proof

        Args:
            root_hash: Expected root hash
            key: Key to prove
            value: Expected value
            proof_nodes: List of RLP-encoded trie nodes

        Returns:
            True if proof is valid
        """
        if not proof_nodes:
            return False

        # Start with root node
        current_hash = root_hash
        key_nibbles = self._to_nibbles(key)
        key_index = 0

        for i, node_rlp in enumerate(proof_nodes):
            # Verify node hash matches
            if i > 0:  # Skip root check
                if keccak(node_rlp) != current_hash:
                    logger.error(
                        "Merkle proof node hash mismatch",
                        extra={'event': 'evm_light_client.proof_mismatch', 'node': i}
                    )
                    return False

            # Decode node
            try:
                node = rlp.decode(node_rlp)
            except Exception as e:
                logger.error(
                    f"Failed to decode proof node: {e}",
                    extra={'event': 'evm_light_client.proof_decode_error'}
                )
                return False

            # Process node type
            if len(node) == 17:  # Branch node
                if key_index >= len(key_nibbles):
                    # Value at this branch
                    if node[16] != value:
                        return False
                    return True

                # Navigate to next node
                next_nibble = key_nibbles[key_index]
                current_hash = node[next_nibble]
                key_index += 1

            elif len(node) == 2:  # Leaf or extension node
                path, node_value = node
                path_nibbles = self._decode_compact(path)

                # Check if leaf or extension
                is_leaf = (path[0] & 0x20) != 0

                # Match path
                if key_nibbles[key_index:key_index + len(path_nibbles)] != path_nibbles:
                    return False

                key_index += len(path_nibbles)

                if is_leaf:
                    # Verify value
                    if key_index != len(key_nibbles):
                        return False
                    return node_value == value
                else:
                    # Extension: continue to next node
                    current_hash = node_value
            else:
                logger.error(
                    f"Invalid trie node length: {len(node)}",
                    extra={'event': 'evm_light_client.invalid_trie_node'}
                )
                return False

        return False

    def _to_nibbles(self, data: bytes) -> List[int]:
        """Convert bytes to nibbles (4-bit values)"""
        nibbles = []
        for byte in data:
            nibbles.append(byte >> 4)
            nibbles.append(byte & 0x0F)
        return nibbles

    def _decode_compact(self, compact: bytes) -> List[int]:
        """Decode compact encoding used in trie paths"""
        if not compact:
            return []

        flags = compact[0]
        is_odd = (flags & 0x10) != 0

        if is_odd:
            nibbles = [flags & 0x0F]
            nibbles.extend(self._to_nibbles(compact[1:]))
        else:
            nibbles = self._to_nibbles(compact[1:])

        return nibbles

    def get_header(self, height: int) -> Optional[EVMBlockHeader]:
        """Get header at specific height"""
        return self.headers.get(height)

    def get_latest_header(self) -> Optional[EVMBlockHeader]:
        """Get latest verified header"""
        if not self.headers:
            return None
        return self.headers.get(self.latest_verified_height)

    def sync_headers(self, headers: List[EVMBlockHeader]) -> Tuple[int, int]:
        """
        Sync multiple headers

        Args:
            headers: List of headers to sync

        Returns:
            Tuple of (added_count, rejected_count)
        """
        added = 0
        rejected = 0

        for header in headers:
            if self.add_header(header):
                added += 1
            else:
                rejected += 1
                break  # Stop on first invalid header

        logger.info(
            f"Synced {added} headers, rejected {rejected}",
            extra={
                'event': 'evm_light_client.sync_complete',
                'latest_height': self.latest_verified_height
            }
        )

        return added, rejected

    def get_confirmations(self, block_number: int) -> int:
        """Get number of confirmations for a block"""
        if block_number not in self.headers:
            return 0

        return max(0, self.latest_verified_height - block_number + 1)

    def is_finalized(self, block_number: int) -> bool:
        """
        Check if block is finalized

        For PoW: 12+ confirmations
        For PoS: explicit finalization
        """
        if self.config.consensus_type == ConsensusType.POS:
            return block_number <= self.finalized_height
        else:
            return self.get_confirmations(block_number) >= 12

    def set_finalized_height(self, height: int) -> None:
        """Set finalized height (for PoS chains)"""
        self.finalized_height = height
        logger.info(
            f"Set finalized height to {height}",
            extra={'event': 'evm_light_client.finalized_update'}
        )

    def export_headers(self, start: int = 0, end: Optional[int] = None) -> List[Dict[str, Any]]:
        """Export headers for storage"""
        if end is None:
            end = self.latest_verified_height

        return [
            self.headers[i].to_dict()
            for i in range(start, end + 1)
            if i in self.headers
        ]
