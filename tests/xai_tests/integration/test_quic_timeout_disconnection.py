"""
QUIC timeout and disconnection scenario tests.

Tests edge cases for QUIC transport handling:
- Connection timeouts
- Dial timeouts
- Graceful disconnection
- Reconnection after failure
- Metrics recording on failure
"""

import asyncio
import socket
import ssl
import time
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Skip module if aioquic is not available
pytest.importorskip("aioquic")

try:
    from aioquic.crypto import generate_ec_certificate  # type: ignore
except Exception:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    from datetime import datetime, timedelta

    def generate_ec_certificate(common_name: str):
        key = ec.generate_private_key(ec.SECP256R1())
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=1))
            .sign(key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cert_pem, key_pem


from xai.core.p2p_quic import (
    QUICServer,
    quic_client_send,
    quic_client_send_with_timeout,
    QuicConfiguration,
    QuicDialTimeout,
)


def _free_port() -> int:
    """Find a free UDP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _create_server_config(host: str):
    """Create server config with temp certificates."""
    cert_pem, key_pem = generate_ec_certificate(common_name=host)
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    key_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    cert_file.write(cert_pem)
    key_file.write(key_pem)
    cert_file.close()
    key_file.close()

    server_conf = QuicConfiguration(is_client=False, alpn_protocols=["xai-p2p"])
    server_conf.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)
    return server_conf, cert_file.name, key_file.name


class TestQuicDialTimeout:
    """Test QUIC dial timeout handling."""

    @pytest.mark.asyncio
    async def test_dial_timeout_no_server(self):
        """Connection to non-existent server should timeout with QuicDialTimeout."""
        host = "127.0.0.1"
        port = _free_port()  # No server listening
        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        with pytest.raises((QuicDialTimeout, ConnectionError)):
            await quic_client_send_with_timeout(
                host, port, b"test", client_conf, timeout=0.5
            )

    @pytest.mark.asyncio
    async def test_dial_timeout_value_respected(self):
        """Timeout should be approximately the configured value."""
        host = "127.0.0.1"
        port = _free_port()
        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        start = time.monotonic()
        with pytest.raises((QuicDialTimeout, ConnectionError)):
            await quic_client_send_with_timeout(
                host, port, b"test", client_conf, timeout=0.3
            )
        elapsed = time.monotonic() - start

        # Should complete within timeout + some buffer
        assert elapsed < 1.0  # Well under 1 second
        assert elapsed >= 0.2  # At least waited some time

    @pytest.mark.asyncio
    async def test_short_timeout_fails_fast(self):
        """Very short timeout should fail quickly."""
        host = "127.0.0.1"
        port = _free_port()
        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        start = time.monotonic()
        with pytest.raises((QuicDialTimeout, ConnectionError, asyncio.TimeoutError)):
            await quic_client_send_with_timeout(
                host, port, b"test", client_conf, timeout=0.1
            )
        elapsed = time.monotonic() - start
        # Allow some buffer for connection cleanup overhead
        assert elapsed < 1.5


class TestQuicConnectionFailure:
    """Test QUIC connection failure scenarios."""

    @pytest.mark.asyncio
    async def test_server_shutdown_during_send(self):
        """Client should handle server shutdown gracefully."""
        host = "127.0.0.1"
        port = _free_port()
        received = []

        server_conf, cert_path, key_path = _create_server_config(host)
        server = QUICServer(host, port, server_conf, handler=lambda d: received.append(d))
        await server.start()

        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        # First send should succeed
        await quic_client_send_with_timeout(host, port, b"msg1", client_conf, timeout=1.0)
        assert len(received) == 1

        # Shutdown server
        await server.close()
        await asyncio.sleep(0.1)  # Allow shutdown to complete

        # Next send should fail
        with pytest.raises((QuicDialTimeout, ConnectionError)):
            await quic_client_send_with_timeout(
                host, port, b"msg2", client_conf, timeout=0.5
            )

    @pytest.mark.asyncio
    async def test_reconnect_after_failure(self):
        """Client should be able to reconnect after server restart."""
        host = "127.0.0.1"
        port = _free_port()
        received = []

        server_conf, cert_path, key_path = _create_server_config(host)
        server = QUICServer(host, port, server_conf, handler=lambda d: received.append(d))
        await server.start()

        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        # First send
        await quic_client_send_with_timeout(host, port, b"msg1", client_conf, timeout=1.0)
        assert len(received) == 1

        # Shutdown server
        await server.close()
        await asyncio.sleep(0.1)

        # Restart server (with fresh config to avoid cert issues)
        server_conf2, _, _ = _create_server_config(host)
        server2 = QUICServer(host, port, server_conf2, handler=lambda d: received.append(d))
        await server2.start()

        # Should succeed after reconnect
        await quic_client_send_with_timeout(host, port, b"msg2", client_conf, timeout=1.0)
        assert len(received) == 2

        await server2.close()


class TestQuicGracefulDisconnection:
    """Test graceful disconnection scenarios."""

    @pytest.mark.asyncio
    async def test_server_close_graceful(self):
        """Server close should not crash or hang."""
        host = "127.0.0.1"
        port = _free_port()
        received = []

        server_conf, cert_path, key_path = _create_server_config(host)
        server = QUICServer(host, port, server_conf, handler=lambda d: received.append(d))
        await server.start()

        # Close without any connections should be clean
        await server.close()

    @pytest.mark.asyncio
    async def test_server_close_with_pending_handler(self):
        """Server close with pending handler should not crash."""
        host = "127.0.0.1"
        port = _free_port()

        async def slow_handler(data):
            await asyncio.sleep(1.0)
            return data

        server_conf, cert_path, key_path = _create_server_config(host)
        server = QUICServer(host, port, server_conf, handler=slow_handler)
        await server.start()

        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        # Start send but don't wait
        asyncio.create_task(
            quic_client_send_with_timeout(host, port, b"test", client_conf, timeout=2.0)
        )
        await asyncio.sleep(0.1)

        # Close server immediately - should not hang or crash
        await asyncio.wait_for(server.close(), timeout=2.0)


class TestQuicMetricsRecording:
    """Test that QUIC failures record proper metrics."""

    def test_record_quic_timeout_increments_counter(self):
        """_record_quic_timeout should increment timeout counter."""
        from xai.core.node_p2p import P2PNetworkManager
        from xai.core.blockchain import Blockchain

        bc = Blockchain()
        manager = P2PNetworkManager(bc, max_connections=1)

        # Mock metrics collector - patch at the import location in node_p2p
        mock_metric = MagicMock()
        mock_collector = MagicMock()
        mock_collector.get_metric.return_value = mock_metric

        with patch("xai.core.monitoring.MetricsCollector") as mock_mc:
            mock_mc.instance.return_value = mock_collector
            manager._record_quic_timeout("test-host")

        # Verify timeout metric was incremented
        mock_collector.get_metric.assert_any_call("xai_p2p_quic_timeouts_total")

    def test_record_quic_error_increments_counter(self):
        """_record_quic_error should increment error counter."""
        from xai.core.node_p2p import P2PNetworkManager
        from xai.core.blockchain import Blockchain

        bc = Blockchain()
        manager = P2PNetworkManager(bc, max_connections=1)

        mock_metric = MagicMock()
        mock_collector = MagicMock()
        mock_collector.get_metric.return_value = mock_metric

        with patch("xai.core.monitoring.MetricsCollector") as mock_mc:
            mock_mc.instance.return_value = mock_collector
            manager._record_quic_error("test-host")

        mock_collector.get_metric.assert_any_call("xai_p2p_quic_errors_total")


class TestQuicConcurrency:
    """Test QUIC under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_sends(self):
        """Multiple concurrent sends should all succeed."""
        host = "127.0.0.1"
        port = _free_port()
        received = []

        server_conf, cert_path, key_path = _create_server_config(host)
        server = QUICServer(host, port, server_conf, handler=lambda d: received.append(d))
        await server.start()

        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        try:
            # Send 5 messages concurrently
            tasks = [
                quic_client_send_with_timeout(host, port, f"msg{i}".encode(), client_conf, timeout=2.0)
                for i in range(5)
            ]
            await asyncio.gather(*tasks)
            await asyncio.sleep(0.2)  # Allow processing

            assert len(received) == 5
        finally:
            await server.close()

    @pytest.mark.asyncio
    async def test_rapid_send_receive(self):
        """Rapid sequential sends should all succeed."""
        host = "127.0.0.1"
        port = _free_port()
        received = []

        server_conf, cert_path, key_path = _create_server_config(host)
        server = QUICServer(host, port, server_conf, handler=lambda d: received.append(d))
        await server.start()

        client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
        client_conf.verify_mode = ssl.CERT_NONE

        try:
            for i in range(10):
                await quic_client_send_with_timeout(
                    host, port, f"rapid-{i}".encode(), client_conf, timeout=1.0
                )
            await asyncio.sleep(0.2)

            assert len(received) == 10
        finally:
            await server.close()
