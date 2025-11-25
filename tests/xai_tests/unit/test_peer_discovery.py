"""
Comprehensive unit tests for xai.core.peer_discovery module.
Tests all peer discovery and network bootstrap functionality.

Target: 90%+ coverage for peer_discovery.py
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from xai.core.peer_discovery import (
    PeerInfo,
    BootstrapNodes,
    PeerDiscoveryProtocol,
    PeerDiversityManager,
    PeerDiscoveryManager
)


class TestPeerInfo:
    """Test PeerInfo class"""

    def test_peer_info_init(self):
        """Test peer info initialization"""
        peer = PeerInfo("http://peer1.local:5000")
        assert peer.url == "http://peer1.local:5000"
        assert peer.quality_score == 50
        assert peer.success_count == 0
        assert peer.failure_count == 0
        assert peer.is_bootstrap is False

    def test_peer_info_extract_ip(self):
        """Test IP extraction from URL"""
        peer = PeerInfo("http://192.168.1.100:5000")
        assert peer.ip_address == "192.168.1.100"

    def test_peer_info_extract_ip_no_match(self):
        """Test IP extraction with no IP in URL"""
        peer = PeerInfo("http://localhost:5000")
        assert peer.ip_address == "unknown"

    def test_update_success(self):
        """Test updating peer on successful interaction"""
        peer = PeerInfo("http://peer1.local:5000")
        initial_score = peer.quality_score
        peer.update_success(response_time=0.5)
        
        assert peer.success_count == 1
        assert peer.quality_score > initial_score
        assert len(peer.response_times) == 1
        assert peer.response_times[0] == 0.5

    def test_update_success_max_response_times(self):
        """Test response times limited to 10"""
        peer = PeerInfo("http://peer1.local:5000")
        for i in range(15):
            peer.update_success(response_time=0.1 * i)
        
        assert len(peer.response_times) == 10

    def test_update_success_max_quality(self):
        """Test quality score caps at 100"""
        peer = PeerInfo("http://peer1.local:5000")
        for _ in range(50):
            peer.update_success()
        
        assert peer.quality_score == 100

    def test_update_failure(self):
        """Test updating peer on failed interaction"""
        peer = PeerInfo("http://peer1.local:5000")
        initial_score = peer.quality_score
        peer.update_failure()
        
        assert peer.failure_count == 1
        assert peer.quality_score < initial_score

    def test_update_failure_min_quality(self):
        """Test quality score floors at 0"""
        peer = PeerInfo("http://peer1.local:5000")
        for _ in range(20):
            peer.update_failure()
        
        assert peer.quality_score == 0

    def test_get_avg_response_time(self):
        """Test average response time calculation"""
        peer = PeerInfo("http://peer1.local:5000")
        peer.update_success(0.1)
        peer.update_success(0.3)
        peer.update_success(0.2)
        
        avg = peer.get_avg_response_time()
        assert avg == pytest.approx(0.2)

    def test_get_avg_response_time_empty(self):
        """Test average response time with no data"""
        peer = PeerInfo("http://peer1.local:5000")
        assert peer.get_avg_response_time() == 0.0

    def test_get_uptime_hours(self):
        """Test uptime calculation"""
        peer = PeerInfo("http://peer1.local:5000")
        time.sleep(0.1)
        uptime = peer.get_uptime_hours()
        assert uptime > 0

    def test_get_reliability(self):
        """Test reliability percentage calculation"""
        peer = PeerInfo("http://peer1.local:5000")
        peer.update_success()
        peer.update_success()
        peer.update_failure()
        
        reliability = peer.get_reliability()
        assert reliability == pytest.approx(66.67, rel=0.1)

    def test_get_reliability_no_interactions(self):
        """Test reliability with no interactions"""
        peer = PeerInfo("http://peer1.local:5000")
        assert peer.get_reliability() == 50.0

    def test_is_dead_active(self):
        """Test is_dead for active peer"""
        peer = PeerInfo("http://peer1.local:5000")
        peer.last_seen = time.time()
        assert peer.is_dead(timeout=3600) is False

    def test_is_dead_timeout(self):
        """Test is_dead for timed out peer"""
        peer = PeerInfo("http://peer1.local:5000")
        peer.last_seen = time.time() - 4000  # 4000 seconds ago
        assert peer.is_dead(timeout=3600) is True

    def test_to_dict(self):
        """Test converting peer to dictionary"""
        peer = PeerInfo("http://192.168.1.100:5000")
        peer.update_success(0.5)
        peer.is_bootstrap = True
        peer.version = "1.0.0"
        peer.chain_height = 100
        
        peer_dict = peer.to_dict()
        assert peer_dict['url'] == "http://192.168.1.100:5000"
        assert peer_dict['ip_address'] == "192.168.1.100"
        assert peer_dict['quality_score'] == 52
        assert peer_dict['is_bootstrap'] is True
        assert peer_dict['version'] == "1.0.0"
        assert peer_dict['chain_height'] == 100


class TestBootstrapNodes:
    """Test BootstrapNodes class"""

    def test_get_seeds_mainnet(self):
        """Test getting mainnet seeds"""
        seeds = BootstrapNodes.get_seeds("mainnet")
        assert len(seeds) == 5
        assert all("seed" in s and "xaicoin.network" in s for s in seeds)

    def test_get_seeds_testnet(self):
        """Test getting testnet seeds"""
        seeds = BootstrapNodes.get_seeds("testnet")
        assert len(seeds) == 3
        assert all("testnet" in s for s in seeds)

    def test_get_seeds_devnet(self):
        """Test getting devnet seeds"""
        seeds = BootstrapNodes.get_seeds("devnet")
        assert len(seeds) == 3
        assert all("127.0.0.1" in s for s in seeds)

    def test_get_seeds_default(self):
        """Test getting seeds with invalid network type"""
        seeds = BootstrapNodes.get_seeds("invalid")
        assert seeds == BootstrapNodes.MAINNET_SEEDS


class TestPeerDiscoveryProtocol:
    """Test PeerDiscoveryProtocol class"""

    @patch('xai.core.peer_discovery.requests.get')
    def test_send_get_peers_request_success(self, mock_get):
        """Test successful peer list request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            'peers': ['http://peer1:5000', 'http://peer2:5000']
        })
        mock_get.return_value = mock_response
        
        peers = PeerDiscoveryProtocol.send_get_peers_request('http://seed:5000')
        assert len(peers) == 2
        assert 'http://peer1:5000' in peers

    @patch('xai.core.peer_discovery.requests.get')
    def test_send_get_peers_request_failure(self, mock_get):
        """Test failed peer list request"""
        mock_get.side_effect = Exception("Connection error")
        
        peers = PeerDiscoveryProtocol.send_get_peers_request('http://seed:5000')
        assert peers is None

    @patch('xai.core.peer_discovery.requests.get')
    def test_send_get_peers_request_404(self, mock_get):
        """Test peer list request with 404 response"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        peers = PeerDiscoveryProtocol.send_get_peers_request('http://seed:5000')
        assert peers is None

    @patch('xai.core.peer_discovery.requests.post')
    def test_send_peers_announcement_success(self, mock_post):
        """Test successful peer announcement"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = PeerDiscoveryProtocol.send_peers_announcement(
            'http://peer:5000',
            'http://my-node:5000'
        )
        assert result is True

    @patch('xai.core.peer_discovery.requests.post')
    def test_send_peers_announcement_failure(self, mock_post):
        """Test failed peer announcement"""
        mock_post.side_effect = Exception("Connection error")
        
        result = PeerDiscoveryProtocol.send_peers_announcement(
            'http://peer:5000',
            'http://my-node:5000'
        )
        assert result is False

    @patch('xai.core.peer_discovery.requests.get')
    def test_ping_peer_alive(self, mock_get):
        """Test pinging alive peer"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        is_alive, response_time = PeerDiscoveryProtocol.ping_peer('http://peer:5000')
        assert is_alive is True
        assert response_time > 0

    @patch('xai.core.peer_discovery.requests.get')
    def test_ping_peer_dead(self, mock_get):
        """Test pinging dead peer"""
        mock_get.side_effect = Exception("Timeout")
        
        is_alive, response_time = PeerDiscoveryProtocol.ping_peer('http://peer:5000')
        assert is_alive is False
        assert response_time == 0.0

    @patch('xai.core.peer_discovery.requests.get')
    def test_get_peer_info_success(self, mock_get):
        """Test getting peer info successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            'version': '1.0.0',
            'chain_height': 100
        })
        mock_get.return_value = mock_response
        
        info = PeerDiscoveryProtocol.get_peer_info('http://peer:5000')
        assert info is not None
        assert info['version'] == '1.0.0'

    @patch('xai.core.peer_discovery.requests.get')
    def test_get_peer_info_failure(self, mock_get):
        """Test getting peer info failure"""
        mock_get.side_effect = Exception("Connection error")
        
        info = PeerDiscoveryProtocol.get_peer_info('http://peer:5000')
        assert info is None


class TestPeerDiversityManager:
    """Test PeerDiversityManager class"""

    def test_get_ip_prefix_16(self):
        """Test getting /16 IP prefix"""
        prefix = PeerDiversityManager.get_ip_prefix("192.168.1.100", 16)
        assert prefix == "192.168"

    def test_get_ip_prefix_24(self):
        """Test getting /24 IP prefix"""
        prefix = PeerDiversityManager.get_ip_prefix("192.168.1.100", 24)
        assert prefix == "192.168.1"

    def test_calculate_diversity_score_high(self):
        """Test diversity score with diverse peers"""
        peers = [
            PeerInfo("http://10.0.0.1:5000"),
            PeerInfo("http://20.0.0.1:5000"),
            PeerInfo("http://30.0.0.1:5000"),
        ]
        
        score = PeerDiversityManager.calculate_diversity_score(peers)
        assert score > 50

    def test_calculate_diversity_score_low(self):
        """Test diversity score with same subnet peers"""
        peers = [
            PeerInfo("http://192.168.1.1:5000"),
            PeerInfo("http://192.168.1.2:5000"),
            PeerInfo("http://192.168.1.3:5000"),
        ]
        
        score = PeerDiversityManager.calculate_diversity_score(peers)
        assert score < 50

    def test_calculate_diversity_score_empty(self):
        """Test diversity score with no peers"""
        score = PeerDiversityManager.calculate_diversity_score([])
        assert score == 0.0

    def test_select_diverse_peers_less_than_count(self):
        """Test selecting peers when we have less than requested"""
        peers = [PeerInfo("http://peer1:5000")]
        selected = PeerDiversityManager.select_diverse_peers(peers, 5)
        assert len(selected) == 1

    def test_select_diverse_peers_diversity_preferred(self):
        """Test selecting diverse peers prefers unique subnets"""
        peers = [
            PeerInfo("http://192.168.1.1:5000"),
            PeerInfo("http://192.168.1.2:5000"),
            PeerInfo("http://10.0.0.1:5000"),
            PeerInfo("http://20.0.0.1:5000"),
        ]
        
        selected = PeerDiversityManager.select_diverse_peers(peers, 2, prefer_quality=False)
        # Should prefer different subnets
        assert len(selected) == 2

    def test_select_diverse_peers_quality_preferred(self):
        """Test selecting peers with quality preference"""
        peers = [
            PeerInfo("http://192.168.1.1:5000"),
            PeerInfo("http://192.168.1.2:5000"),
        ]
        peers[0].quality_score = 80
        peers[1].quality_score = 60
        
        selected = PeerDiversityManager.select_diverse_peers(peers, 1, prefer_quality=True)
        assert selected[0].quality_score == 80


class TestPeerDiscoveryManager:
    """Test PeerDiscoveryManager class"""

    def test_init(self):
        """Test peer discovery manager initialization"""
        manager = PeerDiscoveryManager(
            network_type="testnet",
            my_url="http://my-node:5000",
            max_peers=30
        )
        
        assert manager.network_type == "testnet"
        assert manager.my_url == "http://my-node:5000"
        assert manager.max_peers == 30
        assert manager.is_running is False
        assert len(manager.known_peers) == 0

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_peers_announcement')
    def test_bootstrap_network_success(self, mock_announce, mock_get_peers, mock_ping):
        """Test successful network bootstrap"""
        mock_ping.return_value = (True, 0.5)
        mock_get_peers.return_value = ['http://peer1:5000', 'http://peer2:5000']
        mock_announce.return_value = True
        
        manager = PeerDiscoveryManager(my_url="http://my-node:5000")
        discovered = manager.bootstrap_network()
        
        assert discovered > 0
        assert len(manager.known_peers) > 0

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_bootstrap_network_seed_failure(self, mock_ping):
        """Test bootstrap with seed failures"""
        mock_ping.return_value = (False, 0.0)
        
        manager = PeerDiscoveryManager(my_url="http://my-node:5000")
        discovered = manager.bootstrap_network()
        
        assert discovered == 0

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_bootstrap_network_skip_own_url(self, mock_ping):
        """Test bootstrap skips own URL"""
        mock_ping.return_value = (True, 0.5)
        
        # Use one of the seed URLs as our own
        my_url = BootstrapNodes.MAINNET_SEEDS[0]
        manager = PeerDiscoveryManager(my_url=my_url)
        manager.bootstrap_network()
        
        # Should not add self as peer
        assert my_url not in manager.known_peers

    def test_discover_peers_no_connected(self):
        """Test peer discovery with no connected peers"""
        manager = PeerDiscoveryManager()
        new_peers = manager.discover_peers()
        assert new_peers == 0

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    def test_discover_peers_success(self, mock_get_peers):
        """Test successful peer discovery"""
        mock_get_peers.return_value = [
            'http://new-peer1:5000',
            'http://new-peer2:5000'
        ]
        
        manager = PeerDiscoveryManager(my_url="http://my-node:5000")
        manager.connected_peers.add('http://seed:5000')
        
        new_peers = manager.discover_peers()
        assert new_peers == 2
        assert 'http://new-peer1:5000' in manager.known_peers

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
    def test_discover_peers_skip_own_url(self, mock_get_peers):
        """Test peer discovery skips own URL"""
        mock_get_peers.return_value = [
            'http://my-node:5000',  # Our own URL
            'http://new-peer:5000'
        ]
        
        manager = PeerDiscoveryManager(my_url="http://my-node:5000")
        manager.connected_peers.add('http://seed:5000')
        
        new_peers = manager.discover_peers()
        assert new_peers == 1
        assert 'http://my-node:5000' not in manager.known_peers

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_connect_to_best_peers_success(self, mock_ping):
        """Test connecting to best quality peers"""
        mock_ping.return_value = (True, 0.5)
        
        manager = PeerDiscoveryManager(max_peers=10)
        
        # Add some known peers
        for i in range(5):
            peer = PeerInfo(f"http://peer{i}:5000")
            peer.quality_score = 50 + i * 10
            manager.known_peers[peer.url] = peer
        
        connected = manager.connect_to_best_peers(count=3)
        assert len(connected) == 3
        assert len(manager.connected_peers) == 3

    @patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
    def test_connect_to_best_peers_dead_peers(self, mock_ping):
        """Test connection skips dead peers"""
        mock_ping.return_value = (False, 0.0)
        
        manager = PeerDiscoveryManager()
        manager.known_peers['http://peer1:5000'] = PeerInfo('http://peer1:5000')
        
        connected = manager.connect_to_best_peers(count=1)
        assert len(connected) == 0

    def test_remove_dead_peers(self):
        """Test removing dead peers"""
        manager = PeerDiscoveryManager()
        
        # Add alive and dead peers
        alive_peer = PeerInfo('http://alive:5000')
        alive_peer.last_seen = time.time()
        
        dead_peer = PeerInfo('http://dead:5000')
        dead_peer.last_seen = time.time() - 5000  # 5000 seconds ago
        
        manager.known_peers['http://alive:5000'] = alive_peer
        manager.known_peers['http://dead:5000'] = dead_peer
        manager.connected_peers.add('http://dead:5000')
        
        removed = manager.remove_dead_peers(timeout=3600)
        
        assert removed == 1
        assert 'http://alive:5000' in manager.known_peers
        assert 'http://dead:5000' not in manager.known_peers
        assert 'http://dead:5000' not in manager.connected_peers

    def test_update_peer_info_success(self):
        """Test updating peer info on success"""
        manager = PeerDiscoveryManager()
        peer = PeerInfo('http://peer:5000')
        manager.known_peers['http://peer:5000'] = peer
        
        manager.update_peer_info('http://peer:5000', success=True, response_time=0.3)
        
        assert peer.success_count == 1
        assert peer.quality_score > 50

    def test_update_peer_info_failure_disconnect(self):
        """Test peer disconnected on low quality"""
        manager = PeerDiscoveryManager()
        peer = PeerInfo('http://peer:5000')
        peer.quality_score = 15
        manager.known_peers['http://peer:5000'] = peer
        manager.connected_peers.add('http://peer:5000')
        
        # Multiple failures to drop quality below 10
        for _ in range(3):
            manager.update_peer_info('http://peer:5000', success=False)
        
        assert 'http://peer:5000' not in manager.connected_peers

    def test_get_peer_list(self):
        """Test getting peer list for sharing"""
        manager = PeerDiscoveryManager()
        
        # Add connected peers
        for i in range(3):
            peer = PeerInfo(f"http://connected{i}:5000")
            manager.known_peers[peer.url] = peer
            manager.connected_peers.add(peer.url)
        
        # Add known but not connected peers
        for i in range(5):
            peer = PeerInfo(f"http://known{i}:5000")
            peer.quality_score = 60 + i * 5
            manager.known_peers[peer.url] = peer
        
        peer_list = manager.get_peer_list()
        
        # Should include all connected peers
        assert all(f"http://connected{i}:5000" in peer_list for i in range(3))
        # Should be limited to 50 total
        assert len(peer_list) <= 50

    def test_get_connected_peer_urls(self):
        """Test getting connected peer URLs"""
        manager = PeerDiscoveryManager()
        manager.connected_peers = {'http://peer1:5000', 'http://peer2:5000'}
        
        urls = manager.get_connected_peer_urls()
        assert len(urls) == 2
        assert 'http://peer1:5000' in urls

    @patch('xai.core.peer_discovery.time.sleep')
    def test_discovery_loop_runs(self, mock_sleep):
        """Test discovery loop executes"""
        manager = PeerDiscoveryManager(discovery_interval=1)
        manager.is_running = True
        manager.last_discovery = 0
        
        # Make sleep stop the loop
        def stop_loop(*args):
            manager.is_running = False
        mock_sleep.side_effect = stop_loop
        
        manager._discovery_loop()
        
        assert mock_sleep.called

    def test_start(self):
        """Test starting peer discovery"""
        with patch.object(PeerDiscoveryManager, 'bootstrap_network'), \
             patch.object(PeerDiscoveryManager, 'connect_to_best_peers'):
            manager = PeerDiscoveryManager()
            manager.start()
            
            assert manager.is_running is True
            assert manager.discovery_thread is not None
            
            manager.stop()

    def test_stop(self):
        """Test stopping peer discovery"""
        with patch.object(PeerDiscoveryManager, 'bootstrap_network'), \
             patch.object(PeerDiscoveryManager, 'connect_to_best_peers'):
            manager = PeerDiscoveryManager()
            manager.start()
            time.sleep(0.1)
            manager.stop()
            
            assert manager.is_running is False

    def test_stop_not_running(self):
        """Test stopping when not running"""
        manager = PeerDiscoveryManager()
        manager.stop()  # Should not raise exception
        assert manager.is_running is False

    def test_get_stats(self):
        """Test getting peer discovery statistics"""
        manager = PeerDiscoveryManager(network_type="testnet", max_peers=50)
        
        # Add some peers
        for i in range(5):
            peer = PeerInfo(f"http://peer{i}:5000")
            peer.quality_score = 60 + i * 5
            manager.known_peers[peer.url] = peer
            if i < 3:
                manager.connected_peers.add(peer.url)
        
        manager.total_discoveries = 10
        manager.total_connections = 15
        manager.total_failed_connections = 5
        
        stats = manager.get_stats()
        
        assert stats['network_type'] == "testnet"
        assert stats['connected_peers'] == 3
        assert stats['known_peers'] == 5
        assert stats['max_peers'] == 50
        assert stats['total_discoveries'] == 10
        assert stats['total_connections'] == 15
        assert stats['total_failed_connections'] == 5
        assert 'diversity_score' in stats
        assert 'avg_peer_quality' in stats

    def test_get_peer_details(self):
        """Test getting detailed peer information"""
        manager = PeerDiscoveryManager()
        
        peer1 = PeerInfo('http://peer1:5000')
        peer1.quality_score = 75
        peer2 = PeerInfo('http://peer2:5000')
        peer2.quality_score = 60
        
        manager.known_peers['http://peer1:5000'] = peer1
        manager.known_peers['http://peer2:5000'] = peer2
        
        details = manager.get_peer_details()
        
        assert len(details) == 2
        assert all('url' in d and 'quality_score' in d for d in details)


class TestPeerDiscoveryAPI:
    """Test peer discovery API setup"""

    def test_setup_peer_discovery_api(self):
        """Test API endpoint setup"""
        from flask import Flask
        from xai.core.peer_discovery import setup_peer_discovery_api

        app = Flask(__name__)
        node = Mock()
        node.peer_discovery_manager = Mock()
        node.peer_discovery_manager.get_peer_list = Mock(return_value=['http://peer1:5000'])
        node.peer_discovery_manager.get_stats = Mock(return_value={})
        node.peer_discovery_manager.get_peer_details = Mock(return_value=[])

        setup_peer_discovery_api(app, node)

        # Verify routes are registered
        assert any('/peers/list' in str(rule) for rule in app.url_map.iter_rules())
        assert any('/peers/announce' in str(rule) for rule in app.url_map.iter_rules())
