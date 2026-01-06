from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

from flask import request

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes


def _finality_manager(routes: "NodeAPIRoutes"):
    blockchain = getattr(routes, "blockchain", None)
    return getattr(blockchain, "finality_manager", None)


def register_finality_routes(routes: "NodeAPIRoutes") -> None:
    """Expose finality status and certificate endpoints."""
    app = routes.app

    @app.route("/finality/status", methods=["GET"])
    def finality_status() -> tuple[dict[str, Any], int]:
        manager = _finality_manager(routes)
        if manager is None:
            return routes._success_response(
                {
                    "finality_enabled": False,
                    "reason": "finality_manager_unavailable",
                }
            )

        lock = getattr(manager, "_lock", None)
        with lock if lock is not None else nullcontext():
            summary = manager.summarize()
            payload = {
                "finality_enabled": True,
                **summary,
                "total_power": manager.total_power,
                "quorum_power": manager.quorum_power,
                "quorum_threshold": getattr(
                    routes.blockchain, "_finality_quorum_threshold", None
                ),
                "pending_blocks": len(getattr(manager, "pending_votes", {})),
            }
        return routes._success_response(payload)

    @app.route("/finality/validators", methods=["GET"])
    def finality_validators() -> tuple[dict[str, Any], int]:
        manager = _finality_manager(routes)
        if manager is None:
            return routes._success_response(
                {"finality_enabled": False, "validators": [], "total_validators": 0}
            )

        lock = getattr(manager, "_lock", None)
        with lock if lock is not None else nullcontext():
            validators = [
                {
                    "address": v.address,
                    "public_key": v.public_key,
                    "voting_power": v.voting_power,
                }
                for v in manager.validators.values()
            ]
        return routes._success_response(
            {"finality_enabled": True, "validators": validators, "total_validators": len(validators)}
        )

    @app.route("/finality/certificates", methods=["GET"])
    def finality_certificates() -> tuple[dict[str, Any], int]:
        manager = _finality_manager(routes)
        if manager is None:
            return routes._success_response(
                {"finality_enabled": False, "certificates": [], "count": 0, "total": 0}
            )

        try:
            limit = int(request.args.get("limit", "20"))
        except (TypeError, ValueError):
            limit = 20
        limit = max(1, min(limit, 200))

        lock = getattr(manager, "_lock", None)
        with lock if lock is not None else nullcontext():
            certificates = sorted(
                manager.certificates_by_height.values(),
                key=lambda cert: cert.block_height,
                reverse=True,
            )
            sliced = [cert.to_dict() for cert in certificates[:limit]]
            total = len(manager.certificates_by_height)

        return routes._success_response(
            {
                "finality_enabled": True,
                "certificates": sliced,
                "count": len(sliced),
                "total": total,
            }
        )

    @app.route("/finality/vote", methods=["POST"])
    def finality_vote() -> tuple[dict[str, Any], int]:
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error
        paused = routes._reject_if_paused("finality_vote")
        if paused:
            return paused

        ok, err, payload = routes._verify_signed_peer_message()
        if not ok:
            return routes._error_response(
                "Unauthorized P2P message",
                status=401,
                code=f"p2p_{err}",
            )
        if not isinstance(payload, dict):
            return routes._error_response(
                "Invalid finality vote payload",
                status=400,
                code="invalid_payload",
            )

        validator_address = payload.get("validator_address") or payload.get("validator")
        signature = payload.get("signature")
        block_hash = payload.get("block_hash") or payload.get("hash")
        block_index = payload.get("block_index")

        if validator_address in (None, "") or signature in (None, ""):
            return routes._error_response(
                "Missing finality vote fields",
                status=400,
                code="invalid_payload",
                context={"missing": ["validator_address", "signature"]},
            )

        if block_hash in (None, "") and block_index is None:
            return routes._error_response(
                "Missing block reference for finality vote",
                status=400,
                code="invalid_payload",
                context={"missing": ["block_hash|block_index"]},
            )

        if block_index is not None:
            try:
                block_index = int(block_index)
            except (TypeError, ValueError):
                return routes._error_response(
                    "Invalid block_index in finality vote",
                    status=400,
                    code="invalid_payload",
                    context={"block_index": block_index},
                )

        try:
            result = routes.blockchain.submit_finality_vote(
                validator_address=str(validator_address),
                signature=str(signature),
                block_hash=str(block_hash) if block_hash not in (None, "") else None,
                block_index=block_index,
            )
        except ValueError as exc:
            return routes._error_response(
                str(exc),
                status=400,
                code="finality_vote_rejected",
            )
        except RuntimeError as exc:
            return routes._error_response(
                str(exc),
                status=503,
                code="finality_unavailable",
            )

        return routes._success_response(result)
