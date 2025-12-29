import asyncio
import socket
import ssl
import time

import pytest

pytest.importorskip("aioquic")
try:
    from aioquic.crypto import generate_ec_certificate  # type: ignore
except Exception:
    # Fallback: generate a self-signed EC cert with cryptography when aioquic helper is unavailable
    from cryptography import x509  # type: ignore
    from cryptography.hazmat.primitives import hashes, serialization  # type: ignore
    from cryptography.hazmat.primitives.asymmetric import ec  # type: ignore
    from cryptography.x509.oid import NameOID  # type: ignore
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

from xai.core.p2p.p2p_quic import QUICServer, quic_client_send, quic_client_send_with_timeout, QuicConfiguration  # type: ignore


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_quic_latency_soak_under_threshold():
    host = "127.0.0.1"
    port = _free_port()
    received = []

    cert_pem, key_pem = generate_ec_certificate(common_name=host)
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as cert_file, tempfile.NamedTemporaryFile(delete=False) as key_file:
        cert_file.write(cert_pem)
        key_file.write(key_pem)
        cert_path, key_path = cert_file.name, key_file.name

    server_conf = QuicConfiguration(is_client=False, alpn_protocols=["xai-p2p"])
    server_conf.load_cert_chain(certfile=cert_path, keyfile=key_path)

    server = QUICServer(host, port, server_conf, handler=lambda data: received.append(data))
    await server.start()

    client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
    client_conf.verify_mode = ssl.CERT_NONE

    messages = [f"quic-{i}".encode() for i in range(10)]
    latencies = []
    try:
        for payload in messages:
            start = time.perf_counter()
            await asyncio.wait_for(quic_client_send(host, port, payload, client_conf), timeout=1.5)
            latencies.append(time.perf_counter() - start)
            await asyncio.sleep(0.01)
    finally:
        await server.close()

    assert len(received) == len(messages)
    assert sum(latencies) / len(latencies) < 0.5
    assert max(latencies) < 1.0


@pytest.mark.asyncio
async def test_quic_stream_error_handling():
    host = "127.0.0.1"
    port = _free_port()
    # No server started to force connection failure
    client_conf = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
    client_conf.verify_mode = ssl.CERT_NONE

    with pytest.raises(ConnectionError):
        await quic_client_send_with_timeout(host, port, b"fail-fast", client_conf, timeout=0.5)
