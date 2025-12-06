"""
P2P message signing, verification, and security controls.

Implements:
- Header-based message signing/verification
- Peer reputation and admission controls
- Rate limiting and bandwidth limiting
- Message validation (size/type)
- Unified security manager used by connection manager and tests
"""

from __future__ import annotations

import hashlib
import time
from typing import Dict, Tuple, Deque, Any, Set
from collections import deque
from threading import RLock

from xai.core.crypto_utils import sign_message_hex, verify_signature_hex


HEADER_VERSION = "X-Node-Version"
HEADER_PUBKEY = "X-Node-Pub"
HEADER_SIG = "X-Node-Signature"
HEADER_TS = "X-Node-Timestamp"
HEADER_NONCE = "X-Node-Nonce"
HEADER_FEATURES = "X-Node-Features"
HEADER_CLIENT_VERSION = "X-Node-Client"


class P2PSecurityConfig:
    """Centralized P2P security configuration constants."""

    MAX_PEERS_TOTAL = 50
    MAX_CONNECTIONS_PER_IP = 3
    MIN_PEER_DIVERSITY = 3  # distinct /16 prefixes

    MAX_MESSAGE_SIZE = 2 * 1024 * 1024  # 2MB
    MAX_MESSAGES_PER_SECOND = 100

    INITIAL_REPUTATION = 100.0
    MIN_REPUTATION = 0.0
    MAX_REPUTATION = 200.0
    BAN_THRESHOLD = 10.0
    BAN_DURATION = 86400  # 24h

    REWARD_GOOD = 5.0
    PENALTY_MINOR = 5.0
    PENALTY_MAJOR = 15.0
    PENALTY_CRITICAL = 30.0
    PROTOCOL_VERSION = "1"
    SUPPORTED_VERSIONS = {"1"}
    SUPPORTED_FEATURES = {"quic", "ws"}


def _digest(body_bytes: bytes, ts: str, nonce: str) -> bytes:
    h = hashlib.sha256(body_bytes).hexdigest()
    msg = f"{h}|{ts}|{nonce}".encode("utf-8")
    return hashlib.sha256(msg).digest()


def sign_headers(
    private_hex: str,
    public_hex: str,
    body_bytes: bytes,
    *,
    timestamp: int | None = None,
    nonce: str | None = None,
    version: str | None = None,
    features: Set[str] | None = None,
) -> Dict[str, str]:
    ts = str(int(timestamp if timestamp is not None else time.time()))
    nn = nonce if nonce is not None else hashlib.sha256(f"{time.time()}".encode()).hexdigest()[:32]
    digest = _digest(body_bytes, ts, nn)
    sig = sign_message_hex(private_hex, digest)
    ver = version or P2PSecurityConfig.PROTOCOL_VERSION
    feat = ",".join(sorted((features or P2PSecurityConfig.SUPPORTED_FEATURES) & P2PSecurityConfig.SUPPORTED_FEATURES))
    return {
        HEADER_VERSION: ver,
        HEADER_PUBKEY: public_hex,
        HEADER_TS: ts,
        HEADER_NONCE: nn,
        HEADER_SIG: sig,
        HEADER_FEATURES: feat,
    }


def verify_headers(headers: Dict[str, str], body_bytes: bytes, *, max_skew_seconds: int = 300) -> Tuple[bool, str]:
    version = headers.get(HEADER_VERSION, "")
    if version and version not in P2PSecurityConfig.SUPPORTED_VERSIONS:
        return False, "unsupported_protocol_version"
    if not version:
        return False, "missing_protocol_version"
    features = set(filter(None, headers.get(HEADER_FEATURES, "").split(",")))
    if features and not features.issubset(P2PSecurityConfig.SUPPORTED_FEATURES):
        return False, "unsupported_feature"
    pub = headers.get(HEADER_PUBKEY, "")
    sig = headers.get(HEADER_SIG, "")
    ts = headers.get(HEADER_TS, "")
    nn = headers.get(HEADER_NONCE, "")
    if not pub or not sig or not ts or not nn:
        return False, "missing_signature_headers"

    # Timestamp skew check
    try:
        ts_int = int(ts)
    except ValueError:
        return False, "invalid_timestamp"

    now = int(time.time())
    if abs(now - ts_int) > max_skew_seconds:
        return False, "timestamp_out_of_window"

    digest = _digest(body_bytes, ts, nn)
    if not verify_signature_hex(pub, digest, sig):
        return False, "invalid_signature"

    return True, "ok"


class PeerReputation:
    """Track and manage peer reputation and bans."""

    def __init__(self) -> None:
        self.reputation: Dict[str, float] = {}
        self.ban_list: Dict[str, float] = {}  # peer_url -> ban_expiry
        self.peer_ips: Dict[str, str] = {}
        self.connections_per_ip: Dict[str, int] = {}
        self.lock = RLock()

    def _normalize(self, peer_url: str) -> str:
        return peer_url.lower()

    def get_reputation(self, peer_url: str) -> float:
        peer = self._normalize(peer_url)
        with self.lock:
            return self.reputation.get(peer, P2PSecurityConfig.INITIAL_REPUTATION)

    def _set_reputation(self, peer_url: str, value: float) -> float:
        peer = self._normalize(peer_url)
        bounded = max(P2PSecurityConfig.MIN_REPUTATION, min(P2PSecurityConfig.MAX_REPUTATION, value))
        self.reputation[peer] = bounded
        return bounded

    def is_banned(self, peer_url: str) -> bool:
        peer = self._normalize(peer_url)
        with self.lock:
            expiry = self.ban_list.get(peer)
            if not expiry:
                return False
            if expiry < time.time():
                del self.ban_list[peer]
                return False
            return True

    def ban_peer(self, peer_url: str, duration: int | None = None) -> None:
        peer = self._normalize(peer_url)
        dur = duration if duration is not None else P2PSecurityConfig.BAN_DURATION
        with self.lock:
            self.ban_list[peer] = time.time() + dur

    def reward_good_behavior(self, peer_url: str, amount: float | None = None) -> float:
        delta = amount if amount is not None else P2PSecurityConfig.REWARD_GOOD
        with self.lock:
            new_score = self._set_reputation(peer_url, self.get_reputation(peer_url) + delta)
        return new_score

    def penalize_bad_behavior(self, peer_url: str, amount: float | None = None) -> float:
        delta = amount if amount is not None else P2PSecurityConfig.PENALTY_MINOR
        with self.lock:
            new_score = self._set_reputation(peer_url, self.get_reputation(peer_url) - delta)
            if new_score <= P2PSecurityConfig.BAN_THRESHOLD:
                self.ban_peer(peer_url)
        return new_score

    def track_peer_ip(self, peer_url: str, ip_address: str) -> None:
        peer = self._normalize(peer_url)
        ip = ip_address.lower() if ip_address else "unknown"
        with self.lock:
            # Decrement previous IP count if changed
            if peer in self.peer_ips:
                old_ip = self.peer_ips[peer]
                if old_ip != ip:
                    self.connections_per_ip[old_ip] = max(0, self.connections_per_ip.get(old_ip, 1) - 1)
            self.peer_ips[peer] = ip
            self.connections_per_ip[ip] = self.connections_per_ip.get(ip, 0) + 1

    def can_accept_connection(self, peer_url: str, ip_address: str) -> Tuple[bool, str | None]:
        peer = self._normalize(peer_url)
        ip = ip_address.lower() if ip_address else "unknown"

        if self.is_banned(peer):
            return False, "peer_banned"

        if self.connections_per_ip.get(ip, 0) >= P2PSecurityConfig.MAX_CONNECTIONS_PER_IP:
            return False, "too_many_connections_from_ip"

        return True, None

    def get_peer_ip_prefix(self, ip_address: str) -> str:
        parts = ip_address.split(".")
        return ".".join(parts[:2]) if len(parts) >= 2 else ip_address

    def check_peer_diversity(self, peers: Set[str]) -> int:
        prefixes = set()
        with self.lock:
            for peer in peers:
                ip = self.peer_ips.get(self._normalize(peer))
                if ip:
                    prefixes.add(self.get_peer_ip_prefix(ip))
        return len(prefixes)


class MessageRateLimiter:
    """Limits messages per peer per second."""

    def __init__(self, max_rate: int | None = None) -> None:
        self.max_rate = max_rate if max_rate is not None else P2PSecurityConfig.MAX_MESSAGES_PER_SECOND
        self.message_log: Dict[str, Deque[float]] = {}
        self.lock = RLock()

    def check_rate_limit(self, peer_url: str) -> Tuple[bool, str | None]:
        peer = peer_url.lower()
        now = time.time()
        with self.lock:
            log = self.message_log.setdefault(peer, deque())
            while log and log[0] < now - 1:
                log.popleft()
            if len(log) >= self.max_rate:
                return False, "rate limit exceeded"
            log.append(now)
            return True, None

    # Backward compatibility for existing usage
    def is_rate_limited(self, peer_id: str) -> bool:
        allowed, _ = self.check_rate_limit(peer_id)
        return not allowed


class MessageValidator:
    """Validates message size and type."""

    VALID_TYPES = {"block", "transaction", "peer_discovery", "sync_request", "ping"}

    @staticmethod
    def validate_message_size(message_data: bytes) -> Tuple[bool, str | None]:
        if len(message_data) > P2PSecurityConfig.MAX_MESSAGE_SIZE:
            return False, "message too large"
        return True, None

    @staticmethod
    def validate_message_type(message: Dict[str, Any]) -> Tuple[bool, str | None]:
        msg_type = message.get("type")
        if not msg_type:
            return False, "missing type"
        if msg_type not in MessageValidator.VALID_TYPES:
            return False, "invalid type"
        return True, None


class P2PSecurityManager:
    """Unified P2P security manager composing reputation, rate limits, and validation."""

    def __init__(self) -> None:
        self.peer_reputation = PeerReputation()
        self.rate_limiter = MessageRateLimiter()
        self.message_validator = MessageValidator()

    def can_accept_peer(self, peer_url: str, ip_address: str) -> Tuple[bool, str | None]:
        return self.peer_reputation.can_accept_connection(peer_url, ip_address)

    def track_peer_connection(self, peer_url: str, ip_address: str) -> None:
        self.peer_reputation.track_peer_ip(peer_url, ip_address)

    def validate_message(self, peer_url: str, message_data: bytes, message: Dict[str, Any]) -> Tuple[bool, str | None]:
        peer = peer_url.lower()

        if self.peer_reputation.is_banned(peer):
            return False, "peer_banned"

        allowed, error = self.rate_limiter.check_rate_limit(peer)
        if not allowed:
            self.report_bad_behavior(peer, severity="minor")
            return False, error

        ok, error = self.message_validator.validate_message_size(message_data)
        if not ok:
            self.report_bad_behavior(peer, severity="minor")
            return False, error

        ok, error = self.message_validator.validate_message_type(message)
        if not ok:
            self.report_bad_behavior(peer, severity="minor")
            return False, error

        return True, None

    def report_good_behavior(self, peer_url: str) -> float:
        return self.peer_reputation.reward_good_behavior(peer_url)

    def report_bad_behavior(self, peer_url: str, severity: str = "minor") -> float:
        severity = severity.lower()
        if severity == "critical":
            return self.peer_reputation.penalize_bad_behavior(peer_url, P2PSecurityConfig.PENALTY_CRITICAL)
        if severity == "major":
            return self.peer_reputation.penalize_bad_behavior(peer_url, P2PSecurityConfig.PENALTY_MAJOR)
        # default/minor
        return self.peer_reputation.penalize_bad_behavior(peer_url, P2PSecurityConfig.PENALTY_MINOR)

    def ban_peer(self, peer_url: str, duration: int | None = None) -> None:
        self.peer_reputation.ban_peer(peer_url, duration=duration)

    def check_peer_diversity(self, peers: Set[str]) -> bool:
        diversity = self.peer_reputation.check_peer_diversity(peers)
        return diversity >= P2PSecurityConfig.MIN_PEER_DIVERSITY

    def get_peer_stats(self) -> Dict[str, Any]:
        with self.peer_reputation.lock:
            total = len(self.peer_reputation.reputation)
            banned = len(self.peer_reputation.ban_list)
            avg_rep = 0
            if total:
                avg_rep = sum(self.peer_reputation.reputation.values()) / total
            return {
                "total_peers_tracked": total,
                "banned_peers": banned,
                "connections_per_ip": dict(self.peer_reputation.connections_per_ip),
                "average_reputation": avg_rep,
            }


class BandwidthLimiter:
    """
    Limits the bandwidth usage of each peer using a token bucket algorithm.
    """

    def __init__(self, capacity: int, fill_rate: int) -> None:
        """
        Args:
            capacity: Maximum burst size in bytes.
            fill_rate: Tokens added per second (bytes/second).
        """
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.peers: Dict[str, Dict[str, Any]] = {}  # {peer_id: {'tokens': float, 'last_fill': float}}
        self._lock = RLock()

    def _get_bucket(self, peer_id: str) -> Dict[str, float]:
        with self._lock:
            if peer_id not in self.peers:
                self.peers[peer_id] = {'tokens': float(self.capacity), 'last_fill': time.time()}
            return self.peers[peer_id]

    def _fill_bucket(self, peer_id: str) -> None:
        bucket = self._get_bucket(peer_id)
        now = time.time()
        time_passed = now - bucket['last_fill']
        tokens_to_add = time_passed * self.fill_rate
        bucket['tokens'] = min(bucket['tokens'] + tokens_to_add, float(self.capacity))
        bucket['last_fill'] = now

    def consume(self, peer_id: str, amount: int) -> bool:
        """
        Consumes tokens from the peer's bucket.

        Args:
            peer_id: The ID of the peer.
            amount: The amount of bytes to consume.

        Returns:
            True if tokens were consumed (within limit), False otherwise.
        """
        with self._lock:
            self._fill_bucket(peer_id)
            bucket = self._get_bucket(peer_id)

            if bucket['tokens'] >= amount:
                bucket['tokens'] -= amount
                return True
            return False
