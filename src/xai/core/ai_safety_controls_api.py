"""
XAI Blockchain - AI Safety Controls API

REST API endpoints for emergency stop and AI control mechanisms.
Users can instantly cancel AI operations at multiple levels.
"""

from flask import request, jsonify
from xai.core.ai_safety_controls import StopReason, AISafetyLevel


def add_safety_control_routes(app, node):
    """
    Add AI safety control API endpoints to the node

    Args:
        app: Flask application
        node: IntegratedXAINode instance
    """

    safety = node.safety_controls

    # ===== PERSONAL AI CONTROLS =====

    @app.route("/ai/cancel-request/<request_id>", methods=["POST"])
    def cancel_personal_ai_request(request_id):
        """
        Cancel a Personal AI request immediately

        POST /ai/cancel-request/<request_id>
        {
            "user_address": "XAI1a2b3c..."
        }
        """
        try:
            data = request.get_json()
            user_address = data.get("user_address")

            if not user_address:
                return jsonify({"error": "user_address required"}), 400

            result = safety.cancel_personal_ai_request(request_id, user_address)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/request-status/<request_id>", methods=["GET"])
    def check_request_status(request_id):
        """
        Check if a Personal AI request is cancelled

        GET /ai/request-status/<request_id>
        """
        try:
            is_cancelled = safety.is_request_cancelled(request_id)

            return jsonify({"request_id": request_id, "is_cancelled": is_cancelled}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ===== TRADING BOT CONTROLS =====

    @app.route("/ai/emergency-stop/trading-bot", methods=["POST"])
    def emergency_stop_trading_bot():
        """
        Emergency stop for trading bot (instant)

        POST /ai/emergency-stop/trading-bot
        {
            "user_address": "XAI1a2b3c..."
        }
        """
        try:
            data = request.get_json()
            user_address = data.get("user_address")

            if not user_address:
                return jsonify({"error": "user_address required"}), 400

            result = safety.emergency_stop_trading_bot(user_address)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/stop-all-trading-bots", methods=["POST"])
    def stop_all_trading_bots():
        """
        Stop ALL trading bots (emergency use only)

        POST /ai/stop-all-trading-bots
        {
            "reason": "security_threat|emergency|error_threshold",
            "activator": "system|address"
        }

        Requires authorization
        """
        try:
            data = request.get_json()
            reason_str = data.get("reason", "emergency")

            # Convert string to StopReason enum
            try:
                reason = StopReason[reason_str.upper()]
            except KeyError:
                reason = StopReason.EMERGENCY

            result = safety.stop_all_trading_bots(reason)

            return jsonify(result), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ===== GOVERNANCE AI CONTROLS =====

    @app.route("/ai/pause-governance-task/<task_id>", methods=["POST"])
    def pause_governance_task(task_id):
        """
        Pause a Governance AI task

        POST /ai/pause-governance-task/<task_id>
        {
            "pauser": "XAI1a2b3c..."
        }

        Requires authorization (governance system)
        """
        try:
            data = request.get_json()
            pauser = data.get("pauser", "system")

            result = safety.pause_governance_task(task_id, pauser)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/resume-governance-task/<task_id>", methods=["POST"])
    def resume_governance_task(task_id):
        """
        Resume a paused Governance AI task

        POST /ai/resume-governance-task/<task_id>
        """
        try:
            result = safety.resume_governance_task(task_id)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/governance-task-status/<task_id>", methods=["GET"])
    def check_governance_task_status(task_id):
        """
        Check if Governance AI task is paused

        GET /ai/governance-task-status/<task_id>
        """
        try:
            is_paused = safety.is_task_paused(task_id)

            return jsonify({"task_id": task_id, "is_paused": is_paused}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ===== GLOBAL EMERGENCY STOP =====

    @app.route("/ai/emergency-stop/global", methods=["POST"])
    def activate_global_emergency_stop():
        """
        🚨 GLOBAL EMERGENCY STOP - Halt ALL AI operations

        POST /ai/emergency-stop/global
        {
            "reason": "security_threat|emergency|error_threshold",
            "details": "Description of why emergency stop activated",
            "activator": "system|address"
        }

        CRITICAL: This stops ALL AI operations immediately:
        - All Personal AI requests cancelled
        - All Trading Bots stopped
        - All Governance AI tasks paused

        Use only for:
        - Security threats
        - Critical bugs
        - Unexpected AI behavior
        - Community emergency vote

        Requires authorization
        """
        try:
            data = request.get_json()

            reason_str = data.get("reason", "emergency")
            details = data.get("details", "Emergency stop activated via API")
            activator = data.get("activator", "system")

            # Convert string to StopReason enum
            try:
                reason = StopReason[reason_str.upper()]
            except KeyError:
                reason = StopReason.EMERGENCY

            result = safety.activate_emergency_stop(reason, details, activator)

            return jsonify(result), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/emergency-stop/deactivate", methods=["POST"])
    def deactivate_global_emergency_stop():
        """
        Deactivate global emergency stop

        POST /ai/emergency-stop/deactivate
        {
            "deactivator": "system|address"
        }

        Requires authorization
        """
        try:
            data = request.get_json()
            deactivator = data.get("deactivator", "system")

            result = safety.deactivate_emergency_stop(deactivator)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/safety-level", methods=["POST"])
    def set_safety_level():
        """
        Set global AI safety level

        POST /ai/safety-level
        {
            "level": "normal|caution|restricted|emergency_stop|lockdown",
            "setter": "system|address"
        }

        Levels:
        - NORMAL: Normal AI operations
        - CAUTION: Elevated monitoring
        - RESTRICTED: Limited AI operations
        - EMERGENCY_STOP: All AI stopped
        - LOCKDOWN: All AI disabled, manual only

        Requires authorization
        """
        try:
            data = request.get_json()

            level_str = data.get("level", "normal")
            setter = data.get("setter", "system")

            # Convert string to AISafetyLevel enum
            try:
                level = AISafetyLevel[level_str.upper()]
            except KeyError:
                return jsonify({"error": "Invalid safety level"}), 400

            result = safety.set_safety_level(level, setter)

            return jsonify(result), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ===== STATUS & MONITORING =====

    @app.route("/ai/safety-status", methods=["GET"])
    def get_safety_status():
        """
        Get current AI safety status

        GET /ai/safety-status

        Returns:
        - Current safety level
        - Emergency stop status
        - Active operations counts
        - Statistics
        """
        try:
            status = safety.get_status()
            return jsonify(status), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/active-operations", methods=["GET"])
    def get_active_operations():
        """
        Get list of all active AI operations

        GET /ai/active-operations

        Returns detailed list of:
        - Personal AI requests (running)
        - Governance tasks (running)
        - Trading bots (active)
        """
        try:
            operations = safety.get_active_operations()
            return jsonify(operations), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/safety-callers", methods=["GET"])
    def list_safety_callers():
        """List all authorized safety-level callers"""

        try:
            callers = list(safety.authorized_callers)
            return jsonify({"authorized_callers": callers}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/safety-callers", methods=["POST"])
    def add_safety_caller():
        """Authorize a new safety-level caller"""

        try:
            data = request.get_json()
            identifier = data.get("identifier") if data else None

            result = safety.authorize_safety_caller(identifier)

            if result.get("success"):
                return jsonify(result), 200
            return jsonify(result), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/ai/safety-callers/<identifier>", methods=["DELETE"])
    def remove_safety_caller(identifier):
        """Revoke a safety-level caller"""

        try:
            result = safety.revoke_safety_caller(identifier)

            if result.get("success"):
                return jsonify(result), 200
            return jsonify(result), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    print("✅ AI Safety Control API endpoints added:")
    print("   • POST   /ai/cancel-request/<request_id>")
    print("   • GET    /ai/request-status/<request_id>")
    print("   • POST   /ai/emergency-stop/trading-bot")
    print("   • POST   /ai/stop-all-trading-bots")
    print("   • POST   /ai/pause-governance-task/<task_id>")
    print("   • POST   /ai/resume-governance-task/<task_id>")
    print("   • GET    /ai/governance-task-status/<task_id>")
    print("   • POST   /ai/emergency-stop/global")
    print("   • POST   /ai/emergency-stop/deactivate")
    print("   • POST   /ai/safety-level")
    print("   • GET    /ai/safety-status")
    print("   • GET    /ai/active-operations")
    print("   • GET    /ai/safety-callers")
    print("   • POST   /ai/safety-callers")
    print("   • DELETE /ai/safety-callers/<identifier>")
