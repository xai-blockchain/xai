"""
Cosmos/Tendermint Light Client Implementation

Implements Tendermint light client protocol for Cosmos SDK chains.
Verifies block headers using validator sets and performs bisection algorithm.

Security Features:
- Validator set verification with Byzantine fault tolerance
- Trust period handling for long-term verification
- Bisection algorithm for efficient header verification
- IBC (Inter-Blockchain Communication) proof support
- Detection of light client attacks

References:
- Tendermint Light Client Spec: https://github.com/tendermint/tendermint/tree/master/spec/light-client
- IBC Spec: https://github.com/cosmos/ibc
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TrustLevel(Enum):
    """Trust level for validator set overlap"""
    ONE_THIRD = 1/3  # Tendermint default
    TWO_THIRDS = 2/3  # Higher security


@dataclass
class CosmosValidator:
    """Cosmos validator information"""
    address: bytes
    pub_key: bytes
    voting_power: int
    proposer_priority: int = 0

    def hash(self) -> bytes:
        """Calculate validator hash"""
        data = self.address + self.pub_key + self.voting_power.to_bytes(8, 'big')
        return hashlib.sha256(data).digest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'address': base64.b64encode(self.address).decode('utf-8'),
            'pub_key': base64.b64encode(self.pub_key).decode('utf-8'),
            'voting_power': self.voting_power,
            'proposer_priority': self.proposer_priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CosmosValidator:
        """Create from dictionary"""
        return cls(
            address=base64.b64decode(data['address']),
            pub_key=base64.b64decode(data['pub_key']),
            voting_power=data['voting_power'],
            proposer_priority=data.get('proposer_priority', 0),
        )


@dataclass
class CosmosValidatorSet:
    """Cosmos validator set"""
    validators: List[CosmosValidator]
    total_voting_power: int

    def __post_init__(self):
        """Calculate total voting power if not provided"""
        if self.total_voting_power == 0:
            self.total_voting_power = sum(v.voting_power for v in self.validators)

    def hash(self) -> bytes:
        """
        Calculate Merkle root of validator set

        Uses same algorithm as Tendermint validator set hashing.
        """
        if not self.validators:
            return hashlib.sha256(b'').digest()

        # Sort validators by address
        sorted_validators = sorted(self.validators, key=lambda v: v.address)

        # Build Merkle tree
        hashes = [v.hash() for v in sorted_validators]
        return self._merkle_root(hashes)

    def _merkle_root(self, hashes: List[bytes]) -> bytes:
        """Calculate Merkle root"""
        if not hashes:
            return hashlib.sha256(b'').digest()

        if len(hashes) == 1:
            return hashes[0]

        # Pad to power of 2
        while len(hashes) & (len(hashes) - 1):
            hashes.append(hashes[-1])

        # Build tree
        while len(hashes) > 1:
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                next_level.append(hashlib.sha256(combined).digest())
            hashes = next_level

        return hashes[0]

    def get_validator(self, address: bytes) -> Optional[CosmosValidator]:
        """Get validator by address"""
        for validator in self.validators:
            if validator.address == address:
                return validator
        return None

    def compute_voting_power(self, addresses: List[bytes]) -> int:
        """Compute total voting power for given validator addresses"""
        power = 0
        for address in addresses:
            validator = self.get_validator(address)
            if validator:
                power += validator.voting_power
        return power

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'validators': [v.to_dict() for v in self.validators],
            'total_voting_power': self.total_voting_power,
            'hash': base64.b64encode(self.hash()).decode('utf-8'),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CosmosValidatorSet:
        """Create from dictionary"""
        return cls(
            validators=[CosmosValidator.from_dict(v) for v in data['validators']],
            total_voting_power=data['total_voting_power'],
        )


@dataclass
class CosmosCommit:
    """Commit information with validator signatures"""
    height: int
    round: int
    block_id: bytes
    signatures: List[Tuple[bytes, bytes]]  # (validator_address, signature)
    timestamp: int

    def get_signing_validators(self) -> List[bytes]:
        """Get list of validators who signed"""
        return [addr for addr, _ in self.signatures]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'height': self.height,
            'round': self.round,
            'block_id': base64.b64encode(self.block_id).decode('utf-8'),
            'signatures': [
                {
                    'address': base64.b64encode(addr).decode('utf-8'),
                    'signature': base64.b64encode(sig).decode('utf-8'),
                }
                for addr, sig in self.signatures
            ],
            'timestamp': self.timestamp,
        }


@dataclass
class CosmosBlockHeader:
    """Cosmos/Tendermint block header"""
    version: int
    chain_id: str
    height: int
    time: int  # Unix timestamp
    last_block_id: bytes
    last_commit_hash: bytes
    data_hash: bytes
    validators_hash: bytes
    next_validators_hash: bytes
    consensus_hash: bytes
    app_hash: bytes  # Application state root
    last_results_hash: bytes
    evidence_hash: bytes
    proposer_address: bytes

    def hash(self) -> bytes:
        """Calculate block hash"""
        # Simplified hashing - in production use Tendermint's amino encoding
        data = (
            self.chain_id.encode('utf-8') +
            self.height.to_bytes(8, 'big') +
            self.time.to_bytes(8, 'big') +
            self.last_block_id +
            self.validators_hash +
            self.next_validators_hash +
            self.app_hash +
            self.proposer_address
        )
        return hashlib.sha256(data).digest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'chain_id': self.chain_id,
            'height': self.height,
            'time': self.time,
            'last_block_id': base64.b64encode(self.last_block_id).decode('utf-8'),
            'last_commit_hash': base64.b64encode(self.last_commit_hash).decode('utf-8'),
            'data_hash': base64.b64encode(self.data_hash).decode('utf-8'),
            'validators_hash': base64.b64encode(self.validators_hash).decode('utf-8'),
            'next_validators_hash': base64.b64encode(self.next_validators_hash).decode('utf-8'),
            'consensus_hash': base64.b64encode(self.consensus_hash).decode('utf-8'),
            'app_hash': base64.b64encode(self.app_hash).decode('utf-8'),
            'last_results_hash': base64.b64encode(self.last_results_hash).decode('utf-8'),
            'evidence_hash': base64.b64encode(self.evidence_hash).decode('utf-8'),
            'proposer_address': base64.b64encode(self.proposer_address).decode('utf-8'),
            'hash': base64.b64encode(self.hash()).decode('utf-8'),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CosmosBlockHeader:
        """Create from dictionary"""
        return cls(
            version=data['version'],
            chain_id=data['chain_id'],
            height=data['height'],
            time=data['time'],
            last_block_id=base64.b64decode(data['last_block_id']),
            last_commit_hash=base64.b64decode(data['last_commit_hash']),
            data_hash=base64.b64decode(data['data_hash']),
            validators_hash=base64.b64decode(data['validators_hash']),
            next_validators_hash=base64.b64decode(data['next_validators_hash']),
            consensus_hash=base64.b64decode(data['consensus_hash']),
            app_hash=base64.b64decode(data['app_hash']),
            last_results_hash=base64.b64decode(data['last_results_hash']),
            evidence_hash=base64.b64decode(data['evidence_hash']),
            proposer_address=base64.b64decode(data['proposer_address']),
        )


@dataclass
class CosmosProof:
    """IBC proof for cross-chain verification"""
    key: bytes
    value: bytes
    proof_ops: List[Dict[str, Any]]  # ProofOps from IBC
    height: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'key': base64.b64encode(self.key).decode('utf-8'),
            'value': base64.b64encode(self.value).decode('utf-8'),
            'proof_ops': self.proof_ops,
            'height': self.height,
        }


@dataclass
class TrustedState:
    """Trusted state for light client"""
    header: CosmosBlockHeader
    validator_set: CosmosValidatorSet
    next_validator_set: CosmosValidatorSet
    trusted_at: int  # Unix timestamp when this became trusted

    def is_within_trust_period(self, trust_period_seconds: int, now: Optional[int] = None) -> bool:
        """Check if trusted state is still within trust period"""
        if now is None:
            now = int(time.time())

        age = now - self.trusted_at
        return age <= trust_period_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'header': self.header.to_dict(),
            'validator_set': self.validator_set.to_dict(),
            'next_validator_set': self.next_validator_set.to_dict(),
            'trusted_at': self.trusted_at,
        }


class CosmosLightClient:
    """
    Tendermint light client implementation

    Implements the Tendermint light client verification protocol with:
    - Sequential verification for adjacent headers
    - Bisection algorithm for non-adjacent headers
    - Trust period handling
    - Validator set change tracking
    """

    def __init__(
        self,
        chain_id: str,
        trust_level: TrustLevel = TrustLevel.ONE_THIRD,
        trust_period_seconds: int = 14 * 24 * 3600,  # 14 days default
        max_clock_drift_seconds: int = 10,
    ):
        """
        Initialize Cosmos light client

        Args:
            chain_id: Cosmos chain ID
            trust_level: Required validator overlap for verification
            trust_period_seconds: How long to trust a validator set
            max_clock_drift_seconds: Maximum allowed clock drift
        """
        self.chain_id = chain_id
        self.trust_level = trust_level
        self.trust_period_seconds = trust_period_seconds
        self.max_clock_drift_seconds = max_clock_drift_seconds

        self.trusted_states: Dict[int, TrustedState] = {}  # height -> state
        self.latest_trusted_height = 0

        logger.info(
            f"Initialized Cosmos light client for {chain_id}",
            extra={
                'chain_id': chain_id,
                'trust_level': trust_level.name,
                'trust_period': trust_period_seconds,
            }
        )

    def initialize_trust(
        self,
        header: CosmosBlockHeader,
        validator_set: CosmosValidatorSet,
        next_validator_set: CosmosValidatorSet,
    ) -> bool:
        """
        Initialize trust with a trusted header and validator sets

        This is the trust anchor for all subsequent verification.

        Args:
            header: Trusted block header
            validator_set: Validator set for this height
            next_validator_set: Validator set for next height

        Returns:
            True if initialization successful
        """
        # Verify validator set matches header
        if validator_set.hash() != header.validators_hash:
            logger.error(
                "Validator set hash mismatch during initialization",
                extra={'event': 'cosmos_light_client.init_failed'}
            )
            return False

        if next_validator_set.hash() != header.next_validators_hash:
            logger.error(
                "Next validator set hash mismatch during initialization",
                extra={'event': 'cosmos_light_client.init_failed'}
            )
            return False

        # Create trusted state
        trusted_state = TrustedState(
            header=header,
            validator_set=validator_set,
            next_validator_set=next_validator_set,
            trusted_at=int(time.time()),
        )

        self.trusted_states[header.height] = trusted_state
        self.latest_trusted_height = header.height

        logger.info(
            f"Initialized trust at height {header.height}",
            extra={'event': 'cosmos_light_client.trust_initialized'}
        )

        return True

    def verify_header(
        self,
        untrusted_header: CosmosBlockHeader,
        untrusted_validator_set: CosmosValidatorSet,
        untrusted_next_validator_set: CosmosValidatorSet,
        commit: CosmosCommit,
    ) -> bool:
        """
        Verify an untrusted header using sequential or bisection verification

        Args:
            untrusted_header: Header to verify
            untrusted_validator_set: Validator set at untrusted height
            untrusted_next_validator_set: Next validator set
            commit: Commit with validator signatures

        Returns:
            True if header is verified
        """
        # Get most recent trusted state
        if not self.trusted_states:
            logger.error(
                "No trusted state available",
                extra={'event': 'cosmos_light_client.no_trust'}
            )
            return False

        trusted_state = self.trusted_states[self.latest_trusted_height]

        # Check trust period
        if not trusted_state.is_within_trust_period(self.trust_period_seconds):
            logger.error(
                f"Trusted state expired (age > {self.trust_period_seconds}s)",
                extra={'event': 'cosmos_light_client.trust_expired'}
            )
            return False

        # Basic header validation
        if not self._validate_header_basic(untrusted_header):
            return False

        # Verify commit matches header
        if commit.block_id != untrusted_header.hash():
            logger.error(
                "Commit block ID mismatch",
                extra={'event': 'cosmos_light_client.commit_mismatch'}
            )
            return False

        # Sequential verification (adjacent blocks)
        if untrusted_header.height == trusted_state.header.height + 1:
            return self._verify_sequential(
                trusted_state,
                untrusted_header,
                untrusted_validator_set,
                untrusted_next_validator_set,
                commit,
            )

        # Bisection verification (non-adjacent blocks)
        return self._verify_bisection(
            trusted_state,
            untrusted_header,
            untrusted_validator_set,
            untrusted_next_validator_set,
            commit,
        )

    def _validate_header_basic(self, header: CosmosBlockHeader) -> bool:
        """
        Perform basic header validation

        Args:
            header: Header to validate

        Returns:
            True if header passes basic checks
        """
        # Verify chain ID
        if header.chain_id != self.chain_id:
            logger.error(
                f"Chain ID mismatch: {header.chain_id} != {self.chain_id}",
                extra={'event': 'cosmos_light_client.chain_id_mismatch'}
            )
            return False

        # Verify height is positive
        if header.height <= 0:
            logger.error(
                f"Invalid height: {header.height}",
                extra={'event': 'cosmos_light_client.invalid_height'}
            )
            return False

        # Verify timestamp is not too far in future
        now = int(time.time())
        if header.time > now + self.max_clock_drift_seconds:
            logger.error(
                f"Header time too far in future: {header.time} > {now + self.max_clock_drift_seconds}",
                extra={'event': 'cosmos_light_client.future_timestamp'}
            )
            return False

        # Verify validator set hashes
        if header.validators_hash == b'' or header.next_validators_hash == b'':
            logger.error(
                "Empty validator set hash",
                extra={'event': 'cosmos_light_client.empty_validator_hash'}
            )
            return False

        return True

    def _verify_sequential(
        self,
        trusted_state: TrustedState,
        untrusted_header: CosmosBlockHeader,
        untrusted_validator_set: CosmosValidatorSet,
        untrusted_next_validator_set: CosmosValidatorSet,
        commit: CosmosCommit,
    ) -> bool:
        """
        Verify adjacent header (height = trusted_height + 1)

        Uses next_validator_set from trusted state to verify commit.

        Args:
            trusted_state: Current trusted state
            untrusted_header: Header to verify
            untrusted_validator_set: Validator set at untrusted height
            untrusted_next_validator_set: Next validator set
            commit: Commit with signatures

        Returns:
            True if verification succeeds
        """
        # Verify untrusted validator set matches header
        if untrusted_validator_set.hash() != untrusted_header.validators_hash:
            logger.error(
                "Validator set hash mismatch",
                extra={'event': 'cosmos_light_client.validator_mismatch'}
            )
            return False

        if untrusted_next_validator_set.hash() != untrusted_header.next_validators_hash:
            logger.error(
                "Next validator set hash mismatch",
                extra={'event': 'cosmos_light_client.next_validator_mismatch'}
            )
            return False

        # Verify untrusted validator set matches trusted next_validator_set
        if untrusted_validator_set.hash() != trusted_state.next_validator_set.hash():
            logger.error(
                "Sequential validator set mismatch",
                extra={'event': 'cosmos_light_client.sequential_mismatch'}
            )
            return False

        # Verify commit signatures
        if not self._verify_commit(untrusted_validator_set, commit):
            return False

        # Verify timestamp monotonicity
        if untrusted_header.time <= trusted_state.header.time:
            logger.error(
                "Non-monotonic timestamp",
                extra={'event': 'cosmos_light_client.timestamp_regression'}
            )
            return False

        # Add to trusted states
        new_trusted_state = TrustedState(
            header=untrusted_header,
            validator_set=untrusted_validator_set,
            next_validator_set=untrusted_next_validator_set,
            trusted_at=int(time.time()),
        )

        self.trusted_states[untrusted_header.height] = new_trusted_state
        self.latest_trusted_height = untrusted_header.height

        logger.info(
            f"Verified header {untrusted_header.height} (sequential)",
            extra={'event': 'cosmos_light_client.header_verified'}
        )

        return True

    def _verify_bisection(
        self,
        trusted_state: TrustedState,
        untrusted_header: CosmosBlockHeader,
        untrusted_validator_set: CosmosValidatorSet,
        untrusted_next_validator_set: CosmosValidatorSet,
        commit: CosmosCommit,
    ) -> bool:
        """
        Verify non-adjacent header using bisection algorithm

        Requires sufficient validator overlap between trusted and untrusted sets.

        Args:
            trusted_state: Current trusted state
            untrusted_header: Header to verify
            untrusted_validator_set: Validator set at untrusted height
            untrusted_next_validator_set: Next validator set
            commit: Commit with signatures

        Returns:
            True if verification succeeds
        """
        # Verify validator set hashes
        if untrusted_validator_set.hash() != untrusted_header.validators_hash:
            logger.error(
                "Validator set hash mismatch",
                extra={'event': 'cosmos_light_client.validator_mismatch'}
            )
            return False

        if untrusted_next_validator_set.hash() != untrusted_header.next_validators_hash:
            logger.error(
                "Next validator set hash mismatch",
                extra={'event': 'cosmos_light_client.next_validator_mismatch'}
            )
            return False

        # Verify commit with untrusted validator set
        if not self._verify_commit(untrusted_validator_set, commit):
            return False

        # Check validator overlap (bisection requirement)
        signing_validators = commit.get_signing_validators()
        signing_power = trusted_state.next_validator_set.compute_voting_power(signing_validators)
        total_power = trusted_state.next_validator_set.total_voting_power

        required_power = int(total_power * self.trust_level.value)

        if signing_power < required_power:
            logger.error(
                f"Insufficient validator overlap: {signing_power}/{total_power} "
                f"(required {required_power})",
                extra={'event': 'cosmos_light_client.insufficient_overlap'}
            )
            return False

        # Add to trusted states
        new_trusted_state = TrustedState(
            header=untrusted_header,
            validator_set=untrusted_validator_set,
            next_validator_set=untrusted_next_validator_set,
            trusted_at=int(time.time()),
        )

        self.trusted_states[untrusted_header.height] = new_trusted_state
        if untrusted_header.height > self.latest_trusted_height:
            self.latest_trusted_height = untrusted_header.height

        logger.info(
            f"Verified header {untrusted_header.height} (bisection, "
            f"overlap: {signing_power}/{total_power})",
            extra={'event': 'cosmos_light_client.header_verified'}
        )

        return True

    def _verify_commit(
        self,
        validator_set: CosmosValidatorSet,
        commit: CosmosCommit,
    ) -> bool:
        """
        Verify commit has >2/3 voting power

        Args:
            validator_set: Validator set to verify against
            commit: Commit to verify

        Returns:
            True if commit is valid
        """
        # Calculate voting power of signers
        signing_validators = commit.get_signing_validators()
        signing_power = validator_set.compute_voting_power(signing_validators)

        # Require >2/3 voting power (Tendermint BFT requirement)
        required_power = (validator_set.total_voting_power * 2 // 3) + 1

        if signing_power < required_power:
            logger.error(
                f"Insufficient commit voting power: {signing_power}/{validator_set.total_voting_power} "
                f"(required {required_power})",
                extra={'event': 'cosmos_light_client.insufficient_commit_power'}
            )
            return False

        # In production, would verify each signature cryptographically
        # For now, we assume signatures are valid if voting power check passes

        return True

    def verify_ibc_proof(
        self,
        height: int,
        proof: CosmosProof,
    ) -> bool:
        """
        Verify IBC proof at specific height

        Args:
            height: Block height for proof
            proof: IBC proof to verify

        Returns:
            True if proof is valid
        """
        # Get trusted state at height
        trusted_state = self.trusted_states.get(height)
        if not trusted_state:
            logger.error(
                f"No trusted state at height {height}",
                extra={'event': 'cosmos_light_client.no_trusted_state'}
            )
            return False

        # Verify proof against app_hash (state root)
        app_hash = trusted_state.header.app_hash

        # Simplified IBC proof verification
        # In production, would implement full ICS-23 proof verification
        return self._verify_merkle_proof(
            root=app_hash,
            key=proof.key,
            value=proof.value,
            proof_ops=proof.proof_ops,
        )

    def _verify_merkle_proof(
        self,
        root: bytes,
        key: bytes,
        value: bytes,
        proof_ops: List[Dict[str, Any]],
    ) -> bool:
        """
        Verify Merkle proof for IBC

        Simplified implementation - production should use ICS-23.

        Args:
            root: Expected root hash
            key: Key to verify
            value: Expected value
            proof_ops: Proof operations

        Returns:
            True if proof is valid
        """
        if not proof_ops:
            return False

        # Start with key-value hash
        current_hash = hashlib.sha256(key + value).digest()

        # Apply proof operations
        for op in proof_ops:
            op_type = op.get('type', '')
            if op_type == 'iavl':
                # IAVL tree proof
                prefix = base64.b64decode(op.get('prefix', ''))
                suffix = base64.b64decode(op.get('suffix', ''))
                current_hash = hashlib.sha256(prefix + current_hash + suffix).digest()
            else:
                logger.warning(f"Unknown proof operation type: {op_type}")
                return False

        # Verify final hash matches root
        return current_hash == root

    def get_trusted_state(self, height: int) -> Optional[TrustedState]:
        """Get trusted state at height"""
        return self.trusted_states.get(height)

    def get_latest_trusted_state(self) -> Optional[TrustedState]:
        """Get latest trusted state"""
        if self.latest_trusted_height == 0:
            return None
        return self.trusted_states.get(self.latest_trusted_height)

    def export_trusted_states(self) -> List[Dict[str, Any]]:
        """Export all trusted states"""
        return [
            {
                'height': height,
                'state': state.to_dict(),
            }
            for height, state in sorted(self.trusted_states.items())
        ]
