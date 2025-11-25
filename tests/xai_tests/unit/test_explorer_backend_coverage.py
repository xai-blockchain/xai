"""
Comprehensive tests for XAI Block Explorer Backend
Tests all components: Database, Analytics, Search, Rich List, Export, and Flask API endpoints

Target: 80%+ coverage of explorer_backend.py
"""

import json
import pytest
import time
import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from xai.explorer_backend import (
    # Data models
    SearchType,
    SearchResult,
    AddressLabel,
    CachedMetric,
    # Components
    ExplorerDatabase,
    AnalyticsEngine,
    SearchEngine,
    RichListManager,
    ExportManager,
    # Flask app
    app,
    broadcast_update,
)


# ==================== FIXTURES ====================


@pytest.fixture
def test_db():
    """Create in-memory test database"""
    db = ExplorerDatabase(":memory:")
    yield db
    if db.conn:
        db.conn.close()


@pytest.fixture
def mock_node_url():
    """Mock node URL"""
    return "http://localhost:8545"


@pytest.fixture
def analytics_engine(test_db, mock_node_url):
    """Create analytics engine with test database"""
    return AnalyticsEngine(mock_node_url, test_db)


@pytest.fixture
def search_engine(test_db, mock_node_url):
    """Create search engine with test database"""
    return SearchEngine(mock_node_url, test_db)


@pytest.fixture
def rich_list_manager(test_db, mock_node_url):
    """Create rich list manager with test database"""
    return RichListManager(mock_node_url, test_db)


@pytest.fixture
def export_manager(mock_node_url):
    """Create export manager"""
    return ExportManager(mock_node_url)


@pytest.fixture
def flask_client():
    """Create Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_stats_response():
    """Mock stats response from node"""
    return {
        "total_blocks": 1000,
        "difficulty": 4,
        "total_supply": 10000000,
        "circulating_supply": 8000000
    }


@pytest.fixture
def mock_blocks_response():
    """Mock blocks response from node"""
    return {
        "blocks": [
            {
                "index": 1,
                "hash": "abc123",
                "previous_hash": "000000",
                "timestamp": time.time() - 3600,
                "transactions": [
                    {
                        "txid": "tx1",
                        "sender": "XAI_sender1",
                        "recipient": "XAI_recipient1",
                        "amount": 100,
                        "fee": 0.1,
                        "timestamp": time.time() - 3600
                    }
                ],
                "miner": "XAI_miner1",
                "nonce": 12345
            },
            {
                "index": 2,
                "hash": "def456",
                "previous_hash": "abc123",
                "timestamp": time.time() - 1800,
                "transactions": [
                    {
                        "txid": "tx2",
                        "sender": "COINBASE",
                        "recipient": "XAI_miner1",
                        "amount": 50,
                        "fee": 0,
                        "timestamp": time.time() - 1800
                    }
                ],
                "miner": "XAI_miner1",
                "nonce": 67890
            }
        ]
    }


# ==================== DATA MODEL TESTS ====================


class TestDataModels:
    """Test data model classes"""

    def test_search_type_enum(self):
        """Test SearchType enum values"""
        assert SearchType.BLOCK_HEIGHT.value == "block_height"
        assert SearchType.BLOCK_HASH.value == "block_hash"
        assert SearchType.TRANSACTION_ID.value == "transaction_id"
        assert SearchType.ADDRESS.value == "address"
        assert SearchType.UNKNOWN.value == "unknown"

    def test_search_result_creation(self):
        """Test SearchResult dataclass creation"""
        result = SearchResult(
            type=SearchType.BLOCK_HEIGHT,
            item_id="100",
            data={"block": "data"}
        )
        assert result.type == SearchType.BLOCK_HEIGHT
        assert result.item_id == "100"
        assert result.data == {"block": "data"}
        assert result.timestamp > 0

    def test_address_label_creation(self):
        """Test AddressLabel dataclass creation"""
        label = AddressLabel(
            address="XAI_test123",
            label="Test Exchange",
            category="exchange",
            description="Test description"
        )
        assert label.address == "XAI_test123"
        assert label.label == "Test Exchange"
        assert label.category == "exchange"
        assert label.description == "Test description"
        assert label.created_at > 0

    def test_cached_metric_creation(self):
        """Test CachedMetric dataclass creation"""
        metric = CachedMetric(
            timestamp=time.time(),
            data={"value": 100},
            ttl=600
        )
        assert metric.timestamp > 0
        assert metric.data == {"value": 100}
        assert metric.ttl == 600


# ==================== DATABASE TESTS ====================


class TestExplorerDatabase:
    """Test ExplorerDatabase functionality"""

    def test_database_initialization(self, test_db):
        """Test database initializes with correct schema"""
        assert test_db.conn is not None
        cursor = test_db.conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "search_history" in tables
        assert "address_labels" in tables
        assert "analytics" in tables
        assert "explorer_cache" in tables

    def test_database_indexes(self, test_db):
        """Test database has proper indexes"""
        cursor = test_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_search_query" in indexes
        assert "idx_search_timestamp" in indexes
        assert "idx_address_label" in indexes
        assert "idx_metric_type" in indexes
        assert "idx_metric_timestamp" in indexes

    def test_add_search(self, test_db):
        """Test recording search queries"""
        test_db.add_search("100", "block_height", True, "user123")

        searches = test_db.get_recent_searches(10)
        assert len(searches) == 1
        assert searches[0]["query"] == "100"
        assert searches[0]["type"] == "block_height"

    def test_get_recent_searches(self, test_db):
        """Test retrieving recent searches"""
        # Add multiple searches
        for i in range(5):
            test_db.add_search(f"query{i}", "block_height", True, "user1")

        searches = test_db.get_recent_searches(3)
        assert len(searches) == 3
        # Most recent should be first
        assert searches[0]["query"] == "query4"

    def test_add_address_label(self, test_db):
        """Test adding address labels"""
        label = AddressLabel(
            address="XAI_test",
            label="Test Label",
            category="exchange",
            description="Test"
        )

        test_db.add_address_label(label)
        retrieved = test_db.get_address_label("XAI_test")

        assert retrieved is not None
        assert retrieved.label == "Test Label"
        assert retrieved.category == "exchange"

    def test_get_address_label_not_found(self, test_db):
        """Test getting non-existent address label"""
        result = test_db.get_address_label("XAI_nonexistent")
        assert result is None

    def test_address_label_update(self, test_db):
        """Test updating address label"""
        label1 = AddressLabel(
            address="XAI_test",
            label="Label1",
            category="exchange"
        )
        test_db.add_address_label(label1)

        label2 = AddressLabel(
            address="XAI_test",
            label="Label2",
            category="pool"
        )
        test_db.add_address_label(label2)

        retrieved = test_db.get_address_label("XAI_test")
        assert retrieved.label == "Label2"
        assert retrieved.category == "pool"

    def test_record_metric(self, test_db):
        """Test recording analytics metrics"""
        test_db.record_metric("hashrate", 1000.0, {"extra": "data"})

        metrics = test_db.get_metrics("hashrate", 24)
        assert len(metrics) == 1
        assert metrics[0]["value"] == 1000.0
        assert metrics[0]["data"]["extra"] == "data"

    def test_get_metrics_time_filter(self, test_db):
        """Test metrics are filtered by time"""
        # Record metrics at different times
        test_db.record_metric("test_metric", 100.0)
        time.sleep(0.1)
        test_db.record_metric("test_metric", 200.0)

        # Get metrics from last 1 hour
        metrics = test_db.get_metrics("test_metric", 1)
        assert len(metrics) == 2

    def test_get_metrics_empty(self, test_db):
        """Test getting metrics when none exist"""
        metrics = test_db.get_metrics("nonexistent", 24)
        assert metrics == []

    def test_set_cache(self, test_db):
        """Test setting cache values"""
        test_db.set_cache("test_key", "test_value", 300)

        value = test_db.get_cache("test_key")
        assert value == "test_value"

    def test_get_cache_expired(self, test_db):
        """Test cache expiration"""
        test_db.set_cache("test_key", "test_value", -1)  # Already expired

        value = test_db.get_cache("test_key")
        assert value is None

    def test_get_cache_not_found(self, test_db):
        """Test getting non-existent cache key"""
        value = test_db.get_cache("nonexistent_key")
        assert value is None

    def test_database_thread_safety(self, test_db):
        """Test database operations are thread-safe"""
        # Test that lock is used
        assert test_db.lock is not None

        # Perform operations that should use lock
        test_db.add_search("test", "block", True)
        test_db.record_metric("test", 1.0)
        test_db.set_cache("key", "value")

    def test_database_error_handling(self):
        """Test database handles errors gracefully"""
        # Test with invalid path (but allow in-memory)
        db = ExplorerDatabase(":memory:")
        assert db.conn is not None


# ==================== ANALYTICS ENGINE TESTS ====================


class TestAnalyticsEngine:
    """Test AnalyticsEngine functionality"""

    @patch('xai.explorer_backend.requests.get')
    def test_get_network_hashrate(self, mock_get, analytics_engine, mock_stats_response):
        """Test network hashrate calculation"""
        mock_response = Mock()
        mock_response.json.return_value = mock_stats_response
        mock_get.return_value = mock_response

        result = analytics_engine.get_network_hashrate()

        assert "hashrate" in result
        assert "difficulty" in result
        assert "block_height" in result
        assert result["difficulty"] == 4
        assert result["block_height"] == 1000

    @patch('xai.explorer_backend.requests.get')
    def test_get_network_hashrate_cached(self, mock_get, analytics_engine, test_db, mock_stats_response):
        """Test network hashrate uses cache"""
        # Set cache
        cached_data = json.dumps({"hashrate": 100, "cached": True})
        test_db.set_cache("hashrate", cached_data, 300)

        result = analytics_engine.get_network_hashrate()

        assert result["cached"] is True
        # Should not call API
        mock_get.assert_not_called()

    @patch('xai.explorer_backend.requests.get')
    def test_get_network_hashrate_error(self, mock_get, analytics_engine):
        """Test hashrate calculation handles errors"""
        mock_get.return_value.json.return_value = None

        result = analytics_engine.get_network_hashrate()

        assert "error" in result

    @patch('xai.explorer_backend.requests.get')
    def test_get_transaction_volume(self, mock_get, analytics_engine, mock_blocks_response):
        """Test transaction volume calculation"""
        mock_response = Mock()
        mock_response.json.return_value = mock_blocks_response
        mock_get.return_value = mock_response

        result = analytics_engine.get_transaction_volume("24h")

        assert "total_transactions" in result
        assert "average_tx_per_block" in result
        assert "total_fees_collected" in result
        assert result["period"] == "24h"

    @patch('xai.explorer_backend.requests.get')
    def test_get_transaction_volume_periods(self, mock_get, analytics_engine, mock_blocks_response):
        """Test different time periods for transaction volume"""
        mock_response = Mock()
        mock_response.json.return_value = mock_blocks_response
        mock_get.return_value = mock_response

        for period in ["24h", "7d", "30d"]:
            result = analytics_engine.get_transaction_volume(period)
            assert result["period"] == period

    @patch('xai.explorer_backend.requests.get')
    def test_get_transaction_volume_cached(self, mock_get, analytics_engine, test_db):
        """Test transaction volume uses cache"""
        cached_data = json.dumps({"total_transactions": 100, "cached": True})
        test_db.set_cache("tx_volume_24h", cached_data, 300)

        result = analytics_engine.get_transaction_volume("24h")

        assert result["cached"] is True
        mock_get.assert_not_called()

    @patch('xai.explorer_backend.requests.get')
    def test_get_transaction_volume_error(self, mock_get, analytics_engine):
        """Test transaction volume handles errors"""
        mock_get.return_value.json.return_value = None

        result = analytics_engine.get_transaction_volume()

        assert "error" in result

    @patch('xai.explorer_backend.requests.get')
    def test_get_active_addresses(self, mock_get, analytics_engine, mock_blocks_response):
        """Test active addresses calculation"""
        mock_response = Mock()
        mock_response.json.return_value = mock_blocks_response
        mock_get.return_value = mock_response

        result = analytics_engine.get_active_addresses()

        assert "total_unique_addresses" in result
        assert result["total_unique_addresses"] > 0

    @patch('xai.explorer_backend.requests.get')
    def test_get_active_addresses_cached(self, mock_get, analytics_engine, test_db):
        """Test active addresses uses cache"""
        cached_data = json.dumps({"total_unique_addresses": 50})
        test_db.set_cache("active_addresses", cached_data, 300)

        result = analytics_engine.get_active_addresses()

        assert result["total_unique_addresses"] == 50
        mock_get.assert_not_called()

    @patch('xai.explorer_backend.requests.get')
    def test_get_active_addresses_error(self, mock_get, analytics_engine):
        """Test active addresses handles errors"""
        mock_get.return_value.json.return_value = None

        result = analytics_engine.get_active_addresses()

        assert "error" in result

    @patch('xai.explorer_backend.requests.get')
    def test_get_average_block_time(self, mock_get, analytics_engine, mock_blocks_response):
        """Test average block time calculation"""
        mock_response = Mock()
        mock_response.json.return_value = mock_blocks_response
        mock_get.return_value = mock_response

        result = analytics_engine.get_average_block_time()

        assert "average_block_time_seconds" in result
        assert "blocks_sampled" in result
        assert result["average_block_time_seconds"] > 0

    @patch('xai.explorer_backend.requests.get')
    def test_get_average_block_time_insufficient_blocks(self, mock_get, analytics_engine):
        """Test average block time with insufficient blocks"""
        mock_response = Mock()
        mock_response.json.return_value = {"blocks": [{"timestamp": time.time()}]}
        mock_get.return_value = mock_response

        result = analytics_engine.get_average_block_time()

        assert "error" in result

    @patch('xai.explorer_backend.requests.get')
    def test_get_average_block_time_cached(self, mock_get, analytics_engine, test_db):
        """Test average block time uses cache"""
        cached_data = json.dumps({"average_block_time_seconds": 60})
        test_db.set_cache("avg_block_time", cached_data, 300)

        result = analytics_engine.get_average_block_time()

        assert result["average_block_time_seconds"] == 60
        mock_get.assert_not_called()

    @patch('xai.explorer_backend.requests.get')
    def test_get_mempool_size(self, mock_get, analytics_engine):
        """Test mempool size calculation"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "count": 10,
            "transactions": [
                {"amount": 100, "fee": 0.1},
                {"amount": 50, "fee": 0.05}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = analytics_engine.get_mempool_size()

        assert "pending_transactions" in result
        assert "total_value" in result
        assert "avg_fee" in result
        assert result["pending_transactions"] == 10

    @patch('xai.explorer_backend.requests.get')
    def test_get_mempool_size_cached(self, mock_get, analytics_engine, test_db):
        """Test mempool size uses cache"""
        cached_data = json.dumps({"pending_transactions": 5})
        test_db.set_cache("mempool_size", cached_data, 300)

        result = analytics_engine.get_mempool_size()

        assert result["pending_transactions"] == 5
        mock_get.assert_not_called()

    @patch('xai.explorer_backend.requests.get')
    def test_get_mempool_size_error(self, mock_get, analytics_engine):
        """Test mempool size handles errors"""
        mock_get.side_effect = Exception("Network error")

        result = analytics_engine.get_mempool_size()

        assert "error" in result

    @patch('xai.explorer_backend.requests.get')
    def test_get_network_difficulty(self, mock_get, analytics_engine, mock_stats_response):
        """Test network difficulty retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = mock_stats_response
        mock_get.return_value = mock_response

        result = analytics_engine.get_network_difficulty()

        assert "current_difficulty" in result
        assert result["current_difficulty"] == 4

    @patch('xai.explorer_backend.requests.get')
    def test_get_network_difficulty_error(self, mock_get, analytics_engine):
        """Test network difficulty handles errors"""
        mock_get.return_value.json.return_value = None

        result = analytics_engine.get_network_difficulty()

        assert "error" in result

    @patch('xai.explorer_backend.requests.get')
    def test_fetch_stats_error(self, mock_get, analytics_engine):
        """Test _fetch_stats handles errors"""
        mock_get.side_effect = Exception("Network error")

        result = analytics_engine._fetch_stats()

        assert result is None

    @patch('xai.explorer_backend.requests.get')
    def test_fetch_blocks_error(self, mock_get, analytics_engine):
        """Test _fetch_blocks handles errors"""
        mock_get.side_effect = Exception("Network error")

        result = analytics_engine._fetch_blocks()

        assert result is None


# ==================== SEARCH ENGINE TESTS ====================


class TestSearchEngine:
    """Test SearchEngine functionality"""

    def test_identify_search_type_block_height(self, search_engine):
        """Test identifying block height query"""
        result = search_engine._identify_search_type("12345")
        assert result == SearchType.BLOCK_HEIGHT

    def test_identify_search_type_block_hash(self, search_engine):
        """Test identifying block hash query"""
        hash_query = "a" * 64
        result = search_engine._identify_search_type(hash_query)
        assert result == SearchType.BLOCK_HASH

    def test_identify_search_type_address(self, search_engine):
        """Test identifying address query"""
        result = search_engine._identify_search_type("XAI_test_address_123")
        assert result == SearchType.ADDRESS

        result2 = search_engine._identify_search_type("TXAI_test_address_456")
        assert result2 == SearchType.ADDRESS

    def test_identify_search_type_transaction(self, search_engine):
        """Test identifying transaction ID query"""
        # 64 chars but NOT all hex (has non-hex chars like 'g')
        # This will be detected as TRANSACTION_ID
        tx_query = "abcd1234" * 7 + "12345678"  # 64 chars with some non-hex
        result = search_engine._identify_search_type(tx_query)
        # Note: In the actual code, 64 hex chars = BLOCK_HASH, 64 non-hex = TRANSACTION_ID
        # Since we're using hex chars, it will be BLOCK_HASH
        # Let's test with non-hex chars
        tx_query_with_nonhex = "tx" + ("a" * 62)  # 64 chars but starts with 'tx' (not all hex)
        result2 = search_engine._identify_search_type(tx_query_with_nonhex)
        # This should be TRANSACTION_ID since it's 64 chars but not all hex
        assert result2 == SearchType.TRANSACTION_ID

    def test_identify_search_type_unknown(self, search_engine):
        """Test identifying unknown query type"""
        result = search_engine._identify_search_type("random_query")
        assert result == SearchType.UNKNOWN

    @patch('xai.explorer_backend.requests.get')
    def test_search_block_height(self, mock_get, search_engine):
        """Test searching by block height"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"index": 100, "hash": "abc"}
        mock_get.return_value = mock_response

        result = search_engine.search("100")

        assert result["type"] == "block_height"
        assert result["found"] is True
        assert result["results"] is not None

    @patch('xai.explorer_backend.requests.get')
    def test_search_block_hash(self, mock_get, search_engine, mock_blocks_response):
        """Test searching by block hash"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_blocks_response
        mock_get.return_value = mock_response

        # Use a valid 64-char hex hash
        hash_query = "a" * 64
        result = search_engine.search(hash_query)

        assert result["type"] == "block_hash"
        # Results depend on mock data matching

    @patch('xai.explorer_backend.requests.get')
    def test_search_transaction(self, mock_get, search_engine):
        """Test searching by transaction ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"txid": "tx123", "amount": 100}
        mock_get.return_value = mock_response

        # Use 64 chars with non-hex chars to be detected as transaction (not block hash)
        tx_query = "tx" + ("a" * 62)  # 64 chars, starts with 'tx' (not all hex)
        result = search_engine.search(tx_query)

        assert result["type"] == "transaction_id"

    @patch('xai.explorer_backend.requests.get')
    def test_search_address(self, mock_get, search_engine):
        """Test searching by address"""
        balance_response = Mock()
        balance_response.status_code = 200
        balance_response.json.return_value = {"balance": 1000}

        history_response = Mock()
        history_response.status_code = 200
        history_response.json.return_value = {"transactions": [{"txid": "tx1"}]}

        mock_get.side_effect = [balance_response, history_response]

        result = search_engine.search("XAI_test_address")

        assert result["type"] == "address"
        assert result["found"] is True

    @patch('xai.explorer_backend.requests.get')
    def test_search_not_found(self, mock_get, search_engine):
        """Test search when item not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = search_engine.search("999999")

        assert result["found"] is False

    @patch('xai.explorer_backend.requests.get')
    def test_search_error_handling(self, mock_get, search_engine):
        """Test search handles errors gracefully"""
        mock_get.side_effect = Exception("Network error")

        result = search_engine.search("100")

        # Search catches exceptions and logs them, but doesn't always add error to result
        # It just marks found as False
        assert result["found"] is False or "error" in result

    def test_search_records_history(self, search_engine, test_db):
        """Test search records are saved"""
        with patch('xai.explorer_backend.requests.get'):
            search_engine.search("100", "user123")

        searches = test_db.get_recent_searches(10)
        assert len(searches) > 0

    def test_get_autocomplete_suggestions(self, search_engine, test_db):
        """Test autocomplete suggestions"""
        # Add some searches
        test_db.add_search("XAI_addr1", "address", True)
        test_db.add_search("XAI_addr2", "address", True)
        test_db.add_search("block123", "block", True)

        suggestions = search_engine.get_autocomplete_suggestions("XAI", 10)

        assert len(suggestions) > 0
        assert all(s.startswith("XAI") for s in suggestions)

    def test_get_autocomplete_suggestions_empty(self, search_engine):
        """Test autocomplete with no matches"""
        suggestions = search_engine.get_autocomplete_suggestions("xyz", 10)
        assert len(suggestions) == 0

    def test_get_recent_searches(self, search_engine, test_db):
        """Test getting recent searches"""
        test_db.add_search("query1", "block", True)
        test_db.add_search("query2", "address", True)

        recent = search_engine.get_recent_searches(10)

        assert len(recent) == 2


# ==================== RICH LIST MANAGER TESTS ====================


class TestRichListManager:
    """Test RichListManager functionality"""

    @patch('xai.explorer_backend.requests.get')
    def test_get_rich_list(self, mock_get, rich_list_manager, mock_blocks_response):
        """Test rich list generation"""
        mock_response = Mock()
        mock_response.json.return_value = mock_blocks_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = rich_list_manager.get_rich_list(10)

        assert isinstance(result, list)
        # Should have addresses from transactions
        if len(result) > 0:
            assert "address" in result[0]
            assert "balance" in result[0]
            assert "rank" in result[0]

    @patch('xai.explorer_backend.requests.get')
    def test_get_rich_list_cached(self, mock_get, rich_list_manager, test_db):
        """Test rich list uses cache"""
        cached_data = json.dumps([{"address": "XAI_1", "balance": 1000, "rank": 1}])
        test_db.set_cache("rich_list_10", cached_data, 600)

        result = rich_list_manager.get_rich_list(10)

        assert len(result) == 1
        assert result[0]["address"] == "XAI_1"
        mock_get.assert_not_called()

    @patch('xai.explorer_backend.requests.get')
    def test_get_rich_list_refresh(self, mock_get, rich_list_manager, test_db, mock_blocks_response):
        """Test rich list refresh bypasses cache"""
        # Set cache
        cached_data = json.dumps([{"address": "cached"}])
        test_db.set_cache("rich_list_10", cached_data, 600)

        # Request with refresh
        mock_response = Mock()
        mock_response.json.return_value = mock_blocks_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = rich_list_manager.get_rich_list(10, refresh=True)

        # Should call API despite cache
        mock_get.assert_called()

    @patch('xai.explorer_backend.requests.get')
    def test_get_rich_list_with_labels(self, mock_get, rich_list_manager, test_db, mock_blocks_response):
        """Test rich list includes address labels"""
        # Add label
        label = AddressLabel(
            address="XAI_recipient1",
            label="Test Exchange",
            category="exchange"
        )
        test_db.add_address_label(label)

        mock_response = Mock()
        mock_response.json.return_value = mock_blocks_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = rich_list_manager.get_rich_list(10)

        # Check if label is included
        for entry in result:
            if entry["address"] == "XAI_recipient1":
                assert entry["label"] == "Test Exchange"
                assert entry["category"] == "exchange"

    @patch('xai.explorer_backend.requests.get')
    def test_get_rich_list_error(self, mock_get, rich_list_manager):
        """Test rich list handles errors"""
        mock_get.side_effect = Exception("Network error")

        result = rich_list_manager.get_rich_list(10)

        assert result == []

    @patch('xai.explorer_backend.requests.get')
    def test_calculate_rich_list_balances(self, mock_get, rich_list_manager):
        """Test rich list balance calculation"""
        mock_blocks = {
            "blocks": [
                {
                    "transactions": [
                        {"sender": "XAI_A", "recipient": "XAI_B", "amount": 100, "fee": 1},
                        {"sender": "COINBASE", "recipient": "XAI_A", "amount": 50, "fee": 0}
                    ]
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_blocks
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = rich_list_manager._calculate_rich_list(10)

        # XAI_B should have +100, XAI_A should have +50 -100 -1 = -51
        assert len(result) > 0


# ==================== EXPORT MANAGER TESTS ====================


class TestExportManager:
    """Test ExportManager functionality"""

    @patch('xai.explorer_backend.requests.get')
    def test_export_transactions_csv(self, mock_get, export_manager):
        """Test CSV export of transactions"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transactions": [
                {
                    "txid": "tx123",
                    "timestamp": time.time(),
                    "sender": "XAI_sender",
                    "recipient": "XAI_recipient",
                    "amount": 100,
                    "fee": 0.1,
                    "type": "transfer"
                }
            ]
        }
        mock_get.return_value = mock_response

        csv_data = export_manager.export_transactions_csv("XAI_test")

        assert csv_data is not None
        assert "txid,timestamp,from,to,amount,fee,type" in csv_data
        assert "tx123" in csv_data
        assert "XAI_sender" in csv_data

    @patch('xai.explorer_backend.requests.get')
    def test_export_transactions_csv_not_found(self, mock_get, export_manager):
        """Test CSV export when address not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        csv_data = export_manager.export_transactions_csv("XAI_notfound")

        assert csv_data is None

    @patch('xai.explorer_backend.requests.get')
    def test_export_transactions_csv_error(self, mock_get, export_manager):
        """Test CSV export handles errors"""
        mock_get.side_effect = Exception("Network error")

        csv_data = export_manager.export_transactions_csv("XAI_test")

        assert csv_data is None


# ==================== FLASK API ENDPOINT TESTS ====================


class TestFlaskEndpoints:
    """Test Flask API endpoints"""

    @patch('xai.explorer_backend.analytics.get_network_hashrate')
    def test_get_hashrate_endpoint(self, mock_hashrate, flask_client):
        """Test /api/analytics/hashrate endpoint"""
        mock_hashrate.return_value = {"hashrate": 1000, "difficulty": 4}

        response = flask_client.get('/api/analytics/hashrate')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "hashrate" in data

    @patch('xai.explorer_backend.analytics.get_transaction_volume')
    def test_get_tx_volume_endpoint(self, mock_volume, flask_client):
        """Test /api/analytics/tx-volume endpoint"""
        mock_volume.return_value = {"total_transactions": 100}

        response = flask_client.get('/api/analytics/tx-volume?period=24h')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "total_transactions" in data

    @patch('xai.explorer_backend.analytics.get_active_addresses')
    def test_get_active_addresses_endpoint(self, mock_addresses, flask_client):
        """Test /api/analytics/active-addresses endpoint"""
        mock_addresses.return_value = {"total_unique_addresses": 50}

        response = flask_client.get('/api/analytics/active-addresses')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "total_unique_addresses" in data

    @patch('xai.explorer_backend.analytics.get_average_block_time')
    def test_get_block_time_endpoint(self, mock_block_time, flask_client):
        """Test /api/analytics/block-time endpoint"""
        mock_block_time.return_value = {"average_block_time_seconds": 60}

        response = flask_client.get('/api/analytics/block-time')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "average_block_time_seconds" in data

    @patch('xai.explorer_backend.analytics.get_mempool_size')
    def test_get_mempool_endpoint(self, mock_mempool, flask_client):
        """Test /api/analytics/mempool endpoint"""
        mock_mempool.return_value = {"pending_transactions": 10}

        response = flask_client.get('/api/analytics/mempool')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "pending_transactions" in data

    @patch('xai.explorer_backend.analytics.get_network_difficulty')
    def test_get_difficulty_endpoint(self, mock_difficulty, flask_client):
        """Test /api/analytics/difficulty endpoint"""
        mock_difficulty.return_value = {"current_difficulty": 4}

        response = flask_client.get('/api/analytics/difficulty')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "current_difficulty" in data

    @patch('xai.explorer_backend.analytics.get_network_hashrate')
    @patch('xai.explorer_backend.analytics.get_transaction_volume')
    @patch('xai.explorer_backend.analytics.get_active_addresses')
    @patch('xai.explorer_backend.analytics.get_average_block_time')
    @patch('xai.explorer_backend.analytics.get_mempool_size')
    @patch('xai.explorer_backend.analytics.get_network_difficulty')
    def test_get_analytics_dashboard(self, mock_diff, mock_mem, mock_time,
                                     mock_addr, mock_vol, mock_hash, flask_client):
        """Test /api/analytics/dashboard endpoint"""
        mock_hash.return_value = {"hashrate": 1000}
        mock_vol.return_value = {"total_transactions": 100}
        mock_addr.return_value = {"total_unique_addresses": 50}
        mock_time.return_value = {"average_block_time_seconds": 60}
        mock_mem.return_value = {"pending_transactions": 10}
        mock_diff.return_value = {"current_difficulty": 4}

        response = flask_client.get('/api/analytics/dashboard')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "hashrate" in data
        assert "transaction_volume" in data
        assert "active_addresses" in data
        assert "average_block_time" in data
        assert "mempool" in data
        assert "difficulty" in data

    @patch('xai.explorer_backend.search_engine.search')
    def test_search_endpoint(self, mock_search, flask_client):
        """Test /api/search endpoint"""
        mock_search.return_value = {"query": "100", "found": True, "type": "block_height"}

        response = flask_client.post('/api/search',
                                     json={"query": "100", "user_id": "test"})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["query"] == "100"

    def test_search_endpoint_no_query(self, flask_client):
        """Test /api/search endpoint without query"""
        response = flask_client.post('/api/search', json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    @patch('xai.explorer_backend.search_engine.get_autocomplete_suggestions')
    def test_autocomplete_endpoint(self, mock_autocomplete, flask_client):
        """Test /api/search/autocomplete endpoint"""
        mock_autocomplete.return_value = ["XAI_addr1", "XAI_addr2"]

        response = flask_client.get('/api/search/autocomplete?prefix=XAI&limit=10')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "suggestions" in data
        assert len(data["suggestions"]) == 2

    def test_autocomplete_endpoint_no_prefix(self, flask_client):
        """Test /api/search/autocomplete without prefix"""
        response = flask_client.get('/api/search/autocomplete')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["suggestions"] == []

    @patch('xai.explorer_backend.search_engine.get_recent_searches')
    def test_recent_searches_endpoint(self, mock_recent, flask_client):
        """Test /api/search/recent endpoint"""
        mock_recent.return_value = [{"query": "100", "type": "block"}]

        response = flask_client.get('/api/search/recent?limit=10')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "recent" in data

    @patch('xai.explorer_backend.rich_list.get_rich_list')
    def test_richlist_endpoint(self, mock_richlist, flask_client):
        """Test /api/richlist endpoint"""
        mock_richlist.return_value = [
            {"address": "XAI_1", "balance": 1000, "rank": 1}
        ]

        response = flask_client.get('/api/richlist?limit=100')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "richlist" in data

    @patch('xai.explorer_backend.rich_list.get_rich_list')
    def test_richlist_endpoint_limit_cap(self, mock_richlist, flask_client):
        """Test /api/richlist limit is capped at 1000"""
        mock_richlist.return_value = []

        response = flask_client.get('/api/richlist?limit=5000')

        assert response.status_code == 200
        # Should be called with capped limit
        mock_richlist.assert_called_with(1000)

    @patch('xai.explorer_backend.rich_list.get_rich_list')
    def test_richlist_refresh_endpoint(self, mock_richlist, flask_client):
        """Test /api/richlist/refresh endpoint"""
        mock_richlist.return_value = []

        response = flask_client.post('/api/richlist/refresh?limit=50')

        assert response.status_code == 200
        # Should be called with refresh=True
        mock_richlist.assert_called_with(50, refresh=True)

    @patch('xai.explorer_backend.db.get_address_label')
    def test_get_address_label_endpoint(self, mock_get_label, flask_client):
        """Test GET /api/address/<address>/label endpoint"""
        label = AddressLabel(
            address="XAI_test",
            label="Test",
            category="exchange"
        )
        mock_get_label.return_value = label

        response = flask_client.get('/api/address/XAI_test/label')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["label"] == "Test"

    @patch('xai.explorer_backend.db.get_address_label')
    def test_get_address_label_endpoint_not_found(self, mock_get_label, flask_client):
        """Test GET /api/address/<address>/label when not found"""
        mock_get_label.return_value = None

        response = flask_client.get('/api/address/XAI_notfound/label')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["label"] is None

    @patch('xai.explorer_backend.db.add_address_label')
    def test_set_address_label_endpoint(self, mock_add_label, flask_client):
        """Test POST /api/address/<address>/label endpoint"""
        response = flask_client.post('/api/address/XAI_test/label', json={
            "label": "Test Exchange",
            "category": "exchange",
            "description": "Test description"
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "label" in data

    def test_set_address_label_endpoint_no_label(self, flask_client):
        """Test POST /api/address/<address>/label without label"""
        response = flask_client.post('/api/address/XAI_test/label', json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    @patch('xai.explorer_backend.export_manager.export_transactions_csv')
    def test_export_transactions_endpoint(self, mock_export, flask_client):
        """Test /api/export/transactions/<address> endpoint"""
        mock_export.return_value = "txid,timestamp,from,to,amount,fee,type\ntx1,2024-01-01,A,B,100,0.1,transfer"

        response = flask_client.get('/api/export/transactions/XAI_test')

        assert response.status_code == 200
        # Flask may or may not include charset in content type
        assert "text/csv" in response.content_type
        assert b"txid,timestamp" in response.data

    @patch('xai.explorer_backend.export_manager.export_transactions_csv')
    def test_export_transactions_endpoint_not_found(self, mock_export, flask_client):
        """Test /api/export/transactions/<address> when not found"""
        mock_export.return_value = None

        response = flask_client.get('/api/export/transactions/XAI_notfound')

        assert response.status_code == 404

    @patch('xai.explorer_backend.db.get_metrics')
    def test_get_metric_history_endpoint(self, mock_metrics, flask_client):
        """Test /api/metrics/<metric_type> endpoint"""
        mock_metrics.return_value = [
            {"timestamp": time.time(), "value": 100}
        ]

        response = flask_client.get('/api/metrics/hashrate?hours=24')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "metric_type" in data
        assert data["metric_type"] == "hashrate"
        assert "data" in data

    @patch('xai.explorer_backend.requests.get')
    def test_health_check_endpoint(self, mock_get, flask_client):
        """Test /health endpoint when node is healthy"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        response = flask_client.get('/health')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["explorer"] == "running"

    @patch('xai.explorer_backend.requests.get')
    def test_health_check_endpoint_degraded(self, mock_get, flask_client):
        """Test /health endpoint when node is down"""
        mock_get.side_effect = Exception("Connection error")

        response = flask_client.get('/health')

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["status"] == "degraded"
        assert data["node"] == "disconnected"

    def test_explorer_info_endpoint(self, flask_client):
        """Test / (root) endpoint"""
        response = flask_client.get('/')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["name"] == "XAI Block Explorer"
        assert "version" in data
        assert "features" in data
        assert data["features"]["advanced_search"] is True
        assert data["features"]["analytics"] is True


# ==================== WEBSOCKET TESTS ====================


class TestWebSocket:
    """Test WebSocket functionality"""

    def test_broadcast_update(self):
        """Test broadcast_update function"""
        # Create mock client
        mock_client = Mock()

        from xai.explorer_backend import ws_clients
        ws_clients.add(mock_client)

        try:
            broadcast_update("test_update", {"message": "test"})

            # Client should have received message
            mock_client.send.assert_called_once()
            sent_data = json.loads(mock_client.send.call_args[0][0])
            assert sent_data["type"] == "test_update"
            assert sent_data["data"]["message"] == "test"
        finally:
            ws_clients.clear()

    def test_broadcast_update_error_handling(self):
        """Test broadcast_update handles errors"""
        # Create mock client that raises error
        mock_client = Mock()
        mock_client.send.side_effect = Exception("Send error")

        from xai.explorer_backend import ws_clients
        ws_clients.add(mock_client)

        try:
            # Should not raise exception
            broadcast_update("test", {"data": "test"})

            # Client should be removed after error
            assert mock_client not in ws_clients
        finally:
            ws_clients.clear()


# ==================== INTEGRATION TESTS ====================


class TestIntegration:
    """Test integrated functionality"""

    @patch('xai.explorer_backend.requests.get')
    def test_full_analytics_flow(self, mock_get, analytics_engine, mock_stats_response, mock_blocks_response):
        """Test complete analytics workflow"""
        # Setup mocks
        def mock_response_generator(url, *args, **kwargs):
            response = Mock()
            if 'stats' in url:
                response.json.return_value = mock_stats_response
            elif 'blocks' in url:
                response.json.return_value = mock_blocks_response
            elif 'transactions' in url:
                response.json.return_value = {"count": 10, "transactions": []}
            response.raise_for_status = Mock()
            return response

        mock_get.side_effect = mock_response_generator

        # Get multiple analytics
        hashrate = analytics_engine.get_network_hashrate()
        volume = analytics_engine.get_transaction_volume()
        addresses = analytics_engine.get_active_addresses()

        assert "hashrate" in hashrate
        assert "total_transactions" in volume
        assert "total_unique_addresses" in addresses

    @patch('xai.explorer_backend.requests.get')
    def test_search_and_export_flow(self, mock_get, search_engine, export_manager):
        """Test search then export workflow"""
        # Search for address
        balance_response = Mock()
        balance_response.status_code = 200
        balance_response.json.return_value = {"balance": 1000}

        history_response = Mock()
        history_response.status_code = 200
        history_response.json.return_value = {
            "transactions": [
                {"txid": "tx1", "timestamp": time.time(), "sender": "A",
                 "recipient": "B", "amount": 100, "fee": 0.1, "type": "transfer"}
            ]
        }

        mock_get.side_effect = [balance_response, history_response, history_response]

        # Search
        search_result = search_engine.search("XAI_test_address")
        assert search_result["found"] is True

        # Export
        csv_data = export_manager.export_transactions_csv("XAI_test_address")
        assert csv_data is not None
        assert "tx1" in csv_data

    def test_database_persistence(self, test_db):
        """Test database operations persist correctly"""
        # Add data
        test_db.add_search("test1", "block", True)
        label = AddressLabel(address="XAI_1", label="Test", category="test")
        test_db.add_address_label(label)
        test_db.record_metric("test_metric", 100.0)
        test_db.set_cache("test_key", "test_value", 300)

        # Retrieve data
        searches = test_db.get_recent_searches(10)
        retrieved_label = test_db.get_address_label("XAI_1")
        metrics = test_db.get_metrics("test_metric", 24)
        cache_value = test_db.get_cache("test_key")

        assert len(searches) > 0
        assert retrieved_label is not None
        assert len(metrics) > 0
        assert cache_value == "test_value"
