"""
AI and Personal AI API Handler

Handles all AI-related API endpoints including:
- Personal AI assistant operations
- Atomic swaps with AI
- Smart contract creation and deployment
- Transaction optimization
- Blockchain analysis
- Wallet analysis and recovery
- Node setup recommendations
- Liquidity pool alerts
"""

import json
import logging
from typing import Dict, Any, Tuple, Optional
from flask import Flask, jsonify, request, Response, stream_with_context
from xai.core.security_validation import ValidationError

logger = logging.getLogger(__name__)


class AIAPIHandler:
    """Handles all AI and Personal AI-related API endpoints."""

    def __init__(self, node: Any, app: Flask):
        """
        Initialize AI API Handler.

        Args:
            node: BlockchainNode instance
            app: Flask application instance
        """
        self.node = node
        self.app = app

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all AI routes."""

        @self.app.route("/personal-ai/atomic-swap", methods=["POST"])
        def personal_atomic_swap() -> Tuple[Dict[str, Any], int]:
            """Execute atomic swap with AI."""
            return self.personal_atomic_swap_handler()

        @self.app.route("/personal-ai/smart-contract/create", methods=["POST"])
        def personal_contract_create() -> Tuple[Dict[str, Any], int]:
            """Create smart contract with AI."""
            return self.personal_contract_create_handler()

        @self.app.route("/personal-ai/smart-contract/deploy", methods=["POST"])
        def personal_contract_deploy() -> Tuple[Dict[str, Any], int]:
            """Deploy smart contract with AI."""
            return self.personal_contract_deploy_handler()

        @self.app.route("/personal-ai/transaction/optimize", methods=["POST"])
        def personal_transaction_optimize() -> Tuple[Dict[str, Any], int]:
            """Optimize transaction with AI."""
            return self.personal_transaction_optimize_handler()

        @self.app.route("/personal-ai/analyze", methods=["POST"])
        def personal_analyze() -> Tuple[Dict[str, Any], int]:
            """Analyze blockchain with AI."""
            return self.personal_analyze_handler()

        @self.app.route("/personal-ai/wallet/analyze", methods=["POST"])
        def personal_wallet_analyze() -> Tuple[Dict[str, Any], int]:
            """Analyze wallet with AI."""
            return self.personal_wallet_analyze_handler()

        @self.app.route("/personal-ai/wallet/recovery", methods=["POST"])
        def personal_wallet_recovery() -> Tuple[Dict[str, Any], int]:
            """Get wallet recovery advice."""
            return self.personal_wallet_recovery_handler()

        @self.app.route("/personal-ai/node/setup", methods=["POST"])
        def personal_node_setup() -> Tuple[Dict[str, Any], int]:
            """Get node setup recommendations."""
            return self.personal_node_setup_handler()

        @self.app.route("/personal-ai/liquidity/alert", methods=["POST"])
        def personal_liquidity_alert() -> Tuple[Dict[str, Any], int]:
            """Handle liquidity pool alert."""
            return self.personal_liquidity_alert_handler()

        @self.app.route("/personal-ai/assistants", methods=["GET"])
        def personal_ai_assistants() -> Tuple[Dict[str, Any], int]:
            """List available AI assistants."""
            return self.personal_ai_assistants_handler()

        @self.app.route("/personal-ai/stream", methods=["POST"])
        def personal_ai_stream() -> Response:
            """Stream AI response chunks."""
            return self.personal_ai_stream_handler()

        @self.app.route("/questioning/submit", methods=["POST"])
        def submit_question() -> Tuple[Dict[str, Any], int]:
            """AI submits question to node operators."""
            return self.submit_question_handler()

        @self.app.route("/questioning/answer", methods=["POST"])
        def submit_answer() -> Tuple[Dict[str, Any], int]:
            """Node operator submits answer."""
            return self.submit_answer_handler()

        @self.app.route("/questioning/pending", methods=["GET"])
        def get_pending_questions() -> Tuple[Dict[str, Any], int]:
            """Get questions needing answers."""
            return self.get_pending_questions_handler()

    def personal_atomic_swap_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle atomic swap with AI assistance.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        try:
            ctx = self._personal_ai_context()
            if not ctx["success"]:
                return jsonify(ctx), 400

            payload = request.get_json(silent=True) or {}
            swap_details = payload.get("swap_details") or payload

            result = ctx["personal_ai"].execute_atomic_swap_with_ai(
                user_address=ctx["user_address"],
                ai_provider=ctx["ai_provider"],
                ai_model=ctx["ai_model"],
                user_api_key=ctx["user_api_key"],
                swap_details=swap_details,
                assistant_name=ctx.get("assistant_name"),
            )
            return self._personal_ai_response(result)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(
                "Personal AI atomic swap operation failed",
                error_type=type(e).__name__,
                error=str(e),
                function="personal_atomic_swap_handler",
            )
            return jsonify({
                "success": False,
                "error": "OPERATION_FAILED",
                "message": str(e)
            }), 500

    def personal_contract_create_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle smart contract creation with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}
        description = payload.get("contract_description") or payload.get("description", "")
        contract_type = payload.get("contract_type")

        result = ctx["personal_ai"].create_smart_contract_with_ai(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            contract_description=description,
            contract_type=contract_type,
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_contract_deploy_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle smart contract deployment with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}

        result = ctx["personal_ai"].deploy_smart_contract_with_ai(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            contract_code=payload.get("contract_code", ""),
            constructor_params=payload.get("constructor_params"),
            testnet=payload.get("testnet", True),
            signature=payload.get("signature"),
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_transaction_optimize_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle transaction optimization with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}
        transaction = payload.get("transaction") or payload

        if not transaction:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "transaction required",
                        "message": "Provide a transaction payload",
                    }
                ),
                400,
            )

        result = ctx["personal_ai"].optimize_transaction_with_ai(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            transaction=transaction,
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_analyze_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle blockchain analysis with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}
        query = payload.get("query")

        if not query:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "query required",
                        "message": "Provide a query to analyze",
                    }
                ),
                400,
            )

        result = ctx["personal_ai"].analyze_blockchain_with_ai(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            query=query,
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_wallet_analyze_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle wallet analysis with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}
        analysis_type = payload.get("analysis_type", "portfolio_optimization")

        result = ctx["personal_ai"].wallet_analysis_with_ai(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            analysis_type=analysis_type,
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_wallet_recovery_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle wallet recovery advice with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}
        recovery_details = payload.get("recovery_details") or payload
        guardians = recovery_details.get("guardians", [])

        for guardian in guardians:
            try:
                self.node.validator.validate_address(guardian)
            except ValidationError as ve:
                logger.warning(
                    "Invalid guardian address in wallet recovery",
                    error_type="ValidationError",
                    error=str(ve),
                    guardian=guardian,
                    function="personal_wallet_recovery_handler",
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "INVALID_GUARDIAN_ADDRESS",
                            "message": str(ve),
                        }
                    ),
                    400,
                )

        result = ctx["personal_ai"].wallet_recovery_advice(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            recovery_details=recovery_details,
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_node_setup_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle node setup recommendations with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}
        setup_request = payload.get("setup_request") or payload
        region = setup_request.get("preferred_region", "")

        try:
            if region:
                self.node.validator.validate_string(region, "preferred_region", max_length=100)
        except ValidationError as ve:
            logger.warning(
                "Invalid region in node setup request",
                error_type="ValidationError",
                error=str(ve),
                region=region,
                function="personal_node_setup_handler",
            )
            return (
                jsonify({"success": False, "error": "INVALID_REGION", "message": str(ve)}),
                400,
            )

        result = ctx["personal_ai"].node_setup_recommendations(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            setup_request=setup_request,
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_liquidity_alert_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle liquidity pool alert with AI.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return jsonify(ctx), 400

        payload = request.get_json(silent=True) or {}
        pool_name = payload.get("pool_name")

        if not pool_name:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "pool_name required",
                        "message": "Specify the liquidity pool name",
                    }
                ),
                400,
            )

        try:
            self.node.validator.validate_string(pool_name, "pool_name", max_length=120)
        except ValidationError as ve:
            logger.warning(
                "Invalid pool name in liquidity pool alert",
                error_type="ValidationError",
                error=str(ve),
                pool_name=pool_name,
                function="personal_liquidity_pool_alerts_handler",
            )
            return (
                jsonify({"success": False, "error": "INVALID_POOL_NAME", "message": str(ve)}),
                400,
            )

        alert_details = payload.get("alert_details") or payload

        result = ctx["personal_ai"].liquidity_alert_response(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            pool_name=pool_name,
            alert_details=alert_details,
            assistant_name=ctx.get("assistant_name"),
        )
        return self._personal_ai_response(result)

    def personal_ai_assistants_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle listing of available AI assistants.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        assistant_layer = getattr(self.node, "personal_ai", None)
        if not assistant_layer:
            return jsonify({"success": False, "error": "PERSONAL_AI_DISABLED"}), 503

        return (
            jsonify({"success": True, "assistants": assistant_layer.list_micro_assistants()}),
            200,
        )

    def personal_ai_stream_handler(self) -> Response:
        """Stream personal AI output via Server-Sent Events."""
        ctx = self._personal_ai_context()
        if not ctx["success"]:
            return Response(
                json.dumps(ctx), status=400, mimetype="application/json"
            )

        payload = request.get_json(silent=True) or {}
        prompt = payload.get("prompt")
        if not prompt:
            return Response(
                json.dumps(
                    {
                        "success": False,
                        "error": "PROMPT_REQUIRED",
                        "message": "Provide a prompt to stream",
                    }
                ),
                status=400,
                mimetype="application/json",
            )

        result = ctx["personal_ai"].stream_prompt_with_ai(
            user_address=ctx["user_address"],
            ai_provider=ctx["ai_provider"],
            ai_model=ctx["ai_model"],
            user_api_key=ctx["user_api_key"],
            prompt=prompt,
            assistant_name=ctx.get("assistant_name"),
        )

        if not result.get("success"):
            return Response(
                json.dumps(result), status=400, mimetype="application/json"
            )

        return Response(
            stream_with_context(result["stream"]),
            mimetype="text/event-stream",
        )

    def submit_question_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle AI question submission to node operators.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        import hashlib
        import time

        data = request.json

        question_id = hashlib.sha256(
            f"{time.time()}{data.get('question_text')}".encode()
        ).hexdigest()[:16]

        # This would normally broadcast via WebSocket, but we don't have access here
        # The main extensions class will need to handle this

        return (
            jsonify(
                {
                    "success": True,
                    "question_id": question_id,
                    "status": "open_for_voting",
                    "voting_opened_at": time.time(),
                }
            ),
            200,
        )

    def submit_answer_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle node operator answer submission.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json

        # In production, integrate with ai_node_operator_questioning
        return (
            jsonify(
                {
                    "success": True,
                    "question_id": data.get("question_id"),
                    "total_votes": 18,
                    "min_required": 25,
                    "consensus_reached": False,
                }
            ),
            200,
        )

    def get_pending_questions_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle pending questions retrieval.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        # In production, query from questioning system
        return jsonify({"count": 0, "questions": []}), 200

    def _personal_ai_context(self) -> Dict[str, Any]:
        """
        Extract and validate Personal AI context from request headers.

        Returns:
            Dictionary containing validated context or error information
        """
        headers = request.headers
        user_address = headers.get("X-User-Address")
        ai_provider = headers.get("X-AI-Provider", "anthropic")
        ai_model = headers.get("X-AI-Model", "claude-opus-4")
        user_api_key = headers.get("X-User-API-Key")
        assistant_name = headers.get("X-AI-Assistant", "").strip()

        if not all([user_address, ai_provider, ai_model, user_api_key]):
            missing = [
                key
                for key, value in [
                    ("X-User-Address", user_address),
                    ("X-AI-Provider", ai_provider),
                    ("X-AI-Model", ai_model),
                    ("X-User-API-Key", user_api_key),
                ]
                if not value
            ]
            return {
                "success": False,
                "error": "MISSING_HEADERS",
                "message": f'Missing headers: {", ".join(missing)}',
            }

        try:
            self.node.validator.validate_address(user_address)
        except ValidationError as ve:
            logger.warning(
                "Invalid user address in personal AI context",
                error_type="ValidationError",
                error=str(ve),
                user_address=user_address,
                function="_personal_ai_context",
            )
            return {"success": False, "error": "INVALID_ADDRESS", "message": str(ve)}

        personal_ai = getattr(self.node, "personal_ai", None)
        if not personal_ai:
            return {
                "success": False,
                "error": "PERSONAL_AI_DISABLED",
                "message": "Personal AI assistant is not configured on this node.",
            }

        return {
            "success": True,
            "personal_ai": personal_ai,
            "user_address": user_address,
            "ai_provider": ai_provider,
            "ai_model": ai_model,
            "user_api_key": user_api_key,
            "assistant_name": assistant_name or None,
        }

    def _personal_ai_response(self, result: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Format Personal AI response.

        Args:
            result: Result from Personal AI operation

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        status = 200 if result.get("success") else 400
        return jsonify(result), status
