"""
Test suite for P2P connection pooling functionality.

Tests verify:
- Connection reuse across multiple requests
- Health checking for pooled connections
- Graceful handling of connection failures
- Pool metrics tracking
- Context manager usage
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

from xai.network.peer_manager import (
    PeerConnectionPool,
    PeerConnection,
    PeerDiscovery,
)


def create_healthy_mock_ws():
    """Create a mock WebSocket that passes health checks."""
    mock_ws = AsyncMock()
    mock_ws.closed = False
    mock_ws.close = AsyncMock()

    # Create a future for ping
    ping_future = asyncio.Future()
    ping_future.set_result(None)
    mock_ws.ping = AsyncMock(return_value=ping_future)

    return mock_ws


class TestPeerConnectionPool:
    """Test PeerConnectionPool class for WebSocket connection reuse."""

    @pytest.mark.asyncio
    async def test_connection_pool_creates_new_connection(self):
        """Test that pool creates new connection when pool is empty."""
        pool = PeerConnectionPool(max_connections_per_peer=3)
        peer_uri = "ws://test.peer:8333"

        async def mock_websockets_connect(*args, **kwargs):
            return create_healthy_mock_ws()

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            conn = await pool.get_connection(peer_uri)

            # Verify connection was created
            assert conn is not None
            assert pool._total_connections_created == 1
            assert pool._total_connections_reused == 0

        await pool.close_all()

    @pytest.mark.asyncio
    async def test_connection_pool_reuses_connection(self):
        """Test that pool reuses existing healthy connection."""
        pool = PeerConnectionPool(max_connections_per_peer=3)
        peer_uri = "ws://test.peer:8333"

        connection_count = 0

        async def mock_websockets_connect(*args, **kwargs):
            nonlocal connection_count
            connection_count += 1
            return create_healthy_mock_ws()

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # First request creates connection
            conn1 = await pool.get_connection(peer_uri)
            assert connection_count == 1
            assert pool._total_connections_created == 1

            # Return connection to pool
            await pool.return_connection(peer_uri, conn1)

            # Second request reuses connection
            conn2 = await pool.get_connection(peer_uri)

            # Should not create new connection
            assert connection_count == 1
            assert conn2 is not None
            assert pool._total_connections_created == 1
            assert pool._total_connections_reused == 1

        await pool.close_all()

    @pytest.mark.asyncio
    async def test_connection_pool_health_check_failure(self):
        """Test that unhealthy connections are not reused."""
        pool = PeerConnectionPool(max_connections_per_peer=3, ping_timeout=1.0)
        peer_uri = "ws://test.peer:8333"

        connection_count = 0

        async def mock_websockets_connect(*args, **kwargs):
            nonlocal connection_count
            connection_count += 1

            if connection_count == 1:
                # First connection becomes unhealthy
                mock_ws = AsyncMock()
                mock_ws.closed = False
                mock_ws.close = AsyncMock()
                # Make ping fail
                mock_ws.ping = AsyncMock(side_effect=ConnectionError("Connection lost"))
                return mock_ws
            else:
                # Second connection is healthy
                return create_healthy_mock_ws()

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Get first connection
            conn1 = await pool.get_connection(peer_uri)
            assert connection_count == 1

            # Return to pool
            await pool.return_connection(peer_uri, conn1)

            # Try to get connection again - should fail health check and create new
            conn2 = await pool.get_connection(peer_uri)

            # Should have created second connection due to health check failure
            assert connection_count == 2
            assert pool._total_health_check_failures >= 1

        await pool.close_all()

    @pytest.mark.asyncio
    async def test_connection_pool_max_connections_enforced(self):
        """Test that pool enforces max connections per peer."""
        pool = PeerConnectionPool(max_connections_per_peer=2, connection_timeout=0.5)
        peer_uri = "ws://test.peer:8333"

        async def mock_websockets_connect(*args, **kwargs):
            return create_healthy_mock_ws()

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Get two connections (fills pool)
            conn1 = await pool.get_connection(peer_uri)
            conn2 = await pool.get_connection(peer_uri)

            assert pool._active_connections[peer_uri] == 2

            # Try to get third connection - should timeout waiting
            with pytest.raises(asyncio.TimeoutError):
                await pool.get_connection(peer_uri)

        await pool.close_all()

    @pytest.mark.asyncio
    async def test_connection_pool_context_manager(self):
        """Test PeerConnection context manager."""
        pool = PeerConnectionPool(max_connections_per_peer=3)
        peer_uri = "ws://test.peer:8333"

        async def mock_websockets_connect(*args, **kwargs):
            mock_ws = create_healthy_mock_ws()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(return_value='{"type": "pong"}')
            return mock_ws

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Use context manager
            async with PeerConnection(pool, peer_uri) as ws:
                await ws.send(json.dumps({"type": "ping"}))
                response = await ws.recv()
                assert json.loads(response)["type"] == "pong"

            # Connection should be returned to pool
            assert pool.pools[peer_uri].qsize() == 1

            # Reuse connection via context manager
            async with PeerConnection(pool, peer_uri) as ws:
                await ws.send(json.dumps({"type": "ping"}))

            # Should have reused connection
            assert pool._total_connections_reused >= 1

        await pool.close_all()

    @pytest.mark.asyncio
    async def test_connection_pool_close_all(self):
        """Test that close_all properly cleans up all connections."""
        pool = PeerConnectionPool(max_connections_per_peer=3)
        peer_uri = "ws://test.peer:8333"

        async def mock_websockets_connect(*args, **kwargs):
            return create_healthy_mock_ws()

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Create and return connection to pool
            conn = await pool.get_connection(peer_uri)
            await pool.return_connection(peer_uri, conn)

            # Close all connections
            await pool.close_all()

            # Verify connection was closed
            conn.close.assert_called()

            # Verify pool is marked as closed
            assert pool._closed is True

            # Subsequent get_connection should fail
            with pytest.raises(RuntimeError, match="Connection pool is closed"):
                await pool.get_connection(peer_uri)

    @pytest.mark.asyncio
    async def test_connection_pool_metrics(self):
        """Test that pool tracks metrics correctly."""
        pool = PeerConnectionPool(max_connections_per_peer=3)
        peer_uri = "ws://test.peer:8333"

        async def mock_websockets_connect(*args, **kwargs):
            return create_healthy_mock_ws()

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Create connection
            conn1 = await pool.get_connection(peer_uri)
            await pool.return_connection(peer_uri, conn1)

            # Reuse connection
            conn2 = await pool.get_connection(peer_uri)
            await pool.return_connection(peer_uri, conn2)

            # Get metrics
            metrics = pool.get_metrics()

            assert metrics["connections_created"] == 1
            assert metrics["connections_reused"] == 1
            assert metrics["total_operations"] == 2
            assert metrics["reuse_ratio"] == 0.5
            assert metrics["active_pools"] == 1

        await pool.close_all()

    @pytest.mark.asyncio
    async def test_connection_pool_multiple_peers(self):
        """Test that pool maintains separate pools per peer URI."""
        pool = PeerConnectionPool(max_connections_per_peer=3)
        peer_uri1 = "ws://peer1:8333"
        peer_uri2 = "ws://peer2:8333"

        async def mock_websockets_connect(*args, **kwargs):
            return create_healthy_mock_ws()

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Create connections to different peers
            conn1 = await pool.get_connection(peer_uri1)
            conn2 = await pool.get_connection(peer_uri2)

            # Should have created 2 connections total
            assert pool._total_connections_created == 2

            # Should have 2 separate pools
            assert peer_uri1 in pool.pools
            assert peer_uri2 in pool.pools

        await pool.close_all()


class TestPeerDiscoveryWithPooling:
    """Test PeerDiscovery with connection pooling."""

    @pytest.mark.asyncio
    async def test_discovery_uses_connection_pool(self):
        """Test that discovery reuses connections from pool."""
        # Create discovery with custom connection pool
        connection_pool = PeerConnectionPool(max_connections_per_peer=3)
        discovery = PeerDiscovery(
            bootstrap_nodes=["ws://bootstrap1:8333", "ws://bootstrap2:8333"],
            connection_pool=connection_pool,
        )

        async def mock_websockets_connect(*args, **kwargs):
            mock_ws = create_healthy_mock_ws()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(return_value=json.dumps({
                "type": "peers",
                "payload": ["peer1:8333", "peer2:8333"]
            }))
            return mock_ws

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # First discovery
            peers1 = await discovery.discover_from_bootstrap()
            assert len(peers1) == 4  # 2 peers * 2 bootstrap nodes

            # Second discovery should reuse connections
            peers2 = await discovery.discover_from_bootstrap()
            assert len(peers2) == 4

            # Verify connections were reused
            assert connection_pool._total_connections_reused >= 2

        await discovery.close()

    @pytest.mark.asyncio
    async def test_discovery_pool_metrics(self):
        """Test that discovery exposes pool metrics."""
        connection_pool = PeerConnectionPool(max_connections_per_peer=3)
        discovery = PeerDiscovery(
            bootstrap_nodes=["ws://bootstrap:8333"],
            connection_pool=connection_pool,
        )

        async def mock_websockets_connect(*args, **kwargs):
            mock_ws = create_healthy_mock_ws()
            mock_ws.send = AsyncMock()
            mock_ws.recv = AsyncMock(return_value=json.dumps({
                "type": "peers",
                "payload": ["peer1:8333"]
            }))
            return mock_ws

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Perform discovery
            await discovery.discover_from_bootstrap()

            # Get metrics
            metrics = discovery.get_pool_metrics()

            assert "connections_created" in metrics
            assert "connections_reused" in metrics
            assert "reuse_ratio" in metrics
            assert metrics["connections_created"] >= 1

        await discovery.close()

    @pytest.mark.asyncio
    async def test_discovery_handles_connection_failure(self):
        """Test that discovery handles connection failures gracefully."""
        discovery = PeerDiscovery(
            bootstrap_nodes=["ws://failing:8333"],
        )

        async def mock_websockets_connect(*args, **kwargs):
            raise ConnectionError("Failed to connect")

        with patch('xai.network.peer_manager.websockets.connect', new=mock_websockets_connect):
            # Discovery should handle error gracefully
            peers = await discovery.discover_from_bootstrap()

            # Should return empty list, not raise exception
            assert peers == []

        await discovery.close()
