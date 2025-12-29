"""
Unit tests for mobile telemetry system

Tests:
- MobileTelemetryCollector event recording and aggregation
- NetworkOptimizer adaptive optimization
- API endpoints for telemetry submission
"""

import time
import json
import gzip
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from xai.mobile.telemetry import (
    MobileTelemetryCollector,
    TelemetryEvent,
    AggregatedStats
)
from xai.mobile.network_optimizer import (
    NetworkOptimizer,
    NetworkProfile,
    ConnectionType,
    BandwidthMode,
    QueuedTransaction
)
from xai.core.api.api_mobile_telemetry import MobileTelemetryAPIHandler


class TestTelemetryEvent:
    """Test TelemetryEvent data structure"""

    def test_create_event(self):
        """Test creating telemetry event"""
        event = TelemetryEvent(
            event_type='sync',
            timestamp=time.time(),
            client_id='test_device_123',
            bytes_sent=1024,
            bytes_received=2048,
            duration_ms=150.5,
            connection_type='wifi'
        )

        assert event.event_type == 'sync'
        assert event.bytes_sent == 1024
        assert event.bytes_received == 2048
        assert event.total_bytes() == 3072

    def test_battery_drain(self):
        """Test battery drain calculation"""
        event = TelemetryEvent(
            event_type='sync',
            timestamp=time.time(),
            client_id='test_device',
            battery_level_start=95.0,
            battery_level_end=93.5
        )

        assert event.battery_drain() == 1.5

    def test_battery_drain_none(self):
        """Test battery drain when not tracked"""
        event = TelemetryEvent(
            event_type='sync',
            timestamp=time.time(),
            client_id='test_device'
        )

        assert event.battery_drain() is None

    def test_bytes_per_second(self):
        """Test throughput calculation"""
        event = TelemetryEvent(
            event_type='sync',
            timestamp=time.time(),
            client_id='test_device',
            bytes_sent=1000,
            bytes_received=2000,
            duration_ms=1000  # 1 second
        )

        # 3000 bytes / 1 second = 3000 bytes/sec
        assert event.bytes_per_second() == 3000.0

    def test_to_dict_from_dict(self):
        """Test serialization round-trip"""
        event = TelemetryEvent(
            event_type='api_call',
            timestamp=1234567890.0,
            client_id='device_abc',
            bytes_sent=500,
            bytes_received=1500,
            metadata={'endpoint': '/api/v1/sync', 'method': 'POST'}
        )

        data = event.to_dict()
        restored = TelemetryEvent.from_dict(data)

        assert restored.event_type == event.event_type
        assert restored.client_id == event.client_id
        assert restored.metadata == event.metadata


class TestMobileTelemetryCollector:
    """Test MobileTelemetryCollector functionality"""

    def test_record_event(self):
        """Test recording individual events"""
        collector = MobileTelemetryCollector(max_events=100)

        event = TelemetryEvent(
            event_type='sync',
            timestamp=time.time(),
            client_id='device_1',
            bytes_sent=1024,
            bytes_received=2048
        )

        assert collector.record_event(event) is True
        assert len(collector._events) == 1

    def test_record_sync_event(self):
        """Test recording sync event convenience method"""
        collector = MobileTelemetryCollector()

        collector.record_sync_event(
            client_id='device_1',
            bytes_sent=1000,
            bytes_received=5000,
            duration_ms=200,
            connection_type='wifi',
            blocks_synced=10,
            battery_start=95.0,
            battery_end=94.5
        )

        assert len(collector._events) == 1
        event = collector._events[0]
        assert event.event_type == 'sync'
        assert event.bytes_sent == 1000
        assert event.bytes_received == 5000
        assert event.metadata['blocks_synced'] == 10

    def test_record_api_call(self):
        """Test recording API call event"""
        collector = MobileTelemetryCollector()

        collector.record_api_call(
            client_id='device_1',
            endpoint='/api/v1/blocks',
            method='GET',
            bytes_sent=100,
            bytes_received=5000,
            latency_ms=50,
            duration_ms=150,
            connection_type='cellular',
            status_code=200
        )

        assert len(collector._events) == 1
        event = collector._events[0]
        assert event.event_type == 'api_call'
        assert event.metadata['endpoint'] == '/api/v1/blocks'
        assert event.metadata['status_code'] == 200

    def test_max_events_pruning(self):
        """Test that old events are pruned when limit exceeded"""
        collector = MobileTelemetryCollector(max_events=10)

        # Record 20 events
        for i in range(20):
            event = TelemetryEvent(
                event_type='sync',
                timestamp=time.time() + i,
                client_id=f'device_{i}',
                bytes_sent=i * 100
            )
            collector.record_event(event)

        # Should only keep last 10
        assert len(collector._events) == 10
        # First event should be from iteration 10 (bytes_sent=1000)
        assert collector._events[0].bytes_sent == 1000

    def test_get_stats_all_events(self):
        """Test getting aggregated statistics"""
        collector = MobileTelemetryCollector()

        # Record multiple events
        for i in range(5):
            collector.record_sync_event(
                client_id=f'device_{i}',
                bytes_sent=1000,
                bytes_received=2000,
                duration_ms=100 + i * 10,
                connection_type='wifi',
                battery_start=95.0,
                battery_end=94.0
            )

        stats = collector.get_stats()

        assert stats.event_count == 5
        assert stats.total_bytes_sent == 5000
        assert stats.total_bytes_received == 10000
        assert stats.avg_duration_ms == 120  # (100 + 110 + 120 + 130 + 140) / 5
        assert stats.connection_types['wifi'] == 5

    def test_get_stats_with_filters(self):
        """Test getting stats with filters"""
        collector = MobileTelemetryCollector()

        # Record different event types
        collector.record_sync_event(
            client_id='device_1',
            bytes_sent=1000,
            bytes_received=2000,
            duration_ms=100,
            connection_type='wifi'
        )

        collector.record_api_call(
            client_id='device_1',
            endpoint='/api/v1/blocks',
            method='GET',
            bytes_sent=100,
            bytes_received=500,
            latency_ms=50,
            duration_ms=75,
            connection_type='cellular'
        )

        # Filter by event type
        stats = collector.get_stats(event_type='sync')
        assert stats.event_count == 1
        assert stats.total_bytes_sent == 1000

        # Filter by connection type
        stats = collector.get_stats(connection_type='cellular')
        assert stats.event_count == 1
        assert stats.total_bytes_sent == 100

    def test_get_bandwidth_by_operation(self):
        """Test bandwidth breakdown by operation type"""
        collector = MobileTelemetryCollector()

        collector.record_sync_event(
            client_id='device_1',
            bytes_sent=1000,
            bytes_received=5000,
            duration_ms=100,
            connection_type='wifi'
        )

        collector.record_transaction(
            client_id='device_1',
            tx_size_bytes=250,
            broadcast_latency_ms=50,
            connection_type='wifi'
        )

        breakdown = collector.get_bandwidth_by_operation()

        assert 'sync' in breakdown
        assert breakdown['sync']['bytes_sent'] == 1000
        assert breakdown['sync']['bytes_received'] == 5000
        assert breakdown['sync']['total'] == 6000

        assert 'transaction' in breakdown
        assert breakdown['transaction']['bytes_sent'] == 250

    def test_get_battery_impact_by_operation(self):
        """Test battery impact breakdown"""
        collector = MobileTelemetryCollector()

        # Sync with battery drain
        collector.record_sync_event(
            client_id='device_1',
            bytes_sent=1000,
            bytes_received=5000,
            duration_ms=200,
            connection_type='wifi',
            battery_start=95.0,
            battery_end=94.0
        )

        collector.record_sync_event(
            client_id='device_1',
            bytes_sent=1000,
            bytes_received=5000,
            duration_ms=200,
            connection_type='wifi',
            battery_start=94.0,
            battery_end=92.5
        )

        breakdown = collector.get_battery_impact_by_operation()

        assert 'sync' in breakdown
        assert breakdown['sync']['total_drain'] == 2.5  # 1.0 + 1.5
        assert breakdown['sync']['avg_drain'] == 1.25  # 2.5 / 2
        assert breakdown['sync']['event_count'] == 2

    def test_get_performance_trends(self):
        """Test performance trends over time"""
        collector = MobileTelemetryCollector()

        base_time = time.time()

        # Record events across multiple time buckets
        for i in range(10):
            collector.record_api_call(
                client_id='device_1',
                endpoint='/api/v1/sync',
                method='POST',
                bytes_sent=100,
                bytes_received=1000,
                latency_ms=50 + i * 5,
                duration_ms=100,
                connection_type='wifi'
            )
            # Manually set timestamp to spread across buckets
            collector._events[-1].timestamp = base_time + i * 3600  # 1 hour apart

        trends = collector.get_performance_trends(hours=24, bucket_size_minutes=60)

        # Should have multiple buckets
        assert len(trends) > 0
        # Each bucket should have metrics
        for bucket in trends:
            assert 'timestamp' in bucket
            assert 'event_count' in bucket
            assert 'avg_latency_ms' in bucket

    def test_clear_events(self):
        """Test clearing all events"""
        collector = MobileTelemetryCollector()

        for i in range(5):
            collector.record_sync_event(
                client_id=f'device_{i}',
                bytes_sent=1000,
                bytes_received=2000,
                duration_ms=100,
                connection_type='wifi'
            )

        assert len(collector._events) == 5

        count = collector.clear_events()
        assert count == 5
        assert len(collector._events) == 0

    def test_export_events(self):
        """Test exporting events"""
        collector = MobileTelemetryCollector()

        for i in range(10):
            collector.record_sync_event(
                client_id=f'device_{i}',
                bytes_sent=1000,
                bytes_received=2000,
                duration_ms=100,
                connection_type='wifi'
            )

        # Export all
        exported = collector.export_events()
        assert len(exported) == 10

        # Export limited
        exported = collector.export_events(max_events=5)
        assert len(exported) == 5

    def test_get_summary(self):
        """Test comprehensive summary"""
        collector = MobileTelemetryCollector()

        collector.record_sync_event(
            client_id='device_1',
            bytes_sent=1000,
            bytes_received=5000,
            duration_ms=200,
            connection_type='wifi',
            battery_start=95.0,
            battery_end=94.0
        )

        summary = collector.get_summary()

        assert 'overall' in summary
        assert 'bandwidth_by_operation' in summary
        assert 'battery_by_operation' in summary
        assert 'total_events' in summary
        assert summary['total_events'] == 1


class TestNetworkProfile:
    """Test NetworkProfile functionality"""

    def test_quality_score_excellent(self):
        """Test quality score for excellent connection"""
        profile = NetworkProfile(
            connection_type=ConnectionType.WIFI,
            signal_strength=5,
            estimated_bandwidth_kbps=10000,
            latency_ms=20,
            packet_loss_percent=0
        )

        score = profile.quality_score()
        assert score >= 0.9

    def test_quality_score_poor(self):
        """Test quality score for poor connection"""
        profile = NetworkProfile(
            connection_type=ConnectionType.CELLULAR,
            signal_strength=1,
            estimated_bandwidth_kbps=100,
            latency_ms=500,
            packet_loss_percent=10
        )

        score = profile.quality_score()
        assert score < 0.5

    def test_recommended_mode(self):
        """Test bandwidth mode recommendations"""
        # Excellent connection
        profile = NetworkProfile(
            connection_type=ConnectionType.WIFI,
            signal_strength=5,
            estimated_bandwidth_kbps=10000,
            latency_ms=20,
            packet_loss_percent=0
        )
        assert profile.recommended_mode() == BandwidthMode.FULL

        # Poor connection
        profile = NetworkProfile(
            connection_type=ConnectionType.CELLULAR,
            signal_strength=1,
            estimated_bandwidth_kbps=100,
            latency_ms=500,
            packet_loss_percent=10
        )
        assert profile.recommended_mode() in [BandwidthMode.LOW, BandwidthMode.MINIMAL]

        # Offline
        profile = NetworkProfile(
            connection_type=ConnectionType.OFFLINE,
            signal_strength=0,
            estimated_bandwidth_kbps=0,
            latency_ms=0
        )
        assert profile.recommended_mode() == BandwidthMode.MINIMAL

    def test_recommended_batch_size(self):
        """Test batch size recommendations"""
        # Good connection
        profile = NetworkProfile(
            connection_type=ConnectionType.WIFI,
            signal_strength=5,
            estimated_bandwidth_kbps=10000,
            latency_ms=20,
            packet_loss_percent=0
        )
        assert profile.recommended_batch_size(50) == 50

        # Poor connection
        profile = NetworkProfile(
            connection_type=ConnectionType.CELLULAR,
            signal_strength=1,
            estimated_bandwidth_kbps=100,
            latency_ms=500,
            packet_loss_percent=10
        )
        batch_size = profile.recommended_batch_size(50)
        assert batch_size < 50
        assert batch_size >= 1


class TestNetworkOptimizer:
    """Test NetworkOptimizer functionality"""

    def test_update_network_profile(self):
        """Test updating network profile"""
        optimizer = NetworkOptimizer()

        profile = optimizer.update_network_profile(
            connection_type='wifi',
            signal_strength=4,
            latency_ms=30,
            estimated_bandwidth_kbps=5000
        )

        assert profile.connection_type == ConnectionType.WIFI
        assert profile.signal_strength == 4
        assert profile.latency_ms == 30

        current = optimizer.get_current_profile()
        assert current is not None
        assert current.connection_type == ConnectionType.WIFI

    def test_get_recommended_batch_size(self):
        """Test getting recommended batch size"""
        optimizer = NetworkOptimizer()

        # Set good connection
        optimizer.update_network_profile(
            connection_type='wifi',
            signal_strength=5,
            latency_ms=20,
            estimated_bandwidth_kbps=10000
        )

        batch_size = optimizer.get_recommended_batch_size('sync')
        assert batch_size == 50  # Full size for good connection

    def test_compression_decision(self):
        """Test compression decision logic"""
        optimizer = NetworkOptimizer(
            enable_compression=True,
            compression_threshold_bytes=1024
        )

        # Set low bandwidth mode
        optimizer.update_network_profile(
            connection_type='cellular',
            signal_strength=2,
            latency_ms=200,
            estimated_bandwidth_kbps=500
        )

        # Should compress large data
        assert optimizer.should_compress(5000) is True

        # Should not compress small data
        assert optimizer.should_compress(500) is False

    def test_compress_response(self):
        """Test response compression"""
        optimizer = NetworkOptimizer(enable_compression=True)

        data = {'blocks': [{'height': i, 'data': 'x' * 1000} for i in range(10)]}

        compressed, was_compressed = optimizer.compress_response(data)

        if was_compressed:
            # Verify it's actually compressed
            assert len(compressed) < len(json.dumps(data).encode('utf-8'))
            # Verify we can decompress
            decompressed_data = optimizer.decompress_request(compressed)
            assert decompressed_data == data

    def test_queue_transaction(self):
        """Test queuing transactions"""
        optimizer = NetworkOptimizer(max_queue_size=10)

        tx_data = {'from': 'addr1', 'to': 'addr2', 'amount': 100}

        assert optimizer.queue_transaction('tx_1', tx_data, priority=1) is True
        assert optimizer.queue_transaction('tx_1', tx_data, priority=1) is False  # Duplicate

        queued = optimizer.get_queued_transactions()
        assert len(queued) == 1
        assert queued[0].tx_id == 'tx_1'

    def test_queue_priority_ordering(self):
        """Test that queue maintains priority order"""
        optimizer = NetworkOptimizer()

        optimizer.queue_transaction('tx_low', {'data': 'low'}, priority=1)
        optimizer.queue_transaction('tx_high', {'data': 'high'}, priority=10)
        optimizer.queue_transaction('tx_med', {'data': 'med'}, priority=5)

        queued = optimizer.get_queued_transactions()

        # Should be ordered by priority (descending)
        assert queued[0].tx_id == 'tx_high'
        assert queued[1].tx_id == 'tx_med'
        assert queued[2].tx_id == 'tx_low'

    def test_remove_transaction(self):
        """Test removing transaction from queue"""
        optimizer = NetworkOptimizer()

        optimizer.queue_transaction('tx_1', {'data': 'test'}, priority=1)
        optimizer.queue_transaction('tx_2', {'data': 'test'}, priority=1)

        assert len(optimizer.get_queued_transactions()) == 2

        assert optimizer.remove_transaction('tx_1') is True
        assert len(optimizer.get_queued_transactions()) == 1

        assert optimizer.remove_transaction('tx_1') is False  # Already removed

    def test_optimize_sync_params(self):
        """Test sync parameter optimization"""
        optimizer = NetworkOptimizer()

        # Set very poor connection (to trigger LOW mode)
        optimizer.update_network_profile(
            connection_type='cellular',
            signal_strength=1,
            latency_ms=500,
            estimated_bandwidth_kbps=100
        )

        base_params = {
            'batch_size': 50,
            'poll_interval': 30,
            'include_full_blocks': True,
            'include_tx_details': True
        }

        optimized = optimizer.optimize_sync_params(base_params)

        # Should reduce batch size
        assert optimized['batch_size'] < base_params['batch_size']
        # Should increase poll interval
        assert optimized['poll_interval'] >= base_params['poll_interval']
        # Should disable optional data
        assert optimized['include_full_blocks'] is False
        # Should enable compression
        assert optimized['use_compression'] is True

    def test_get_stats(self):
        """Test getting optimizer stats"""
        optimizer = NetworkOptimizer()

        optimizer.update_network_profile(
            connection_type='wifi',
            signal_strength=4,
            latency_ms=30
        )

        optimizer.queue_transaction('tx_1', {'data': 'test'}, priority=1)

        stats = optimizer.get_stats()

        assert 'current_profile' in stats
        assert 'bandwidth_mode' in stats
        assert 'queue_status' in stats
        assert stats['queue_status']['total_queued'] == 1


class TestMobileTelemetryAPI:
    """Test Mobile Telemetry API endpoints"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        flask_app = Flask(__name__)
        flask_app.config['TESTING'] = True
        return flask_app

    @pytest.fixture
    def node(self):
        """Mock blockchain node"""
        return Mock()

    @pytest.fixture
    def api_handler(self, node, app):
        """Create API handler"""
        return MobileTelemetryAPIHandler(node, app)

    @pytest.fixture
    def client(self, app):
        """Flask test client"""
        return app.test_client()

    def test_submit_telemetry_success(self, client, api_handler):
        """Test successful telemetry submission"""
        payload = {
            'events': [
                {
                    'event_type': 'sync',
                    'timestamp': time.time(),
                    'client_id': 'device_123',
                    'bytes_sent': 1000,
                    'bytes_received': 5000,
                    'duration_ms': 200,
                    'connection_type': 'wifi',
                    'signal_strength': 4,
                    'latency_ms': 30
                }
            ]
        }

        response = client.post(
            '/api/v1/telemetry/mobile',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['processed'] == 1
        assert 'recommendations' in data

    def test_submit_telemetry_invalid_json(self, client, api_handler):
        """Test telemetry submission with invalid JSON"""
        response = client.post(
            '/api/v1/telemetry/mobile',
            data='invalid json',
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_submit_telemetry_missing_events(self, client, api_handler):
        """Test telemetry submission without events array"""
        payload = {'wrong_field': []}

        response = client.post(
            '/api/v1/telemetry/mobile',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_submit_telemetry_too_many_events(self, client, api_handler):
        """Test telemetry submission with too many events"""
        payload = {
            'events': [
                {
                    'event_type': 'sync',
                    'timestamp': time.time(),
                    'client_id': 'device_123'
                }
            ] * 1001  # Exceed limit
        }

        response = client.post(
            '/api/v1/telemetry/mobile',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_get_optimization_recommendations(self, client, api_handler):
        """Test getting optimization recommendations"""
        payload = {
            'connection_type': 'cellular',
            'signal_strength': 2,
            'latency_ms': 200,
            'bandwidth_kbps': 1000,
            'is_metered': True,
            'operation': 'sync'
        }

        response = client.post(
            '/api/v1/telemetry/mobile/optimize',
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'network_profile' in data
        assert 'bandwidth_mode' in data
        assert 'recommended_batch_size' in data
        assert 'optimized_sync_params' in data

    def test_get_queue_status(self, client, api_handler):
        """Test getting offline queue status"""
        # Queue some transactions first
        api_handler.network_optimizer.queue_transaction(
            'tx_1', {'data': 'test'}, priority=1
        )

        response = client.get('/api/v1/telemetry/mobile/queue')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'queue' in data
        assert data['queue']['total_queued'] == 1

    def test_get_stats(self, client, api_handler):
        """Test getting public stats"""
        # Submit some telemetry first
        api_handler.telemetry_collector.record_sync_event(
            client_id='device_1',
            bytes_sent=1000,
            bytes_received=5000,
            duration_ms=200,
            connection_type='wifi'
        )

        response = client.get('/api/v1/telemetry/mobile/stats?hours=24')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'event_count' in data
        assert 'latency_percentiles' in data

    def test_get_stats_limits_time_window(self, client, api_handler):
        """Test that public stats limits time window"""
        # Request excessive time window
        response = client.get('/api/v1/telemetry/mobile/stats?hours=1000')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be capped at 168 hours (1 week)
        assert data['time_window_hours'] == 168


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
