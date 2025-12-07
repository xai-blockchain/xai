"""
Comprehensive P2P Security Tests

Tests for 100% coverage of p2p_security.py module.
Tests all P2P network security features including peer reputation,
message rate limiting, connection management, and attack prevention.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from xai.core.p2p_security import (
    P2PSecurityConfig,
    PeerReputation,
    MessageRateLimiter,
    MessageValidator,
    P2PSecurityManager,
)


class TestP2PSecurityConfig:
    """Test P2P security configuration constants"""

    def test_config_constants_defined(self):
        """Test that all P2P security config constants are defined"""
        assert P2PSecurityConfig.MAX_PEERS_TOTAL > 0
        assert P2PSecurityConfig.MAX_CONNECTIONS_PER_IP > 0
        assert P2PSecurityConfig.MIN_PEER_DIVERSITY > 0
        assert P2PSecurityConfig.MAX_MESSAGE_SIZE > 0
        assert P2PSecurityConfig.MAX_MESSAGES_PER_SECOND > 0
        assert P2PSecurityConfig.INITIAL_REPUTATION >= 0
        assert P2PSecurityConfig.MIN_REPUTATION >= 0
        assert P2PSecurityConfig.MAX_REPUTATION > 0
        assert P2PSecurityConfig.BAN_THRESHOLD >= 0
        assert P2PSecurityConfig.BAN_DURATION > 0

    def test_config_values_reasonable(self):
        """Test that config values are reasonable"""
        assert P2PSecurityConfig.MAX_PEERS_TOTAL == 50
        assert P2PSecurityConfig.MAX_CONNECTIONS_PER_IP == 3
        assert P2PSecurityConfig.BAN_DURATION == 86400


class TestPeerReputation:
    """Test peer reputation tracking and management"""

    def test_init(self):
        """Test peer reputation initialization"""
        reputation = PeerReputation()

        assert isinstance(reputation.reputation, dict)
        assert isinstance(reputation.ban_list, dict)
        assert isinstance(reputation.peer_ips, dict)
        assert isinstance(reputation.connections_per_ip, dict)

    def test_get_reputation_default(self):
        """Test getting default reputation for new peer"""
        reputation = PeerReputation()

        score = reputation.get_reputation("http://peer1.com:5000")

        assert score == P2PSecurityConfig.INITIAL_REPUTATION

    def test_get_reputation_existing_peer(self):
        """Test getting reputation for existing peer"""
        reputation = PeerReputation()

        reputation.reputation["http://peer1.com:5000"] = 150

        score = reputation.get_reputation("http://peer1.com:5000")

        assert score == 150

    def test_is_banned_false_for_new_peer(self):
        """Test that new peer is not banned"""
        reputation = PeerReputation()

        is_banned = reputation.is_banned("http://peer1.com:5000")

        assert is_banned is False

    def test_is_banned_true_for_banned_peer(self):
        """Test that banned peer is detected"""
        reputation = PeerReputation()

        # Ban peer
        reputation.ban_peer("http://peer1.com:5000", duration=3600)

        is_banned = reputation.is_banned("http://peer1.com:5000")

        assert is_banned is True

    def test_ban_expires(self):
        """Test that ban expires after duration"""
        reputation = PeerReputation()

        # Ban peer for 1 second
        reputation.ban_peer("http://peer1.com:5000", duration=1)

        assert reputation.is_banned("http://peer1.com:5000") is True

        # Wait for ban to expire
        time.sleep(1.1)

        assert reputation.is_banned("http://peer1.com:5000") is False

    def test_ban_peer_with_default_duration(self):
        """Test banning peer with default duration"""
        reputation = PeerReputation()

        reputation.ban_peer("http://peer1.com:5000")

        assert reputation.is_banned("http://peer1.com:5000") is True
        assert "http://peer1.com:5000" in reputation.ban_list

    def test_ban_peer_with_custom_duration(self):
        """Test banning peer with custom duration"""
        reputation = PeerReputation()

        reputation.ban_peer("http://peer1.com:5000", duration=7200)

        assert reputation.is_banned("http://peer1.com:5000") is True

    def test_reward_good_behavior(self):
        """Test rewarding good peer behavior"""
        reputation = PeerReputation()

        initial = reputation.get_reputation("http://peer1.com:5000")

        reputation.reward_good_behavior("http://peer1.com:5000", amount=10)

        new_score = reputation.get_reputation("http://peer1.com:5000")

        assert new_score == initial + 10

    def test_reward_good_behavior_capped_at_max(self):
        """Test that reputation cannot exceed maximum"""
        reputation = PeerReputation()

        reputation.reputation["http://peer1.com:5000"] = P2PSecurityConfig.MAX_REPUTATION

        reputation.reward_good_behavior("http://peer1.com:5000", amount=50)

        score = reputation.get_reputation("http://peer1.com:5000")

        assert score == P2PSecurityConfig.MAX_REPUTATION

    def test_penalize_bad_behavior(self):
        """Test penalizing bad peer behavior"""
        reputation = PeerReputation()

        initial = reputation.get_reputation("http://peer1.com:5000")

        reputation.penalize_bad_behavior("http://peer1.com:5000", amount=20)

        new_score = reputation.get_reputation("http://peer1.com:5000")

        assert new_score == initial - 20

    def test_penalize_bad_behavior_capped_at_min(self):
        """Test that reputation cannot go below minimum"""
        reputation = PeerReputation()

        reputation.reputation["http://peer1.com:5000"] = P2PSecurityConfig.MIN_REPUTATION

        reputation.penalize_bad_behavior("http://peer1.com:5000", amount=50)

        score = reputation.get_reputation("http://peer1.com:5000")

        assert score == P2PSecurityConfig.MIN_REPUTATION

    def test_penalize_triggers_auto_ban(self):
        """Test that low reputation triggers automatic ban"""
        reputation = PeerReputation()

        # Set reputation just above ban threshold
        reputation.reputation["http://peer1.com:5000"] = P2PSecurityConfig.BAN_THRESHOLD + 5

        # Penalize enough to drop below threshold
        reputation.penalize_bad_behavior("http://peer1.com:5000", amount=10)

        # Should be auto-banned
        assert reputation.is_banned("http://peer1.com:5000") is True

    def test_track_peer_ip(self):
        """Test tracking peer IP address"""
        reputation = PeerReputation()

        reputation.track_peer_ip("http://peer1.com:5000", "192.168.1.1")

        assert reputation.peer_ips["http://peer1.com:5000"] == "192.168.1.1"
        assert reputation.connections_per_ip["192.168.1.1"] == 1

    def test_track_peer_ip_update(self):
        """Test updating peer IP address"""
        reputation = PeerReputation()

        # Track initial IP
        reputation.track_peer_ip("http://peer1.com:5000", "192.168.1.1")

        # Change IP
        reputation.track_peer_ip("http://peer1.com:5000", "192.168.1.2")

        assert reputation.peer_ips["http://peer1.com:5000"] == "192.168.1.2"
        assert reputation.connections_per_ip["192.168.1.1"] == 0
        assert reputation.connections_per_ip["192.168.1.2"] == 1

    def test_can_accept_connection_new_peer(self):
        """Test accepting connection from new peer"""
        reputation = PeerReputation()

        can_accept, error = reputation.can_accept_connection(
            "http://peer1.com:5000",
            "192.168.1.1"
        )

        assert can_accept is True
        assert error is None

    def test_cannot_accept_connection_from_banned_peer(self):
        """Test rejecting connection from banned peer"""
        reputation = PeerReputation()

        reputation.ban_peer("http://peer1.com:5000")

        can_accept, error = reputation.can_accept_connection(
            "http://peer1.com:5000",
            "192.168.1.1"
        )

        assert can_accept is False
        assert "banned" in error.lower()

    def test_cannot_accept_connection_exceeding_ip_limit(self):
        """Test rejecting connection when IP limit reached"""
        reputation = PeerReputation()

        # Max out connections from IP
        for i in range(P2PSecurityConfig.MAX_CONNECTIONS_PER_IP):
            reputation.track_peer_ip(f"http://peer{i}.com:5000", "192.168.1.1")

        can_accept, error = reputation.can_accept_connection(
            "http://newpeer.com:5000",
            "192.168.1.1"
        )

        assert can_accept is False
        assert "too_many" in error.lower()

    def test_get_peer_ip_prefix(self):
        """Test extracting IP /16 prefix"""
        reputation = PeerReputation()

        prefix = reputation.get_peer_ip_prefix("192.168.1.1")

        assert prefix == "192.168"

    def test_get_peer_ip_prefix_short_ip(self):
        """Test IP prefix extraction with short IP"""
        reputation = PeerReputation()

        prefix = reputation.get_peer_ip_prefix("192")

        assert prefix == "192"

    def test_check_peer_diversity(self):
        """Test checking peer diversity"""
        reputation = PeerReputation()

        # Track peers from different IP ranges
        reputation.track_peer_ip("http://peer1.com:5000", "192.168.1.1")
        reputation.track_peer_ip("http://peer2.com:5000", "10.0.1.1")
        reputation.track_peer_ip("http://peer3.com:5000", "172.16.1.1")

        peers = {"http://peer1.com:5000", "http://peer2.com:5000", "http://peer3.com:5000"}

        diversity = reputation.check_peer_diversity(peers)

        assert diversity == 3  # Three different /16 prefixes

    def test_check_peer_diversity_same_subnet(self):
        """Test peer diversity with peers in same subnet"""
        reputation = PeerReputation()

        # Track peers from same IP range
        reputation.track_peer_ip("http://peer1.com:5000", "192.168.1.1")
        reputation.track_peer_ip("http://peer2.com:5000", "192.168.2.1")
        reputation.track_peer_ip("http://peer3.com:5000", "192.168.3.1")

        peers = {"http://peer1.com:5000", "http://peer2.com:5000", "http://peer3.com:5000"}

        diversity = reputation.check_peer_diversity(peers)

        assert diversity == 1  # Same /16 prefix


class TestMessageRateLimiter:
    """Test message rate limiting"""

    def test_init(self):
        """Test rate limiter initialization"""
        limiter = MessageRateLimiter()

        assert isinstance(limiter.message_log, dict)
        assert limiter.max_rate == P2PSecurityConfig.MAX_MESSAGES_PER_SECOND

    def test_check_rate_limit_first_message(self):
        """Test rate limit check for first message"""
        limiter = MessageRateLimiter()

        allowed, error = limiter.check_rate_limit("http://peer1.com:5000")

        assert allowed is True
        assert error is None

    def test_check_rate_limit_within_limit(self):
        """Test rate limit check within limit"""
        limiter = MessageRateLimiter()

        # Send messages within limit
        for _ in range(P2PSecurityConfig.MAX_MESSAGES_PER_SECOND // 2):
            allowed, error = limiter.check_rate_limit("http://peer1.com:5000")
            assert allowed is True

    def test_check_rate_limit_exceeding_limit(self):
        """Test rate limit check when limit exceeded"""
        limiter = MessageRateLimiter()

        # Send messages up to limit
        for _ in range(P2PSecurityConfig.MAX_MESSAGES_PER_SECOND):
            limiter.check_rate_limit("http://peer1.com:5000")

        # Next message should be rate limited
        allowed, error = limiter.check_rate_limit("http://peer1.com:5000")

        assert allowed is False
        assert "rate limit" in error.lower()

    def test_rate_limit_resets_after_time(self):
        """Test that rate limit resets after 1 second"""
        limiter = MessageRateLimiter()

        # Max out rate limit
        for _ in range(P2PSecurityConfig.MAX_MESSAGES_PER_SECOND):
            limiter.check_rate_limit("http://peer1.com:5000")

        # Should be rate limited
        allowed, _ = limiter.check_rate_limit("http://peer1.com:5000")
        assert allowed is False

        # Wait for reset
        time.sleep(1.1)

        # Should be allowed again
        allowed, error = limiter.check_rate_limit("http://peer1.com:5000")
        assert allowed is True

    def test_rate_limit_per_peer(self):
        """Test that rate limit is enforced per peer"""
        limiter = MessageRateLimiter()

        # Max out rate for peer1
        for _ in range(P2PSecurityConfig.MAX_MESSAGES_PER_SECOND):
            limiter.check_rate_limit("http://peer1.com:5000")

        # Peer1 should be limited
        allowed, _ = limiter.check_rate_limit("http://peer1.com:5000")
        assert allowed is False

        # Peer2 should still be allowed
        allowed, _ = limiter.check_rate_limit("http://peer2.com:5000")
        assert allowed is True


class TestMessageValidator:
    """Test message validation"""

    def test_validate_message_size_valid(self):
        """Test validation of valid message size"""
        message_data = b"test message"

        is_valid, error = MessageValidator.validate_message_size(message_data)

        assert is_valid is True
        assert error is None

    def test_reject_oversized_message(self):
        """Test rejection of oversized message"""
        # Create message exceeding max size
        large_message = b"x" * (P2PSecurityConfig.MAX_MESSAGE_SIZE + 1)

        is_valid, error = MessageValidator.validate_message_size(large_message)

        assert is_valid is False
        assert "too large" in error.lower()

    def test_validate_message_type_valid(self):
        """Test validation of valid message types"""
        valid_types = ["block", "transaction", "peer_discovery", "sync_request", "ping"]

        for msg_type in valid_types:
            message = {"type": msg_type}

            is_valid, error = MessageValidator.validate_message_type(message)

            assert is_valid is True
            assert error is None

    def test_reject_message_missing_type(self):
        """Test rejection of message missing type field"""
        message = {"data": "test"}

        is_valid, error = MessageValidator.validate_message_type(message)

        assert is_valid is False
        assert "missing" in error.lower()

    def test_reject_message_invalid_type(self):
        """Test rejection of message with invalid type"""
        message = {"type": "invalid_type"}

        is_valid, error = MessageValidator.validate_message_type(message)

        assert is_valid is False
        assert "invalid" in error.lower()


class TestP2PSecurityManager:
    """Test unified P2P security manager"""

    def test_init(self):
        """Test P2P security manager initialization"""
        manager = P2PSecurityManager()

        assert manager.peer_reputation is not None
        assert manager.rate_limiter is not None
        assert manager.message_validator is not None

    def test_can_accept_peer(self):
        """Test peer acceptance check"""
        manager = P2PSecurityManager()

        can_accept, error = manager.can_accept_peer(
            "http://peer1.com:5000",
            "192.168.1.1"
        )

        assert can_accept is True

    def test_cannot_accept_banned_peer(self):
        """Test rejection of banned peer"""
        manager = P2PSecurityManager()

        manager.peer_reputation.ban_peer("http://peer1.com:5000")

        can_accept, error = manager.can_accept_peer(
            "http://peer1.com:5000",
            "192.168.1.1"
        )

        assert can_accept is False

    def test_track_peer_connection(self):
        """Test tracking peer connection"""
        manager = P2PSecurityManager()

        manager.track_peer_connection("http://peer1.com:5000", "192.168.1.1")

        assert "http://peer1.com:5000" in manager.peer_reputation.peer_ips

    def test_validate_message_from_banned_peer(self):
        """Test rejection of message from banned peer"""
        manager = P2PSecurityManager()

        manager.peer_reputation.ban_peer("http://peer1.com:5000")

        message_data = b"test"
        message = {"type": "block"}

        is_valid, error = manager.validate_message(
            "http://peer1.com:5000",
            message_data,
            message
        )

        assert is_valid is False
        assert "banned" in error.lower()

    def test_validate_message_rate_limited(self):
        """Test rejection of rate-limited message"""
        manager = P2PSecurityManager()

        message_data = b"test"
        message = {"type": "block"}

        # Max out rate limit
        for _ in range(P2PSecurityConfig.MAX_MESSAGES_PER_SECOND):
            manager.validate_message("http://peer1.com:5000", message_data, message)

        # Next message should be rejected and peer penalized
        is_valid, error = manager.validate_message(
            "http://peer1.com:5000",
            message_data,
            message
        )

        assert is_valid is False
        # Reputation should have been penalized
        assert manager.peer_reputation.get_reputation("http://peer1.com:5000") < P2PSecurityConfig.INITIAL_REPUTATION

    def test_validate_message_oversized(self):
        """Test rejection of oversized message"""
        manager = P2PSecurityManager()

        large_message = b"x" * (P2PSecurityConfig.MAX_MESSAGE_SIZE + 1)
        message = {"type": "block"}

        is_valid, error = manager.validate_message(
            "http://peer1.com:5000",
            large_message,
            message
        )

        assert is_valid is False
        # Reputation should have been penalized
        assert manager.peer_reputation.get_reputation("http://peer1.com:5000") < P2PSecurityConfig.INITIAL_REPUTATION

    def test_validate_message_invalid_type(self):
        """Test rejection of message with invalid type"""
        manager = P2PSecurityManager()

        message_data = b"test"
        message = {"type": "invalid"}

        is_valid, error = manager.validate_message(
            "http://peer1.com:5000",
            message_data,
            message
        )

        assert is_valid is False
        # Reputation should have been penalized
        assert manager.peer_reputation.get_reputation("http://peer1.com:5000") < P2PSecurityConfig.INITIAL_REPUTATION

    def test_validate_message_valid(self):
        """Test validation of valid message"""
        manager = P2PSecurityManager()

        message_data = b"test"
        message = {"type": "block"}

        is_valid, error = manager.validate_message(
            "http://peer1.com:5000",
            message_data,
            message
        )

        assert is_valid is True
        assert error is None

    def test_report_good_behavior(self):
        """Test reporting good peer behavior"""
        manager = P2PSecurityManager()

        initial = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        manager.report_good_behavior("http://peer1.com:5000")

        new_score = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        assert new_score > initial

    def test_report_bad_behavior_minor(self):
        """Test reporting minor bad behavior"""
        manager = P2PSecurityManager()

        initial = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        manager.report_bad_behavior("http://peer1.com:5000", severity="minor")

        new_score = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        assert new_score < initial

    def test_report_bad_behavior_major(self):
        """Test reporting major bad behavior"""
        manager = P2PSecurityManager()

        initial = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        manager.report_bad_behavior("http://peer1.com:5000", severity="major")

        new_score = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        assert new_score < initial
        # Major should penalize more than minor
        assert (initial - new_score) > 5

    def test_report_bad_behavior_critical(self):
        """Test reporting critical bad behavior"""
        manager = P2PSecurityManager()

        initial = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        manager.report_bad_behavior("http://peer1.com:5000", severity="critical")

        new_score = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        # Critical should penalize heavily
        assert new_score < initial
        assert (initial - new_score) >= P2PSecurityConfig.PENALTY_CRITICAL

    def test_report_bad_behavior_unknown_severity(self):
        """Test reporting bad behavior with unknown severity"""
        manager = P2PSecurityManager()

        initial = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        manager.report_bad_behavior("http://peer1.com:5000", severity="unknown")

        new_score = manager.peer_reputation.get_reputation("http://peer1.com:5000")

        # Should still penalize with default amount
        assert new_score < initial

    def test_ban_peer(self):
        """Test banning peer"""
        manager = P2PSecurityManager()

        manager.ban_peer("http://peer1.com:5000")

        assert manager.peer_reputation.is_banned("http://peer1.com:5000")

    def test_ban_peer_custom_duration(self):
        """Test banning peer with custom duration"""
        manager = P2PSecurityManager()

        manager.ban_peer("http://peer1.com:5000", duration=7200)

        assert manager.peer_reputation.is_banned("http://peer1.com:5000")

    def test_check_peer_diversity_sufficient(self):
        """Test peer diversity check when sufficient"""
        manager = P2PSecurityManager()

        # Track peers from different subnets
        for i in range(P2PSecurityConfig.MIN_PEER_DIVERSITY):
            manager.track_peer_connection(f"http://peer{i}.com:5000", f"{i}.0.0.1")

        peers = {f"http://peer{i}.com:5000" for i in range(P2PSecurityConfig.MIN_PEER_DIVERSITY)}

        is_sufficient = manager.check_peer_diversity(peers)

        assert is_sufficient is True

    def test_check_peer_diversity_insufficient(self):
        """Test peer diversity check when insufficient"""
        manager = P2PSecurityManager()

        # Track peers from same subnet
        for i in range(P2PSecurityConfig.MIN_PEER_DIVERSITY - 1):
            manager.track_peer_connection(f"http://peer{i}.com:5000", f"192.168.1.{i}")

        peers = {f"http://peer{i}.com:5000" for i in range(P2PSecurityConfig.MIN_PEER_DIVERSITY - 1)}

        is_sufficient = manager.check_peer_diversity(peers)

        assert is_sufficient is False

    def test_get_peer_stats(self):
        """Test getting peer statistics"""
        manager = P2PSecurityManager()

        # Add some peers and interact with them to populate reputation dict
        manager.track_peer_connection("http://peer1.com:5000", "192.168.1.1")
        manager.track_peer_connection("http://peer2.com:5000", "192.168.1.2")
        # Report behavior to populate the reputation dict (get_reputation doesn't add to dict)
        manager.report_good_behavior("http://peer1.com:5000")
        manager.report_good_behavior("http://peer2.com:5000")
        manager.ban_peer("http://peer3.com:5000")

        stats = manager.get_peer_stats()

        assert "total_peers_tracked" in stats
        assert "banned_peers" in stats
        assert "connections_per_ip" in stats
        assert "average_reputation" in stats

        assert stats["total_peers_tracked"] >= 2
        assert stats["banned_peers"] >= 1

    def test_get_peer_stats_empty(self):
        """Test getting peer statistics when empty"""
        manager = P2PSecurityManager()

        stats = manager.get_peer_stats()

        assert stats["total_peers_tracked"] == 0
        assert stats["banned_peers"] == 0
        assert stats["average_reputation"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
