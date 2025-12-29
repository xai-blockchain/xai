"""
Webhook API Routes

Provides endpoints for webhook management:
- Registration and unregistration
- Event subscription updates
- Webhook testing/verification
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from flask import jsonify, request

from xai.core.api.webhook_manager import WebhookEvent, get_webhook_manager

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_webhook_routes(routes: "NodeAPIRoutes") -> None:
    """Register webhook management routes."""
    app = routes.app

    @app.route("/api/v1/webhooks/register", methods=["POST"])
    def register_webhook() -> tuple[dict[str, Any], int]:
        """
        Register a new webhook for event notifications.

        Request body:
        {
            "url": "https://example.com/webhook",
            "events": ["new_block", "new_transaction"],
            "owner": "XAI...",
            "metadata": {}  // optional
        }

        Supported events:
        - new_block: New block mined
        - new_transaction: Transaction added to mempool
        - governance_vote: Vote cast on proposal
        - proposal_created: New governance proposal
        - proposal_executed: Proposal execution completed
        - balance_change: Address balance changed
        - contract_deployed: New smart contract deployed
        - contract_called: Smart contract invoked
        - mining_reward: Mining reward received
        - ai_task_completed: AI compute task finished

        Returns:
            {
                "success": true,
                "webhook_id": "wh_...",
                "secret": "...",  // Use for signature verification
                "events": ["new_block", ...]
            }
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        data = request.get_json(silent=True) or {}

        url = data.get("url")
        events = data.get("events", [])
        owner = data.get("owner")
        metadata = data.get("metadata", {})

        if not url:
            return routes._error_response(
                "URL is required",
                status=400,
                code="missing_url",
            )

        if not events:
            return routes._error_response(
                "At least one event type is required",
                status=400,
                code="missing_events",
            )

        if not owner:
            return routes._error_response(
                "Owner address is required",
                status=400,
                code="missing_owner",
            )

        manager = get_webhook_manager()
        if not manager:
            return routes._error_response(
                "Webhook service unavailable",
                status=503,
                code="service_unavailable",
            )

        result = manager.register_webhook(
            url=url,
            events=events,
            owner=owner,
            metadata=metadata,
        )

        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    @app.route("/api/v1/webhooks/<webhook_id>", methods=["GET"])
    def get_webhook(webhook_id: str) -> tuple[dict[str, Any], int]:
        """
        Get webhook details.

        Path Parameters:
            webhook_id: Webhook ID

        Query Parameters:
            owner: Owner address (required for authentication)

        Returns:
            Webhook configuration and status
        """
        owner = request.args.get("owner")

        manager = get_webhook_manager()
        if not manager:
            return routes._error_response(
                "Webhook service unavailable",
                status=503,
                code="service_unavailable",
            )

        webhook = manager.get_webhook(webhook_id, owner)

        if not webhook:
            return routes._error_response(
                "Webhook not found",
                status=404,
                code="not_found",
            )

        return jsonify({"success": True, "webhook": webhook}), 200

    @app.route("/api/v1/webhooks/<webhook_id>", methods=["DELETE"])
    def delete_webhook(webhook_id: str) -> tuple[dict[str, Any], int]:
        """
        Delete a webhook registration.

        Path Parameters:
            webhook_id: Webhook ID to delete

        Request body:
        {
            "owner": "XAI..."  // Must match registration
        }

        Returns:
            Deletion confirmation
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        data = request.get_json(silent=True) or {}
        owner = data.get("owner")

        if not owner:
            return routes._error_response(
                "Owner address required",
                status=400,
                code="missing_owner",
            )

        manager = get_webhook_manager()
        if not manager:
            return routes._error_response(
                "Webhook service unavailable",
                status=503,
                code="service_unavailable",
            )

        result = manager.unregister_webhook(webhook_id, owner)

        if result.get("success"):
            return jsonify(result), 200
        else:
            error = result.get("error", {})
            status = 404 if error.get("code") == "not_found" else 403
            return jsonify(result), status

    @app.route("/api/v1/webhooks/<webhook_id>", methods=["PATCH"])
    def update_webhook(webhook_id: str) -> tuple[dict[str, Any], int]:
        """
        Update webhook configuration.

        Path Parameters:
            webhook_id: Webhook ID to update

        Request body:
        {
            "owner": "XAI...",  // Required
            "events": ["new_block"],  // Optional - new event list
            "active": true  // Optional - enable/disable
        }

        Returns:
            Updated webhook configuration
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        data = request.get_json(silent=True) or {}
        owner = data.get("owner")
        events = data.get("events")
        active = data.get("active")

        if not owner:
            return routes._error_response(
                "Owner address required",
                status=400,
                code="missing_owner",
            )

        manager = get_webhook_manager()
        if not manager:
            return routes._error_response(
                "Webhook service unavailable",
                status=503,
                code="service_unavailable",
            )

        result = manager.update_webhook(
            webhook_id=webhook_id,
            owner=owner,
            events=events,
            active=active,
        )

        if result.get("success"):
            return jsonify(result), 200
        else:
            error = result.get("error", {})
            status = 404 if error.get("code") == "not_found" else 403
            return jsonify(result), status

    @app.route("/api/v1/webhooks", methods=["GET"])
    def list_webhooks() -> tuple[dict[str, Any], int]:
        """
        List webhooks for an owner.

        Query Parameters:
            owner: Owner address to filter by

        Returns:
            List of webhook registrations
        """
        owner = request.args.get("owner")

        manager = get_webhook_manager()
        if not manager:
            return routes._error_response(
                "Webhook service unavailable",
                status=503,
                code="service_unavailable",
            )

        webhooks = manager.list_webhooks(owner)

        return (
            jsonify(
                {
                    "success": True,
                    "count": len(webhooks),
                    "webhooks": webhooks,
                }
            ),
            200,
        )

    @app.route("/api/v1/webhooks/events", methods=["GET"])
    def list_webhook_events() -> tuple[dict[str, Any], int]:
        """
        List available webhook event types.

        Returns:
            List of supported event types with descriptions
        """
        event_descriptions = {
            WebhookEvent.NEW_BLOCK.value: "Triggered when a new block is mined",
            WebhookEvent.NEW_TRANSACTION.value: "Triggered when a transaction enters the mempool",
            WebhookEvent.GOVERNANCE_VOTE.value: "Triggered when a vote is cast on a proposal",
            WebhookEvent.PROPOSAL_CREATED.value: "Triggered when a new governance proposal is created",
            WebhookEvent.PROPOSAL_EXECUTED.value: "Triggered when a proposal is executed",
            WebhookEvent.BALANCE_CHANGE.value: "Triggered when an address balance changes",
            WebhookEvent.CONTRACT_DEPLOYED.value: "Triggered when a smart contract is deployed",
            WebhookEvent.CONTRACT_CALLED.value: "Triggered when a smart contract is called",
            WebhookEvent.MINING_REWARD.value: "Triggered when a mining reward is received",
            WebhookEvent.AI_TASK_COMPLETED.value: "Triggered when an AI compute task completes",
        }

        events = [
            {"name": e.value, "description": event_descriptions.get(e.value, "")}
            for e in WebhookEvent
        ]

        return (
            jsonify(
                {
                    "success": True,
                    "events": events,
                }
            ),
            200,
        )

    @app.route("/api/v1/webhooks/<webhook_id>/test", methods=["POST"])
    def test_webhook(webhook_id: str) -> tuple[dict[str, Any], int]:
        """
        Send a test event to a webhook.

        Path Parameters:
            webhook_id: Webhook ID to test

        Request body:
        {
            "owner": "XAI...",
            "event": "new_block"  // Event type to simulate
        }

        Returns:
            Test delivery result
        """
        auth_error = routes._require_api_auth()
        if auth_error:
            return auth_error

        data = request.get_json(silent=True) or {}
        owner = data.get("owner")
        event_type = data.get("event", "new_block")

        if not owner:
            return routes._error_response(
                "Owner address required",
                status=400,
                code="missing_owner",
            )

        manager = get_webhook_manager()
        if not manager:
            return routes._error_response(
                "Webhook service unavailable",
                status=503,
                code="service_unavailable",
            )

        webhook = manager.get_webhook(webhook_id, owner)
        if not webhook:
            return routes._error_response(
                "Webhook not found or unauthorized",
                status=404,
                code="not_found",
            )

        # Create test payload
        test_payload = {
            "test": True,
            "event": event_type,
            "message": "This is a test webhook delivery",
            "webhook_id": webhook_id,
        }

        # Dispatch synchronously for testing
        registration = manager._webhooks.get(webhook_id)
        if registration:
            success = manager._deliver_webhook(
                registration,
                event_type,
                {"event": event_type, "data": test_payload},
            )
        else:
            success = False

        return (
            jsonify(
                {
                    "success": success,
                    "test": True,
                    "webhook_id": webhook_id,
                    "event": event_type,
                    "message": "Test delivery successful" if success else "Test delivery failed",
                }
            ),
            200 if success else 502,
        )

    @app.route("/api/v1/webhooks/<webhook_id>/stats", methods=["GET"])
    def webhook_stats(webhook_id: str) -> tuple[dict[str, Any], int]:
        """
        Get delivery statistics for a webhook.

        Path Parameters:
            webhook_id: Webhook ID

        Returns:
            Delivery statistics
        """
        manager = get_webhook_manager()
        if not manager:
            return routes._error_response(
                "Webhook service unavailable",
                status=503,
                code="service_unavailable",
            )

        stats = manager.get_delivery_stats(webhook_id)

        return jsonify({"success": True, "webhook_id": webhook_id, "stats": stats}), 200
