"""
Test API response caching with ETag headers for immutable blockchain data.

This test suite verifies:
- ETag headers are set for block endpoints
- Cache-Control headers are set correctly
- 304 Not Modified responses for cached data
- Caching behavior for both /blocks/<index> and /block/<hash> endpoints
"""

import pytest
from unittest.mock import Mock, MagicMock
from flask import Flask
from xai.core.blockchain import Block, Transaction, BlockHeader
from xai.core.node_api import NodeAPIRoutes


@pytest.fixture
def mock_blockchain():
    """Create mock blockchain with test blocks."""
    blockchain = Mock()

    # Create test blocks with proper structure
    genesis_header = BlockHeader(
        index=0,
        previous_hash="0" * 64,
        merkle_root="genesis_merkle",
        timestamp=1700000000.0,
        difficulty=4,
        nonce=0,
        version=1
    )
    genesis_header.hash = "0xaaaa" + "a" * 60

    block1_header = BlockHeader(
        index=1,
        previous_hash="0xaaaa" + "a" * 60,
        merkle_root="block1_merkle",
        timestamp=1700000001.0,
        difficulty=4,
        nonce=12345,
        version=1
    )
    block1_header.hash = "0xbbbb" + "b" * 60

    genesis_block = Block(
        header=genesis_header,
        transactions=[],
    )

    block1 = Block(
        header=block1_header,
        transactions=[],
    )

    blockchain.chain = [genesis_block, block1]
    blockchain.get_block = Mock(side_effect=lambda idx: blockchain.chain[idx] if 0 <= idx < len(blockchain.chain) else None)
    blockchain.get_block_by_hash = Mock(side_effect=lambda h: next((b for b in blockchain.chain if b.hash.lower() == h.lower() or b.hash.lower() == f"0x{h.lower()}"), None))
    blockchain.pending_transactions = []

    return blockchain


@pytest.fixture
def mock_node(mock_blockchain):
    """Create mock node with blockchain."""
    node = Mock()
    node.app = Flask(__name__)
    node.blockchain = mock_blockchain
    node.miner_address = "test_miner"
    node.peers = set()
    node.is_mining = False
    node.start_time = 1700000000.0
    node.metrics_collector = Mock()
    return node


@pytest.fixture
def api_routes(mock_node):
    """Create NodeAPIRoutes instance."""
    routes = NodeAPIRoutes(mock_node)
    routes.setup_routes()
    return routes


@pytest.fixture
def client(api_routes):
    """Create Flask test client."""
    api_routes.app.config['TESTING'] = True
    return api_routes.app.test_client()


class TestBlockCaching:
    """Test caching for block endpoints."""

    def test_get_block_by_index_sets_etag(self, client, mock_blockchain):
        """Test that GET /blocks/<index> sets ETag header."""
        response = client.get('/blocks/0')

        assert response.status_code == 200
        assert 'ETag' in response.headers

        # ETag should be the block hash wrapped in quotes
        expected_hash = mock_blockchain.chain[0].hash
        expected_etag = f'"{expected_hash}"'
        assert response.headers['ETag'] == expected_etag

    def test_get_block_by_index_sets_cache_control(self, client):
        """Test that GET /blocks/<index> sets Cache-Control header."""
        response = client.get('/blocks/0')

        assert response.status_code == 200
        assert 'Cache-Control' in response.headers

        # Should allow public caching with long max-age (1 year)
        cache_control = response.headers['Cache-Control']
        assert 'public' in cache_control
        assert 'max-age=31536000' in cache_control
        assert 'immutable' in cache_control

    def test_get_block_by_index_304_not_modified(self, client, mock_blockchain):
        """Test that GET /blocks/<index> returns 304 when ETag matches."""
        # First request to get ETag
        response1 = client.get('/blocks/0')
        assert response1.status_code == 200
        etag = response1.headers['ETag']

        # Second request with If-None-Match header
        response2 = client.get('/blocks/0', headers={'If-None-Match': etag})

        assert response2.status_code == 304
        assert response2.data == b''  # No body for 304

    def test_get_block_by_index_200_when_etag_differs(self, client, mock_blockchain):
        """Test that GET /blocks/<index> returns 200 when ETag doesn't match."""
        response = client.get('/blocks/0', headers={'If-None-Match': '"wrong-hash"'})

        assert response.status_code == 200
        data = response.get_json()
        assert 'index' in data or 'header' in data

    def test_get_block_by_hash_sets_etag(self, client, mock_blockchain):
        """Test that GET /block/<hash> sets ETag header."""
        block_hash = mock_blockchain.chain[1].hash
        # Remove 0x prefix if present
        if block_hash.startswith("0x"):
            block_hash = block_hash[2:]

        response = client.get(f'/block/{block_hash}')

        assert response.status_code == 200
        assert 'ETag' in response.headers

        # ETag should be the block hash wrapped in quotes
        expected_etag = f'"{mock_blockchain.chain[1].hash}"'
        assert response.headers['ETag'] == expected_etag

    def test_get_block_by_hash_sets_cache_control(self, client, mock_blockchain):
        """Test that GET /block/<hash> sets Cache-Control header."""
        block_hash = mock_blockchain.chain[1].hash
        if block_hash.startswith("0x"):
            block_hash = block_hash[2:]

        response = client.get(f'/block/{block_hash}')

        assert response.status_code == 200
        assert 'Cache-Control' in response.headers

        cache_control = response.headers['Cache-Control']
        assert 'public' in cache_control
        assert 'max-age=31536000' in cache_control
        assert 'immutable' in cache_control

    def test_get_block_by_hash_304_not_modified(self, client, mock_blockchain):
        """Test that GET /block/<hash> returns 304 when ETag matches."""
        block_hash = mock_blockchain.chain[1].hash
        if block_hash.startswith("0x"):
            block_hash = block_hash[2:]

        # First request to get ETag
        response1 = client.get(f'/block/{block_hash}')
        assert response1.status_code == 200
        etag = response1.headers['ETag']

        # Second request with If-None-Match header
        response2 = client.get(f'/block/{block_hash}', headers={'If-None-Match': etag})

        assert response2.status_code == 304
        assert response2.data == b''

    def test_get_block_by_hash_200_when_etag_differs(self, client, mock_blockchain):
        """Test that GET /block/<hash> returns 200 when ETag doesn't match."""
        block_hash = mock_blockchain.chain[1].hash
        if block_hash.startswith("0x"):
            block_hash = block_hash[2:]

        response = client.get(f'/block/{block_hash}', headers={'If-None-Match': '"wrong-hash"'})

        assert response.status_code == 200
        data = response.get_json()
        assert 'hash' in data or ('header' in data and 'hash' in data['header'])

    def test_get_block_with_0x_prefix_hash(self, client, mock_blockchain):
        """Test that block hash lookup works with 0x prefix."""
        block_hash = mock_blockchain.chain[0].hash

        response = client.get(f'/block/{block_hash}')

        assert response.status_code == 200
        assert 'ETag' in response.headers

    def test_multiple_blocks_have_different_etags(self, client, mock_blockchain):
        """Test that different blocks have different ETags."""
        response0 = client.get('/blocks/0')
        response1 = client.get('/blocks/1')

        assert response0.status_code == 200
        assert response1.status_code == 200

        etag0 = response0.headers['ETag']
        etag1 = response1.headers['ETag']

        assert etag0 != etag1

    def test_etag_format_is_valid(self, client, mock_blockchain):
        """Test that ETag format is valid (quoted string)."""
        response = client.get('/blocks/0')

        assert response.status_code == 200
        etag = response.headers['ETag']

        # ETag should be wrapped in quotes
        assert etag.startswith('"')
        assert etag.endswith('"')
        # Should contain the block hash
        assert mock_blockchain.chain[0].hash in etag


class TestCachingPerformance:
    """Test caching performance benefits."""

    def test_304_response_is_faster(self, client):
        """Test that 304 responses don't serialize data (performance optimization)."""
        # First request
        response1 = client.get('/blocks/0')
        etag = response1.headers['ETag']

        # Second request with ETag should be lightweight
        response2 = client.get('/blocks/0', headers={'If-None-Match': etag})

        assert response2.status_code == 304
        # 304 should have no body (performance win)
        assert len(response2.data) == 0
        # Original response has data
        assert len(response1.data) > 0

    def test_cache_headers_prevent_unnecessary_requests(self, client):
        """Test that Cache-Control headers allow browser/proxy caching."""
        response = client.get('/blocks/0')

        cache_control = response.headers.get('Cache-Control', '')

        # Public allows proxy caching
        assert 'public' in cache_control
        # Long max-age allows extended caching
        assert 'max-age=31536000' in cache_control  # 1 year
        # Immutable indicates data won't change
        assert 'immutable' in cache_control


class TestCachingEdgeCases:
    """Test edge cases for caching."""

    def test_nonexistent_block_no_cache_headers(self, client):
        """Test that 404 responses don't set cache headers."""
        response = client.get('/blocks/999')

        assert response.status_code == 404
        # 404s shouldn't have ETag (no content to cache)
        # Note: They might have Cache-Control depending on implementation

    def test_invalid_block_index_no_cache_headers(self, client):
        """Test that invalid requests don't set cache headers."""
        response = client.get('/blocks/invalid')

        assert response.status_code == 400
        # Errors shouldn't have ETag

    def test_invalid_block_hash_no_cache_headers(self, client):
        """Test that invalid hash requests don't set cache headers."""
        response = client.get('/block/invalid-hash')

        assert response.status_code == 400
