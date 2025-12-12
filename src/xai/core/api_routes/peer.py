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
        """Get list of connected peers.

        Returns basic peer count and list by default. With verbose=true,
        includes detailed snapshot of peer connections and network state.

        Query Parameters:
            verbose (str, optional): Set to "true", "1", "yes", or "on" for detailed info

        Returns:
            Dict containing:
                - count (int): Number of connected peers
                - peers (list): List of peer URLs
                - verbose (bool): Whether verbose mode was requested
                - Additional fields if verbose=true from _build_peer_snapshot()
        """
        verbose = request.args.get("verbose", "false")
        verbose_requested = str(verbose).lower() in {"1", "true", "yes", "on"}
        payload: Dict[str, Any] = {"count": len(node.peers), "peers": list(node.peers), "verbose": verbose_requested}
        if verbose_requested:
            payload.update(routes._build_peer_snapshot())
        return jsonify(payload)

    @app.route("/peers/add", methods=["POST"])
    @validate_request(routes.request_validator, PeerAddInput)
    def add_peer() -> Tuple[Dict[str, str], int]:
        """Add a new peer to the network (admin only).

        Adds a peer node to this node's peer list for blockchain synchronization
        and transaction broadcasting.

        This endpoint requires API authentication.

        Request Body (PeerAddInput):
            {
                "url": "http://peer-node:port"
            }

        Returns:
            Tuple containing (response_dict, http_status_code) where:
                - response_dict: Success message with peer URL
                - http_status_code: 200 on success, 400/401 on error

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
            ValidationError: If peer URL is invalid (400).
        """
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
        """Trigger blockchain synchronization with network peers.

        Forces the node to sync its blockchain with all connected peers,
        fetching any missing blocks and resolving chain conflicts.

        This endpoint requires API authentication.

        Returns:
            Dict containing:
                - synced (bool): Whether sync operation completed successfully
                - chain_length (int): Current blockchain length after sync

        Raises:
            AuthenticationError: If API key is missing or invalid (401).
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        synced = node.sync_with_network()
        return jsonify({"synced": synced, "chain_length": len(routes.blockchain.chain)})
