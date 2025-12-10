from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple, Any

from flask import jsonify, request

from xai.core.request_validator_middleware import validate_request
from xai.core.input_validation_schemas import PeerAddInput

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def register_peer_routes(routes: "NodeAPIRoutes") -> None:
    """Expose peer management endpoints."""
    app = routes.app
    node = routes.node

    @app.route("/peers", methods=["GET"])
    def get_peers() -> Dict[str, Any]:
        verbose = request.args.get("verbose", "false")
        verbose_requested = str(verbose).lower() in {"1", "true", "yes", "on"}
        payload: Dict[str, Any] = {"count": len(node.peers), "peers": list(node.peers), "verbose": verbose_requested}
        if verbose_requested:
            payload.update(routes._build_peer_snapshot())
        return jsonify(payload)

    @app.route("/peers/add", methods=["POST"])
    @validate_request(routes.request_validator, PeerAddInput)
    def add_peer() -> Tuple[Dict[str, str], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        model = getattr(request, "validated_model", None)
        if model is None:
            return routes._error_response("Invalid peer payload", status=400, code="invalid_payload")

        node.add_peer(model.url)
        return routes._success_response({"message": f"Peer {model.url} added"})

    @app.route("/sync", methods=["POST"])
    def sync_blockchain() -> Dict[str, Any]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        synced = node.sync_with_network()
        return jsonify({"synced": synced, "chain_length": len(routes.blockchain.chain)})
