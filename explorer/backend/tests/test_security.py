import sys
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

sys.path.append(str(Path(__file__).resolve().parents[1]))

from security import (  # noqa: E402
    APIAuthConfig,
    APIKeyAuthError,
    build_api_key_dependency,
    enforce_websocket_api_key,
)


def _create_test_app():
    config = APIAuthConfig(require_api_key=True, initial_keys=["unit-test-key"])
    dependency = Depends(build_api_key_dependency(config))
    app = FastAPI()

    @app.get("/secured", dependencies=[dependency])
    async def secured_endpoint():
        return {"status": "ok"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        try:
            await enforce_websocket_api_key(websocket, config)
        except APIKeyAuthError:
            return
        await websocket.accept()
        await websocket.send_json({"ready": True})

    return app, config


@pytest.fixture()
def secured_client():
    app, _ = _create_test_app()
    return TestClient(app)


def test_http_request_without_key_rejected(secured_client):
    response = secured_client.get("/secured")
    assert response.status_code == 401


def test_http_request_with_header_key_allowed(secured_client):
    response = secured_client.get("/secured", headers={"X-API-Key": "unit-test-key"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_http_request_with_query_key_allowed(secured_client):
    response = secured_client.get("/secured", params={"api_key": "unit-test-key"})
    assert response.status_code == 200


def test_websocket_rejects_missing_key():
    app, _ = _create_test_app()
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws"):
            pass
    assert excinfo.value.code == 1008


def test_websocket_accepts_valid_key():
    app, _ = _create_test_app()
    client = TestClient(app)
    with client.websocket_connect("/ws?api_key=unit-test-key") as connection:
        message = connection.receive_json()
        assert message["ready"] is True
