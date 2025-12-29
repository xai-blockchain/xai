from __future__ import annotations

"""
XAI Blockchain - AI Safety Controls API

REST API endpoints for emergency stop and AI control mechanisms.
Users can instantly cancel AI operations at multiple levels.
"""

import logging
from typing import Any

from flask import jsonify, request

from xai.core.security.ai_safety_controls import AISafetyLevel, StopReason

logger = logging.getLogger(__name__)

def _json_body() -> dict[str, Any]:
    """
    Parse JSON body defensively and return a dict or raise ValueError.
    """
    data = request.get_json(silent=True)
    if data is None:
        raise ValueError("Invalid or missing JSON payload")
    if not isinstance(data, dict):
        raise ValueError("Malformed JSON payload")
    return data

def _server_error(exc: Exception, event: str) -> tuple[Any, int]:
    logger.exception("AI safety control failed: %s", exc, extra={"event": event})
    return jsonify({"error": str(exc)}), 500

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
    def cancel_personal_ai_request(request_id: str) -> tuple[Any, int]:
        """
        Cancel a Personal AI request immediately

        POST /ai/cancel-request/<request_id>
        {
            "user_address": "XAI1a2b3c..."
        }
        """
        try:
            data = _json_body()
            user_address = data.get("user_address")

            if not user_address:
                return jsonify({"error": "user_address required"}), 400

            result = safety.cancel_personal_ai_request(request_id, user_address)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ValueError as exc:
            logger.warning(
                "ValueError in cancel_personal_ai_request",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "cancel_personal_ai_request"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.cancel_personal_ai_request_failed")

    @app.route("/ai/request-status/<request_id>", methods=["GET"])
    def check_request_status(request_id: str) -> tuple[Any, int]:
        """
        Check if a Personal AI request is cancelled

        GET /ai/request-status/<request_id>
        """
        try:
            is_cancelled = safety.is_request_cancelled(request_id)

            return jsonify({"request_id": request_id, "is_cancelled": is_cancelled}), 200

        except ValueError as exc:
            logger.warning(
                "ValueError in check_request_status",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "check_request_status"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.request_status_failed")

    # ===== TRADING BOT CONTROLS =====

    @app.route("/ai/emergency-stop/trading-bot", methods=["POST"])
    def emergency_stop_trading_bot() -> tuple[Any, int]:
        """
        Emergency stop for trading bot (instant)

        POST /ai/emergency-stop/trading-bot
        {
            "user_address": "XAI1a2b3c..."
        }
        """
        try:
            data = _json_body()
            user_address = data.get("user_address")

            if not user_address:
                return jsonify({"error": "user_address required"}), 400

            result = safety.emergency_stop_trading_bot(user_address)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ValueError as exc:
            logger.warning(
                "ValueError in emergency_stop_trading_bot",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "emergency_stop_trading_bot"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.emergency_stop_trading_bot_failed")

    @app.route("/ai/stop-all-trading-bots", methods=["POST"])
    def stop_all_trading_bots() -> tuple[Any, int]:
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
            data = _json_body()
            reason_str = data.get("reason", "emergency")

            # Convert string to StopReason enum
            try:
                reason = StopReason[reason_str.upper()]
            except KeyError:
                reason = StopReason.EMERGENCY

            result = safety.stop_all_trading_bots(reason)

            return jsonify(result), 200

        except ValueError as exc:
            logger.warning(
                "ValueError in stop_all_trading_bots",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "stop_all_trading_bots"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.stop_all_trading_bots_failed")

    # ===== GOVERNANCE AI CONTROLS =====

    @app.route("/ai/pause-governance-task/<task_id>", methods=["POST"])
    def pause_governance_task(task_id: str) -> tuple[Any, int]:
        """
        Pause a Governance AI task

        POST /ai/pause-governance-task/<task_id>
        {
            "pauser": "XAI1a2b3c..."
        }

        Requires authorization (governance system)
        """
        try:
            data = _json_body()
            pauser = data.get("pauser", "system")

            result = safety.pause_governance_task(task_id, pauser)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ValueError as exc:
            logger.warning(
                "ValueError in pause_governance_task",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "pause_governance_task"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.pause_governance_task_failed")

    @app.route("/ai/resume-governance-task/<task_id>", methods=["POST"])
    def resume_governance_task(task_id: str) -> tuple[Any, int]:
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

        except ValueError as exc:
            logger.warning(
                "ValueError in resume_governance_task",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "resume_governance_task"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.resume_governance_task_failed")

    @app.route("/ai/governance-task-status/<task_id>", methods=["GET"])
    def check_governance_task_status(task_id: str) -> tuple[Any, int]:
        """
        Check if Governance AI task is paused

        GET /ai/governance-task-status/<task_id>
        """
        try:
            is_paused = safety.is_task_paused(task_id)

            return jsonify({"task_id": task_id, "is_paused": is_paused}), 200

        except ValueError as exc:
            logger.warning(
                "ValueError in check_governance_task_status",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "check_governance_task_status"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.governance_task_status_failed")

    # ===== GLOBAL EMERGENCY STOP =====

    @app.route("/ai/emergency-stop/global", methods=["POST"])
    def activate_global_emergency_stop() -> tuple[Any, int]:
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
            data = _json_body()

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

        except ValueError as exc:
            logger.warning(
                "ValueError in activate_global_emergency_stop",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "activate_global_emergency_stop"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.emergency_stop_global_failed")

    @app.route("/ai/emergency-stop/deactivate", methods=["POST"])
    def deactivate_global_emergency_stop() -> tuple[Any, int]:
        """
        Deactivate global emergency stop

        POST /ai/emergency-stop/deactivate
        {
            "deactivator": "system|address"
        }

        Requires authorization
        """
        try:
            data = _json_body()
            deactivator = data.get("deactivator", "system")

            result = safety.deactivate_emergency_stop(deactivator)

            if result["success"]:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except ValueError as exc:
            logger.warning(
                "ValueError in deactivate_global_emergency_stop",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "deactivate_global_emergency_stop"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.emergency_stop_deactivate_failed")

    @app.route("/ai/safety-level", methods=["POST"])
    def set_safety_level() -> tuple[Any, int]:
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
            data = _json_body()

            level_str = data.get("level", "normal")
            setter = data.get("setter", "system")

            # Convert string to AISafetyLevel enum
            try:
                level = AISafetyLevel[level_str.upper()]
            except KeyError:
                return jsonify({"error": "Invalid safety level"}), 400

            result = safety.set_safety_level(level, setter)

            return jsonify(result), 200

        except ValueError as exc:
            logger.warning(
                "ValueError in set_safety_level",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "set_safety_level"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.set_safety_level_failed")

    # ===== STATUS & MONITORING =====

    @app.route("/ai/safety-status", methods=["GET"])
    def get_safety_status() -> tuple[Any, int]:
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

        except ValueError as exc:
            logger.warning(
                "ValueError in get_safety_status",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "get_safety_status"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.safety_status_failed")

    @app.route("/ai/active-operations", methods=["GET"])
    def get_active_operations() -> tuple[Any, int]:
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

        except ValueError as exc:
            logger.warning(
                "ValueError in get_active_operations",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "get_active_operations"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.active_operations_failed")

    @app.route("/ai/safety-callers", methods=["GET"])
    def list_safety_callers() -> tuple[Any, int]:
        """List all authorized safety-level callers"""

        try:
            callers = list(safety.authorized_callers)
            return jsonify({"authorized_callers": callers}), 200
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            logger.warning(
                "Exception in list_safety_callers",
                extra={
                    "error_type": "Exception",
                    "error": str(exc),
                    "function": "list_safety_callers"
                }
            )
            return _server_error(exc, "ai.list_safety_callers_failed")

    @app.route("/ai/safety-callers", methods=["POST"])
    def add_safety_caller() -> tuple[Any, int]:
        """Authorize a new safety-level caller"""

        try:
            data = _json_body()
            identifier = data.get("identifier")

            result = safety.authorize_safety_caller(identifier)

            if result.get("success"):
                return jsonify(result), 200
            return jsonify(result), 400
        except ValueError as exc:
            logger.warning(
                "ValueError in add_safety_caller",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "add_safety_caller"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.add_safety_caller_failed")

    @app.route("/ai/safety-callers/<identifier>", methods=["DELETE"])
    def remove_safety_caller(identifier: str) -> tuple[Any, int]:
        """Revoke a safety-level caller"""

        try:
            result = safety.revoke_safety_caller(identifier)

            if result.get("success"):
                return jsonify(result), 200
            return jsonify(result), 400
        except ValueError as exc:
            logger.warning(
                "ValueError in remove_safety_caller",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "remove_safety_caller"
                }
            )
            return jsonify({"error": str(exc)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            return _server_error(exc, "ai.remove_safety_caller_failed")

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
