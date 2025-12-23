"""
Test suite for XAI Blockchain Peer Discovery System
"""

import time
import unittest

from peer_discovery import (
    BootstrapNodes,
    PeerDiscoveryManager,
    PeerDiscoveryProtocol,
    PeerDiversityManager,
    PeerInfo,
)


class TestPeerInfo(unittest.TestCase):
    """Test PeerInfo class"""

    def test_peer_creation(self):
        """Test creating peer info"""
        peer = PeerInfo("http://192.168.1.100:5000")

        self.assertEqual(peer.url, "http://192.168.1.100:5000")
        self.assertEqual(peer.ip_address, "192.168.1.100")
        self.assertEqual(peer.quality_score, 50)
        self.assertFalse(peer.is_bootstrap)

    def test_peer_success_update(self):
        """Test updating peer on success"""
        peer = PeerInfo("http://192.168.1.100:5000")
        initial_score = peer.quality_score

        peer.update_success(0.5)

        self.assertEqual(peer.success_count, 1)
        self.assertGreater(peer.quality_score, initial_score)
        self.assertEqual(len(peer.response_times), 1)
        self.assertEqual(peer.response_times[0], 0.5)

    def test_peer_failure_update(self):
        """Test updating peer on failure"""
        peer = PeerInfo("http://192.168.1.100:5000")
        initial_score = peer.quality_score

        peer.update_failure()

        self.assertEqual(peer.failure_count, 1)
        self.assertLess(peer.quality_score, initial_score)

    def test_peer_reliability(self):
        """Test reliability calculation"""
        peer = PeerInfo("http://192.168.1.100:5000")

        # Add some successes and failures
        for _ in range(8):
            peer.update_success()
        for _ in range(2):
            peer.update_failure()

        reliability = peer.get_reliability()
        self.assertEqual(reliability, 80.0)  # 8/10 = 80%

    def test_peer_avg_response_time(self):
        """Test average response time"""
        peer = PeerInfo("http://192.168.1.100:5000")

        peer.update_success(0.1)
        peer.update_success(0.2)
        peer.update_success(0.3)

        avg = peer.get_avg_response_time()
        self.assertAlmostEqual(avg, 0.2, places=5)  # (0.1 + 0.2 + 0.3) / 3

    def test_peer_dead_check(self):
        """Test dead peer detection"""
        peer = PeerInfo("http://192.168.1.100:5000")

        # Fresh peer is not dead
        self.assertFalse(peer.is_dead(timeout=10))

        # Simulate old peer
        peer.last_seen = time.time() - 3700  # Over 1 hour ago
        self.assertTrue(peer.is_dead(timeout=3600))


class TestBootstrapNodes(unittest.TestCase):
    """Test bootstrap node configuration"""

    def test_get_mainnet_seeds(self):
        """Test getting mainnet seeds"""
        seeds = BootstrapNodes.get_seeds("mainnet")

        self.assertIsInstance(seeds, list)
        self.assertGreater(len(seeds), 0)
        self.assertTrue(all("http" in seed for seed in seeds))

    def test_get_testnet_seeds(self):
        """Test getting testnet seeds"""
        seeds = BootstrapNodes.get_seeds("testnet")

        self.assertIsInstance(seeds, list)
        self.assertGreater(len(seeds), 0)

    def test_default_to_mainnet(self):
        """Test default network type"""
        seeds = BootstrapNodes.get_seeds("invalid")
        mainnet_seeds = BootstrapNodes.get_seeds("mainnet")

        self.assertEqual(seeds, mainnet_seeds)


class TestPeerDiversityManager(unittest.TestCase):
    """Test peer diversity management"""

    def test_get_ip_prefix_16(self):
        """Test /16 IP prefix extraction"""
        prefix = PeerDiversityManager.get_ip_prefix("192.168.1.100", 16)
        self.assertEqual(prefix, "192.168")

    def test_get_ip_prefix_24(self):
        """Test /24 IP prefix extraction"""
        prefix = PeerDiversityManager.get_ip_prefix("192.168.1.100", 24)
        self.assertEqual(prefix, "192.168.1")

    def test_diversity_score(self):
        """Test diversity score calculation"""
        # Create peers with same subnet
        peers_same = [
            PeerInfo("http://192.168.1.100:5000"),
            PeerInfo("http://192.168.1.101:5000"),
            PeerInfo("http://192.168.1.102:5000"),
        ]

        # Create diverse peers
        peers_diverse = [
            PeerInfo("http://10.0.0.1:5000"),
            PeerInfo("http://172.16.0.1:5000"),
            PeerInfo("http://192.168.0.1:5000"),
        ]

        score_same = PeerDiversityManager.calculate_diversity_score(peers_same)
        score_diverse = PeerDiversityManager.calculate_diversity_score(peers_diverse)

        # Diverse peers should have higher score
        self.assertGreater(score_diverse, score_same)

    def test_select_diverse_peers(self):
        """Test diverse peer selection"""
        peers = [
            PeerInfo("http://192.168.1.100:5000"),  # 192.168 subnet
            PeerInfo("http://192.168.1.101:5000"),  # 192.168 subnet
            PeerInfo("http://10.0.0.1:5000"),  # 10.0 subnet
            PeerInfo("http://172.16.0.1:5000"),  # 172.16 subnet
        ]

        # Give different quality scores
        peers[0].quality_score = 90
        peers[1].quality_score = 95
        peers[2].quality_score = 85
        peers[3].quality_score = 80

        selected = PeerDiversityManager.select_diverse_peers(peers, 3, prefer_quality=True)

        self.assertEqual(len(selected), 3)

        # Should prefer diversity over quality
        # (one from 192.168, one from 10.0, one from 172.16)
        ip_prefixes = set(
            PeerDiversityManager.get_ip_prefix(peer.ip_address, 16) for peer in selected
        )
        self.assertGreaterEqual(len(ip_prefixes), 2)


class TestPeerDiscoveryManager(unittest.TestCase):
    """Test main peer discovery manager"""

    def setUp(self):
        """Setup test manager"""
        self.manager = PeerDiscoveryManager(
            network_type="testnet",
            my_url="http://127.0.0.1:9999",
            max_peers=20,
            discovery_interval=60,
        )

    def test_manager_initialization(self):
        """Test manager initialization"""
        self.assertEqual(self.manager.network_type, "testnet")
        self.assertEqual(self.manager.my_url, "http://127.0.0.1:9999")
        self.assertEqual(self.manager.max_peers, 20)
        self.assertEqual(len(self.manager.known_peers), 0)
        self.assertEqual(len(self.manager.connected_peers), 0)

    def test_update_peer_info(self):
        """Test updating peer information"""
        peer_url = "http://192.168.1.100:5000"
        peer = PeerInfo(peer_url)
        self.manager.known_peers[peer_url] = peer

        # Update success
        self.manager.update_peer_info(peer_url, success=True, response_time=0.5)

        self.assertEqual(peer.success_count, 1)
        self.assertEqual(len(peer.response_times), 1)

    def test_get_peer_list(self):
        """Test getting peer list for sharing"""
        # Add some peers
        for i in range(10):
            peer_url = f"http://192.168.1.{100+i}:5000"
            self.manager.known_peers[peer_url] = PeerInfo(peer_url)

        # Connect to some
        connected = list(self.manager.known_peers.keys())[:3]
        self.manager.connected_peers.update(connected)

        peer_list = self.manager.get_peer_list()

        self.assertIsInstance(peer_list, list)
        self.assertGreater(len(peer_list), 0)
        self.assertLessEqual(len(peer_list), 50)

    def test_remove_dead_peers(self):
        """Test removing dead peers"""
        # Add some peers
        peer1 = PeerInfo("http://192.168.1.100:5000")
        peer2 = PeerInfo("http://192.168.1.101:5000")

        # Make peer1 old (dead)
        peer1.last_seen = time.time() - 7200  # 2 hours ago

        self.manager.known_peers[peer1.url] = peer1
        self.manager.known_peers[peer2.url] = peer2

        removed = self.manager.remove_dead_peers(timeout=3600)

        self.assertEqual(removed, 1)
        self.assertNotIn(peer1.url, self.manager.known_peers)
        self.assertIn(peer2.url, self.manager.known_peers)

    def test_get_stats(self):
        """Test getting statistics"""
        # Add some peers
        for i in range(5):
            peer_url = f"http://192.168.1.{100+i}:5000"
            self.manager.known_peers[peer_url] = PeerInfo(peer_url)

        stats = self.manager.get_stats()

        self.assertEqual(stats["network_type"], "testnet")
        self.assertEqual(stats["known_peers"], 5)
        self.assertEqual(stats["max_peers"], 20)
        self.assertIn("diversity_score", stats)
        self.assertIn("avg_peer_quality", stats)

    def test_get_peer_details(self):
        """Test getting peer details"""
        # Add some peers
        for i in range(3):
            peer_url = f"http://192.168.1.{100+i}:5000"
            peer = PeerInfo(peer_url)
            peer.quality_score = 70 + i * 10
            self.manager.known_peers[peer_url] = peer

        details = self.manager.get_peer_details()

        self.assertEqual(len(details), 3)
        self.assertTrue(all(isinstance(d, dict) for d in details))
        self.assertTrue(all("url" in d for d in details))
        self.assertTrue(all("quality_score" in d for d in details))


class TestIntegration(unittest.TestCase):
    """Integration tests"""

    def test_full_peer_lifecycle(self):
        """Test complete peer lifecycle"""
        manager = PeerDiscoveryManager(
            network_type="testnet", my_url="http://127.0.0.1:9999", max_peers=10
        )

        # Add a peer
        peer_url = "http://192.168.1.100:5000"
        peer = PeerInfo(peer_url)
        manager.known_peers[peer_url] = peer

        # Update with successes
        for _ in range(5):
            manager.update_peer_info(peer_url, success=True, response_time=0.5)

        # Check quality improved
        self.assertGreater(peer.quality_score, 50)

        # Add failures
        for _ in range(10):
            manager.update_peer_info(peer_url, success=False)

        # Check quality decreased
        self.assertLess(peer.quality_score, 50)

        # Get stats
        stats = manager.get_stats()
        self.assertEqual(stats["known_peers"], 1)


def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
