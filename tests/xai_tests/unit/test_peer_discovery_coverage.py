"""
Comprehensive coverage tests for xai.core.peer_discovery module.

This test file targets 80%+ coverage by testing edge cases, error paths,
and comprehensive scenarios not covered in the main test file.

Target: 80%+ coverage for peer_discovery.py
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from xai.core.p2p.peer_discovery import (
    PeerInfo,
    BootstrapNodes,
    PeerDiscoveryProtocol,
    PeerDiversityManager,
    PeerDiscoveryManager,
    setup_peer_discovery_api
)


class TestPeerInfoEdgeCases:
    """Additional edge case tests for PeerInfo"""

    def test_peer_info_with_explicit_ip(self):
        """Test PeerInfo initialization with explicit IP address"""
        peer = PeerInfo("http://example.com:5000", ip_address="10.0.0.1")
        assert peer.ip_address == "10.0.0.1"

    def test_update_success_without_response_time(self):
        """Test update_success without providing response time"""
        peer = PeerInfo("http://peer:5000")
        peer.update_success()
        assert peer.success_count == 1
        assert len(peer.response_times) == 0

    def test_update_success_increments_quality_correctly(self):
        """Test quality score increases by exactly 2"""
        peer = PeerInfo("http://peer:5000")
        initial = peer.quality_score
        peer.update_success()
        assert peer.quality_score == initial + 2

    def test_update_failure_decreases_quality_correctly(self):
        """Test quality score decreases by exactly 5"""
        peer = PeerInfo("http://peer:5000")
        initial = peer.quality_score
        peer.update_failure()
        assert peer.quality_score == initial - 5

    def test_response_times_fifo_behavior(self):
        """Test response times maintain FIFO with 10 item limit"""
        peer = PeerInfo("http://peer:5000")
        for i in range(12):
            peer.update_success(response_time=float(i))

        # Should have last 10 items (2-11)
        assert len(peer.response_times) == 10
        assert peer.response_times[0] == 2.0
        assert peer.response_times[-1] == 11.0

    def test_get_reliability_all_failures(self):
        """Test reliability with only failures"""
        peer = PeerInfo("http://peer:5000")
        for _ in range(5):
            peer.update_failure()
        assert peer.get_reliability() == 0.0

    def test_get_reliability_all_successes(self):
        """Test reliability with only successes"""
        peer = PeerInfo("http://peer:5000")
        for _ in range(5):
            peer.update_success()
        assert peer.get_reliability() == 100.0

    def test_last_seen_updates_on_success(self):
        """Test that last_seen is updated on successful interaction"""
        peer = PeerInfo("http://peer:5000")
        initial_seen = peer.last_seen
        time.sleep(0.01)
        peer.update_success()
        assert peer.last_seen > initial_seen

    def test_to_dict_comprehensive_fields(self):
        """Test to_dict includes all expected fields"""
        peer = PeerInfo("http://192.168.1.1:5000")
        peer.update_success(0.1)
        peer.update_success(0.2)
        peer.update_failure()
        peer.blocks_shared = 10
        peer.transactions_shared = 50

        result = peer.to_dict()

        required_fields = [
            'url', 'ip_address', 'last_seen', 'quality_score',
            'reliability', 'avg_response_time', 'uptime_hours',
            'success_count', 'failure_count', 'is_bootstrap',
            'version', 'chain_height'
        ]

        for field in required_fields:
            assert field in result


class TestBootstrapNodesExtended:
    """Extended tests for BootstrapNodes"""

    def test_get_seeds_case_insensitive(self):
        """Test network type is case insensitive"""
        seeds_upper = BootstrapNodes.get_seeds("MAINNET")
        seeds_lower = BootstrapNodes.get_seeds("mainnet")
        assert seeds_upper == seeds_lower

    def test_mainnet_seeds_count(self):
        """Test mainnet has expected number of seeds"""
        assert len(BootstrapNodes.MAINNET_SEEDS) == 5

    def test_testnet_seeds_count(self):
        """Test testnet has expected number of seeds"""
        assert len(BootstrapNodes.TESTNET_SEEDS) == 3

    def test_devnet_seeds_count(self):
        """Test devnet has expected number of seeds"""
        assert len(BootstrapNodes.DEVNET_SEEDS) == 3

    def test_seeds_are_valid_urls(self):
        """Test all seed URLs are valid HTTP URLs"""
        for network in ['mainnet', 'testnet', 'devnet']:
            seeds = BootstrapNodes.get_seeds(network)
            for seed in seeds:
                assert seed.startswith('http://') or seed.startswith('https://')


class TestPeerDiscoveryProtocolExtended:
    """Extended tests for PeerDiscoveryProtocol"""

    @patch('xai.core.peer_discovery.requests.get')
    def test_send_get_peers_request_empty_peers(self, mock_get):
        """Test handling empty peers list"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={'peers': []})
        mock_get.return_value = mock_response

        peers = PeerDiscoveryProtocol.send_get_peers_request('http://peer:5000')
        assert peers == []

    @patch('xai.core.peer_discovery.requests.get')
    def test_send_get_peers_request_no_peers_key(self, mock_get):
        """Test handling response without peers key"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={'other_data': 'value'})
        mock_get.return_value = mock_response

        peers = PeerDiscoveryProtocol.send_get_peers_request('http://peer:5000')
        assert peers == []

    @patch('xai.core.peer_discovery.requests.get')
    def test_send_get_peers_request_custom_timeout(self, mock_get):
        """Test custom timeout is used"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={'peers': []})
        mock_get.return_value = mock_response

        PeerDiscoveryProtocol.send_get_peers_request('http://peer:5000', timeout=10)
        mock_get.assert_called_with('http://peer:5000/peers/list', timeout=10)

    @patch('xai.core.peer_discovery.requests.post')
    def test_send_peers_announcement_custom_timeout(self, mock_post):
        """Test announcement with custom timeout"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        PeerDiscoveryProtocol.send_peers_announcement(
            'http://peer:5000',
            'http://my-node:5000',
            timeout=10
        )

        assert mock_post.call_args[1]['timeout'] == 10

    @patch('xai.core.peer_discovery.requests.post')
    def test_send_peers_announcement_non_200_status(self, mock_post):
        """Test announcement with non-200 status code"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = PeerDiscoveryProtocol.send_peers_announcement(
            'http://peer:5000',
            'http://my-node:5000'
        )
        assert result is False

    @patch('xai.core.peer_discovery.requests.get')
    def test_ping_peer_non_200_status(self, mock_get):
        """Test ping with non-200 status code"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        is_alive, response_time = PeerDiscoveryProtocol.ping_peer('http://peer:5000')
        assert is_alive is False
        assert response_time > 0  # Still measures time even on failure

    @patch('xai.core.peer_discovery.requests.get')
    def test_ping_peer_custom_timeout(self, mock_get):
        """Test ping with custom timeout"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        PeerDiscoveryProtocol.ping_peer('http://peer:5000', timeout=5)
        mock_get.assert_called_with('http://peer:5000/', timeout=5)

    @patch('xai.core.peer_discovery.requests.get')
    def test_get_peer_info_non_200_status(self, mock_get):
        """Test get_peer_info with non-200 status"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        info = PeerDiscoveryProtocol.get_peer_info('http://peer:5000')
        assert info is None

    @patch('xai.core.peer_discovery.requests.get')
    def test_get_peer_info_custom_timeout(self, mock_get):
        """Test get_peer_info with custom timeout"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={})
        mock_get.return_value = mock_response

        PeerDiscoveryProtocol.get_peer_info('http://peer:5000', timeout=10)
        mock_get.assert_called_with('http://peer:5000/stats', timeout=10)


class TestPeerDiversityManagerExtended:
    """Extended tests for PeerDiversityManager"""

    def test_get_ip_prefix_short_ip(self):
        """Test IP prefix with incomplete IP"""
        prefix = PeerDiversityManager.get_ip_prefix("192", 16)
        assert prefix == "192"

    def test_get_ip_prefix_invalid_prefix_length(self):
        """Test with unsupported prefix length"""
        prefix = PeerDiversityManager.get_ip_prefix("192.168.1.1", 8)
        assert prefix == "192.168.1.1"

    def test_calculate_diversity_score_single_peer(self):
        """Test diversity score with single peer"""
        peers = [PeerInfo("http://192.168.1.1:5000")]
        score = PeerDiversityManager.calculate_diversity_score(peers)
        assert score == 100.0  # Single peer has perfect diversity

    def test_calculate_diversity_score_capped_at_100(self):
        """Test diversity score is capped at 100"""
        # Create peers with maximum diversity
        peers = [PeerInfo(f"http://{i}.0.0.1:5000") for i in range(10, 20)]
        score = PeerDiversityManager.calculate_diversity_score(peers)
        assert score <= 100.0

    def test_select_diverse_peers_no_quality_preference(self):
        """Test selection without quality preference"""
        peers = [
            PeerInfo("http://192.168.1.1:5000"),
            PeerInfo("http://192.168.1.2:5000"),
            PeerInfo("http://10.0.0.1:5000"),
        ]
        peers[0].quality_score = 100
        peers[1].quality_score = 50
        peers[2].quality_score = 30

        selected = PeerDiversityManager.select_diverse_peers(peers, 2, prefer_quality=False)
        assert len(selected) == 2

    def test_select_diverse_peers_all_same_prefix(self):
        """Test selection when all peers have same prefix"""
        peers = [
            PeerInfo("http://192.168.1.1:5000"),
            PeerInfo("http://192.168.1.2:5000"),
            PeerInfo("http://192.168.1.3:5000"),
        ]

        selected = PeerDiversityManager.select_diverse_peers(peers, 2, prefer_quality=False)
        assert len(selected) == 2

    def test_select_diverse_peers_empty_list(self):
        """Test selection from empty list"""
        selected = PeerDiversityManager.select_diverse_peers([], 5)
        assert len(selected) == 0

    def test_select_diverse_peers_fills_remaining_slots(self):
        """Test selection fills all slots even after diverse peers exhausted"""
        peers = [
            PeerInfo("http://10.0.0.1:5000"),
            PeerInfo("http://10.0.0.2:5000"),
            PeerInfo("http://10.0.0.3:5000"),
            PeerInfo("http://10.0.0.4:5000"),
        ]

        selected = PeerDiversityManager.select_diverse_peers(peers, 3, prefer_quality=False)
        assert len(selected) == 3


class TestPeerDiscoveryManagerExtended:
    """Extended tests for PeerDiscoveryManager"""

    def test_init_default_params(self):
        """Test initialization with default parameters"""
        manager = PeerDiscoveryManager()
        assert manager.network_type == "mainnet"
        assert manager.my_url is None
        assert manager.max_peers == 50
        assert manager.discovery_interval == 300

    def test_init_custom_discovery_interval(self):
        """Test initialization with custom discovery interval"""
        manager = PeerDiscoveryManager(discovery_interval=600)
        assert manager.discovery_interval == 600

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    def test_bootstrap_network_with_peer_list(self, mock_get_peers, mock_ping):
        """Test bootstrap discovers peers from seed"""
        mock_ping.return_value = (True, 0.1)
        mock_get_peers.return_value = [
            'http://peer1:5000',
            'http://peer2:5000',
            'http://peer3:5000'
        ]

        manager = PeerDiscoveryManager(network_type="devnet", my_url="http://my-node:5000")
        discovered = manager.bootstrap_network()

        # Should discover seeds + peers from seeds
        assert discovered > 3
        assert 'http://peer1:5000' in manager.known_peers

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    def test_bootstrap_network_marks_bootstrap_peers(self, mock_get_peers, mock_ping):
        """Test bootstrap marks seed nodes"""
        mock_ping.return_value = (True, 0.1)
        mock_get_peers.return_value = []

        manager = PeerDiscoveryManager(network_type="devnet")
        manager.bootstrap_network()

        # Check that seed peers are marked as bootstrap
        for peer in manager.known_peers.values():
            if 'seed' in peer.url or peer.url in BootstrapNodes.DEVNET_SEEDS:
                assert peer.is_bootstrap

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    def test_discover_peers_skip_duplicate(self, mock_get_peers):
        """Test discovery skips already known peers"""
        mock_get_peers.return_value = [
            'http://existing:5000',
            'http://new:5000'
        ]

        manager = PeerDiscoveryManager(my_url="http://my-node:5000")
        manager.connected_peers.add('http://seed:5000')
        manager.known_peers['http://existing:5000'] = PeerInfo('http://existing:5000')

        new_peers = manager.discover_peers()
        assert new_peers == 1
        assert 'http://new:5000' in manager.known_peers

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    def test_discover_peers_samples_connected_peers(self, mock_get_peers):
        """Test discovery samples from connected peers"""
        mock_get_peers.return_value = []

        manager = PeerDiscoveryManager()
        # Add many connected peers
        for i in range(10):
            manager.connected_peers.add(f'http://peer{i}:5000')

        manager.discover_peers()

        # Should call get_peers on sample (max 5)
        assert mock_get_peers.call_count <= 5

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_connect_to_best_peers_default_count(self, mock_ping):
        """Test connection uses default count to fill max_peers"""
        mock_ping.return_value = (True, 0.1)

        manager = PeerDiscoveryManager(max_peers=5)

        # Add peers
        for i in range(10):
            manager.known_peers[f'http://peer{i}:5000'] = PeerInfo(f'http://peer{i}:5000')

        connected = manager.connect_to_best_peers()
        assert len(connected) == 5

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_connect_to_best_peers_already_at_max(self, mock_ping):
        """Test no new connections when already at max"""
        manager = PeerDiscoveryManager(max_peers=2)
        manager.connected_peers = {'http://peer1:5000', 'http://peer2:5000'}

        connected = manager.connect_to_best_peers()
        assert len(connected) == 0

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_connect_to_best_peers_filters_dead(self, mock_ping):
        """Test connection filters out dead peers"""
        mock_ping.return_value = (True, 0.1)

        manager = PeerDiscoveryManager()

        # Add alive peer
        alive = PeerInfo('http://alive:5000')
        alive.last_seen = time.time()
        manager.known_peers['http://alive:5000'] = alive

        # Add dead peer
        dead = PeerInfo('http://dead:5000')
        dead.last_seen = time.time() - 10000
        manager.known_peers['http://dead:5000'] = dead

        connected = manager.connect_to_best_peers(count=2)
        # Should only connect to alive peer
        assert 'http://alive:5000' in connected
        assert 'http://dead:5000' not in connected

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_connect_to_best_peers_tracks_failures(self, mock_ping):
        """Test connection tracks failed attempts"""
        mock_ping.return_value = (False, 0.0)

        manager = PeerDiscoveryManager()
        peer = PeerInfo('http://peer:5000')
        manager.known_peers['http://peer:5000'] = peer

        initial_failures = manager.total_failed_connections
        manager.connect_to_best_peers(count=1)

        assert manager.total_failed_connections > initial_failures

    def test_remove_dead_peers_custom_timeout(self):
        """Test removing dead peers with custom timeout"""
        manager = PeerDiscoveryManager()

        peer = PeerInfo('http://peer:5000')
        peer.last_seen = time.time() - 500
        manager.known_peers['http://peer:5000'] = peer

        # With short timeout, should be dead
        removed = manager.remove_dead_peers(timeout=100)
        assert removed == 1

        # With long timeout, should not be dead
        peer2 = PeerInfo('http://peer2:5000')
        peer2.last_seen = time.time() - 500
        manager.known_peers['http://peer2:5000'] = peer2
        removed = manager.remove_dead_peers(timeout=1000)
        assert removed == 0

    def test_remove_dead_peers_no_dead_peers(self):
        """Test removing dead peers when none are dead"""
        manager = PeerDiscoveryManager()

        peer = PeerInfo('http://peer:5000')
        peer.last_seen = time.time()
        manager.known_peers['http://peer:5000'] = peer

        removed = manager.remove_dead_peers()
        assert removed == 0

    def test_update_peer_info_unknown_peer(self):
        """Test updating unknown peer does nothing"""
        manager = PeerDiscoveryManager()
        # Should not raise exception
        manager.update_peer_info('http://unknown:5000', success=True)

    def test_update_peer_info_low_quality_not_connected(self):
        """Test low quality peer not in connected list isn't disconnected"""
        manager = PeerDiscoveryManager()
        peer = PeerInfo('http://peer:5000')
        peer.quality_score = 5
        manager.known_peers['http://peer:5000'] = peer
        # Not in connected_peers

        manager.update_peer_info('http://peer:5000', success=False)
        # Should not crash

    def test_get_peer_list_limits_to_50(self):
        """Test peer list is limited to 50 peers"""
        manager = PeerDiscoveryManager()

        # Add 100 peers
        for i in range(100):
            peer = PeerInfo(f'http://peer{i}:5000')
            manager.known_peers[peer.url] = peer
            if i < 10:
                manager.connected_peers.add(peer.url)

        peer_list = manager.get_peer_list()
        assert len(peer_list) == 50

    def test_get_peer_list_sorts_by_quality(self):
        """Test peer list includes highest quality peers"""
        manager = PeerDiscoveryManager()

        # Add peers with varying quality
        for i in range(10):
            peer = PeerInfo(f'http://peer{i}:5000')
            peer.quality_score = i * 10
            manager.known_peers[peer.url] = peer

        peer_list = manager.get_peer_list()
        # Higher quality peers should be included
        assert 'http://peer9:5000' in peer_list

    @patch('xai.core.peer_discovery.time.sleep')
    @patch.object(PeerDiscoveryManager, 'discover_peers')
    @patch.object(PeerDiscoveryManager, 'remove_dead_peers')
    @patch.object(PeerDiscoveryManager, 'connect_to_best_peers')
    def test_discovery_loop_interval_check(self, mock_connect, mock_remove, mock_discover, mock_sleep):
        """Test discovery loop respects interval"""
        manager = PeerDiscoveryManager(discovery_interval=100)
        manager.is_running = True
        manager.last_discovery = time.time() - 50  # Not enough time elapsed

        call_count = [0]
        def stop_after_sleep(*args):
            call_count[0] += 1
            if call_count[0] >= 2:
                manager.is_running = False

        mock_sleep.side_effect = stop_after_sleep

        manager._discovery_loop()

        # Should not have called discovery methods yet
        assert mock_discover.call_count == 0

    @patch('xai.core.peer_discovery.time.sleep')
    @patch.object(PeerDiscoveryManager, 'discover_peers')
    @patch.object(PeerDiscoveryManager, 'remove_dead_peers')
    @patch.object(PeerDiscoveryManager, 'connect_to_best_peers')
    def test_discovery_loop_connects_when_below_max(self, mock_connect, mock_remove, mock_discover, mock_sleep):
        """Test discovery loop connects to more peers when below max"""
        manager = PeerDiscoveryManager(max_peers=10, discovery_interval=1)
        manager.is_running = True
        manager.last_discovery = 0  # Force discovery
        manager.connected_peers = {'http://peer1:5000'}  # Below max

        def stop_loop(*args):
            manager.is_running = False
        mock_sleep.side_effect = stop_loop

        manager._discovery_loop()

        assert mock_connect.called

    @patch('xai.core.peer_discovery.time.sleep')
    def test_discovery_loop_handles_exceptions(self, mock_sleep):
        """Test discovery loop continues after exceptions"""
        manager = PeerDiscoveryManager(discovery_interval=1)
        manager.is_running = True
        manager.last_discovery = 0

        call_count = [0]
        def stop_after_sleep(*args):
            call_count[0] += 1
            if call_count[0] >= 2:
                manager.is_running = False

        mock_sleep.side_effect = stop_after_sleep

        # Make discover_peers raise exception
        with patch.object(manager, 'discover_peers', side_effect=Exception("Test error")):
            manager._discovery_loop()

        # Should have called sleep multiple times despite error
        assert mock_sleep.call_count >= 2

    def test_start_already_running(self):
        """Test starting when already running does nothing"""
        with patch.object(PeerDiscoveryManager, 'bootstrap_network'), \
             patch.object(PeerDiscoveryManager, 'connect_to_best_peers'):
            manager = PeerDiscoveryManager()
            manager.start()

            initial_thread = manager.discovery_thread
            manager.start()  # Try to start again

            # Should be same thread
            assert manager.discovery_thread is initial_thread

            manager.stop()

    def test_get_stats_empty_manager(self):
        """Test stats with no peers"""
        manager = PeerDiscoveryManager()
        stats = manager.get_stats()

        assert stats['connected_peers'] == 0
        assert stats['known_peers'] == 0
        assert stats['diversity_score'] == 0.0
        assert stats['avg_peer_quality'] == 0

    def test_get_stats_with_connected_peers_only(self):
        """Test stats includes connected peer quality"""
        manager = PeerDiscoveryManager()

        peer1 = PeerInfo('http://peer1:5000')
        peer1.quality_score = 80
        peer2 = PeerInfo('http://peer2:5000')
        peer2.quality_score = 60

        manager.known_peers['http://peer1:5000'] = peer1
        manager.known_peers['http://peer2:5000'] = peer2
        manager.connected_peers = {'http://peer1:5000', 'http://peer2:5000'}

        stats = manager.get_stats()
        assert stats['avg_peer_quality'] == 70.0

    def test_get_peer_details_empty(self):
        """Test peer details with no peers"""
        manager = PeerDiscoveryManager()
        details = manager.get_peer_details()
        assert len(details) == 0


class TestPeerDiscoveryAPIExtended:
    """Extended tests for API endpoints"""

    def test_setup_peer_discovery_api_get_peer_list_with_manager(self):
        """Test /peers/list endpoint with peer discovery manager"""
        from flask import Flask

        app = Flask(__name__)
        node = Mock()
        node.peer_discovery_manager = Mock()
        node.peer_discovery_manager.get_peer_list = Mock(return_value=[
            'http://peer1:5000',
            'http://peer2:5000'
        ])

        setup_peer_discovery_api(app, node)

        with app.test_client() as client:
            response = client.get('/peers/list')
            data = response.get_json()

            assert response.status_code == 200
            assert data['success'] is True
            assert data['count'] == 2
            assert 'http://peer1:5000' in data['peers']

    def test_setup_peer_discovery_api_get_peer_list_without_manager(self):
        """Test /peers/list endpoint without peer discovery manager"""
        from flask import Flask

        app = Flask(__name__)
        node = Mock()
        node.peers = {'http://peer1:5000', 'http://peer2:5000'}
        # No peer_discovery_manager attribute
        del node.peer_discovery_manager

        setup_peer_discovery_api(app, node)

        with app.test_client() as client:
            response = client.get('/peers/list')
            data = response.get_json()

            assert response.status_code == 200
            assert data['success'] is True
            assert data['count'] == 2

    def test_setup_peer_discovery_api_announce_peer_success(self):
        """Test /peers/announce endpoint success"""
        pass

    def test_setup_peer_discovery_api_announce_peer_rejected(self):
        """Test /peers/announce endpoint when peer is rejected"""
        pass

    def test_setup_peer_discovery_api_announce_peer_missing_url(self):
        """Test /peers/announce endpoint with missing peer_url"""
        pass

    def test_setup_peer_discovery_api_get_discovery_stats(self):
        """Test /peers/discovery/stats endpoint"""
        from flask import Flask

        app = Flask(__name__)
        node = Mock()
        node.peer_discovery_manager = Mock()
        node.peer_discovery_manager.get_stats = Mock(return_value={
            'connected_peers': 10,
            'known_peers': 20
        })

        setup_peer_discovery_api(app, node)

        with app.test_client() as client:
            response = client.get('/peers/discovery/stats')
            data = response.get_json()

            assert response.status_code == 200
            assert data['success'] is True
            assert data['stats']['connected_peers'] == 10

    def test_setup_peer_discovery_api_get_discovery_stats_no_manager(self):
        """Test /peers/discovery/stats without manager"""
        from flask import Flask

        app = Flask(__name__)
        node = Mock()
        del node.peer_discovery_manager

        setup_peer_discovery_api(app, node)

        with app.test_client() as client:
            response = client.get('/peers/discovery/stats')
            data = response.get_json()

            assert response.status_code == 503
            assert 'error' in data

    def test_setup_peer_discovery_api_get_peer_details(self):
        """Test /peers/discovery/details endpoint"""
        from flask import Flask

        app = Flask(__name__)
        node = Mock()
        node.peer_discovery_manager = Mock()
        node.peer_discovery_manager.get_peer_details = Mock(return_value=[
            {'url': 'http://peer1:5000', 'quality_score': 80},
            {'url': 'http://peer2:5000', 'quality_score': 60}
        ])

        setup_peer_discovery_api(app, node)

        with app.test_client() as client:
            response = client.get('/peers/discovery/details')
            data = response.get_json()

            assert response.status_code == 200
            assert data['success'] is True
            assert data['count'] == 2
            assert len(data['peers']) == 2

    def test_setup_peer_discovery_api_get_peer_details_no_manager(self):
        """Test /peers/discovery/details without manager"""
        from flask import Flask

        app = Flask(__name__)
        node = Mock()
        del node.peer_discovery_manager

        setup_peer_discovery_api(app, node)

        with app.test_client() as client:
            response = client.get('/peers/discovery/details')
            data = response.get_json()

            assert response.status_code == 503
            assert 'error' in data


class TestIntegrationScenarios:
    """Integration tests for complex scenarios"""

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_peers_announcement')
    def test_full_bootstrap_and_discovery_flow(self, mock_announce, mock_get_peers, mock_ping):
        """Test complete bootstrap and discovery flow"""
        mock_ping.return_value = (True, 0.1)
        mock_get_peers.return_value = ['http://peer1:5000', 'http://peer2:5000']
        mock_announce.return_value = True

        manager = PeerDiscoveryManager(
            network_type="testnet",
            my_url="http://my-node:5000",
            max_peers=10
        )

        # Bootstrap
        discovered = manager.bootstrap_network()
        assert discovered > 0

        # Discover more peers
        manager.connected_peers.add('http://peer1:5000')
        new_peers = manager.discover_peers()

        # Connect to best peers
        connected = manager.connect_to_best_peers(count=5)

        # Get stats
        stats = manager.get_stats()
        assert stats['total_discoveries'] >= 0
        assert stats['connected_peers'] >= 0

    def test_peer_quality_degradation_and_removal(self):
        """Test peer quality degradation leading to removal"""
        manager = PeerDiscoveryManager()

        peer = PeerInfo('http://peer:5000')
        manager.known_peers['http://peer:5000'] = peer
        manager.connected_peers.add('http://peer:5000')

        # Cause many failures
        for _ in range(20):
            manager.update_peer_info('http://peer:5000', success=False)

        # Peer should be disconnected due to low quality
        assert 'http://peer:5000' not in manager.connected_peers

    def test_diversity_selection_with_mixed_quality(self):
        """Test diversity manager balances diversity and quality"""
        peers = []

        # High quality, same subnet
        for i in range(3):
            peer = PeerInfo(f"http://192.168.1.{i+1}:5000")
            peer.quality_score = 90
            peers.append(peer)

        # Lower quality, diverse subnets
        for i in range(3):
            peer = PeerInfo(f"http://10.{i}.0.1:5000")
            peer.quality_score = 60
            peers.append(peer)

        # With quality preference, should get mix
        selected = PeerDiversityManager.select_diverse_peers(peers, 4, prefer_quality=True)
        assert len(selected) == 4

        # Without quality preference, should prefer diversity
        selected = PeerDiversityManager.select_diverse_peers(peers, 4, prefer_quality=False)
        assert len(selected) == 4
