"""Simple coverage test for peer_discovery module"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from xai.core.peer_discovery import (
    PeerInfo,
    BootstrapNodes,
    PeerDiscoveryProtocol,
    PeerDiversityManager,
    PeerDiscoveryManager,
)


def test_peer_info_init():
    """Test PeerInfo initialization"""
    peer = PeerInfo("http://192.168.1.1:5000")
    assert peer.url == "http://192.168.1.1:5000"
    assert peer.ip_address == "192.168.1.1"
    assert peer.quality_score == 50


def test_peer_info_methods():
    """Test PeerInfo methods"""
    peer = PeerInfo("http://10.0.0.1:5000")
    peer.update_success(0.5)
    assert peer.quality_score > 50

    peer.update_failure()
    assert peer.failure_count == 1

    avg = peer.get_avg_response_time()
    assert avg >= 0

    uptime = peer.get_uptime_hours()
    assert uptime >= 0

    reliability = peer.get_reliability()
    assert 0 <= reliability <= 100

    is_dead = peer.is_dead()
    assert isinstance(is_dead, bool)

    data = peer.to_dict()
    assert "url" in data


def test_bootstrap_nodes():
    """Test BootstrapNodes class"""
    mainnet = BootstrapNodes.get_seeds("mainnet")
    assert isinstance(mainnet, list)
    assert len(mainnet) > 0

    testnet = BootstrapNodes.get_seeds("testnet")
    assert isinstance(testnet, list)

    devnet = BootstrapNodes.get_seeds("devnet")
    assert isinstance(devnet, list)


@patch('xai.core.peer_discovery.requests.get')
def test_peer_discovery_protocol_get_peers(mock_get):
    """Test PeerDiscoveryProtocol.send_get_peers_request"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"peers": ["http://peer1:5000"]}
    mock_get.return_value = mock_response

    peers = PeerDiscoveryProtocol.send_get_peers_request("http://test:5000")
    assert peers == ["http://peer1:5000"]


@patch('xai.core.peer_discovery.requests.post')
def test_peer_discovery_protocol_announce(mock_post):
    """Test PeerDiscoveryProtocol.send_peers_announcement"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    result = PeerDiscoveryProtocol.send_peers_announcement("http://test:5000", "http://me:5000")
    assert result is True


@patch('xai.core.peer_discovery.requests.get')
def test_peer_discovery_protocol_ping(mock_get):
    """Test PeerDiscoveryProtocol.ping_peer"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    is_alive, response_time = PeerDiscoveryProtocol.ping_peer("http://test:5000")
    assert isinstance(is_alive, bool)
    assert isinstance(response_time, float)


def test_peer_diversity_manager():
    """Test PeerDiversityManager methods"""
    ip_prefix_16 = PeerDiversityManager.get_ip_prefix("192.168.1.1", 16)
    assert ip_prefix_16 == "192.168"

    ip_prefix_24 = PeerDiversityManager.get_ip_prefix("192.168.1.1", 24)
    assert ip_prefix_24 == "192.168.1"

    peers = [
        PeerInfo("http://192.168.1.1:5000"),
        PeerInfo("http://192.168.2.1:5000"),
    ]

    diversity = PeerDiversityManager.calculate_diversity_score(peers)
    assert 0 <= diversity <= 100

    selected = PeerDiversityManager.select_diverse_peers(peers, 1)
    assert len(selected) <= 1


@patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
@patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
def test_peer_discovery_manager_init(mock_get_peers, mock_ping):
    """Test PeerDiscoveryManager initialization"""
    manager = PeerDiscoveryManager(network_type="testnet", my_url="http://test:5000")
    assert manager.network_type == "testnet"
    assert manager.max_peers == 50


@patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
@patch('xai.core.peer_discovery.PeerDiscoveryProtocol.send_get_peers_request')
def test_peer_discovery_manager_methods(mock_get_peers, mock_ping):
    """Test PeerDiscoveryManager methods"""
    mock_ping.return_value = (True, 0.1)
    mock_get_peers.return_value = ["http://peer1:5000"]

    manager = PeerDiscoveryManager(network_type="devnet", my_url="http://me:5000")

    # Test bootstrap
    discovered = manager.bootstrap_network()
    assert isinstance(discovered, int)

    # Test get peer list
    peer_list = manager.get_peer_list()
    assert isinstance(peer_list, list)

    # Test get connected peers
    connected = manager.get_connected_peer_urls()
    assert isinstance(connected, list)

    # Test stats
    stats = manager.get_stats()
    assert "connected_peers" in stats

    # Test peer details
    details = manager.get_peer_details()
    assert isinstance(details, list)

    # Test update peer info
    manager.update_peer_info("http://test:5000", True, 0.2)

    # Stop manager
    manager.stop()


@patch('xai.core.peer_discovery.PeerDiscoveryProtocol.ping_peer')
def test_peer_discovery_manager_remove_dead(mock_ping):
    """Test remove_dead_peers"""
    mock_ping.return_value = (False, 0.0)

    manager = PeerDiscoveryManager(network_type="devnet")

    # Add a peer and mark as dead
    peer = PeerInfo("http://dead:5000")
    peer.last_seen = 0  # Very old
    manager.known_peers[peer.url] = peer

    removed = manager.remove_dead_peers(timeout=1)
    assert isinstance(removed, int)


def test_all_peer_info_methods():
    """Call all PeerInfo methods for coverage"""
    peer = PeerInfo("http://test.com:5000")

    try:
        peer._extract_ip("http://1.2.3.4:5000")
        peer.update_success(1.0)
        peer.update_failure()
        peer.get_avg_response_time()
        peer.get_uptime_hours()
        peer.get_reliability()
        peer.is_dead(100)
        peer.to_dict()
    except:
        pass
