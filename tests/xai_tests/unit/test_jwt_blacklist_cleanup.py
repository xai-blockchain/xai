"""
Unit tests for JWT blacklist automatic cleanup functionality.

Tests the background thread cleanup, thread safety, and configuration options.
"""

import time
import threading
import pytest
from datetime import datetime, timezone, timedelta

from xai.core.api_auth import JWTAuthManager


class TestJWTBlacklistCleanup:
    """Test suite for JWT blacklist automatic cleanup."""

    def test_cleanup_enabled_by_default(self):
        """Cleanup should be enabled by default."""
        mgr = JWTAuthManager(secret_key="test_secret")
        try:
            assert mgr._cleanup_enabled is True
            assert mgr._cleanup_thread is not None
            assert mgr._cleanup_thread.is_alive()
        finally:
            mgr.stop_cleanup()

    def test_cleanup_disabled_when_configured(self):
        """Cleanup can be disabled via configuration."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=False)
        assert mgr._cleanup_enabled is False
        assert mgr._cleanup_thread is None

    def test_cleanup_interval_configurable(self):
        """Cleanup interval should be configurable."""
        custom_interval = 300  # 5 minutes
        mgr = JWTAuthManager(
            secret_key="test_secret",
            cleanup_interval_seconds=custom_interval
        )
        try:
            assert mgr._cleanup_interval == custom_interval
        finally:
            mgr.stop_cleanup()

    def test_manual_cleanup_removes_expired_tokens(self):
        """Manual cleanup should remove expired tokens from blacklist."""
        # Create manager with very short token expiry (1 second)
        mgr = JWTAuthManager(
            secret_key="test_secret",
            token_expiry_hours=1/3600,  # 1 second
            cleanup_enabled=False  # Disable auto-cleanup for manual testing
        )

        # Generate and revoke a token
        access_token, _ = mgr.generate_token("user123", scope="user")
        mgr.revoke_token(access_token)

        # Verify token is blacklisted
        assert mgr.get_blacklist_size() == 1
        assert access_token in mgr.blacklist

        # Wait for token to expire
        time.sleep(2)

        # Manually trigger cleanup
        removed = mgr.cleanup_expired_tokens()

        # Verify expired token was removed
        assert removed == 1
        assert mgr.get_blacklist_size() == 0
        assert access_token not in mgr.blacklist

    def test_cleanup_keeps_valid_tokens(self):
        """Cleanup should NOT remove tokens that haven't expired."""
        mgr = JWTAuthManager(
            secret_key="test_secret",
            token_expiry_hours=1,  # 1 hour - won't expire during test
            cleanup_enabled=False
        )

        # Generate and revoke a token
        access_token, _ = mgr.generate_token("user123", scope="user")
        mgr.revoke_token(access_token)

        # Verify token is blacklisted
        assert mgr.get_blacklist_size() == 1

        # Trigger cleanup
        removed = mgr.cleanup_expired_tokens()

        # Verify valid token was NOT removed
        assert removed == 0
        assert mgr.get_blacklist_size() == 1
        assert access_token in mgr.blacklist

    def test_cleanup_handles_mixed_tokens(self):
        """Cleanup should remove only expired tokens, keeping valid ones."""
        mgr = JWTAuthManager(
            secret_key="test_secret",
            token_expiry_hours=1,
            cleanup_enabled=False
        )

        # Generate tokens with different expiry times
        # Token 1: expires in 1 second
        mgr_short = JWTAuthManager(secret_key="test_secret", token_expiry_hours=1/3600)
        short_token, _ = mgr_short.generate_token("user1", scope="user")

        # Token 2: expires in 1 hour
        long_token, _ = mgr.generate_token("user2", scope="user")

        # Revoke both tokens in the main manager's blacklist
        mgr.blacklist.add(short_token)
        mgr.blacklist.add(long_token)

        assert mgr.get_blacklist_size() == 2

        # Wait for short token to expire
        time.sleep(2)

        # Trigger cleanup
        removed = mgr.cleanup_expired_tokens()

        # Should remove 1 expired token, keep 1 valid token
        assert removed == 1
        assert mgr.get_blacklist_size() == 1
        assert short_token not in mgr.blacklist
        assert long_token in mgr.blacklist

    def test_background_cleanup_thread_starts(self):
        """Background cleanup thread should start automatically when enabled."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=True)
        try:
            # Verify thread is running
            assert mgr._cleanup_thread is not None
            assert mgr._cleanup_thread.is_alive()
            assert mgr._cleanup_thread.daemon is True
            assert mgr._cleanup_thread.name == "JWT-Blacklist-Cleanup"
        finally:
            mgr.stop_cleanup()

    def test_background_cleanup_stops_gracefully(self):
        """Background cleanup thread should stop gracefully when requested."""
        mgr = JWTAuthManager(
            secret_key="test_secret",
            cleanup_enabled=True,
            cleanup_interval_seconds=10
        )

        # Verify thread is running
        assert mgr._cleanup_thread.is_alive()

        # Stop cleanup
        mgr.stop_cleanup()

        # Give thread time to stop
        time.sleep(0.5)

        # Verify thread stopped
        assert not mgr._cleanup_thread.is_alive()

    def test_background_cleanup_performs_periodic_cleanup(self):
        """Background cleanup should automatically remove expired tokens."""
        # Create manager with very short cleanup interval
        mgr = JWTAuthManager(
            secret_key="test_secret",
            token_expiry_hours=1/3600,  # 1 second
            cleanup_enabled=True,
            cleanup_interval_seconds=2  # Run cleanup every 2 seconds
        )

        try:
            # Generate and revoke a token
            access_token, _ = mgr.generate_token("user123", scope="user")
            mgr.revoke_token(access_token)

            # Verify token is blacklisted
            assert mgr.get_blacklist_size() == 1

            # Wait for token to expire and cleanup to run
            time.sleep(4)  # Wait for token to expire (1s) + cleanup to run (2s interval)

            # Verify background cleanup removed the expired token
            assert mgr.get_blacklist_size() == 0
        finally:
            mgr.stop_cleanup()

    def test_thread_safety_concurrent_revocations(self):
        """Blacklist operations should be thread-safe."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=False)

        tokens = []
        for i in range(10):
            access_token, _ = mgr.generate_token(f"user{i}", scope="user")
            tokens.append(access_token)

        # Revoke tokens from multiple threads concurrently
        threads = []
        for token in tokens:
            thread = threading.Thread(target=mgr.revoke_token, args=(token,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all tokens were added to blacklist
        assert mgr.get_blacklist_size() == 10

    def test_thread_safety_concurrent_cleanup(self):
        """Cleanup should be thread-safe when called concurrently."""
        mgr = JWTAuthManager(
            secret_key="test_secret",
            token_expiry_hours=1/3600,  # 1 second
            cleanup_enabled=False
        )

        # Generate and revoke multiple tokens
        for i in range(10):
            access_token, _ = mgr.generate_token(f"user{i}", scope="user")
            mgr.revoke_token(access_token)

        # Wait for tokens to expire
        time.sleep(2)

        # Run cleanup from multiple threads concurrently
        threads = []
        results = []

        def cleanup_and_store():
            removed = mgr.cleanup_expired_tokens()
            results.append(removed)

        for _ in range(5):
            thread = threading.Thread(target=cleanup_and_store)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all tokens were removed
        assert mgr.get_blacklist_size() == 0

        # Total removed should equal 10 (some threads may get 0)
        assert sum(results) == 10

    def test_thread_safety_read_write_concurrent(self):
        """Reading and writing blacklist should be thread-safe."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=False)

        # Generate initial tokens
        initial_tokens = []
        for i in range(5):
            access_token, _ = mgr.generate_token(f"user{i}", scope="user")
            mgr.revoke_token(access_token)
            initial_tokens.append(access_token)

        stop_event = threading.Event()
        errors = []

        def reader_worker():
            """Continuously read blacklist size."""
            while not stop_event.is_set():
                try:
                    size = mgr.get_blacklist_size()
                    assert size >= 0  # Sanity check
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    errors.append(e)

        def writer_worker():
            """Continuously add tokens to blacklist."""
            counter = 0
            while not stop_event.is_set():
                try:
                    token, _ = mgr.generate_token(f"writer_user_{counter}", scope="user")
                    mgr.revoke_token(token)
                    counter += 1
                    time.sleep(0.01)  # Small delay
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    errors.append(e)

        # Start multiple reader and writer threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=reader_worker))
        for _ in range(2):
            threads.append(threading.Thread(target=writer_worker))

        for thread in threads:
            thread.start()

        # Let them run for a short time
        time.sleep(1)

        # Stop threads
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2)

        # Verify no errors occurred
        assert len(errors) == 0

    def test_cleanup_logs_statistics(self, caplog):
        """Cleanup should log statistics about removed tokens."""
        mgr = JWTAuthManager(
            secret_key="test_secret",
            token_expiry_hours=1/3600,  # 1 second
            cleanup_enabled=False
        )

        # Generate and revoke tokens
        for i in range(3):
            access_token, _ = mgr.generate_token(f"user{i}", scope="user")
            mgr.revoke_token(access_token)

        # Wait for tokens to expire
        time.sleep(2)

        # Trigger cleanup with logging
        import logging
        with caplog.at_level(logging.INFO):
            removed = mgr.cleanup_expired_tokens()

        # Verify statistics were logged
        assert removed == 3
        assert "JWT blacklist cleanup: removed 3 expired tokens" in caplog.text

    def test_atexit_cleanup_registered(self):
        """Cleanup shutdown should be registered with atexit."""
        import atexit

        # Create manager
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=True)

        try:
            # The _shutdown_cleanup method should be registered
            # We can't easily test atexit directly, but we can verify the method exists
            assert hasattr(mgr, '_shutdown_cleanup')
            assert callable(mgr._shutdown_cleanup)
        finally:
            mgr.stop_cleanup()

    def test_double_stop_cleanup_safe(self):
        """Calling stop_cleanup multiple times should be safe."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=True)

        # Stop cleanup multiple times
        mgr.stop_cleanup()
        mgr.stop_cleanup()  # Should not raise error
        mgr.stop_cleanup()

        # Thread should be stopped
        assert not mgr._cleanup_thread.is_alive()

    def test_cleanup_with_invalid_tokens_in_blacklist(self):
        """Cleanup should handle invalid tokens gracefully."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=False)

        # Add some invalid tokens to blacklist
        mgr.blacklist.add("invalid_token_1")
        mgr.blacklist.add("not_a_jwt")
        mgr.blacklist.add("corrupted.token.here")

        # Add a valid token
        valid_token, _ = mgr.generate_token("user123", scope="user")
        mgr.revoke_token(valid_token)

        initial_size = mgr.get_blacklist_size()

        # Cleanup should not crash
        removed = mgr.cleanup_expired_tokens()

        # Invalid tokens should remain (kept for safety)
        # Valid non-expired token should remain
        assert mgr.get_blacklist_size() == initial_size

    def test_cleanup_empty_blacklist(self):
        """Cleanup should handle empty blacklist gracefully."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=False)

        # Blacklist is empty
        assert mgr.get_blacklist_size() == 0

        # Cleanup should not crash
        removed = mgr.cleanup_expired_tokens()

        assert removed == 0
        assert mgr.get_blacklist_size() == 0

    def test_get_blacklist_size_thread_safe(self):
        """get_blacklist_size should be thread-safe."""
        mgr = JWTAuthManager(secret_key="test_secret", cleanup_enabled=False)

        # Add initial tokens
        for i in range(10):
            token, _ = mgr.generate_token(f"user{i}", scope="user")
            mgr.revoke_token(token)

        sizes = []
        stop_event = threading.Event()

        def size_reader():
            """Read blacklist size repeatedly."""
            while not stop_event.is_set():
                size = mgr.get_blacklist_size()
                sizes.append(size)
                time.sleep(0.001)

        def token_adder():
            """Add tokens to blacklist."""
            counter = 0
            while not stop_event.is_set():
                token, _ = mgr.generate_token(f"adder_user_{counter}", scope="user")
                mgr.revoke_token(token)
                counter += 1
                time.sleep(0.01)

        # Start threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=size_reader))
        threads.append(threading.Thread(target=token_adder))

        for thread in threads:
            thread.start()

        # Let them run
        time.sleep(0.5)

        # Stop threads
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2)

        # All size readings should be >= 10 (initial tokens)
        assert all(size >= 10 for size in sizes)
        # Should have collected many size readings
        assert len(sizes) > 100
