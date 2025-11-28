"""
XAI Token Burning API Endpoints

API endpoints for token consumption and burn statistics.

ANONYMITY GUARANTEES:
- All endpoints return anonymous data only
- UTC timestamps exclusively
- Wallet addresses only (no personal data)
- No IP logging
- No session tracking
- No geographic data collection
- Anonymous statistics only
"""

from flask import jsonify, request
from xai.core.token_burning_engine import TokenBurningEngine, ServiceType
from xai.core.anonymous_treasury import AnonymousTreasury


def setup_burning_api(app, node):
    """
    Setup token burning API endpoints

    All endpoints are ANONYMOUS - no personal data collected!

    Args:
        app: Flask app instance
        node: XAI Node instance
    """

    # Initialize burning engine (anonymous)
    # NOTE: No treasury needed - dev funded by pre-mine (10M XAI) + donated AI API minutes
    burning_engine = TokenBurningEngine(
        blockchain=node.blockchain if hasattr(node, "blockchain") else None
    )

    @app.route("/burn/consume-service", methods=["POST"])
    def consume_service():
        """
        Consume XAI for service usage

        Request (ANONYMOUS - wallet address only!):
        {
          "wallet_address": "XAI...",
          "service_type": "ai_query_simple",
          "custom_amount": 0.5  // Optional
        }

        Response (UTC timestamps only!):
        {
          "success": true,
          "burn_id": "abc123...",
          "total_cost_xai": 0.1,
          "burned_xai": 0.05,
          "to_miners_xai": 0.05,
          "timestamp_utc": 1699564800.0,
          "message": "Service consumed. 0.05 XAI burned (deflationary), 0.05 XAI to miners (security)."
        }

        Distribution: 50% burn + 50% miners
        Development funded by: Pre-mine (10M XAI) + Donated AI API minutes
        """
        data = request.get_json()

        if not data or "wallet_address" not in data or "service_type" not in data:
            return jsonify({"error": "Missing wallet_address or service_type"}), 400

        wallet_address = data["wallet_address"]
        service_type_str = data["service_type"]
        custom_amount = data.get("custom_amount")

        # Validate service type
        try:
            service_type = ServiceType[service_type_str.upper()]
        except KeyError:
            return jsonify({"error": f"Invalid service_type: {service_type_str}"}), 400

        # Consume service (anonymous) - NO treasury, dev funded separately!
        result = burning_engine.consume_service(
            wallet_address=wallet_address, service_type=service_type, custom_amount=custom_amount
        )

        return jsonify(result)

    @app.route("/burn/stats", methods=["GET"])
    def get_burn_stats():
        """
        Get anonymous burn statistics

        Response (ANONYMOUS, UTC only!):
        {
          "total_burned": 50000.0,
          "total_to_miners": 50000.0,
          "total_services_used": 10000,
          "circulating_supply": 121000000.0,
          "burn_percentage_of_supply": 0.041,
          "distribution": "50% burn (deflationary) + 50% miners (security)",
          "development_funding": "Pre-mine (10M XAI) + AI API donations (encrypted keys)",
          "last_updated_utc": 1699564800.0
        }

        NO personal data!
        Distribution: 50% burn / 50% miners (NO treasury - dev funded separately)
        """
        stats = burning_engine.get_anonymous_stats()
        return jsonify(stats)

    @app.route("/burn/recent", methods=["GET"])
    def get_recent_burns():
        """
        Get recent anonymous burn transactions

        Query params:
            limit: Number of burns to return (default: 100)

        Response (ANONYMOUS - wallet addresses only, UTC timestamps!):
        [
          {
            "burn_id": "abc123...",
            "wallet_address": "XAI...",  // Anonymous only
            "service_type": "ai_query_simple",
            "burned_xai": 0.05,
            "timestamp_utc": 1699564800.0,
            "date_utc": "2025-11-09 12:34:56 UTC"
          },
          ...
        ]

        NO personal identifiers!
        """
        limit = int(request.args.get("limit", 100))
        burns = burning_engine.get_recent_burns(limit=limit)
        return jsonify({"burns": burns, "count": len(burns)})

    @app.route("/burn/service/<service_type>", methods=["GET"])
    def get_service_burn_stats(service_type):
        """
        Get anonymous burn statistics for specific service

        Response (ANONYMOUS!):
        {
          "service_type": "ai_query_simple",
          "count": 5000,
          "total_burned": 250.0
        }
        """
        try:
            service = ServiceType[service_type.upper()]
        except KeyError:
            return jsonify({"error": f"Invalid service_type: {service_type}"}), 400

        stats = burning_engine.get_burn_by_service(service)
        stats["service_type"] = service_type
        return jsonify(stats)

    @app.route("/burn/price/<service_type>", methods=["GET"])
    def get_service_price(service_type):
        """
        Get current XAI price for service (dynamic, USD-pegged)

        Response (ANONYMOUS!):
        {
          "service_type": "ai_query_simple",
          "price_xai": 0.1,
          "price_usd": 0.10,
          "xai_price_usd": 1.0
        }
        """
        try:
            service = ServiceType[service_type.upper()]
        except KeyError:
            return jsonify({"error": f"Invalid service_type: {service_type}"}), 400

        from xai.core.token_burning_engine import SERVICE_PRICES_USD

        price_xai = burning_engine.calculate_service_cost(service)
        price_usd = SERVICE_PRICES_USD[service]

        return jsonify(
            {
                "service_type": service_type,
                "price_xai": price_xai,
                "price_usd": price_usd,
                "xai_price_usd": burning_engine.xai_price_usd,
            }
        )

    print("✓ Token Burning API initialized (100% ANONYMOUS)")
    print("  Distribution: 50% burn (deflationary) + 50% miners (security)")
    print("  Development: Pre-mine (10M XAI) + AI API donations (encrypted keys)")
    return burning_engine
