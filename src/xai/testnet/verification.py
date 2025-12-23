from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests


class NodeCheckError(RuntimeError):
    """Raised when a node or explorer endpoint cannot be queried."""

@dataclass
class NodeTarget:
    """Describes a node API target that should be verified."""

    name: str
    base_url: str
    session: requests.Session | None = None

@dataclass
class NodeStatus:
    """Holds the collected telemetry for a single node."""

    name: str
    base_url: str
    health: dict[str, Any] | None = None
    stats: dict[str, Any] | None = None
    peers: dict[str, Any] | None = None
    latest_summary: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def status_label(self) -> str:
        """Return a short label describing node health."""
        if self.errors:
            return "error"
        if isinstance(self.health, dict):
            return str(self.health.get("status", "unknown"))
        return "unknown"

    @property
    def peer_count(self) -> int:
        """Best-effort peer count derived from peers endpoint or /health."""
        if isinstance(self.peers, dict):
            if isinstance(self.peers.get("connected_total"), int):
                return int(self.peers["connected_total"])
            if isinstance(self.peers.get("count"), int):
                return int(self.peers["count"])
        if isinstance(self.health, dict):
            network = self.health.get("network")
            if isinstance(network, dict) and isinstance(network.get("peers"), (int, float)):
                return int(network["peers"])
        return 0

    @property
    def chain_height(self) -> int | None:
        """Chain height derived from latest summary (preferred) or stats fallback."""
        summary_height = self._summary_value("block_number")
        if summary_height is None:
            summary_height = self._summary_value("height")
        if summary_height is not None:
            try:
                return int(summary_height)
            except (TypeError, ValueError):
                pass
        if not isinstance(self.stats, dict):
            return None
        try:
            return int(self.stats.get("chain_height"))
        except (TypeError, ValueError):
            return None

    @property
    def latest_block_hash(self) -> str | None:
        """Latest block hash, preferring the live summary endpoint."""
        summary_hash = self._summary_value("hash")
        if isinstance(summary_hash, str) and summary_hash:
            return summary_hash
        if not isinstance(self.stats, dict):
            return None
        hash_value = self.stats.get("latest_block_hash")
        if isinstance(hash_value, str):
            return hash_value
        return None

    def _summary_value(self, key: str) -> Any | None:
        """Return a field from the latest summary response."""
        if not isinstance(self.latest_summary, dict):
            return None
        if key in self.latest_summary:
            return self.latest_summary.get(key)
        summary_body = self.latest_summary.get("summary")
        if isinstance(summary_body, dict):
            return summary_body.get(key)
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "status": self.status_label,
            "peer_count": self.peer_count,
            "chain_height": self.chain_height,
            "latest_block_hash": self.latest_block_hash,
            "latest_summary": self.latest_summary,
            "errors": list(self.errors),
        }

@dataclass
class ExplorerStatus:
    """Captures explorer health check results."""

    url: str
    payload: dict[str, Any] | None = None
    error: str | None = None

    @property
    def healthy(self) -> bool:
        """Return True if explorer is reporting a healthy status."""
        if self.payload and isinstance(self.payload.get("status"), str):
            return self.payload["status"] == "healthy"
        return False if self.error else True

    def to_dict(self) -> dict[str, Any]:
        """Return serializable representation."""
        return {
            "url": self.url,
            "healthy": self.healthy,
            "payload": self.payload,
            "error": self.error,
        }

@dataclass
class VerificationResult:
    """Aggregate result from verifying all nodes and optional explorer."""

    node_results: list[NodeStatus]
    node_checks_ok: bool
    consensus_ok: bool
    peer_counts_ok: bool
    explorer_status: ExplorerStatus | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def explorer_ok(self) -> bool:
        """Return True when explorer is healthy or skipped."""
        if self.explorer_status is None:
            return True
        return self.explorer_status.healthy

    @property
    def ok(self) -> bool:
        """Return True when every check succeeded."""
        return self.node_checks_ok and self.consensus_ok and self.peer_counts_ok and self.explorer_ok

    def to_dict(self) -> dict[str, Any]:
        """Return serializable representation."""
        return {
            "ok": self.ok,
            "node_checks_ok": self.node_checks_ok,
            "consensus_ok": self.consensus_ok,
            "peer_counts_ok": self.peer_counts_ok,
            "explorer_ok": self.explorer_ok,
            "nodes": [node.to_dict() for node in self.node_results],
            "explorer": self.explorer_status.to_dict() if self.explorer_status else None,
            "errors": list(self.errors),
        }

class _BaseHTTPClient:
    """Shared helper for talking to HTTP endpoints with common error handling."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float,
        session: requests.Session,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError(f"Base URL {base_url} must include scheme")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session

    def _fetch_json(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NodeCheckError(f"{url} request failed: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise NodeCheckError(f"{url} returned non-JSON payload") from exc
        if not isinstance(payload, dict):
            raise NodeCheckError(f"{url} returned unexpected payload type {type(payload).__name__}")
        return payload

class NodeAPIClient(_BaseHTTPClient):
    """HTTP client for node APIs."""

    def get_health(self) -> dict[str, Any]:
        """Return /health payload."""
        return self._fetch_json("/health")

    def get_stats(self) -> dict[str, Any]:
        """Return /stats payload."""
        return self._fetch_json("/stats")

    def get_peers(self, verbose: bool = True) -> dict[str, Any]:
        """Return /peers payload."""
        suffix = "?verbose=true" if verbose else ""
        return self._fetch_json(f"/peers{suffix}")

    def get_latest_block_summary(self) -> dict[str, Any]:
        """Return /block/latest summary payload."""
        return self._fetch_json("/block/latest?summary=1")

class ExplorerClient(_BaseHTTPClient):
    """HTTP client for explorer backend."""

    def get_health(self) -> dict[str, Any]:
        """Return explorer /health payload."""
        return self._fetch_json("/health")

class TestnetVerifier:
    """Collects health/consensus information from a set of nodes."""

    def __init__(
        self,
        nodes: Sequence[NodeTarget],
        *,
        min_peer_count: int = 2,
        explorer_url: str | None = None,
        request_timeout: float = 3.0,
        explorer_session: requests.Session | None = None,
    ) -> None:
        if not nodes:
            raise ValueError("At least one node target is required")
        self.nodes = list(nodes)
        self.min_peer_count = max(min_peer_count, 0)
        self.explorer_url = explorer_url
        self.request_timeout = request_timeout
        self._explorer_session = explorer_session

    def verify(self) -> VerificationResult:
        """Collect information from every node and produce an aggregate result."""
        node_results: list[NodeStatus] = []
        errors: list[str] = []
        created_sessions: list[requests.Session] = []

        try:
            for target in self.nodes:
                node_results.append(self._check_node(target, created_sessions))

            failing_nodes = [node.name for node in node_results if node.errors]
            node_checks_ok = not failing_nodes
            if failing_nodes:
                errors.append(f"Node API errors detected for: {', '.join(failing_nodes)}")

            consensus_ok, consensus_error = self._evaluate_consensus(node_results)
            peer_ok, peer_error = self._evaluate_peer_counts(node_results)
            explorer_status = self._check_explorer(created_sessions) if self.explorer_url else None

            if consensus_error:
                errors.append(consensus_error)
            if peer_error:
                errors.append(peer_error)
            if explorer_status and not explorer_status.healthy and explorer_status.error:
                errors.append(explorer_status.error)

            return VerificationResult(
                node_results=node_results,
                node_checks_ok=node_checks_ok,
                consensus_ok=consensus_ok,
                peer_counts_ok=peer_ok,
                explorer_status=explorer_status,
                errors=errors,
            )
        finally:
            for session in created_sessions:
                session.close()

    def render_text(self, result: VerificationResult) -> str:
        """Return human-readable summary."""
        lines = [
            "Four-Node Testnet Verification",
            f"Node APIs   : {'PASS' if result.node_checks_ok else 'FAIL'}",
            f"Consensus    : {'PASS' if result.consensus_ok else 'FAIL'}",
            f"Peer Counts  : {'PASS' if result.peer_counts_ok else 'FAIL'} "
            f"(min {self.min_peer_count})",
            f"Explorer     : {'PASS' if result.explorer_ok else 'FAIL' if result.explorer_status else 'SKIP'}",
        ]
        if result.errors:
            lines.append(f"Issues       : {', '.join(result.errors)}")
        lines.append("")
        for node in result.node_results:
            height = node.chain_height
            hash_fragment = (node.latest_block_hash or "")[:12]
            lines.append(f"- {node.name} [{node.base_url}]")
            lines.append(
                f"  Status={node.status_label} "
                f"Height={height if height is not None else 'unknown'} "
                f"Peers={node.peer_count} "
                f"Hash={hash_fragment or 'n/a'}"
            )
            if node.errors:
                lines.append(f"  Errors: {', '.join(node.errors)}")
        if result.explorer_status:
            status = "healthy" if result.explorer_status.healthy else "degraded"
            lines.append("")
            lines.append(f"Explorer [{result.explorer_status.url}] -> {status}")
            if result.explorer_status.error:
                lines.append(f"  Error: {result.explorer_status.error}")
        return "\n".join(lines)

    def _ensure_session(
        self,
        target: NodeTarget,
        created_sessions: list[requests.Session],
    ) -> requests.Session:
        if target.session is not None:
            return target.session
        session = requests.Session()
        created_sessions.append(session)
        return session

    def _check_node(
        self,
        target: NodeTarget,
        created_sessions: list[requests.Session],
    ) -> NodeStatus:
        base_url = target.base_url.rstrip("/")
        session = self._ensure_session(target, created_sessions)
        client = NodeAPIClient(base_url, timeout=self.request_timeout, session=session)
        status = NodeStatus(name=target.name, base_url=base_url)
        try:
            status.health = client.get_health()
        except NodeCheckError as exc:
            status.errors.append(f"health:{exc}")
        try:
            status.stats = client.get_stats()
        except NodeCheckError as exc:
            status.errors.append(f"stats:{exc}")
        try:
            status.peers = client.get_peers(verbose=True)
        except NodeCheckError as exc:
            status.errors.append(f"peers:{exc}")
        try:
            status.latest_summary = client.get_latest_block_summary()
        except NodeCheckError as exc:
            status.errors.append(f"latest_block:{exc}")
        return status

    def _check_explorer(self, created_sessions: list[requests.Session]) -> ExplorerStatus:
        base_url = self.explorer_url.rstrip("/") if self.explorer_url else ""
        session = self._explorer_session
        if session is None:
            session = requests.Session()
            created_sessions.append(session)
        client = ExplorerClient(base_url, timeout=self.request_timeout, session=session)
        try:
            payload = client.get_health()
            return ExplorerStatus(url=base_url, payload=payload)
        except NodeCheckError as exc:
            return ExplorerStatus(url=base_url, error=str(exc))

    def _evaluate_consensus(self, node_results: Sequence[NodeStatus]) -> tuple[bool, str | None]:
        heights: dict[int, list[str]] = {}
        hashes: dict[str, list[str]] = {}
        missing_nodes: list[str] = []

        for node in node_results:
            height = node.chain_height
            block_hash = node.latest_block_hash
            if height is None or block_hash is None:
                missing_nodes.append(node.name)
                continue
            heights.setdefault(height, []).append(node.name)
            hashes.setdefault(block_hash, []).append(node.name)

        if not heights or not hashes:
            return False, f"No height/hash data available for nodes: {', '.join(missing_nodes)}"
        if len(heights) > 1:
            detail = ", ".join(f"{h} -> {names}" for h, names in heights.items())
            return False, f"Chain heights diverged ({detail})"
        if len(hashes) > 1:
            detail = ", ".join(f"{h[:12]} -> {names}" for h, names in hashes.items())
            return False, f"Latest hashes differ ({detail})"
        return True, None

    def _evaluate_peer_counts(self, node_results: Sequence[NodeStatus]) -> tuple[bool, str | None]:
        deficient: list[str] = []
        for node in node_results:
            if node.peer_count < self.min_peer_count:
                deficient.append(f"{node.name}={node.peer_count}")
        if deficient:
            return False, f"Peer counts below threshold: {', '.join(deficient)}"
        return True, None
