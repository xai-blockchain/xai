"""
XAI Blockchain - Peer Discovery and Network Bootstrap

Implements:
- Hardcoded bootstrap/seed nodes
- Automatic peer discovery on startup
- Peer exchange protocol (GetPeers/SendPeers)
- Peer quality scoring and diversity
- Periodic peer discovery (every 5 minutes)
- Dead peer removal
- Geographic and IP diversity preference
"""

import time
import json
import secrets
import threading
import logging
import requests
from flask import request
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class PeerInfo:
    """Information about a discovered peer"""

    def __init__(self, url: str, ip_address: str = None):
        self.url = url
        self.ip_address = ip_address or self._extract_ip(url)
        self.last_seen = time.time()
        self.first_seen = time.time()
        self.quality_score = 50  # Start at medium quality
        self.success_count = 0
        self.failure_count = 0
        self.response_times = []  # Last 10 response times
        self.blocks_shared = 0
        self.transactions_shared = 0
        self.is_bootstrap = False
        self.version = None
        self.asn = None
        self.chain_height = 0

    def _extract_ip(self, url: str) -> str:
        """Extract IP address from URL"""
        import re

        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", url)
        return ip_match.group(1) if ip_match else "unknown"

    def update_success(self, response_time: float = None):
        """Update peer metrics on successful interaction"""
        self.success_count += 1
        self.last_seen = time.time()

        if response_time is not None:
            self.response_times.append(response_time)
            if len(self.response_times) > 10:
                self.response_times.pop(0)

        # Increase quality score (max 100)
        self.quality_score = min(100, self.quality_score + 2)

    def update_failure(self):
        """Update peer metrics on failed interaction"""
        self.failure_count += 1

        # Decrease quality score (min 0)
        self.quality_score = max(0, self.quality_score - 5)

    def get_avg_response_time(self) -> float:
        """Get average response time"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def get_uptime_hours(self) -> float:
        """Get how long we've known this peer"""
        return (time.time() - self.first_seen) / 3600

    def get_reliability(self) -> float:
        """Calculate reliability percentage (0-100)"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 50.0
        return (self.success_count / total) * 100

    def is_dead(self, timeout: int = 3600) -> bool:
        """Check if peer hasn't responded in timeout seconds"""
        return (time.time() - self.last_seen) > timeout

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "url": self.url,
            "ip_address": self.ip_address,
            "last_seen": self.last_seen,
            "quality_score": self.quality_score,
            "reliability": self.get_reliability(),
            "avg_response_time": self.get_avg_response_time(),
            "uptime_hours": self.get_uptime_hours(),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "is_bootstrap": self.is_bootstrap,
            "version": self.version,
            "chain_height": self.chain_height,
        }


class BootstrapNodes:
    """Hardcoded bootstrap/seed nodes for network discovery"""

    # Production seed nodes (example addresses - replace with actual nodes)
    MAINNET_SEEDS = [
        "http://seed1.xaicoin.network:5000",
        "http://seed2.xaicoin.network:5000",
        "http://seed3.xaicoin.network:5000",
        "http://seed4.xaicoin.network:5000",
        "http://seed5.xaicoin.network:5000",
    ]

    # Testnet seed nodes
    TESTNET_SEEDS = [
        "http://testnet-seed1.xaicoin.network:5001",
        "http://testnet-seed2.xaicoin.network:5001",
        "http://testnet-seed3.xaicoin.network:5001",
    ]

    # Local development seeds
    DEVNET_SEEDS = [
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5001",
        "http://127.0.0.1:5002",
    ]

    @classmethod
    def get_seeds(cls, network_type: str = "mainnet") -> List[str]:
        """
        Get bootstrap nodes for network type

        Args:
            network_type: "mainnet", "testnet", or "devnet"

        Returns:
            List of seed node URLs
        """
        network_map = {
            "mainnet": cls.MAINNET_SEEDS,
            "testnet": cls.TESTNET_SEEDS,
            "devnet": cls.DEVNET_SEEDS,
        }
        return network_map.get(network_type.lower(), cls.MAINNET_SEEDS)


class PeerDiscoveryProtocol:
    """Implements peer exchange protocol"""

    @staticmethod
    def send_get_peers_request(peer_url: str, timeout: int = 5) -> Optional[List[str]]:
        """
        Request peer list from a node

        Args:
            peer_url: URL of peer to query
            timeout: Request timeout in seconds

        Returns:
            List of peer URLs or None if failed
        """
        try:
            response = requests.get(f"{peer_url}/peers/list", timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                return data.get("peers", [])

        except requests.RequestException as e:
            logger.warning(
                "Failed to get peers from %s: %s",
                peer_url,
                e,
                extra={"event": "peer_discovery.get_peers_failed", "peer": peer_url},
            )

        return None

    @staticmethod
    def send_peers_announcement(peer_url: str, my_url: str, timeout: int = 5) -> bool:
        """
        Announce ourselves to a peer

        Args:
            peer_url: URL of peer to announce to
            my_url: Our node URL
            timeout: Request timeout

        Returns:
            True if successful
        """
        try:
            response = requests.post(
                f"{peer_url}/peers/announce", json={"peer_url": my_url}, timeout=timeout
            )

            return response.status_code == 200

        except requests.RequestException as e:
            logger.warning(
                "Failed to announce peer to %s: %s",
                peer_url,
                e,
                extra={"event": "peer_discovery.announce_failed", "peer": peer_url},
            )

        return False

    @staticmethod
    def ping_peer(peer_url: str, timeout: int = 3) -> Tuple[bool, float]:
        """
        Ping a peer to check if alive

        Args:
            peer_url: URL of peer
            timeout: Request timeout

        Returns:
            (is_alive, response_time)
        """
        try:
            start = time.time()
            response = requests.get(f"{peer_url}/", timeout=timeout)
            response_time = time.time() - start

            return response.status_code == 200, response_time

        except requests.RequestException as exc:
            logger.debug(
                "Peer ping failed for %s: %s",
                peer_url,
                exc,
                extra={"event": "peer_discovery.ping_failed", "peer": peer_url},
            )
            return False, 0.0

    @staticmethod
    def get_peer_info(peer_url: str, timeout: int = 5) -> Optional[dict]:
        """
        Get detailed peer information

        Args:
            peer_url: URL of peer
            timeout: Request timeout

        Returns:
            Peer info dict or None
        """
        try:
            response = requests.get(f"{peer_url}/stats", timeout=timeout)

            if response.status_code == 200:
                return response.json()

        except requests.RequestException as exc:
            logger.debug(
                "Failed to fetch peer info from %s: %s",
                peer_url,
                exc,
                extra={"event": "peer_discovery.info_failed", "peer": peer_url},
            )

        return None


class PeerDiversityManager:
    """Manages peer diversity for eclipse attack resistance"""

    @staticmethod
    def get_ip_prefix(ip_address: str, prefix_length: int = 16) -> str:
        """
        Get IP prefix for diversity check

        Args:
            ip_address: IP address
            prefix_length: Prefix bits (16 = /16, 24 = /24)

        Returns:
            IP prefix string
        """
        parts = ip_address.split(".")
        if prefix_length == 16 and len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        elif prefix_length == 24 and len(parts) >= 3:
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        return ip_address

    @staticmethod
    def calculate_diversity_score(peers: List[PeerInfo]) -> float:
        """
        Calculate diversity score (0-100) based on IP distribution

        Args:
            peers: List of peer info objects

        Returns:
            Diversity score
        """
        if not peers:
            return 0.0

        # Count unique /16 prefixes
        prefixes_16 = set()
        prefixes_24 = set()

        for peer in peers:
            prefixes_16.add(PeerDiversityManager.get_ip_prefix(peer.ip_address, 16))
            prefixes_24.add(PeerDiversityManager.get_ip_prefix(peer.ip_address, 24))

        # More unique prefixes = better diversity
        total_peers = len(peers)
        diversity_16 = len(prefixes_16) / total_peers
        diversity_24 = len(prefixes_24) / total_peers

        # Weighted average (prefer /16 diversity)
        score = (diversity_16 * 0.7 + diversity_24 * 0.3) * 100

        return min(100, score)

    @staticmethod
    def select_diverse_peers(
        peers: List[PeerInfo], count: int, prefer_quality: bool = True
    ) -> List[PeerInfo]:
        """
        Select diverse set of peers

        Args:
            peers: Available peers
            count: Number to select
            prefer_quality: Also prefer high-quality peers

        Returns:
            List of selected peers
        """
        if len(peers) <= count:
            return peers

        selected = []
        available = peers.copy()
        used_prefixes = set()

        # Sort by quality if preferred
        if prefer_quality:
            available.sort(key=lambda p: p.quality_score, reverse=True)

        # Select diverse peers
        while len(selected) < count and available:
            # Try to find peer with unique prefix
            found_diverse = False

            for peer in available:
                prefix = PeerDiversityManager.get_ip_prefix(peer.ip_address, 16)
                if prefix not in used_prefixes:
                    selected.append(peer)
                    used_prefixes.add(prefix)
                    available.remove(peer)
                    found_diverse = True
                    break

            # If no diverse peer found, just take next available
            if not found_diverse and available:
                peer = available.pop(0)
                selected.append(peer)
                prefix = PeerDiversityManager.get_ip_prefix(peer.ip_address, 16)
                used_prefixes.add(prefix)

        return selected


class PeerDiscoveryManager:
    """
    Main peer discovery and management system

    Features:
    - Connects to bootstrap nodes on startup
    - Periodic peer discovery (every 5 minutes)
    - Peer quality scoring
    - Dead peer removal
    - Diversity preference
    """

    def __init__(
        self,
        network_type: str = "mainnet",
        my_url: str = None,
        max_peers: int = 50,
        discovery_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize peer discovery manager

        Args:
            network_type: Network type (mainnet/testnet/devnet)
            my_url: This node's URL
            max_peers: Maximum number of peers to maintain
            discovery_interval: Seconds between discovery rounds
        """
        self.network_type = network_type
        self.my_url = my_url
        self.max_peers = max_peers
        self.discovery_interval = discovery_interval

        # Peer storage
        self.known_peers: Dict[str, PeerInfo] = {}  # url -> PeerInfo
        self.connected_peers: Set[str] = set()
        self.prefix_counts: Dict[str, int] = defaultdict(int)
        self.asn_counts: Dict[str, int] = defaultdict(int)
        self.max_per_prefix = getattr(Config, "P2P_MAX_PEERS_PER_PREFIX", 8)
        self.max_per_asn = getattr(Config, "P2P_MAX_PEERS_PER_ASN", 16)
        self.min_unique_prefixes = getattr(Config, "P2P_MIN_UNIQUE_PREFIXES", 5)
        self.min_unique_asns = getattr(Config, "P2P_MIN_UNIQUE_ASNS", 5)
        self.diversity_prefix_length = getattr(Config, "P2P_DIVERSITY_PREFIX_LENGTH", 16)

        # Discovery state
        self.is_running = False
        self.discovery_thread = None
        self.last_discovery = 0

        # Statistics
        self.total_discoveries = 0
        self.total_connections = 0
        self.total_failed_connections = 0

        logger.info(
            "Peer discovery initialized for %s network",
            network_type,
            extra={"event": "peer_discovery.init", "network": network_type},
        )

    def bootstrap_network(self) -> int:
        """
        Connect to bootstrap nodes and discover initial peers

        Returns:
            Number of peers discovered
        """
        logger.info(
            "Starting network bootstrap",
            extra={"event": "peer_discovery.bootstrap_start", "network": self.network_type},
        )

        seeds = BootstrapNodes.get_seeds(self.network_type)
        discovered = 0

        for seed_url in seeds:
            # Skip if it's our own URL
            if seed_url == self.my_url:
                continue

            logger.info(
                "Connecting to bootstrap seed %s",
                seed_url,
                extra={"event": "peer_discovery.seed_connect", "peer": seed_url},
            )

            # Ping seed node
            is_alive, response_time = PeerDiscoveryProtocol.ping_peer(seed_url)

            if is_alive:
                # Add as known peer
                peer_info = PeerInfo(seed_url)
                peer_info.is_bootstrap = True
                peer_info.update_success(response_time)

                self.known_peers[seed_url] = peer_info
                discovered += 1

                # Get peers from this seed
                peer_list = PeerDiscoveryProtocol.send_get_peers_request(seed_url)
                if peer_list:
                    for peer_url in peer_list:
                        if peer_url != self.my_url and peer_url not in self.known_peers:
                            self.known_peers[peer_url] = PeerInfo(peer_url)
                            discovered += 1

                # Announce ourselves
                if self.my_url:
                    PeerDiscoveryProtocol.send_peers_announcement(seed_url, self.my_url)

                logger.info(
                    "Connected to bootstrap seed",
                    extra={"event": "peer_discovery.seed_connected", "peer": seed_url},
                )
            else:
                logger.warning(
                    "Failed to connect to bootstrap seed",
                    extra={"event": "peer_discovery.seed_failed", "peer": seed_url},
                )

        logger.info(
            "Bootstrap complete with %d peers discovered",
            discovered,
            extra={"event": "peer_discovery.bootstrap_complete", "count": discovered},
        )
        return discovered

    def discover_peers(self) -> int:
        """
        Discover new peers from connected peers

        Returns:
            Number of new peers discovered
        """
        if not self.connected_peers:
            return 0

        new_peers = 0

        # Sample some connected peers to ask for their peer lists
        # Use cryptographically secure sampling to prevent peer selection prediction
        sample_size = min(5, len(self.connected_peers))
        sr = secrets.SystemRandom()
        sample_peers = sr.sample(list(self.connected_peers), sample_size)

        for peer_url in sample_peers:
            peer_list = PeerDiscoveryProtocol.send_get_peers_request(peer_url)

            if peer_list:
                for new_peer_url in peer_list:
                    # Skip our own URL and already known peers
                    if new_peer_url == self.my_url:
                        continue

                    if new_peer_url not in self.known_peers:
                        self.known_peers[new_peer_url] = PeerInfo(new_peer_url)
                        new_peers += 1

        if new_peers > 0:
            logger.info(
                "Discovered %d new peers",
                new_peers,
                extra={"event": "peer_discovery.discovered", "count": new_peers},
            )

        self.total_discoveries += new_peers
        return new_peers

    def connect_to_best_peers(self, count: int = None) -> List[str]:
        """
        Connect to best quality diverse peers

        Args:
            count: Number of peers to connect to (default: fill to max_peers)

        Returns:
            List of newly connected peer URLs
        """
        if count is None:
            count = self.max_peers - len(self.connected_peers)

        if count <= 0:
            return []

        # Get available peers (not already connected)
        available = [
            peer
            for url, peer in self.known_peers.items()
            if url not in self.connected_peers and not peer.is_dead()
        ]

        if not available:
            return []

        # Select diverse, high-quality peers
        selected = PeerDiversityManager.select_diverse_peers(available, count, prefer_quality=True)

        connected = []

        for peer in selected:
            # Try to connect
            is_alive, response_time = PeerDiscoveryProtocol.ping_peer(peer.url)

            if is_alive:
                peer.update_success(response_time)
                self.connected_peers.add(peer.url)
                connected.append(peer.url)
                self.total_connections += 1
                logger.info(
                    "Connected to peer",
                    extra={"event": "peer_discovery.peer_connected", "peer": peer.url},
                )
            else:
                peer.update_failure()
                self.total_failed_connections += 1

        return connected

    def remove_dead_peers(self, timeout: int = 3600) -> int:
        """
        Remove peers that haven't responded in timeout seconds

        Args:
            timeout: Seconds before considering peer dead

        Returns:
            Number of peers removed
        """
        dead_peers = [url for url, peer in self.known_peers.items() if peer.is_dead(timeout)]

        for url in dead_peers:
            # Disconnect if connected
            if url in self.connected_peers:
                self.connected_peers.remove(url)

            # Remove from known peers
            del self.known_peers[url]
            logger.info(
                "Removed dead peer",
                extra={"event": "peer_discovery.peer_removed", "peer": url},
            )

        return len(dead_peers)

    def update_peer_info(self, peer_url: str, success: bool = True, response_time: float = None):
        """
        Update peer information after interaction

        Args:
            peer_url: Peer URL
            success: Whether interaction was successful
            response_time: Response time in seconds
        """
        if peer_url in self.known_peers:
            peer = self.known_peers[peer_url]

            if success:
                peer.update_success(response_time)
            else:
                peer.update_failure()

                # Disconnect if quality too low
                if peer.quality_score < 10 and peer_url in self.connected_peers:
                    self.connected_peers.remove(peer_url)
                    logger.warning(
                        "Disconnected low-quality peer",
                        extra={
                            "event": "peer_discovery.peer_disconnected_low_quality",
                            "peer": peer_url,
                            "score": peer.quality_score,
                        },
                    )

    def get_peer_list(self) -> List[str]:
        """
        Get list of known peer URLs (for sharing)

        Returns:
            List of peer URLs
        """
        # Return connected peers + best known peers
        connected = list(self.connected_peers)

        # Add best known peers
        other_peers = [url for url in self.known_peers.keys() if url not in self.connected_peers]

        # Sort by quality
        other_peers.sort(key=lambda url: self.known_peers[url].quality_score, reverse=True)

        # Return up to 50 peers
        return (connected + other_peers)[:50]

    def get_connected_peer_urls(self) -> List[str]:
        """Get list of connected peer URLs"""
        return list(self.connected_peers)

    def _discovery_loop(self):
        """Background discovery loop"""
        while self.is_running:
            try:
                current_time = time.time()

                # Run discovery if interval elapsed
                if current_time - self.last_discovery >= self.discovery_interval:
                    logger.info(
                        "Running periodic peer discovery round",
                        extra={"event": "peer_discovery.loop"},
                    )

                    # Discover new peers
                    self.discover_peers()

                    # Remove dead peers
                    self.remove_dead_peers()

                    # Connect to more peers if needed
                    if len(self.connected_peers) < self.max_peers:
                        self.connect_to_best_peers()

                    self.last_discovery = current_time

                # Sleep for a bit
                time.sleep(10)

            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
                logger.error(
                    "Peer discovery loop error: %s",
                    exc,
                    extra={"event": "peer_discovery.loop_error"},
                    exc_info=True,
                )
                time.sleep(10)

    def start(self):
        """Start peer discovery manager"""
        if self.is_running:
            return

        logger.info("Starting peer discovery service", extra={"event": "peer_discovery.start"})

        # Bootstrap network
        self.bootstrap_network()

        # Connect to initial peers
        self.connect_to_best_peers()

        # Start background discovery
        self.is_running = True
        self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.discovery_thread.start()

        logger.info(
            "Peer discovery service started",
            extra={"event": "peer_discovery.started"},
        )

    def stop(self):
        """Stop peer discovery manager"""
        if not self.is_running:
            return

        logger.info("Stopping peer discovery service", extra={"event": "peer_discovery.stop"})
        self.is_running = False

        if self.discovery_thread:
            self.discovery_thread.join(timeout=5)

        logger.info(
            "Peer discovery service stopped",
            extra={"event": "peer_discovery.stopped"},
        )

    def get_stats(self) -> dict:
        """Get peer discovery statistics"""
        diversity_score = PeerDiversityManager.calculate_diversity_score(
            list(self.known_peers.values())
        )

        connected_peers = [
            self.known_peers[url] for url in self.connected_peers if url in self.known_peers
        ]

        avg_quality = (
            sum(p.quality_score for p in connected_peers) / len(connected_peers)
            if connected_peers
            else 0
        )

        return {
            "network_type": self.network_type,
            "connected_peers": len(self.connected_peers),
            "known_peers": len(self.known_peers),
            "max_peers": self.max_peers,
            "diversity_score": diversity_score,
            "avg_peer_quality": avg_quality,
            "total_discoveries": self.total_discoveries,
            "total_connections": self.total_connections,
            "total_failed_connections": self.total_failed_connections,
            "is_running": self.is_running,
        }

    def get_peer_details(self) -> List[dict]:
        """Get detailed information about all known peers"""
        return [peer.to_dict() for peer in self.known_peers.values()]


def setup_peer_discovery_api(app, node):
    """
    Setup peer discovery API endpoints

    Args:
        app: Flask app
        node: BlockchainNode instance
    """

    @app.route("/peers/list", methods=["GET"])
    def get_peer_list():
        """Get list of known peers (for peer exchange)"""
        if hasattr(node, "peer_discovery_manager"):
            peers = node.peer_discovery_manager.get_peer_list()
            return {"success": True, "count": len(peers), "peers": peers}
        else:
            return {"success": True, "count": len(node.peers), "peers": list(node.peers)}

    @app.route("/peers/announce", methods=["POST"])
    def announce_peer():
        """Accept peer announcement"""
        data = request.json

        if "peer_url" not in data:
            return {"error": "Missing peer_url"}, 400

        peer_url = data["peer_url"]

        # Add peer using node's add_peer method (includes security checks)
        if node.add_peer(peer_url):
            return {"success": True, "message": f"Peer {peer_url} added"}
        else:
            return {"success": False, "message": "Peer rejected by security checks"}, 403

    @app.route("/peers/discovery/stats", methods=["GET"])
    def get_discovery_stats():
        """Get peer discovery statistics"""
        if hasattr(node, "peer_discovery_manager"):
            stats = node.peer_discovery_manager.get_stats()
            return {"success": True, "stats": stats}
        else:
            return {"error": "Peer discovery not enabled"}, 503

    @app.route("/peers/discovery/details", methods=["GET"])
    def get_peer_details():
        """Get detailed peer information"""
        if hasattr(node, "peer_discovery_manager"):
            details = node.peer_discovery_manager.get_peer_details()
            return {"success": True, "count": len(details), "peers": details}
        else:
            return {"error": "Peer discovery not enabled"}, 503

    logger.info("Peer discovery API endpoints registered", extra={"event": "peer_discovery.api_ready"})


if __name__ == "__main__":
    # Test peer discovery
    logger.info("=== XAI Peer Discovery Test ===")

    # Create discovery manager
    manager = PeerDiscoveryManager(
        network_type="testnet", my_url="http://127.0.0.1:5555", max_peers=20
    )

    # Start discovery
    manager.start()

    # Let it run for a bit
    time.sleep(30)

    # Show stats
    stats = manager.get_stats()
    logger.info("=== Discovery Statistics ===")
    for key, value in stats.items():
        logger.info("%s: %s", key, value)

    # Show peer details
    details = manager.get_peer_details()
    logger.info("=== Known Peers (%d) ===", len(details))
    for peer in details[:5]:  # Show first 5
        logger.info(
            "Peer %s | quality=%s reliability=%.1f avg_latency=%.3fs",
            peer["url"],
            peer["quality_score"],
            peer["reliability"],
            peer["avg_response_time"],
        )

    # Stop
    manager.stop()
