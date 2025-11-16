"""
AXN Blockchain Node - Full node implementation
Runs blockchain, mines blocks, handles transactions, P2P communication
"""

import json
import os
import sys
import time
import threading
import requests
from flask import Flask, jsonify, request
import yaml
from flask_cors import CORS
from aixn.core.monitoring import MetricsCollector


def get_allowed_origins():
    """Get allowed origins from config file"""
    cors_config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "cors.yaml")
    if os.path.exists(cors_config_path):
        with open(cors_config_path, "r") as f:
            cors_config = yaml.safe_load(f)
            return cors_config.get("origins", [])
    return []


class BlockchainNode:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        # Flask app for API
        self.app = Flask(__name__)
        allowed_origins = get_allowed_origins()
        CORS(self.app, origins=allowed_origins)

        # Initialize metrics collector for Prometheus
        self.metrics_collector = MetricsCollector(blockchain=self.blockchain)
        print("📊 Prometheus metrics collector initialized")

        self.setup_routes()

    def setup_routes(self):
        """Setup API endpoints"""

        @self.app.route("/", methods=["GET"])
        def index():
            return jsonify(
                {
                    "status": "online",
                    "node": "AXN Full Node",
                    "version": "2.0.0",
                    "algorithmic_features": ALGO_FEATURES_ENABLED,
                    "endpoints": {
                        "/stats": "GET - Blockchain statistics",
                        "/blocks": "GET - All blocks",
                        "/blocks/<index>": "GET - Specific block",
                        "/transactions": "GET - Pending transactions",
                        "/transaction/<txid>": "GET - Transaction details",
                        "/balance/<address>": "GET - Address balance",
                        "/history/<address>": "GET - Transaction history",
                        "/send": "POST - Send transaction",
                        "/mine": "POST - Mine pending transactions",
                        "/peers": "GET - Connected peers",
                        "/sync": "POST - Sync with network",
                        "/algo/fee-estimate": "GET - Algorithmic fee recommendation",
                        "/algo/fraud-check": "POST - Fraud detection analysis",
                        "/algo/status": "GET - Algorithmic features status",
                        "/airdrop/winners": "GET - Recent airdrop winners",
                        "/mining/streaks": "GET - Mining streak leaderboard",
                        "/mining/streak/<address>": "GET - Mining streak for address",
                        "/treasure/active": "GET - Active treasure hunts",
                        "/treasure/create": "POST - Create treasure hunt",
                        "/treasure/claim": "POST - Claim treasure by solving puzzle",
                        "/treasure/details/<id>": "GET - Treasure hunt details",
                        "/timecapsule/create": "POST - Create time-locked transaction",
                        "/timecapsule/pending": "GET - List pending time capsules",
                        "/timecapsule/<address>": "GET - User time capsules",
                        "/refunds/stats": "GET - Fee refund statistics",
                        "/refunds/<address>": "GET - Fee refund history for address",
                        "/recovery/setup": "POST - Set up guardians for a wallet",
                        "/recovery/request": "POST - Request recovery to new address",
                        "/recovery/vote": "POST - Guardian votes on recovery request",
                        "/recovery/status/<address>": "GET - Check recovery status",
                        "/recovery/cancel": "POST - Cancel pending recovery",
                        "/recovery/execute": "POST - Execute approved recovery after waiting period",
                        "/recovery/config/<address>": "GET - Get recovery configuration",
                        "/recovery/guardian/<address>": "GET - Get guardian duties",
                        "/recovery/requests": "GET - Get all recovery requests",
                        "/recovery/stats": "GET - Get social recovery statistics",
                        "/mining/register": "POST - Register miner and check early adopter bonus",
                        "/mining/achievements/<address>": "GET - Check mining achievements",
                        "/mining/claim-bonus": "POST - Claim social bonus",
                        "/mining/referral/create": "POST - Create referral code",
                        "/mining/referral/use": "POST - Use referral code",
                        "/mining/user-bonuses/<address>": "GET - Get all bonuses for user",
                        "/mining/leaderboard": "GET - Mining bonus leaderboard",
                        "/mining/stats": "GET - Mining bonus system statistics",
                    },
                }
            )

        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint for Docker and monitoring"""
            try:
                # Check if blockchain is accessible
                chain_height = len(self.blockchain.chain) if self.blockchain else 0

                # Check if we can query stats
                stats = self.blockchain.get_stats() if self.blockchain else {}

                return (
                    jsonify(
                        {
                            "status": "healthy",
                            "timestamp": time.time(),
                            "blockchain": {"height": chain_height, "accessible": chain_height > 0},
                            "services": {
                                "api": "running",
                                "mining": "active" if self.is_mining else "inactive",
                                "peer_network": "ready",
                            },
                        }
                    ),
                    200,
                )
            except Exception as e:
                return (
                    jsonify({"status": "unhealthy", "error": str(e), "timestamp": time.time()}),
                    503,
                )

        @self.app.route("/metrics", methods=["GET"])
        def prometheus_metrics():
            """Prometheus metrics endpoint"""
            try:
                metrics_output = self.metrics_collector.export_prometheus()
                return metrics_output, 200, {"Content-Type": "text/plain; version=0.0.4"}
            except Exception as e:
                return f"# Error generating metrics: {e}\n", 500, {"Content-Type": "text/plain"}

        @self.app.route("/stats", methods=["GET"])
        def get_stats():
            """Get blockchain statistics"""
            stats = self.blockchain.get_stats()
            stats["miner_address"] = self.miner_address
            stats["peers"] = len(self.peers)
            stats["is_mining"] = self.is_mining
            stats["node_uptime"] = time.time() - self.start_time

            return jsonify(stats)

        @self.app.route("/blocks", methods=["GET"])
        def get_blocks():
            """Get all blocks"""
            limit = request.args.get("limit", default=10, type=int)
            offset = request.args.get("offset", default=0, type=int)

            blocks = [block.to_dict() for block in self.blockchain.chain]
            blocks.reverse()  # Most recent first

            return jsonify(
                {
                    "total": len(blocks),
                    "limit": limit,
                    "offset": offset,
                    "blocks": blocks[offset : offset + limit],
                }
            )

        @self.app.route("/blocks/<int:index>", methods=["GET"])
        def get_block(index):
            """Get specific block"""
            if index < 0 or index >= len(self.blockchain.chain):
                return jsonify({"error": "Block not found"}), 404

            return jsonify(self.blockchain.chain[index].to_dict())

        @self.app.route("/transactions", methods=["GET"])
        def get_pending_transactions():
            """Get pending transactions"""
            return jsonify(
                {
                    "count": len(self.blockchain.pending_transactions),
                    "transactions": [tx.to_dict() for tx in self.blockchain.pending_transactions],
                }
            )

        @self.app.route("/transaction/<txid>", methods=["GET"])
        def get_transaction(txid):
            """Get transaction by ID"""
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.txid == txid:
                        return jsonify(
                            {
                                "found": True,
                                "block": block.index,
                                "confirmations": len(self.blockchain.chain) - block.index,
                                "transaction": tx.to_dict(),
                            }
                        )

            # Check pending
            for tx in self.blockchain.pending_transactions:
                if tx.txid == txid:
                    return jsonify(
                        {"found": True, "status": "pending", "transaction": tx.to_dict()}
                    )

            return jsonify({"found": False, "error": "Transaction not found"}), 404

        @self.app.route("/balance/<address>", methods=["GET"])
        def get_balance(address):
            """Get address balance"""
            balance = self.blockchain.get_balance(address)
            return jsonify({"address": address, "balance": balance})

        @self.app.route("/history/<address>", methods=["GET"])
        def get_history(address):
            """Get transaction history for address"""
            history = self.blockchain.get_transaction_history(address)
            return jsonify(
                {"address": address, "transaction_count": len(history), "transactions": history}
            )

        @self.app.route("/send", methods=["POST"])
        def send_transaction():
            """Submit new transaction"""
            data = request.json

            required_fields = ["sender", "recipient", "amount", "public_key", "signature"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                # Create transaction without signature
                tx = Transaction(
                    sender=data["sender"],
                    recipient=data["recipient"],
                    amount=float(data["amount"]),
                    fee=float(data.get("fee", 0.01)),
                    public_key=data["public_key"],
                )

                # Set the signature from the request data
                tx.signature = data["signature"]

                # Verify the signature
                if not tx.verify_signature():
                    return jsonify({"error": "Invalid signature"}), 400

                # Add to blockchain
                if self.blockchain.add_transaction(tx):
                    # Broadcast to peers
                    self.broadcast_transaction(tx)

                    return jsonify(
                        {
                            "success": True,
                            "txid": tx.txid,
                            "message": "Transaction submitted successfully",
                        }
                    )
                else:
                    return (
                        jsonify({"success": False, "error": "Transaction validation failed"}),
                        400,
                    )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mine", methods=["POST"])
        def mine_block():
            """Mine pending transactions"""
            if not self.blockchain.pending_transactions:
                return jsonify({"error": "No pending transactions to mine"}), 400

            try:
                block = self.blockchain.mine_pending_transactions(self.miner_address)

                # Broadcast new block to peers
                self.broadcast_block(block)

                return jsonify(
                    {
                        "success": True,
                        "block": block.to_dict(),
                        "message": f"Block {block.index} mined successfully",
                        "reward": self.blockchain.block_reward,
                    }
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/auto-mine/start", methods=["POST"])
        def start_auto_mining():
            """Start automatic mining"""
            if self.is_mining:
                return jsonify({"message": "Mining already active"})

            self.start_mining()
            return jsonify({"message": "Auto-mining started"})

        @self.app.route("/auto-mine/stop", methods=["POST"])
        def stop_auto_mining():
            """Stop automatic mining"""
            if not self.is_mining:
                return jsonify({"message": "Mining not active"})

            self.stop_mining()
            return jsonify({"message": "Auto-mining stopped"})

        @self.app.route("/peers", methods=["GET"])
        def get_peers():
            """Get connected peers"""
            return jsonify({"count": len(self.peers), "peers": list(self.peers)})

        @self.app.route("/peers/add", methods=["POST"])
        def add_peer():
            """Add peer node"""
            data = request.json
            if "url" not in data:
                return jsonify({"error": "Missing peer URL"}), 400

            self.add_peer(data["url"])
            return jsonify({"message": f'Peer {data["url"]} added'})

        @self.app.route("/sync", methods=["POST"])
        def sync_blockchain():
            """Synchronize blockchain with peers"""
            synced = self.sync_with_network()
            return jsonify({"synced": synced, "chain_length": len(self.blockchain.chain)})

        # Algorithmic Feature Endpoints
        @self.app.route("/algo/fee-estimate", methods=["GET"])
        def estimate_fee():
            """Get algorithmic fee recommendation"""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({"error": "Algorithmic features not enabled"}), 503

            priority = request.args.get("priority", "normal")
            pending_count = len(self.blockchain.pending_transactions)

            recommendation = self.fee_optimizer.predict_optimal_fee(
                pending_tx_count=pending_count, priority=priority
            )

            return jsonify(recommendation)

        @self.app.route("/algo/fraud-check", methods=["POST"])
        def check_fraud():
            """Check transaction for fraud indicators"""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({"error": "Algorithmic features not enabled"}), 503

            data = request.json
            if not data:
                return jsonify({"error": "Missing transaction data"}), 400

            analysis = self.fraud_detector.analyze_transaction(data)
            return jsonify(analysis)

        @self.app.route("/algo/status", methods=["GET"])
        def algo_status():
            """Get algorithmic features status"""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({"enabled": False, "features": []})

            return jsonify(
                {
                    "enabled": True,
                    "features": [
                        {
                            "name": "Fee Optimizer",
                            "description": "Statistical fee prediction using EMA",
                            "status": "active",
                            "transactions_analyzed": len(self.fee_optimizer.fee_history),
                            "confidence": min(100, len(self.fee_optimizer.fee_history) * 2),
                        },
                        {
                            "name": "Fraud Detector",
                            "description": "Pattern-based fraud detection",
                            "status": "active",
                            "addresses_tracked": len(self.fraud_detector.address_history),
                            "flagged_addresses": len(self.fraud_detector.flagged_addresses),
                        },
                    ],
                }
            )

        # Social Recovery Endpoints

        @self.app.route("/recovery/setup", methods=["POST"])
        def setup_recovery():
            """Set up guardians for a wallet"""
            data = request.json

            required_fields = ["owner_address", "guardians", "threshold"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.recovery_manager.setup_guardians(
                    owner_address=data["owner_address"],
                    guardian_addresses=data["guardians"],
                    threshold=int(data["threshold"]),
                    signature=data.get("signature"),
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/request", methods=["POST"])
        def request_recovery():
            """Initiate a recovery request"""
            data = request.json

            required_fields = ["owner_address", "new_address", "guardian_address"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.recovery_manager.initiate_recovery(
                    owner_address=data["owner_address"],
                    new_address=data["new_address"],
                    guardian_address=data["guardian_address"],
                    signature=data.get("signature"),
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/vote", methods=["POST"])
        def vote_recovery():
            """Guardian votes on a recovery request"""
            data = request.json

            required_fields = ["request_id", "guardian_address"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.recovery_manager.vote_recovery(
                    request_id=data["request_id"],
                    guardian_address=data["guardian_address"],
                    signature=data.get("signature"),
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/status/<address>", methods=["GET"])
        def get_recovery_status(address):
            """Get recovery status for an address"""
            try:
                status = self.recovery_manager.get_recovery_status(address)
                return jsonify({"success": True, "address": address, "status": status})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/cancel", methods=["POST"])
        def cancel_recovery():
            """Cancel a pending recovery request"""
            data = request.json

            required_fields = ["request_id", "owner_address"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.recovery_manager.cancel_recovery(
                    request_id=data["request_id"],
                    owner_address=data["owner_address"],
                    signature=data.get("signature"),
                )
                return jsonify(result)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/execute", methods=["POST"])
        def execute_recovery():
            """Execute an approved recovery after waiting period"""
            data = request.json

            if "request_id" not in data:
                return jsonify({"error": "Missing request_id"}), 400

            try:
                result = self.recovery_manager.execute_recovery(
                    request_id=data["request_id"], executor_address=data.get("executor_address")
                )

                # If execution successful, we should transfer funds
                # This is a placeholder - actual implementation would:
                # 1. Get balance of old address
                # 2. Create transaction from old to new address
                # 3. Add to pending transactions
                # For now, we just return the result

                return jsonify(result)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/config/<address>", methods=["GET"])
        def get_recovery_config(address):
            """Get recovery configuration for an address"""
            try:
                config = self.recovery_manager.get_recovery_config(address)
                if config:
                    return jsonify({"success": True, "address": address, "config": config})
                else:
                    return (
                        jsonify({"success": False, "message": "No recovery configuration found"}),
                        404,
                    )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/guardian/<address>", methods=["GET"])
        def get_guardian_duties(address):
            """Get guardian duties for an address"""
            try:
                duties = self.recovery_manager.get_guardian_duties(address)
                return jsonify({"success": True, "duties": duties})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/requests", methods=["GET"])
        def get_recovery_requests():
            """Get all recovery requests with optional status filter"""
            try:
                status_filter = request.args.get("status")
                requests_list = self.recovery_manager.get_all_requests(status=status_filter)
                return jsonify(
                    {"success": True, "count": len(requests_list), "requests": requests_list}
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/stats", methods=["GET"])
        def get_recovery_stats():
            """Get social recovery statistics"""
            try:
                stats = self.recovery_manager.get_stats()
                return jsonify({"success": True, "stats": stats})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # Gamification Endpoints

        @self.app.route("/airdrop/winners", methods=["GET"])
        def get_airdrop_winners():
            """Get recent airdrop winners"""
            limit = request.args.get("limit", default=10, type=int)
            recent_airdrops = self.blockchain.airdrop_manager.get_recent_airdrops(limit)
            return jsonify({"success": True, "airdrops": recent_airdrops})

        @self.app.route("/airdrop/user/<address>", methods=["GET"])
        def get_user_airdrops(address):
            """Get airdrop history for specific address"""
            history = self.blockchain.airdrop_manager.get_user_airdrop_history(address)
            total_received = sum(a["amount"] for a in history)
            return jsonify(
                {
                    "success": True,
                    "address": address,
                    "total_airdrops": len(history),
                    "total_received": total_received,
                    "history": history,
                }
            )

        @self.app.route("/mining/streaks", methods=["GET"])
        def get_mining_streaks():
            """Get mining streak leaderboard"""
            limit = request.args.get("limit", default=10, type=int)
            sort_by = request.args.get("sort_by", default="current_streak")

            leaderboard = self.blockchain.streak_tracker.get_leaderboard(limit, sort_by)
            return jsonify({"success": True, "leaderboard": leaderboard})

        @self.app.route("/mining/streak/<address>", methods=["GET"])
        def get_miner_streak(address):
            """Get mining streak for specific address"""
            stats = self.blockchain.streak_tracker.get_miner_stats(address)
            if not stats:
                return (
                    jsonify(
                        {"success": False, "error": "No mining history found for this address"}
                    ),
                    404,
                )

            return jsonify({"success": True, "address": address, "stats": stats})

        @self.app.route("/treasure/active", methods=["GET"])
        def get_active_treasures():
            """List all active (unclaimed) treasure hunts"""
            treasures = self.blockchain.treasure_manager.get_active_treasures()
            return jsonify({"success": True, "count": len(treasures), "treasures": treasures})

        @self.app.route("/treasure/create", methods=["POST"])
        def create_treasure():
            """Create a new treasure hunt"""
            data = request.json

            required_fields = ["creator", "amount", "puzzle_type", "puzzle_data"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                treasure_id = self.blockchain.treasure_manager.create_treasure_hunt(
                    creator_address=data["creator"],
                    amount=float(data["amount"]),
                    puzzle_type=data["puzzle_type"],
                    puzzle_data=data["puzzle_data"],
                    hint=data.get("hint", ""),
                )

                return jsonify(
                    {
                        "success": True,
                        "treasure_id": treasure_id,
                        "message": "Treasure hunt created successfully",
                    }
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/treasure/claim", methods=["POST"])
        def claim_treasure():
            """Claim a treasure by solving the puzzle"""
            data = request.json

            required_fields = ["treasure_id", "claimer", "solution"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                success, amount = self.blockchain.treasure_manager.claim_treasure(
                    treasure_id=data["treasure_id"],
                    claimer_address=data["claimer"],
                    solution=data["solution"],
                )

                if success:
                    # Create transaction for claimed treasure
                    treasure_tx = Transaction(
                        "COINBASE", data["claimer"], amount, tx_type="treasure"
                    )
                    treasure_tx.txid = treasure_tx.calculate_hash()
                    self.blockchain.pending_transactions.append(treasure_tx)

                    return jsonify(
                        {
                            "success": True,
                            "amount": amount,
                            "message": "Treasure claimed successfully!",
                        }
                    )
                else:
                    return jsonify({"success": False, "message": "Incorrect solution"}), 400

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/treasure/details/<treasure_id>", methods=["GET"])
        def get_treasure_details(treasure_id):
            """Get details of a specific treasure hunt"""
            treasure = self.blockchain.treasure_manager.get_treasure_details(treasure_id)
            if not treasure:
                return jsonify({"error": "Treasure not found"}), 404

            return jsonify({"success": True, "treasure": treasure})

        @self.app.route("/timecapsule/pending", methods=["GET"])
        def get_pending_timecapsules():
            """List all pending (locked) time capsules"""
            capsules = self.blockchain.timecapsule_manager.get_pending_capsules()
            return jsonify({"success": True, "count": len(capsules), "capsules": capsules})

        @self.app.route("/timecapsule/<address>", methods=["GET"])
        def get_user_timecapsules(address):
            """Get time capsules for a specific user"""
            capsules = self.blockchain.timecapsule_manager.get_user_capsules(address)
            return jsonify(
                {
                    "success": True,
                    "address": address,
                    "sent": capsules["sent"],
                    "received": capsules["received"],
                }
            )

        @self.app.route("/refunds/stats", methods=["GET"])
        def get_refund_stats():
            """Get overall fee refund statistics"""
            stats = self.blockchain.fee_refund_calculator.get_refund_stats()
            return jsonify({"success": True, "stats": stats})

        @self.app.route("/refunds/<address>", methods=["GET"])
        def get_user_refunds(address):
            """Get fee refund history for specific address"""
            history = self.blockchain.fee_refund_calculator.get_user_refund_history(address)
            total_refunded = sum(r["amount"] for r in history)
            return jsonify(
                {
                    "success": True,
                    "address": address,
                    "total_refunds": len(history),
                    "total_refunded": total_refunded,
                    "history": history,
                }
            )

        # Mining Bonus Endpoints

        @self.app.route("/mining/register", methods=["POST"])
        def register_miner():
            """Register a new miner and check for early adopter bonus"""
            data = request.json

            if "address" not in data:
                return jsonify({"error": "Missing address field"}), 400

            try:
                result = self.bonus_manager.register_miner(data["address"])
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/achievements/<address>", methods=["GET"])
        def get_achievements(address):
            """Check mining achievements for an address"""
            blocks_mined = request.args.get("blocks_mined", default=0, type=int)
            streak_days = request.args.get("streak_days", default=0, type=int)

            try:
                result = self.bonus_manager.check_achievements(address, blocks_mined, streak_days)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/claim-bonus", methods=["POST"])
        def claim_bonus():
            """Claim a social bonus (tweet verification, discord join, etc.)"""
            data = request.json

            required_fields = ["address", "bonus_type"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.bonus_manager.claim_bonus(data["address"], data["bonus_type"])
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/referral/create", methods=["POST"])
        def create_referral_code():
            """Create a referral code for a miner"""
            data = request.json

            if "address" not in data:
                return jsonify({"error": "Missing address field"}), 400

            try:
                result = self.bonus_manager.create_referral_code(data["address"])
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/referral/use", methods=["POST"])
        def use_referral_code():
            """Use a referral code to register a new miner"""
            data = request.json

            required_fields = ["new_address", "referral_code"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.bonus_manager.use_referral_code(
                    data["new_address"], data["referral_code"]
                )
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/user-bonuses/<address>", methods=["GET"])
        def get_user_bonuses(address):
            """Get all bonuses and rewards for a user"""
            try:
                result = self.bonus_manager.get_user_bonuses(address)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/leaderboard", methods=["GET"])
        def get_bonus_leaderboard():
            """Get mining bonus leaderboard"""
            limit = request.args.get("limit", default=10, type=int)

            try:
                leaderboard = self.bonus_manager.get_leaderboard(limit)
                return jsonify({"success": True, "limit": limit, "leaderboard": leaderboard})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/stats", methods=["GET"])
        def get_mining_bonus_stats():
            """Get mining bonus system statistics"""
            try:
                stats = self.bonus_manager.get_stats()
                return jsonify({"success": True, "stats": stats})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ==================== EXCHANGE API ENDPOINTS ====================

        @self.app.route("/exchange/orders", methods=["GET"])
        def get_order_book():
            """Get current order book (buy and sell orders)"""
            try:
                # Load orders from blockchain data
                orders_file = os.path.join(get_base_dir(), "exchange_data", "orders.json")
                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        all_orders = json.load(f)
                else:
                    all_orders = {"buy": [], "sell": []}

                # Filter only open orders
                buy_orders = [o for o in all_orders.get("buy", []) if o["status"] == "open"]
                sell_orders = [o for o in all_orders.get("sell", []) if o["status"] == "open"]

                # Sort orders (buy: highest first, sell: lowest first)
                buy_orders.sort(key=lambda x: x["price"], reverse=True)
                sell_orders.sort(key=lambda x: x["price"])

                return jsonify(
                    {
                        "success": True,
                        "buy_orders": buy_orders[:20],  # Top 20
                        "sell_orders": sell_orders[:20],
                        "total_buy_orders": len(buy_orders),
                        "total_sell_orders": len(sell_orders),
                    }
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/place-order", methods=["POST"])
        def place_order():
            """Place a buy or sell order with balance verification"""
            data = request.json

            required_fields = ["address", "order_type", "price", "amount"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                # Validate order
                if data["order_type"] not in ["buy", "sell"]:
                    return jsonify({"error": "Invalid order type"}), 400

                price = float(data["price"])
                amount = float(data["amount"])

                if price <= 0 or amount <= 0:
                    return jsonify({"error": "Price and amount must be positive"}), 400

                # Parse trading pair (default AXN/USD)
                pair = data.get("pair", "AXN/USD")
                base_currency, quote_currency = pair.split("/")

                # Calculate total cost
                total_cost = price * amount

                # Verify user has sufficient balance
                user_address = data["address"]
                if data["order_type"] == "buy":
                    # Buying base currency (AXN), need quote currency (USD/BTC/ETH)
                    balance_info = self.exchange_wallet_manager.get_balance(
                        user_address, quote_currency
                    )
                    if balance_info["available"] < total_cost:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": f'Insufficient {quote_currency} balance. Need {total_cost:.2f}, have {balance_info["available"]:.2f}',
                                }
                            ),
                            400,
                        )

                    # Lock the quote currency
                    if not self.exchange_wallet_manager.lock_for_order(
                        user_address, quote_currency, total_cost
                    ):
                        return jsonify({"success": False, "error": "Failed to lock funds"}), 500

                else:  # sell
                    # Selling base currency (AXN), need base currency
                    balance_info = self.exchange_wallet_manager.get_balance(
                        user_address, base_currency
                    )
                    if balance_info["available"] < amount:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": f'Insufficient {base_currency} balance. Need {amount:.2f}, have {balance_info["available"]:.2f}',
                                }
                            ),
                            400,
                        )

                    # Lock the base currency
                    if not self.exchange_wallet_manager.lock_for_order(
                        user_address, base_currency, amount
                    ):
                        return jsonify({"success": False, "error": "Failed to lock funds"}), 500

                # Create order
                order = {
                    "id": f"{user_address}_{int(time.time() * 1000)}",
                    "address": user_address,
                    "order_type": data["order_type"],
                    "pair": pair,
                    "base_currency": base_currency,
                    "quote_currency": quote_currency,
                    "price": price,
                    "amount": amount,
                    "remaining": amount,
                    "total": total_cost,
                    "status": "open",
                    "timestamp": time.time(),
                }

                # Save order
                orders_dir = os.path.join(get_base_dir(), "exchange_data")
                os.makedirs(orders_dir, exist_ok=True)
                orders_file = os.path.join(orders_dir, "orders.json")

                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        all_orders = json.load(f)
                else:
                    all_orders = {"buy": [], "sell": []}

                all_orders[data["order_type"]].append(order)

                with open(orders_file, "w") as f:
                    json.dump(all_orders, f, indent=2)

                # Try to match order immediately
                matched = self._match_orders(order, all_orders)

                # Get updated balances
                balances = self.exchange_wallet_manager.get_all_balances(user_address)

                return jsonify(
                    {
                        "success": True,
                        "order": order,
                        "matched": matched,
                        "balances": balances["available_balances"],
                        "message": f"{data['order_type'].capitalize()} order placed successfully",
                    }
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/cancel-order", methods=["POST"])
        def cancel_order():
            """Cancel an open order"""
            data = request.json

            if "order_id" not in data:
                return jsonify({"error": "Missing order_id"}), 400

            try:
                orders_file = os.path.join(get_base_dir(), "exchange_data", "orders.json")

                if not os.path.exists(orders_file):
                    return jsonify({"error": "Order not found"}), 404

                with open(orders_file, "r") as f:
                    all_orders = json.load(f)

                # Find and cancel order
                found = False
                for order_type in ["buy", "sell"]:
                    for order in all_orders[order_type]:
                        if order["id"] == data["order_id"]:
                            if order["status"] == "open":
                                order["status"] = "cancelled"
                                found = True
                                break
                    if found:
                        break

                if not found:
                    return jsonify({"error": "Order not found or already completed"}), 404

                with open(orders_file, "w") as f:
                    json.dump(all_orders, f, indent=2)

                return jsonify({"success": True, "message": "Order cancelled successfully"})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/my-orders/<address>", methods=["GET"])
        def get_my_orders(address):
            """Get all orders for a specific address"""
            try:
                orders_file = os.path.join(get_base_dir(), "exchange_data", "orders.json")

                if not os.path.exists(orders_file):
                    return jsonify({"success": True, "orders": []})

                with open(orders_file, "r") as f:
                    all_orders = json.load(f)

                # Filter orders for this address
                user_orders = []
                for order_type in ["buy", "sell"]:
                    for order in all_orders[order_type]:
                        if order["address"] == address:
                            user_orders.append(order)

                # Sort by timestamp (newest first)
                user_orders.sort(key=lambda x: x["timestamp"], reverse=True)

                return jsonify({"success": True, "orders": user_orders})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/trades", methods=["GET"])
        def get_recent_trades():
            """Get recent executed trades"""
            limit = request.args.get("limit", default=50, type=int)

            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")

                if not os.path.exists(trades_file):
                    return jsonify({"success": True, "trades": []})

                with open(trades_file, "r") as f:
                    all_trades = json.load(f)

                # Get most recent trades
                all_trades.sort(key=lambda x: x["timestamp"], reverse=True)

                return jsonify({"success": True, "trades": all_trades[:limit]})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/price-history", methods=["GET"])
        def get_price_history():
            """Get historical price data for charts"""
            timeframe = request.args.get("timeframe", default="24h", type=str)

            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")

                if not os.path.exists(trades_file):
                    return jsonify({"success": True, "prices": [], "volumes": []})

                with open(trades_file, "r") as f:
                    all_trades = json.load(f)

                # Filter trades by timeframe
                now = time.time()
                timeframe_seconds = {"1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000}.get(
                    timeframe, 86400
                )

                cutoff_time = now - timeframe_seconds
                recent_trades = [t for t in all_trades if t["timestamp"] >= cutoff_time]

                # Aggregate by time intervals
                interval_seconds = {
                    "1h": 300,  # 5 minutes
                    "24h": 1800,  # 30 minutes
                    "7d": 3600,  # 1 hour
                    "30d": 3600,  # 1 hour
                }.get(timeframe, 1800)

                price_data = []
                volume_data = []

                if recent_trades:
                    recent_trades.sort(key=lambda x: x["timestamp"])

                    current_interval = (
                        int(recent_trades[0]["timestamp"] / interval_seconds) * interval_seconds
                    )
                    interval_prices = []
                    interval_volume = 0

                    for trade in recent_trades:
                        trade_interval = (
                            int(trade["timestamp"] / interval_seconds) * interval_seconds
                        )

                        if trade_interval > current_interval:
                            if interval_prices:
                                price_data.append(
                                    {
                                        "time": current_interval,
                                        "price": sum(interval_prices) / len(interval_prices),
                                    }
                                )
                                volume_data.append(
                                    {"time": current_interval, "volume": interval_volume}
                                )

                            current_interval = trade_interval
                            interval_prices = []
                            interval_volume = 0

                        interval_prices.append(trade["price"])
                        interval_volume += trade["amount"]

                    # Add last interval
                    if interval_prices:
                        price_data.append(
                            {
                                "time": current_interval,
                                "price": sum(interval_prices) / len(interval_prices),
                            }
                        )
                        volume_data.append({"time": current_interval, "volume": interval_volume})

                return jsonify(
                    {
                        "success": True,
                        "timeframe": timeframe,
                        "prices": price_data,
                        "volumes": volume_data,
                    }
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/stats", methods=["GET"])
        def get_exchange_stats():
            """Get exchange statistics (24h volume, current price, etc.)"""
            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
                orders_file = os.path.join(get_base_dir(), "exchange_data", "orders.json")

                stats = {
                    "current_price": 0.05,  # Default starting price
                    "volume_24h": 0,
                    "change_24h": 0,
                    "high_24h": 0,
                    "low_24h": 0,
                    "total_trades": 0,
                    "active_orders": 0,
                }

                # Calculate stats from trades
                if os.path.exists(trades_file):
                    with open(trades_file, "r") as f:
                        all_trades = json.load(f)

                    if all_trades:
                        now = time.time()
                        trades_24h = [t for t in all_trades if t["timestamp"] >= now - 86400]

                        stats["total_trades"] = len(all_trades)
                        stats["current_price"] = all_trades[-1]["price"] if all_trades else 0.05

                        if trades_24h:
                            stats["volume_24h"] = sum(t["amount"] for t in trades_24h)
                            stats["high_24h"] = max(t["price"] for t in trades_24h)
                            stats["low_24h"] = min(t["price"] for t in trades_24h)

                            if len(trades_24h) > 1:
                                first_price = trades_24h[0]["price"]
                                last_price = trades_24h[-1]["price"]
                                stats["change_24h"] = (
                                    (last_price - first_price) / first_price
                                ) * 100

                # Count active orders
                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        all_orders = json.load(f)

                    for order_type in ["buy", "sell"]:
                        stats["active_orders"] += len(
                            [o for o in all_orders.get(order_type, []) if o["status"] == "open"]
                        )

                return jsonify({"success": True, "stats": stats})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/deposit", methods=["POST"])
        def deposit_funds():
            """Deposit funds into exchange wallet"""
            data = request.json

            required_fields = ["address", "currency", "amount"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.exchange_wallet_manager.deposit(
                    user_address=data["address"],
                    currency=data["currency"],
                    amount=float(data["amount"]),
                    deposit_type=data.get("deposit_type", "manual"),
                    tx_hash=data.get("tx_hash"),
                )

                return jsonify(result)

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/withdraw", methods=["POST"])
        def withdraw_funds():
            """Withdraw funds from exchange wallet"""
            data = request.json

            required_fields = ["address", "currency", "amount", "destination"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                result = self.exchange_wallet_manager.withdraw(
                    user_address=data["address"],
                    currency=data["currency"],
                    amount=float(data["amount"]),
                    destination=data["destination"],
                )

                return jsonify(result)

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/balance/<address>", methods=["GET"])
        def get_user_balance(address):
            """Get all balances for a user"""
            try:
                balances = self.exchange_wallet_manager.get_all_balances(address)
                return jsonify({"success": True, "address": address, "balances": balances})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/balance/<address>/<currency>", methods=["GET"])
        def get_currency_balance(address, currency):
            """Get balance for specific currency"""
            try:
                balance = self.exchange_wallet_manager.get_balance(address, currency)
                return jsonify({"success": True, "address": address, **balance})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/transactions/<address>", methods=["GET"])
        def get_transactions(address):
            """Get transaction history for user"""
            try:
                limit = int(request.args.get("limit", 50))
                transactions = self.exchange_wallet_manager.get_transaction_history(address, limit)

                return jsonify({"success": True, "address": address, "transactions": transactions})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/buy-with-card", methods=["POST"])
        def buy_with_card():
            """Buy AXN with credit/debit card"""
            data = request.json

            required_fields = ["address", "usd_amount", "email"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields"}), 400

            try:
                # Calculate purchase
                calc = self.payment_processor.calculate_purchase(data["usd_amount"])
                if not calc["success"]:
                    return jsonify(calc), 400

                # Process payment (test mode - auto success)
                payment_result = self.payment_processor.process_card_payment(
                    user_address=data["address"],
                    usd_amount=data["usd_amount"],
                    card_token=data.get("card_token", "tok_test"),
                    email=data["email"],
                )

                if not payment_result["success"]:
                    return jsonify(payment_result), 400

                # Deposit AXN to user's exchange wallet
                deposit_result = self.exchange_wallet_manager.deposit(
                    user_address=data["address"],
                    currency="AXN",
                    amount=payment_result["axn_amount"],
                    deposit_type="credit_card",
                    tx_hash=payment_result["payment_id"],
                )

                return jsonify(
                    {
                        "success": True,
                        "payment": payment_result,
                        "deposit": deposit_result,
                        "message": f"Successfully purchased {payment_result['axn_amount']:.2f} AXN",
                    }
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/payment-methods", methods=["GET"])
        def get_payment_methods():
            """Get supported payment methods"""
            try:
                methods = self.payment_processor.get_supported_payment_methods()
                return jsonify({"success": True, "methods": methods})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/calculate-purchase", methods=["POST"])
        def calculate_purchase():
            """Calculate AXN amount for USD purchase"""
            data = request.json

            if "usd_amount" not in data:
                return jsonify({"error": "Missing usd_amount"}), 400

            try:
                calc = self.payment_processor.calculate_purchase(data["usd_amount"])
                return jsonify(calc)

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ==================== CRYPTO DEPOSIT API ENDPOINTS ====================

        @self.app.route("/exchange/crypto/generate-address", methods=["POST"])
        def generate_crypto_deposit_address():
            """Generate unique deposit address for BTC/ETH/USDT"""
            data = request.json

            required_fields = ["user_address", "currency"]
            if not all(field in data for field in required_fields):
                return jsonify({"error": "Missing required fields: user_address, currency"}), 400

            try:
                result = self.crypto_deposit_manager.generate_deposit_address(
                    user_address=data["user_address"], currency=data["currency"]
                )
                return jsonify(result)

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/addresses/<address>", methods=["GET"])
        def get_crypto_deposit_addresses(address):
            """Get all crypto deposit addresses for user"""
            try:
                result = self.crypto_deposit_manager.get_user_deposit_addresses(address)
                return jsonify(result)

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/pending-deposits", methods=["GET"])
        def get_pending_crypto_deposits():
            """Get pending crypto deposits (optionally filtered by user)"""
            try:
                user_address = request.args.get("user_address")
                pending = self.crypto_deposit_manager.get_pending_deposits(user_address)

                return jsonify(
                    {"success": True, "pending_deposits": pending, "count": len(pending)}
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/deposit-history/<address>", methods=["GET"])
        def get_crypto_deposit_history(address):
            """Get confirmed crypto deposit history for user"""
            try:
                limit = int(request.args.get("limit", 50))
                history = self.crypto_deposit_manager.get_deposit_history(address, limit)

                return jsonify(
                    {
                        "success": True,
                        "address": address,
                        "deposits": history,
                        "count": len(history),
                    }
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/stats", methods=["GET"])
        def get_crypto_deposit_stats():
            """Get crypto deposit system statistics"""
            try:
                stats = self.crypto_deposit_manager.get_stats()
                return jsonify({"success": True, "stats": stats})

            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def _match_orders(self, new_order, all_orders):
        """Internal method to match buy/sell orders and execute balance transfers"""
        try:
            matched_trades = []

            if new_order["order_type"] == "buy":
                # Match with sell orders
                matching_orders = [
                    o
                    for o in all_orders["sell"]
                    if o["status"] == "open" and o["price"] <= new_order["price"]
                ]
                matching_orders.sort(key=lambda x: x["price"])  # Lowest price first
            else:
                # Match with buy orders
                matching_orders = [
                    o
                    for o in all_orders["buy"]
                    if o["status"] == "open" and o["price"] >= new_order["price"]
                ]
                matching_orders.sort(key=lambda x: x["price"], reverse=True)  # Highest price first

            for match_order in matching_orders:
                if new_order["remaining"] <= 0:
                    break

                # Calculate trade amount
                trade_amount = min(new_order["remaining"], match_order["remaining"])
                trade_price = match_order["price"]  # Use existing order price
                trade_total = trade_price * trade_amount

                # Determine buyer and seller
                buyer_addr = (
                    new_order["address"]
                    if new_order["order_type"] == "buy"
                    else match_order["address"]
                )
                seller_addr = (
                    match_order["address"]
                    if new_order["order_type"] == "buy"
                    else new_order["address"]
                )

                # Get currencies from orders (they should match)
                base_currency = new_order.get("base_currency", "AXN")
                quote_currency = new_order.get("quote_currency", "USD")

                # Execute balance transfer
                trade_result = self.exchange_wallet_manager.execute_trade(
                    buyer_address=buyer_addr,
                    seller_address=seller_addr,
                    base_currency=base_currency,
                    quote_currency=quote_currency,
                    base_amount=trade_amount,
                    quote_amount=trade_total,
                )

                if not trade_result["success"]:
                    print(f"Trade execution failed: {trade_result.get('error')}")
                    continue  # Skip this match if balance transfer failed

                # Unlock the locked balances that were used in the trade
                if new_order["order_type"] == "buy":
                    self.exchange_wallet_manager.unlock_from_order(
                        buyer_addr, quote_currency, trade_total
                    )
                    self.exchange_wallet_manager.unlock_from_order(
                        seller_addr, base_currency, trade_amount
                    )
                else:
                    self.exchange_wallet_manager.unlock_from_order(
                        seller_addr, base_currency, trade_amount
                    )
                    self.exchange_wallet_manager.unlock_from_order(
                        buyer_addr, quote_currency, trade_total
                    )

                # Create trade record
                trade = {
                    "id": f"trade_{int(time.time() * 1000)}",
                    "pair": f"{base_currency}/{quote_currency}",
                    "buyer": buyer_addr,
                    "seller": seller_addr,
                    "price": trade_price,
                    "amount": trade_amount,
                    "total": trade_total,
                    "timestamp": time.time(),
                }

                matched_trades.append(trade)

                # Update order remainings
                new_order["remaining"] -= trade_amount
                match_order["remaining"] -= trade_amount

                # Update order statuses
                if new_order["remaining"] <= 0:
                    new_order["status"] = "filled"
                if match_order["remaining"] <= 0:
                    match_order["status"] = "filled"

            # Save trades
            if matched_trades:
                trades_dir = os.path.join(get_base_dir(), "exchange_data")
                trades_file = os.path.join(trades_dir, "trades.json")

                if os.path.exists(trades_file):
                    with open(trades_file, "r") as f:
                        all_trades = json.load(f)
                else:
                    all_trades = []

                all_trades.extend(matched_trades)

                with open(trades_file, "w") as f:
                    json.dump(all_trades, f, indent=2)

                # Update orders file
                orders_file = os.path.join(trades_dir, "orders.json")
                with open(orders_file, "w") as f:
                    json.dump(all_orders, f, indent=2)

            return len(matched_trades) > 0

        except Exception as e:
            print(f"Error matching orders: {e}")
            return False

    def start_mining(self):
        """Start automatic mining in background thread"""
        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mine_continuously, daemon=True)
        self.mining_thread.start()
        print("⛏️  Auto-mining started")

    def stop_mining(self):
        """Stop automatic mining"""
        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        print("⏸️  Auto-mining stopped")

    def _mine_continuously(self):
        """Continuously mine blocks"""
        while self.is_mining:
            if self.blockchain.pending_transactions:
                print(
                    f"Mining block with {len(self.blockchain.pending_transactions)} transactions..."
                )
                block = self.blockchain.mine_pending_transactions(self.miner_address)
                print(f"✅ Block {block.index} mined! Hash: {block.hash}")

                # Broadcast to peers
                self.broadcast_block(block)

            time.sleep(1)  # Small delay between mining attempts

    def add_peer(self, peer_url: str):
        """Add peer node"""
        if peer_url not in self.peers:
            self.peers.add(peer_url)
            print(f"Added peer: {peer_url}")

    def broadcast_transaction(self, transaction: Transaction):
        """Broadcast transaction to all peers"""
        for peer in self.peers:
            try:
                requests.post(f"{peer}/transaction/receive", json=transaction.to_dict(), timeout=2)
            except:
                pass

    def broadcast_block(self, block):
        """Broadcast new block to all peers"""
        for peer in self.peers:
            try:
                requests.post(f"{peer}/block/receive", json=block.to_dict(), timeout=2)
            except:
                pass

    def sync_with_network(self) -> bool:
        """Sync blockchain with network"""
        longest_chain = None
        max_length = len(self.blockchain.chain)

        # Query all peers
        for peer in self.peers:
            try:
                response = requests.get(f"{peer}/blocks", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    chain_length = data["total"]

                    if chain_length > max_length:
                        # This chain is longer, get full chain
                        full_response = requests.get(
                            f"{peer}/blocks?limit={chain_length}", timeout=10
                        )
                        if full_response.status_code == 200:
                            longest_chain = full_response.json()["blocks"]
                            max_length = chain_length

            except Exception as e:
                print(f"Error syncing with {peer}: {e}")

        # Replace chain if we found a longer valid one
        if longest_chain and len(longest_chain) > len(self.blockchain.chain):
            # Validate new chain before replacing
            # (In production, implement full chain validation)
            print(f"Syncing blockchain... New length: {len(longest_chain)}")
            return True

        return False

    def run(self, debug=False):
        """Start the node"""
        self.start_time = time.time()

        print("=" * 60)
        print("AIXN BLOCKCHAIN NODE")
        print("=" * 60)
        print(f"Miner Address: {self.miner_address}")
        print(f"Listening on: http://{self.host}:{self.port}")
        print(f"Blockchain height: {len(self.blockchain.chain)}")
        print(f"Network difficulty: {self.blockchain.difficulty}")
        print("=" * 60)

        # Start auto-mining by default
        self.start_mining()

        # Run Flask app
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AIXN Blockchain Node")
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("AIXN_API_PORT", 8545)), help="Port to listen on"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--miner", help="Miner wallet address")
    parser.add_argument("--peers", nargs="+", help="Peer node URLs")

    args = parser.parse_args()

    # Create and run node
    node = BlockchainNode(host=args.host, port=args.port, miner_address=args.miner)

    # Add peers if specified
    if args.peers:
        for peer in args.peers:
            node.add_peer(peer)

    # Start the node
    node.run()
