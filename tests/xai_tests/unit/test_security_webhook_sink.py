import types

from xai.core.node import BlockchainNode


def test_security_webhook_sink_creation_accepts_url(monkeypatch):
    sink = BlockchainNode._create_security_webhook_sink(
        url="https://example.com/webhook",
        token="secret-token",
        timeout=2,
        max_retries=1,
        backoff=0.1,
    )
    assert callable(sink)


def test_security_webhook_sink_drops_info_severity(monkeypatch):
    payloads = []

    def fake_enqueue(payload):
        payloads.append(payload)

    # Patch forwarder to avoid network
    monkeypatch.setattr("xai.core.node._SecurityWebhookForwarder.enqueue", lambda self, p: fake_enqueue(p))

    sink = BlockchainNode._create_security_webhook_sink("https://example.com/webhook", token="", timeout=1)
    sink("p2p.replay_detected", {"peer": "test"}, "INFO")
    sink("p2p.replay_detected", {"peer": "test"}, "WARNING")

    assert len(payloads) == 1
    assert payloads[0]["severity"] == "WARNING"
