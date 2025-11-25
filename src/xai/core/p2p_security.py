"""
XAI Blockchain - P2P Network Security

Protection against:
- Sybil attacks (connection limits per IP)
- Eclipse attacks (peer diversity)
- Malicious peers (reputation and banning)
- Message flooding (size and rate limits)
"""

import time
import hashlib
from typing import Dict, Set, Optional, Tuple
from collections import defaultdict


class P2PSecurityConfig:
    """P2P security configuration"""

    # Connection limits
    MAX_PEERS_TOTAL = 50
    MAX_CONNECTIONS_PER_IP = 3
    MIN_PEER_DIVERSITY = 5  # Minimum unique IP prefixes (/16)

    # Message limits
    MAX_MESSAGE_SIZE = 10_000_000  # 10 MB max message
    MAX_MESSAGES_PER_SECOND = 100  # Per peer

    # Reputation
    INITIAL_REPUTATION = 100
    MIN_REPUTATION = 0
    MAX_REPUTATION = 200
    BAN_THRESHOLD = 20

    # Ban duration
    BAN_DURATION = 86400  # 24 hours


class PeerReputation:
    """
    Track peer reputation and ban malicious peers
    """

    def __init__(self):
        self.reputation: Dict[str, int] = {}  # peer_url -> reputation score
        self.ban_list: Dict[str, float] = {}  # peer_url -> ban_expiry_time
        self.peer_ips: Dict[str, str] = {}  # peer_url -> IP address
        self.connections_per_ip: Dict[str, int] = defaultdict(int)  # IP -> count

    def get_reputation(self, peer_url: str) -> int:
        """Get peer reputation score"""
        return self.reputation.get(peer_url, P2PSecurityConfig.INITIAL_REPUTATION)

    def is_banned(self, peer_url: str) -> bool:
        """Check if peer is banned"""
        if peer_url not in self.ban_list:
            return False

        # Check if ban expired
        if time.time() > self.ban_list[peer_url]:
            del self.ban_list[peer_url]
            return False

        return True

    def ban_peer(self, peer_url: str, duration: int = P2PSecurityConfig.BAN_DURATION):
        """
        Ban a peer

        Args:
            peer_url: Peer URL
            duration: Ban duration in seconds
        """
        self.ban_list[peer_url] = time.time() + duration
        print(f"Peer banned: {peer_url} for {duration}s")

    def reward_good_behavior(self, peer_url: str, amount: int = 1):
        """Increase peer reputation for good behavior"""
        current = self.get_reputation(peer_url)
        new_reputation = min(current + amount, P2PSecurityConfig.MAX_REPUTATION)
        self.reputation[peer_url] = new_reputation

    def penalize_bad_behavior(self, peer_url: str, amount: int = 10):
        """
        Decrease peer reputation for bad behavior

        Args:
            peer_url: Peer URL
            amount: Penalty amount
        """
        current = self.get_reputation(peer_url)
        new_reputation = max(current - amount, P2PSecurityConfig.MIN_REPUTATION)
        self.reputation[peer_url] = new_reputation

        # Auto-ban if reputation too low
        if new_reputation <= P2PSecurityConfig.BAN_THRESHOLD:
            self.ban_peer(peer_url)

    def track_peer_ip(self, peer_url: str, ip_address: str):
        """Track peer IP address"""
        # Remove old IP tracking if peer changed IP
        if peer_url in self.peer_ips:
            old_ip = self.peer_ips[peer_url]
            self.connections_per_ip[old_ip] = max(0, self.connections_per_ip[old_ip] - 1)

        self.peer_ips[peer_url] = ip_address
        self.connections_per_ip[ip_address] += 1

        # Initialize peer reputation if not already tracked
        if peer_url not in self.reputation:
            self.reputation[peer_url] = P2PSecurityConfig.INITIAL_REPUTATION

    def can_accept_connection(self, peer_url: str, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if connection from peer can be accepted

        Args:
            peer_url: Peer URL
            ip_address: Peer IP

        Returns:
            (can_accept, error_message)
        """
        # Check if banned
        if self.is_banned(peer_url):
            return False, "Peer is banned"

        # Check connections per IP limit
        if self.connections_per_ip[ip_address] >= P2PSecurityConfig.MAX_CONNECTIONS_PER_IP:
            return False, f"Too many connections from IP {ip_address}"

        return True, None

    def get_peer_ip_prefix(self, ip_address: str) -> str:
        """Get IP /16 prefix for diversity check"""
        parts = ip_address.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return ip_address

    def check_peer_diversity(self, current_peers: Set[str]) -> int:
        """
        Check peer IP diversity

        Args:
            current_peers: Set of current peer URLs

        Returns:
            int: Number of unique IP prefixes
        """
        ip_prefixes = set()

        for peer_url in current_peers:
            if peer_url in self.peer_ips:
                ip = self.peer_ips[peer_url]
                prefix = self.get_peer_ip_prefix(ip)
                ip_prefixes.add(prefix)

        return len(ip_prefixes)


class MessageRateLimiter:
    """
    Rate limit messages per peer to prevent flooding
    """

    def __init__(self):
        self.message_log: Dict[str, list] = defaultdict(list)  # peer -> timestamps
        self.max_rate = P2PSecurityConfig.MAX_MESSAGES_PER_SECOND

    def check_rate_limit(self, peer_url: str) -> Tuple[bool, Optional[str]]:
        """
        Check if peer is within rate limits

        Args:
            peer_url: Peer URL

        Returns:
            (allowed, error_message)
        """
        current_time = time.time()

        # Clean old messages (older than 1 second)
        self.message_log[peer_url] = [
            ts for ts in self.message_log[peer_url] if current_time - ts < 1.0
        ]

        # Check rate
        if len(self.message_log[peer_url]) >= self.max_rate:
            return False, f"Rate limit exceeded: {len(self.message_log[peer_url])} msg/s"

        # Record this message
        self.message_log[peer_url].append(current_time)
        return True, None


class MessageValidator:
    """
    Validate P2P messages for size and content
    """

    @staticmethod
    def validate_message_size(message_data: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate message size

        Args:
            message_data: Message bytes

        Returns:
            (valid, error_message)
        """
        size = len(message_data)

        if size > P2PSecurityConfig.MAX_MESSAGE_SIZE:
            return (
                False,
                f"Message too large: {size} bytes (max {P2PSecurityConfig.MAX_MESSAGE_SIZE})",
            )

        return True, None

    @staticmethod
    def validate_message_type(message: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate message has required fields

        Args:
            message: Message dict

        Returns:
            (valid, error_message)
        """
        if "type" not in message:
            return False, "Message missing 'type' field"

        valid_types = ["block", "transaction", "peer_discovery", "sync_request", "ping"]
        if message["type"] not in valid_types:
            return False, f"Invalid message type: {message['type']}"

        return True, None


class P2PSecurityManager:
    """
    Unified P2P security management
    """

    def __init__(self):
        self.peer_reputation = PeerReputation()
        self.rate_limiter = MessageRateLimiter()
        self.message_validator = MessageValidator()

    def can_accept_peer(self, peer_url: str, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if peer connection can be accepted

        Args:
            peer_url: Peer URL
            ip_address: Peer IP

        Returns:
            (can_accept, error_message)
        """
        return self.peer_reputation.can_accept_connection(peer_url, ip_address)

    def track_peer_connection(self, peer_url: str, ip_address: str):
        """Track new peer connection"""
        self.peer_reputation.track_peer_ip(peer_url, ip_address)

    def validate_message(
        self, peer_url: str, message_data: bytes, message: dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate incoming message from peer

        Args:
            peer_url: Peer URL
            message_data: Raw message bytes
            message: Parsed message dict

        Returns:
            (valid, error_message)
        """
        # Check if peer is banned
        if self.peer_reputation.is_banned(peer_url):
            return False, "Peer is banned"

        # Rate limiting
        valid, error = self.rate_limiter.check_rate_limit(peer_url)
        if not valid:
            self.peer_reputation.penalize_bad_behavior(peer_url, 5)
            return False, error

        # Size validation
        valid, error = self.message_validator.validate_message_size(message_data)
        if not valid:
            self.peer_reputation.penalize_bad_behavior(peer_url, 10)
            return False, error

        # Type validation
        valid, error = self.message_validator.validate_message_type(message)
        if not valid:
            self.peer_reputation.penalize_bad_behavior(peer_url, 5)
            return False, error

        return True, None

    def report_good_behavior(self, peer_url: str):
        """Report peer sent valid data"""
        self.peer_reputation.reward_good_behavior(peer_url, 1)

    def report_bad_behavior(self, peer_url: str, severity: str = "minor"):
        """
        Report peer misbehavior

        Args:
            peer_url: Peer URL
            severity: "minor", "major", or "critical"
        """
        penalties = {"minor": 5, "major": 20, "critical": 100}

        penalty = penalties.get(severity, 10)
        self.peer_reputation.penalize_bad_behavior(peer_url, penalty)

    def ban_peer(self, peer_url: str, duration: int = P2PSecurityConfig.BAN_DURATION):
        """Ban a peer"""
        self.peer_reputation.ban_peer(peer_url, duration)

    def check_peer_diversity(self, current_peers: Set[str]) -> bool:
        """
        Check if peer diversity meets minimum

        Args:
            current_peers: Set of current peers

        Returns:
            bool: Diversity is sufficient
        """
        diversity = self.peer_reputation.check_peer_diversity(current_peers)
        return diversity >= P2PSecurityConfig.MIN_PEER_DIVERSITY

    def get_peer_stats(self) -> dict:
        """Get P2P security statistics"""
        return {
            "total_peers_tracked": len(self.peer_reputation.reputation),
            "banned_peers": len(self.peer_reputation.ban_list),
            "connections_per_ip": dict(self.peer_reputation.connections_per_ip),
            "average_reputation": (
                sum(self.peer_reputation.reputation.values()) / len(self.peer_reputation.reputation)
                if self.peer_reputation.reputation
                else 0
            ),
        }
