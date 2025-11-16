"""
Time Capsule API Endpoints

RESTful API for creating and managing time capsules
"""

from flask import request, jsonify
from datetime import datetime, timedelta
import time


def add_time_capsule_routes(app, node):
    """
    Add time capsule API endpoints to Flask app

    Args:
        app: Flask application
        node: BlockchainNode instance
    """

    node.time_capsule_manager = node.blockchain.time_capsule_manager

    @app.route("/time-capsule/create/xai", methods=["POST"])
    def create_xai_capsule():
        """
        Create time capsule for XAI coins

        POST /time-capsule/create/xai
        {
            "creator": "XAI1a2b3c...",
            "beneficiary": "XAI1a2b3c..." (optional, defaults to creator),
            "amount": 100.0,
            "unlock_date": "2025-12-25" (or unlock_days: 365),
            "message": "Happy future birthday!" (optional)
        }
        """
        data = request.json

        creator = data.get("creator")
        beneficiary = data.get("beneficiary", creator)
        amount = data.get("amount")
        message = data.get("message", "")

        # Parse unlock time
        if "unlock_date" in data:
            # Parse date string
            try:
                unlock_dt = datetime.fromisoformat(data["unlock_date"])
                unlock_time = int(unlock_dt.timestamp())
            except:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid date format. Use ISO format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS",
                        }
                    ),
                    400,
                )
        elif "unlock_days" in data:
            # Days from now
            days = int(data["unlock_days"])
            unlock_time = int(time.time()) + (days * 86400)
        elif "unlock_timestamp" in data:
            unlock_time = int(data["unlock_timestamp"])
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Must provide unlock_date, unlock_days, or unlock_timestamp",
                    }
                ),
                400,
            )

        # Create capsule
        result = node.time_capsule_manager.create_xai_capsule(
            creator=creator,
            beneficiary=beneficiary,
            amount=amount,
            unlock_time=unlock_time,
            message=message,
        )

        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    @app.route("/time-capsule/create/cross-chain", methods=["POST"])
    def create_cross_chain_capsule():
        """
        Create time capsule for other cryptocurrencies

        POST /time-capsule/create/cross-chain
        {
            "creator": "XAI1a2b3c...",
            "beneficiary": "XAI1a2b3c...",
            "coin_type": "BTC",
            "amount": 0.5,
            "unlock_date": "2026-01-01",
            "htlc_hash": "abc123...",
            "htlc_preimage": "secret...",
            "origin_chain_tx": "btc_tx_id...",
            "message": "Your Bitcoin time capsule"
        }
        """
        data = request.json

        creator = data.get("creator")
        beneficiary = data.get("beneficiary", creator)
        coin_type = data.get("coin_type")
        amount = data.get("amount")
        htlc_hash = data.get("htlc_hash")
        htlc_preimage = data.get("htlc_preimage")
        origin_chain_tx = data.get("origin_chain_tx")
        message = data.get("message", "")

        # Parse unlock time
        if "unlock_date" in data:
            try:
                unlock_dt = datetime.fromisoformat(data["unlock_date"])
                unlock_time = int(unlock_dt.timestamp())
            except:
                return jsonify({"success": False, "error": "Invalid date format"}), 400
        elif "unlock_days" in data:
            days = int(data["unlock_days"])
            unlock_time = int(time.time()) + (days * 86400)
        else:
            return (
                jsonify({"success": False, "error": "Must provide unlock_date or unlock_days"}),
                400,
            )

        # Create capsule
        result = node.time_capsule_manager.create_cross_chain_capsule(
            creator=creator,
            beneficiary=beneficiary,
            coin_type=coin_type,
            amount=amount,
            unlock_time=unlock_time,
            htlc_hash=htlc_hash,
            htlc_preimage=htlc_preimage,
            origin_chain_tx=origin_chain_tx,
            message=message,
        )

        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    @app.route("/time-capsule/submit", methods=["POST"])
    def submit_time_capsule_transaction():
        """
        Submit a signed time capsule transaction that has already been built by the wallet.
        The transaction must include metadata (capsule_id, unlock_time, etc.).
        """
        data = request.json or {}
        tx_type = data.get("tx_type")
        if tx_type not in ("time_capsule_lock", "time_capsule_claim"):
            return jsonify({"success": False, "error": "Invalid tx_type"}), 400

        required_fields = ["sender", "recipient", "amount", "fee", "metadata"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"success": False, "error": f"Missing fields: {missing}"}), 400

        try:
            from aixn.core.blockchain import Transaction

            tx = Transaction(
                sender=data["sender"],
                recipient=data["recipient"],
                amount=float(data["amount"]),
                fee=float(data["fee"]),
                public_key=data.get("public_key"),
                tx_type=tx_type,
                metadata=data.get("metadata", {}),
                nonce=data.get("nonce"),
            )
            tx.signature = data.get("signature")
            tx.txid = tx.calculate_hash()
        except Exception as exc:
            return jsonify({"success": False, "error": f"Invalid transaction payload: {exc}"}), 400

        if not node.blockchain.add_transaction(tx):
            return jsonify({"success": False, "error": "Failed to add transaction"}), 400

        return jsonify({"success": True, "txid": tx.txid}), 201

    @app.route("/time-capsule/claim/<capsule_id>", methods=["POST"])
    def claim_capsule(capsule_id):
        """
        Claim an unlocked time capsule

        POST /time-capsule/claim/abc123
        {
            "claimer": "XAI1a2b3c..."
        }
        """
        data = request.json
        claimer = data.get("claimer")

        if not claimer:
            return jsonify({"success": False, "error": "Claimer address required"}), 400

        result = node.time_capsule_manager.claim_capsule(capsule_id, claimer)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    @app.route("/time-capsule/user/<address>", methods=["GET"])
    def get_user_capsules(address):
        """
        Get all time capsules for a user

        GET /time-capsule/user/XAI1a2b3c...

        Returns list of capsules (both as creator and beneficiary)
        """
        capsules = node.time_capsule_manager.get_user_capsules(address)

        return (
            jsonify(
                {
                    "success": True,
                    "address": address,
                    "total_capsules": len(capsules),
                    "capsules": capsules,
                }
            ),
            200,
        )

    @app.route("/time-capsule/unlocked/<address>", methods=["GET"])
    def get_unlocked_capsules(address):
        """
        Get capsules ready to claim

        GET /time-capsule/unlocked/XAI1a2b3c...

        Returns only unlocked, unclaimed capsules for this address
        """
        capsules = node.time_capsule_manager.get_unlocked_capsules(address)

        return (
            jsonify(
                {
                    "success": True,
                    "address": address,
                    "ready_to_claim": len(capsules),
                    "capsules": capsules,
                }
            ),
            200,
        )

    @app.route("/time-capsule/<capsule_id>", methods=["GET"])
    def get_capsule(capsule_id):
        """
        Get specific time capsule details

        GET /time-capsule/abc123
        """
        capsule = node.time_capsule_manager.get_capsule(capsule_id)

        if capsule:
            return jsonify({"success": True, "capsule": capsule}), 200
        else:
            return jsonify({"success": False, "error": "Capsule not found"}), 404

    @app.route("/time-capsule/stats", methods=["GET"])
    def get_stats():
        """
        Get time capsule statistics

        GET /time-capsule/stats
        """
        stats = node.time_capsule_manager.get_statistics()

        return jsonify({"success": True, "statistics": stats}), 200

    @app.route("/time-capsule/examples", methods=["GET"])
    def get_examples():
        """
        Get example time capsule configurations

        GET /time-capsule/examples
        """

        examples = {
            "one_year_savings": {
                "description": "Lock XAI for 1 year savings",
                "request": {
                    "creator": "YOUR_ADDRESS",
                    "amount": 1000,
                    "unlock_days": 365,
                    "message": "Congratulations on not touching this for a year!",
                },
            },
            "birthday_gift": {
                "description": "Gift XAI for birthday",
                "request": {
                    "creator": "YOUR_ADDRESS",
                    "beneficiary": "RECIPIENT_ADDRESS",
                    "amount": 100,
                    "unlock_date": "2025-12-25",
                    "message": "Happy Birthday! Love, Past You",
                },
            },
            "bitcoin_capsule": {
                "description": "Lock Bitcoin for 5 years",
                "request": {
                    "creator": "YOUR_XAI_ADDRESS",
                    "coin_type": "BTC",
                    "amount": 0.1,
                    "unlock_days": 1825,  # 5 years
                    "htlc_hash": "HASH_FROM_BITCOIN_HTLC",
                    "htlc_preimage": "SECRET_PREIMAGE",
                    "origin_chain_tx": "BITCOIN_TX_ID",
                    "message": "Your 5-year Bitcoin time capsule",
                },
            },
            "inheritance": {
                "description": "Lock for 18 years (child inheritance)",
                "request": {
                    "creator": "YOUR_ADDRESS",
                    "beneficiary": "CHILD_ADDRESS",
                    "amount": 10000,
                    "unlock_days": 6570,  # 18 years
                    "message": "For your 18th birthday. We love you!",
                },
            },
        }

        return jsonify({"success": True, "examples": examples}), 200

    print("✅ Time Capsule API routes added:")
    print("   POST /time-capsule/create/xai")
    print("   POST /time-capsule/create/cross-chain")
    print("   POST /time-capsule/claim/<id>")
    print("   GET  /time-capsule/user/<address>")
    print("   GET  /time-capsule/unlocked/<address>")
    print("   GET  /time-capsule/<id>")
    print("   GET  /time-capsule/stats")
    print("   GET  /time-capsule/examples")
