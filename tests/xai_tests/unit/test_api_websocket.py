"""Unit tests for WebSocket API authentication enforcement."""

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from xai.core.api_websocket import WebSocketAPIHandler, WebSocketLimiter


class _DummyThread:
    """No-op thread used to prevent background loops from running in tests."""

    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon

    def start(self):
        # Tests only need the thread to exist, not execute the cleanup loop
        return None


@pytest.fixture
def websocket_handler(monkeypatch):
    """Create a WebSocket handler with mocks for API auth and limiter."""

    app = Flask(__name__)
    monkeypatch.setattr("xai.core.api_websocket.threading.Thread", _DummyThread)

    node = SimpleNamespace(app=app, blockchain=Mock())
    node.blockchain.get_stats.return_value = {}

    api_auth = Mock()
    handler = WebSocketAPIHandler(node, app, api_auth=api_auth)
    handler.api_auth = api_auth

    limiter_mock = Mock(spec=WebSocketLimiter)
    limiter_mock.can_connect.return_value = (True, None)
    handler.limiter = limiter_mock

    return handler, api_auth, app


def test_websocket_authentication_skipped_when_disabled(websocket_handler):
    handler, api_auth, app = websocket_handler
    api_auth.is_enabled.return_value = False

    with app.test_request_context("/ws"):
        allowed, reason = handler._authenticate_ws_request()

    assert allowed is True
    assert reason is None
    api_auth.authorize.assert_not_called()


def test_websocket_authentication_succeeds_with_valid_key(websocket_handler):
    handler, api_auth, app = websocket_handler
    api_auth.is_enabled.return_value = True
    api_auth.authorize.return_value = (True, None)

    headers = {"X-API-Key": "secret"}
    with app.test_request_context("/ws", headers=headers):
        allowed, reason = handler._authenticate_ws_request()

    assert allowed is True
    assert reason is None
    api_auth.authorize.assert_called_once()


def test_unauthorized_websocket_connection_rejected(websocket_handler):
    handler, api_auth, app = websocket_handler
    api_auth.is_enabled.return_value = True
    api_auth.authorize.return_value = (False, "API key missing or invalid")

    mock_ws = Mock()

    with patch("xai.core.api_websocket.log_security_event") as mock_log:
        with app.test_request_context(
            "/ws",
            headers={"User-Agent": "pytest"},
            environ_base={"REMOTE_ADDR": "203.0.113.9"},
        ):
            handler._handle_websocket_connection(mock_ws)

    handler.limiter.can_connect.assert_not_called()
    handler.limiter.register_connection.assert_not_called()
    handler.limiter.unregister_connection.assert_not_called()
    assert handler.ws_clients == []

    mock_ws.send.assert_called_once()
    payload = json.loads(mock_ws.send.call_args[0][0])
    assert payload["code"] == "WS_AUTH_FAILED"
    assert payload["error"] == "API key missing or invalid"
    mock_ws.close.assert_called()
    mock_ws.receive.assert_not_called()

    api_auth.authorize.assert_called_once()
    mock_log.assert_called_once()
