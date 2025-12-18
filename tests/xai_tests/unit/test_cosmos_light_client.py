"""
Unit tests for Cosmos Light Client

Tests Tendermint light client protocol, validator verification, and IBC proofs.
"""

import pytest
import hashlib
import base64
import time

from xai.core.light_clients.cosmos_light_client import (
    CosmosLightClient,
    CosmosBlockHeader,
    CosmosValidator,
    CosmosValidatorSet,
    CosmosCommit,
    CosmosProof,
    TrustedState,
    TrustLevel,
)


class TestCosmosValidator:
    """Test validator functionality"""

    def test_validator_creation(self):
        """Test creating a validator"""
        validator = CosmosValidator(
            address=b'\x01' * 20,
            pub_key=b'\x02' * 32,
            voting_power=1000,
            proposer_priority=0,
        )

        assert validator.voting_power == 1000
        assert len(validator.hash()) == 32

    def test_validator_serialization(self):
        """Test validator to_dict and from_dict"""
        validator = CosmosValidator(
            address=b'\x01' * 20,
            pub_key=b'\x02' * 32,
            voting_power=1000,
        )

        data = validator.to_dict()
        reconstructed = CosmosValidator.from_dict(data)

        assert reconstructed.address == validator.address
        assert reconstructed.pub_key == validator.pub_key
        assert reconstructed.voting_power == validator.voting_power


class TestCosmosValidatorSet:
    """Test validator set functionality"""

    @pytest.fixture
    def validators(self):
        """Create test validators"""
        return [
            CosmosValidator(
                address=b'\x01' * 20,
                pub_key=b'\x11' * 32,
                voting_power=100,
            ),
            CosmosValidator(
                address=b'\x02' * 20,
                pub_key=b'\x22' * 32,
                voting_power=200,
            ),
            CosmosValidator(
                address=b'\x03' * 20,
                pub_key=b'\x33' * 32,
                voting_power=300,
            ),
        ]

    def test_validator_set_creation(self, validators):
        """Test creating a validator set"""
        val_set = CosmosValidatorSet(
            validators=validators,
            total_voting_power=0,  # Will be calculated
        )

        assert val_set.total_voting_power == 600
        assert len(val_set.validators) == 3

    def test_validator_set_hash(self, validators):
        """Test validator set hashing"""
        val_set = CosmosValidatorSet(
            validators=validators,
            total_voting_power=600,
        )

        hash1 = val_set.hash()
        assert len(hash1) == 32

        # Hash should be deterministic
        hash2 = val_set.hash()
        assert hash1 == hash2

    def test_get_validator(self, validators):
        """Test getting validator by address"""
        val_set = CosmosValidatorSet(
            validators=validators,
            total_voting_power=600,
        )

        validator = val_set.get_validator(b'\x02' * 20)
        assert validator is not None
        assert validator.voting_power == 200

        # Non-existent validator
        assert val_set.get_validator(b'\xff' * 20) is None

    def test_compute_voting_power(self, validators):
        """Test computing voting power for subset"""
        val_set = CosmosValidatorSet(
            validators=validators,
            total_voting_power=600,
        )

        # Power of first two validators
        power = val_set.compute_voting_power([b'\x01' * 20, b'\x02' * 20])
        assert power == 300

        # All validators
        power = val_set.compute_voting_power([b'\x01' * 20, b'\x02' * 20, b'\x03' * 20])
        assert power == 600

        # Non-existent validator
        power = val_set.compute_voting_power([b'\xff' * 20])
        assert power == 0

    def test_validator_set_serialization(self, validators):
        """Test validator set to_dict and from_dict"""
        val_set = CosmosValidatorSet(
            validators=validators,
            total_voting_power=600,
        )

        data = val_set.to_dict()
        reconstructed = CosmosValidatorSet.from_dict(data)

        assert reconstructed.total_voting_power == val_set.total_voting_power
        assert len(reconstructed.validators) == len(val_set.validators)


class TestCosmosBlockHeader:
    """Test block header functionality"""

    def test_header_creation(self):
        """Test creating a block header"""
        header = CosmosBlockHeader(
            version=1,
            chain_id="test-chain-1",
            height=100,
            time=1234567890,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=b'\x03' * 32,
            next_validators_hash=b'\x04' * 32,
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x09' * 20,
        )

        assert header.height == 100
        assert header.chain_id == "test-chain-1"
        assert len(header.hash()) == 32

    def test_header_hash_deterministic(self):
        """Test header hash is deterministic"""
        header1 = CosmosBlockHeader(
            version=1,
            chain_id="test-chain-1",
            height=100,
            time=1234567890,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=b'\x03' * 32,
            next_validators_hash=b'\x04' * 32,
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x09' * 20,
        )

        header2 = CosmosBlockHeader(
            version=1,
            chain_id="test-chain-1",
            height=100,
            time=1234567890,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=b'\x03' * 32,
            next_validators_hash=b'\x04' * 32,
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x09' * 20,
        )

        assert header1.hash() == header2.hash()

    def test_header_serialization(self):
        """Test header to_dict and from_dict"""
        header = CosmosBlockHeader(
            version=1,
            chain_id="test-chain-1",
            height=100,
            time=1234567890,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=b'\x03' * 32,
            next_validators_hash=b'\x04' * 32,
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x09' * 20,
        )

        data = header.to_dict()
        reconstructed = CosmosBlockHeader.from_dict(data)

        assert reconstructed.height == header.height
        assert reconstructed.chain_id == header.chain_id
        assert reconstructed.time == header.time


class TestCosmosCommit:
    """Test commit functionality"""

    def test_commit_creation(self):
        """Test creating a commit"""
        commit = CosmosCommit(
            height=100,
            round=0,
            block_id=b'\x00' * 32,
            signatures=[
                (b'\x01' * 20, b'\x11' * 64),
                (b'\x02' * 20, b'\x22' * 64),
            ],
            timestamp=1234567890,
        )

        assert commit.height == 100
        assert len(commit.signatures) == 2

    def test_get_signing_validators(self):
        """Test getting signing validators"""
        commit = CosmosCommit(
            height=100,
            round=0,
            block_id=b'\x00' * 32,
            signatures=[
                (b'\x01' * 20, b'\x11' * 64),
                (b'\x02' * 20, b'\x22' * 64),
                (b'\x03' * 20, b'\x33' * 64),
            ],
            timestamp=1234567890,
        )

        signers = commit.get_signing_validators()
        assert len(signers) == 3
        assert b'\x01' * 20 in signers
        assert b'\x02' * 20 in signers


class TestTrustedState:
    """Test trusted state functionality"""

    @pytest.fixture
    def header(self):
        """Create test header"""
        return CosmosBlockHeader(
            version=1,
            chain_id="test-chain-1",
            height=100,
            time=1234567890,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=b'\x03' * 32,
            next_validators_hash=b'\x04' * 32,
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x09' * 20,
        )

    @pytest.fixture
    def validator_set(self):
        """Create test validator set"""
        return CosmosValidatorSet(
            validators=[
                CosmosValidator(
                    address=b'\x01' * 20,
                    pub_key=b'\x11' * 32,
                    voting_power=100,
                ),
            ],
            total_voting_power=100,
        )

    def test_trusted_state_creation(self, header, validator_set):
        """Test creating trusted state"""
        now = int(time.time())
        state = TrustedState(
            header=header,
            validator_set=validator_set,
            next_validator_set=validator_set,
            trusted_at=now,
        )

        assert state.header.height == 100
        assert state.trusted_at == now

    def test_is_within_trust_period(self, header, validator_set):
        """Test trust period checking"""
        now = int(time.time())
        state = TrustedState(
            header=header,
            validator_set=validator_set,
            next_validator_set=validator_set,
            trusted_at=now,
        )

        # Should be within trust period
        assert state.is_within_trust_period(1000, now + 500)

        # Should be outside trust period
        assert not state.is_within_trust_period(1000, now + 1500)


class TestCosmosLightClient:
    """Test light client functionality"""

    @pytest.fixture
    def client(self):
        """Create test light client"""
        return CosmosLightClient(
            chain_id="test-chain-1",
            trust_level=TrustLevel.ONE_THIRD,
            trust_period_seconds=14 * 24 * 3600,
        )

    @pytest.fixture
    def validators(self):
        """Create test validators"""
        return [
            CosmosValidator(
                address=b'\x01' * 20,
                pub_key=b'\x11' * 32,
                voting_power=100,
            ),
            CosmosValidator(
                address=b'\x02' * 20,
                pub_key=b'\x22' * 32,
                voting_power=200,
            ),
            CosmosValidator(
                address=b'\x03' * 20,
                pub_key=b'\x33' * 32,
                voting_power=300,
            ),
        ]

    @pytest.fixture
    def validator_set(self, validators):
        """Create validator set"""
        return CosmosValidatorSet(
            validators=validators,
            total_voting_power=600,
        )

    @pytest.fixture
    def trusted_header(self, validator_set):
        """Create trusted header"""
        return CosmosBlockHeader(
            version=1,
            chain_id="test-chain-1",
            height=100,
            time=1234567890,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=validator_set.hash(),
            next_validators_hash=validator_set.hash(),
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x01' * 20,
        )

    def test_initialize_trust(self, client, trusted_header, validator_set):
        """Test initializing trust"""
        assert client.initialize_trust(
            header=trusted_header,
            validator_set=validator_set,
            next_validator_set=validator_set,
        )

        assert client.latest_trusted_height == 100
        assert len(client.trusted_states) == 1

    def test_initialize_trust_invalid_validator_hash(self, client, trusted_header, validators):
        """Test initialization fails with wrong validator hash"""
        # Create validator set with different validators
        wrong_val_set = CosmosValidatorSet(
            validators=[
                CosmosValidator(
                    address=b'\xff' * 20,
                    pub_key=b'\xff' * 32,
                    voting_power=100,
                ),
            ],
            total_voting_power=100,
        )

        assert not client.initialize_trust(
            header=trusted_header,
            validator_set=wrong_val_set,
            next_validator_set=wrong_val_set,
        )

    def test_verify_header_no_trust(self, client):
        """Test verification fails without trust"""
        header = CosmosBlockHeader(
            version=1,
            chain_id="test-chain-1",
            height=101,
            time=1234567900,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=b'\x03' * 32,
            next_validators_hash=b'\x04' * 32,
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x01' * 20,
        )

        val_set = CosmosValidatorSet(validators=[], total_voting_power=0)
        commit = CosmosCommit(
            height=101,
            round=0,
            block_id=header.hash(),
            signatures=[],
            timestamp=1234567900,
        )

        assert not client.verify_header(header, val_set, val_set, commit)

    def test_verify_header_wrong_chain_id(self, client, trusted_header, validator_set):
        """Test verification fails with wrong chain ID"""
        client.initialize_trust(trusted_header, validator_set, validator_set)

        header = CosmosBlockHeader(
            version=1,
            chain_id="wrong-chain",  # Wrong chain ID
            height=101,
            time=1234567900,
            last_block_id=b'\x00' * 32,
            last_commit_hash=b'\x01' * 32,
            data_hash=b'\x02' * 32,
            validators_hash=validator_set.hash(),
            next_validators_hash=validator_set.hash(),
            consensus_hash=b'\x05' * 32,
            app_hash=b'\x06' * 32,
            last_results_hash=b'\x07' * 32,
            evidence_hash=b'\x08' * 32,
            proposer_address=b'\x01' * 20,
        )

        commit = CosmosCommit(
            height=101,
            round=0,
            block_id=header.hash(),
            signatures=[
                (b'\x01' * 20, b'\x11' * 64),
                (b'\x02' * 20, b'\x22' * 64),
            ],
            timestamp=1234567900,
        )

        assert not client.verify_header(header, validator_set, validator_set, commit)

    def test_get_trusted_state(self, client, trusted_header, validator_set):
        """Test getting trusted state"""
        client.initialize_trust(trusted_header, validator_set, validator_set)

        state = client.get_trusted_state(100)
        assert state is not None
        assert state.header.height == 100

    def test_get_latest_trusted_state(self, client, trusted_header, validator_set):
        """Test getting latest trusted state"""
        assert client.get_latest_trusted_state() is None

        client.initialize_trust(trusted_header, validator_set, validator_set)

        latest = client.get_latest_trusted_state()
        assert latest is not None
        assert latest.header.height == 100


class TestCosmosProof:
    """Test IBC proof functionality"""

    def test_proof_creation(self):
        """Test creating an IBC proof"""
        proof = CosmosProof(
            key=b'ibc/channel-0',
            value=b'some_value',
            proof_ops=[
                {
                    'type': 'iavl',
                    'prefix': base64.b64encode(b'prefix').decode(),
                    'suffix': base64.b64encode(b'suffix').decode(),
                },
            ],
            height=100,
        )

        assert proof.height == 100
        assert len(proof.proof_ops) == 1

    def test_proof_serialization(self):
        """Test proof to_dict"""
        proof = CosmosProof(
            key=b'test_key',
            value=b'test_value',
            proof_ops=[],
            height=100,
        )

        data = proof.to_dict()
        assert data['height'] == 100
        assert 'key' in data
        assert 'value' in data
