from flask import Flask

from xai.core.config import Config
from xai.core.node import CORSPolicyManager


def test_cors_policy_uses_configured_origins(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/ping")
    def ping():
        return "pong"

    monkeypatch.setattr(Config, "API_ALLOWED_ORIGINS", ["http://foo.test"], raising=False)
    manager = CORSPolicyManager(app)

    assert manager.allowed_origins == ["http://foo.test"]

    with app.test_client() as client:
        response = client.get("/ping", headers={"Origin": "http://foo.test"})
        assert response.status_code == 200
        assert response.data == b"pong"
        assert response.headers["Access-Control-Allow-Origin"] == "http://foo.test"
