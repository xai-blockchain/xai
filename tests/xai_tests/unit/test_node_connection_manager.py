"""
Unit tests for NodeConnectionManager security integrations.
"""

import pytest

from xai.network.node_connection_manager import NodeConnectionManager
from xai.core.security.p2p_security import P2PSecurityManager


class MockSecurityManager(P2PSecurityManager):
    def __init__(self):
        super().__init__()
        self.validated_messages = []

    def validate_message(self, peer_url: str, message_data: bytes, message: dict):
        self.validated_messages.append((peer_url, message))
        return super().validate_message(peer_url, message_data, message)


@pytest.mark.asyncio
async def test_inbound_connection_honors_security_limits():
    mock_security = MockSecurityManager()
    manager = NodeConnectionManager(
        max_inbound_connections=1,
        max_outbound_connections=1,
        security_manager=mock_security,
    )

    peer_data = {"url": "peer://a", "ip": "192.0.2.1"}
    conn_id = await manager.handle_inbound_connection(peer_data)
    assert conn_id.startswith("conn_")

    try:
        await manager.handle_inbound_connection({"url": "peer://b", "ip": "192.0.2.1"})
        raise AssertionError("Expected limit error")
    except ValueError as exc:
        assert "Max inbound" in str(exc)


@pytest.mark.asyncio
async def test_message_validation_uses_security_manager():
    mock_security = MockSecurityManager()
    manager = NodeConnectionManager(security_manager=mock_security)

    peer_url = "peer://valid"
    mock_security.peer_reputation.track_peer_ip(peer_url, "203.0.113.1")

    good_message = {"type": "ping"}
    allowed = await manager.validate_peer_message(peer_url, b"abc", good_message)
    assert allowed
    assert mock_security.validated_messages[-1][1] == good_message

    bad_message = {"type": "unknown"}
    assert not await manager.validate_peer_message(peer_url, b"abc", bad_message)
