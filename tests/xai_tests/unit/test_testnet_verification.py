from __future__ import annotations

import requests

from xai.testnet.verification import NodeTarget, TestnetVerifier


class FakeResponse:
    """Simple stand-in for requests.Response."""

    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self) -> dict:
        return self._payload


class FakeSession:
    """Fake requests.Session that returns canned responses."""

    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self.closed = False

    def get(self, url: str, timeout: float) -> FakeResponse:
        if url not in self._responses:
            raise AssertionError(f"Unexpected URL {url}")
        payload = self._responses[url]
        if isinstance(payload, Exception):
            raise payload
        body = payload.get("json", {})
        status = payload.get("status", 200)
        return FakeResponse(body, status=status)

    def close(self) -> None:  # pragma: no cover - not closed during tests
        self.closed = True


def _build_node(
    name: str,
    base_url: str,
    *,
    height: int,
    block_hash: str,
    peer_count: int,
    stats_height: int | None = None,
    stats_hash: str | None = None,
    summary_height: int | None = None,
    summary_hash: str | None = None,
) -> NodeTarget:
    summary_height = height if summary_height is None else summary_height
    summary_hash = block_hash if summary_hash is None else summary_hash
    stats_height = height if stats_height is None else stats_height
    stats_hash = block_hash if stats_hash is None else stats_hash

    stats_payload: Dict[str, Any] = {}
    if stats_height is not None:
        stats_payload["chain_height"] = stats_height
    if stats_hash is not None:
        stats_payload["latest_block_hash"] = stats_hash

    responses = {
        f"{base_url}/health": {
            "json": {"status": "healthy", "network": {"peers": peer_count}},
        },
        f"{base_url}/stats": {"json": stats_payload},
        f"{base_url}/peers?verbose=true": {
            "json": {"count": peer_count, "connected_total": peer_count},
        },
        f"{base_url}/block/latest?summary=1": {
            "json": {
                "summary": {
                    "height": summary_height,
                    "hash": summary_hash,
                    "difficulty": 1,
                    "timestamp": 0,
                    "transactions": 1,
                },
                "block_number": summary_height,
                "hash": summary_hash,
                "timestamp": 0,
            }
        },
    }
    return NodeTarget(name=name, base_url=base_url, session=FakeSession(responses))


def test_verifier_success_with_explorer() -> None:
    nodes = [
        _build_node("bootstrap", "http://node-a", height=42, block_hash="0xabc", peer_count=3),
        _build_node("node1", "http://node-b", height=42, block_hash="0xabc", peer_count=4),
    ]
    explorer_session = FakeSession(
        {"http://explorer/health": {"json": {"status": "healthy", "components": {}}}}
    )
    verifier = TestnetVerifier(
        nodes,
        min_peer_count=2,
        explorer_url="http://explorer",
        request_timeout=0.1,
        explorer_session=explorer_session,
    )
    result = verifier.verify()

    assert result.ok is True
    assert result.consensus_ok is True
    assert result.peer_counts_ok is True
    assert result.explorer_ok is True
    assert result.to_dict()["ok"] is True


def test_verifier_detects_height_divergence() -> None:
    nodes = [
        _build_node("bootstrap", "http://node-a", height=10, block_hash="0xabc", peer_count=3),
        _build_node("node1", "http://node-b", height=11, block_hash="0xdef", peer_count=3),
    ]
    verifier = TestnetVerifier(nodes, min_peer_count=2, request_timeout=0.1)
    result = verifier.verify()

    assert result.consensus_ok is False
    assert any("diverged" in err for err in result.errors)


def test_verifier_flags_low_peer_counts() -> None:
    nodes = [
        _build_node("bootstrap", "http://node-a", height=10, block_hash="0xabc", peer_count=1),
        _build_node("node1", "http://node-b", height=10, block_hash="0xabc", peer_count=3),
    ]
    verifier = TestnetVerifier(nodes, min_peer_count=2, request_timeout=0.1)
    result = verifier.verify()

    assert result.peer_counts_ok is False
    assert any("Peer counts below threshold" in err for err in result.errors)


def test_verifier_records_http_failures() -> None:
    base_url = "http://node-a"
    responses = {
        f"{base_url}/health": requests.ConnectionError("boom"),
        f"{base_url}/stats": {"json": {"chain_height": 7, "latest_block_hash": "0xabc"}},
        f"{base_url}/peers?verbose=true": {"json": {"count": 0}},
    }
    failing_node = NodeTarget(
        name="bootstrap",
        base_url=base_url,
        session=FakeSession(responses),
    )
    verifier = TestnetVerifier([failing_node], min_peer_count=0, request_timeout=0.1)
    result = verifier.verify()

    assert result.ok is False
    assert "health:" in result.node_results[0].errors[0]
