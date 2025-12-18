"""
Unit tests for EVM Light Client

Tests block header verification, state proof validation, and consensus rules.
"""

import pytest
import hashlib
from eth_utils import keccak, to_bytes

from xai.core.light_clients.evm_light_client import (
    EVMLightClient,
    EVMBlockHeader,
    EVMStateProof,
    EVMChainConfig,
    ConsensusType,
)


class TestEVMChainConfig:
    """Test chain configuration"""

    def test_ethereum_mainnet_config(self):
        """Test Ethereum mainnet configuration"""
        config = EVMChainConfig.ethereum_mainnet()
        assert config.chain_id == 1
        assert config.chain_name == "Ethereum"
        assert config.consensus_type == ConsensusType.POS
        assert config.block_time == 12

    def test_bsc_config(self):
        """Test BSC configuration"""
        config = EVMChainConfig.bsc_mainnet()
        assert config.chain_id == 56
        assert config.chain_name == "BSC"
        assert config.consensus_type == ConsensusType.CLIQUE

    def test_polygon_config(self):
        """Test Polygon configuration"""
        config = EVMChainConfig.polygon_mainnet()
        assert config.chain_id == 137
        assert config.chain_name == "Polygon"


class TestEVMBlockHeader:
    """Test block header functionality"""

    def test_header_creation(self):
        """Test creating a block header"""
        header = EVMBlockHeader(
            parent_hash=b'\x00' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1000,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567890,
            extra_data=b'test',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

        assert header.number == 1
        assert header.difficulty == 1000
        assert len(header.hash()) == 32

    def test_header_hash_deterministic(self):
        """Test that header hash is deterministic"""
        header1 = EVMBlockHeader(
            parent_hash=b'\x00' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1000,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567890,
            extra_data=b'test',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

        header2 = EVMBlockHeader(
            parent_hash=b'\x00' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1000,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567890,
            extra_data=b'test',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

        assert header1.hash() == header2.hash()

    def test_header_to_dict(self):
        """Test header serialization"""
        header = EVMBlockHeader(
            parent_hash=b'\x00' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1000,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567890,
            extra_data=b'test',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

        data = header.to_dict()
        assert data['number'] == 1
        assert data['difficulty'] == 1000
        assert 'hash' in data


class TestEVMLightClient:
    """Test light client functionality"""

    @pytest.fixture
    def client(self):
        """Create a test light client"""
        config = EVMChainConfig(
            chain_id=999,
            chain_name="TestChain",
            consensus_type=ConsensusType.CLIQUE,  # Use PoA for testing (no PoW verification)
            block_time=15,
            epoch_length=2048,
        )
        return EVMLightClient(config)

    @pytest.fixture
    def genesis_header(self):
        """Create a genesis header"""
        return EVMBlockHeader(
            parent_hash=b'\x00' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1,  # Clique difficulty
            number=0,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567890,
            extra_data=b'genesis',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

    def test_add_genesis_header(self, client, genesis_header):
        """Test adding genesis header"""
        assert client.add_header(genesis_header)
        assert client.latest_verified_height == 0
        assert len(client.headers) == 1

    def test_add_duplicate_header(self, client, genesis_header):
        """Test adding same header twice"""
        assert client.add_header(genesis_header)
        assert client.add_header(genesis_header)  # Should succeed (idempotent)
        assert len(client.headers) == 1

    def test_add_header_missing_parent(self, client):
        """Test adding header without parent"""
        header = EVMBlockHeader(
            parent_hash=b'\xff' * 32,  # Non-existent parent
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567900,
            extra_data=b'',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

        assert not client.add_header(header)

    def test_add_header_invalid_parent_hash(self, client, genesis_header):
        """Test adding header with wrong parent hash"""
        client.add_header(genesis_header)

        header = EVMBlockHeader(
            parent_hash=b'\xff' * 32,  # Wrong parent hash
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567900,
            extra_data=b'',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

        assert not client.add_header(header)

    def test_add_header_invalid_timestamp(self, client, genesis_header):
        """Test adding header with past timestamp"""
        client.add_header(genesis_header)

        header = EVMBlockHeader(
            parent_hash=genesis_header.hash(),
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567889,  # Earlier than parent
            extra_data=b'',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )

        assert not client.add_header(header)

    def test_get_header(self, client, genesis_header):
        """Test getting header by height"""
        client.add_header(genesis_header)

        retrieved = client.get_header(0)
        assert retrieved is not None
        assert retrieved.number == 0

    def test_get_latest_header(self, client, genesis_header):
        """Test getting latest header"""
        assert client.get_latest_header() is None

        client.add_header(genesis_header)
        latest = client.get_latest_header()
        assert latest is not None
        assert latest.number == 0

    def test_get_confirmations(self, client, genesis_header):
        """Test confirmation counting"""
        client.add_header(genesis_header)
        assert client.get_confirmations(0) == 1

    def test_sync_headers_success(self, client, genesis_header):
        """Test syncing multiple headers"""
        headers = [genesis_header]

        # Create chain of 5 blocks
        parent = genesis_header
        for i in range(1, 6):
            header = EVMBlockHeader(
                parent_hash=parent.hash(),
                uncle_hash=b'\x01' * 32,
                coinbase=b'\x02' * 20,
                state_root=b'\x03' * 32,
                transactions_root=b'\x04' * 32,
                receipts_root=b'\x05' * 32,
                logs_bloom=b'\x00' * 256,
                difficulty=1,  # Clique difficulty
                number=i,
                gas_limit=8000000,
                gas_used=0,
                timestamp=1234567890 + i * 15,
                extra_data=b'',
                mix_hash=b'\x06' * 32,
                nonce=b'\x00' * 8,
            )
            headers.append(header)
            parent = header

        added, rejected = client.sync_headers(headers)
        assert added == 6
        assert rejected == 0
        assert client.latest_verified_height == 5

    def test_sync_headers_stops_on_invalid(self, client, genesis_header):
        """Test sync stops on first invalid header"""
        headers = [genesis_header]

        # Valid header
        header1 = EVMBlockHeader(
            parent_hash=genesis_header.hash(),
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1,
            number=1,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567905,
            extra_data=b'',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )
        headers.append(header1)

        # Invalid header (wrong parent)
        header2 = EVMBlockHeader(
            parent_hash=b'\xff' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1,
            number=2,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567920,
            extra_data=b'',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
        )
        headers.append(header2)

        added, rejected = client.sync_headers(headers)
        assert added == 2  # Genesis + header1
        assert rejected == 1  # header2
        assert client.latest_verified_height == 1

    def test_export_headers(self, client, genesis_header):
        """Test exporting headers"""
        client.add_header(genesis_header)

        exported = client.export_headers()
        assert len(exported) == 1
        assert exported[0]['number'] == 0


class TestEVMStateProof:
    """Test state proof verification"""

    def test_state_proof_creation(self):
        """Test creating a state proof"""
        proof = EVMStateProof(
            address=b'\xaa' * 20,
            balance=1000000000000000000,  # 1 ETH
            nonce=5,
            code_hash=keccak(b'contract code'),
            storage_hash=b'\xbb' * 32,
            account_proof=[b'\x01' * 32, b'\x02' * 32],
            storage_proofs={
                b'\x00' * 32: [b'\x03' * 32, b'\x04' * 32],
            },
        )

        assert proof.balance == 1000000000000000000
        assert proof.nonce == 5
        assert len(proof.account_proof) == 2

    def test_state_proof_serialization(self):
        """Test state proof to_dict"""
        proof = EVMStateProof(
            address=b'\xaa' * 20,
            balance=1000000000000000000,
            nonce=5,
            code_hash=keccak(b'code'),
            storage_hash=b'\xbb' * 32,
            account_proof=[b'\x01' * 32],
            storage_proofs={},
        )

        data = proof.to_dict()
        assert data['balance'] == 1000000000000000000
        assert data['nonce'] == 5
        assert 'address' in data
        assert 'account_proof' in data


class TestPOSConsensus:
    """Test Proof of Stake verification"""

    @pytest.fixture
    def pos_client(self):
        """Create POS client"""
        config = EVMChainConfig(
            chain_id=1,
            chain_name="Ethereum",
            consensus_type=ConsensusType.POS,
            block_time=12,
            epoch_length=0,
        )
        return EVMLightClient(config)

    @pytest.fixture
    def pos_genesis(self):
        """Create POS genesis"""
        return EVMBlockHeader(
            parent_hash=b'\x00' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=0,  # POS has 0 difficulty
            number=0,
            gas_limit=30000000,
            gas_used=0,
            timestamp=1234567890,
            extra_data=b'',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
            base_fee_per_gas=1000000000,  # 1 gwei
        )

    def test_pos_genesis(self, pos_client, pos_genesis):
        """Test adding POS genesis"""
        assert pos_client.add_header(pos_genesis)
        assert pos_client.latest_verified_height == 0

    def test_pos_block_zero_difficulty(self, pos_client, pos_genesis):
        """Test POS blocks must have zero difficulty"""
        pos_client.add_header(pos_genesis)

        # Valid POS block
        header = EVMBlockHeader(
            parent_hash=pos_genesis.hash(),
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=0,  # Must be 0
            number=1,
            gas_limit=30000000,
            gas_used=0,
            timestamp=1234567902,
            extra_data=b'',
            mix_hash=b'\x06' * 32,
            nonce=b'\x00' * 8,
            base_fee_per_gas=1000000000,
        )

        assert pos_client.add_header(header)


class TestCliqueConsensus:
    """Test Clique PoA verification"""

    @pytest.fixture
    def clique_client(self):
        """Create Clique client"""
        config = EVMChainConfig.bsc_mainnet()
        return EVMLightClient(config)

    def test_clique_difficulty(self, clique_client):
        """Test Clique accepts difficulty 1 or 2"""
        genesis = EVMBlockHeader(
            parent_hash=b'\x00' * 32,
            uncle_hash=b'\x01' * 32,
            coinbase=b'\x02' * 20,
            state_root=b'\x03' * 32,
            transactions_root=b'\x04' * 32,
            receipts_root=b'\x05' * 32,
            logs_bloom=b'\x00' * 256,
            difficulty=1,  # Clique uses 1 or 2
            number=0,
            gas_limit=8000000,
            gas_used=0,
            timestamp=1234567890,
            extra_data=b'\x00' * 32,
            mix_hash=b'\x00' * 32,
            nonce=b'\x00' * 8,
        )

        assert clique_client.add_header(genesis)
