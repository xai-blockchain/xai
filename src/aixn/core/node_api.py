"""
AIXN Blockchain Node API Routes
Handles all Flask route definitions and HTTP request/response logic.

This module contains all API endpoint handlers organized by category:
- Core endpoints (health, metrics, stats)
- Blockchain endpoints (blocks, transactions)
- Wallet endpoints (balance, send)
- Mining endpoints (mine, auto-mine)
- P2P endpoints (peers, sync)
- Algorithmic features (fee estimation, fraud detection)
- Gamification endpoints (airdrops, streaks, treasures)
- Social recovery endpoints
- Mining bonus endpoints
- Exchange endpoints
- Crypto deposit endpoints
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, Tuple, List
from flask import jsonify, request
import time
import json
import os

from aixn.core.node_utils import (
    ALGO_FEATURES_ENABLED,
    NODE_VERSION,
    get_base_dir,
    get_api_endpoints,
    validate_required_fields,
)

if TYPE_CHECKING:
    from aixn.core.blockchain import Transaction
    from flask import Flask


class NodeAPIRoutes:
    """
    Manages all API routes for the blockchain node.

    This class encapsulates all HTTP endpoint handlers and provides
    a clean separation between API logic and core node functionality.
    """

    def __init__(self, node: Any) -> None:
        """
        Initialize API routes handler.

        Args:
            node: The blockchain node instance (BlockchainNode)
        """
        self.node = node
        self.blockchain = node.blockchain
        self.app = node.app

    def setup_routes(self) -> None:
        """
        Register all API routes with the Flask app.

        Organizes routes into logical categories for maintainability.
        """
        self._setup_core_routes()
        self._setup_blockchain_routes()
        self._setup_transaction_routes()
        self._setup_wallet_routes()
        self._setup_mining_routes()
        self._setup_peer_routes()
        self._setup_algo_routes()
        self._setup_recovery_routes()
        self._setup_gamification_routes()
        self._setup_mining_bonus_routes()
        self._setup_exchange_routes()
        self._setup_crypto_deposit_routes()

    # ==================== CORE ROUTES ====================

    def _setup_core_routes(self) -> None:
        """Setup core node routes (index, health, metrics, stats)."""

        @self.app.route("/", methods=["GET"])
        def index() -> Tuple[Dict[str, Any], int]:
            """Node information and available endpoints."""
            return jsonify({
                "status": "online",
                "node": "AXN Full Node",
                "version": NODE_VERSION,
                "algorithmic_features": ALGO_FEATURES_ENABLED,
                "endpoints": get_api_endpoints(),
            }), 200

        @self.app.route("/health", methods=["GET"])
        def health_check() -> Tuple[Dict[str, Any], int]:
            """Health check endpoint for Docker and monitoring."""
            try:
                chain_height = len(self.blockchain.chain) if self.blockchain else 0
                stats = self.blockchain.get_stats() if self.blockchain else {}

                return jsonify({
                    "status": "healthy",
                    "timestamp": time.time(),
                    "blockchain": {
                        "height": chain_height,
                        "accessible": chain_height > 0
                    },
                    "services": {
                        "api": "running",
                        "mining": "active" if self.node.is_mining else "inactive",
                        "peer_network": "ready",
                    },
                }), 200
            except Exception as e:
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }), 503

        @self.app.route("/metrics", methods=["GET"])
        def prometheus_metrics() -> Tuple[str, int, Dict[str, str]]:
            """Prometheus metrics endpoint."""
            try:
                metrics_output = self.node.metrics_collector.export_prometheus()
                return metrics_output, 200, {"Content-Type": "text/plain; version=0.0.4"}
            except Exception as e:
                return f"# Error generating metrics: {e}\n", 500, {"Content-Type": "text/plain"}

        @self.app.route("/stats", methods=["GET"])
        def get_stats() -> Dict[str, Any]:
            """Get blockchain statistics."""
            stats = self.blockchain.get_stats()
            stats["miner_address"] = self.node.miner_address
            stats["peers"] = len(self.node.peers)
            stats["is_mining"] = self.node.is_mining
            stats["node_uptime"] = time.time() - self.node.start_time
            return jsonify(stats)

    # ==================== BLOCKCHAIN ROUTES ====================

    def _setup_blockchain_routes(self) -> None:
        """Setup blockchain query routes."""

        @self.app.route("/blocks", methods=["GET"])
        def get_blocks() -> Dict[str, Any]:
            """Get all blocks with pagination."""
            limit = request.args.get("limit", default=10, type=int)
            offset = request.args.get("offset", default=0, type=int)

            blocks = [block.to_dict() for block in self.blockchain.chain]
            blocks.reverse()  # Most recent first

            return jsonify({
                "total": len(blocks),
                "limit": limit,
                "offset": offset,
                "blocks": blocks[offset:offset + limit]
            })

        @self.app.route("/blocks/<int:index>", methods=["GET"])
        def get_block(index: int) -> Tuple[Dict[str, Any], int]:
            """Get specific block by index."""
            if index < 0 or index >= len(self.blockchain.chain):
                return jsonify({"error": "Block not found"}), 404
            return jsonify(self.blockchain.chain[index].to_dict()), 200

    # ==================== TRANSACTION ROUTES ====================

    def _setup_transaction_routes(self) -> None:
        """Setup transaction-related routes."""

        @self.app.route("/transactions", methods=["GET"])
        def get_pending_transactions() -> Dict[str, Any]:
            """Get pending transactions."""
            return jsonify({
                "count": len(self.blockchain.pending_transactions),
                "transactions": [tx.to_dict() for tx in self.blockchain.pending_transactions],
            })

        @self.app.route("/transaction/<txid>", methods=["GET"])
        def get_transaction(txid: str) -> Tuple[Dict[str, Any], int]:
            """Get transaction by ID."""
            # Search in confirmed blocks
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.txid == txid:
                        return jsonify({
                            "found": True,
                            "block": block.index,
                            "confirmations": len(self.blockchain.chain) - block.index,
                            "transaction": tx.to_dict(),
                        }), 200

            # Check pending transactions
            for tx in self.blockchain.pending_transactions:
                if tx.txid == txid:
                    return jsonify({
                        "found": True,
                        "status": "pending",
                        "transaction": tx.to_dict()
                    }), 200

            return jsonify({"found": False, "error": "Transaction not found"}), 404

        @self.app.route("/send", methods=["POST"])
        def send_transaction() -> Tuple[Dict[str, Any], int]:
            """Submit new transaction."""
            data = request.json
            required_fields = ["sender", "recipient", "amount", "public_key", "signature"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                # Import Transaction here to avoid circular imports
                from aixn.core.blockchain import Transaction

                # Create transaction without signature
                tx = Transaction(
                    sender=data["sender"],
                    recipient=data["recipient"],
                    amount=float(data["amount"]),
                    fee=float(data.get("fee", 0.01)),
                    public_key=data["public_key"],
                )

                # Set the signature from request
                tx.signature = data["signature"]

                # Verify signature
                if not tx.verify_signature():
                    return jsonify({"error": "Invalid signature"}), 400

                # Add to blockchain
                if self.blockchain.add_transaction(tx):
                    # Broadcast to peers
                    self.node.broadcast_transaction(tx)

                    return jsonify({
                        "success": True,
                        "txid": tx.txid,
                        "message": "Transaction submitted successfully",
                    }), 200
                else:
                    return jsonify({
                        "success": False,
                        "error": "Transaction validation failed"
                    }), 400

            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ==================== WALLET ROUTES ====================

    def _setup_wallet_routes(self) -> None:
        """Setup wallet-related routes."""

        @self.app.route("/balance/<address>", methods=["GET"])
        def get_balance(address: str) -> Dict[str, Any]:
            """Get address balance."""
            balance = self.blockchain.get_balance(address)
            return jsonify({"address": address, "balance": balance})

        @self.app.route("/history/<address>", methods=["GET"])
        def get_history(address: str) -> Dict[str, Any]:
            """Get transaction history for address."""
            history = self.blockchain.get_transaction_history(address)
            return jsonify({
                "address": address,
                "transaction_count": len(history),
                "transactions": history
            })

    # ==================== MINING ROUTES ====================

    def _setup_mining_routes(self) -> None:
        """Setup mining-related routes."""

        @self.app.route("/mine", methods=["POST"])
        def mine_block() -> Tuple[Dict[str, Any], int]:
            """Mine pending transactions."""
            if not self.blockchain.pending_transactions:
                return jsonify({"error": "No pending transactions to mine"}), 400

            try:
                block = self.blockchain.mine_pending_transactions(self.node.miner_address)

                # Broadcast new block to peers
                self.node.broadcast_block(block)

                return jsonify({
                    "success": True,
                    "block": block.to_dict(),
                    "message": f"Block {block.index} mined successfully",
                    "reward": self.blockchain.block_reward,
                }), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/auto-mine/start", methods=["POST"])
        def start_auto_mining() -> Dict[str, str]:
            """Start automatic mining."""
            if self.node.is_mining:
                return jsonify({"message": "Mining already active"})

            self.node.start_mining()
            return jsonify({"message": "Auto-mining started"})

        @self.app.route("/auto-mine/stop", methods=["POST"])
        def stop_auto_mining() -> Dict[str, str]:
            """Stop automatic mining."""
            if not self.node.is_mining:
                return jsonify({"message": "Mining not active"})

            self.node.stop_mining()
            return jsonify({"message": "Auto-mining stopped"})

    # ==================== P2P ROUTES ====================

    def _setup_peer_routes(self) -> None:
        """Setup peer-to-peer networking routes."""

        @self.app.route("/peers", methods=["GET"])
        def get_peers() -> Dict[str, Any]:
            """Get connected peers."""
            return jsonify({
                "count": len(self.node.peers),
                "peers": list(self.node.peers)
            })

        @self.app.route("/peers/add", methods=["POST"])
        def add_peer() -> Tuple[Dict[str, str], int]:
            """Add peer node."""
            data = request.json
            if "url" not in data:
                return jsonify({"error": "Missing peer URL"}), 400

            self.node.add_peer(data["url"])
            return jsonify({"message": f'Peer {data["url"]} added'}), 200

        @self.app.route("/sync", methods=["POST"])
        def sync_blockchain() -> Dict[str, Any]:
            """Synchronize blockchain with peers."""
            synced = self.node.sync_with_network()
            return jsonify({
                "synced": synced,
                "chain_length": len(self.blockchain.chain)
            })

    # ==================== ALGORITHMIC FEATURE ROUTES ====================

    def _setup_algo_routes(self) -> None:
        """Setup algorithmic feature routes."""

        @self.app.route("/algo/fee-estimate", methods=["GET"])
        def estimate_fee() -> Tuple[Dict[str, Any], int]:
            """Get algorithmic fee recommendation."""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({"error": "Algorithmic features not enabled"}), 503

            priority = request.args.get("priority", "normal")
            pending_count = len(self.blockchain.pending_transactions)

            recommendation = self.node.fee_optimizer.predict_optimal_fee(
                pending_tx_count=pending_count,
                priority=priority
            )
            return jsonify(recommendation), 200

        @self.app.route("/algo/fraud-check", methods=["POST"])
        def check_fraud() -> Tuple[Dict[str, Any], int]:
            """Check transaction for fraud indicators."""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({"error": "Algorithmic features not enabled"}), 503

            data = request.json
            if not data:
                return jsonify({"error": "Missing transaction data"}), 400

            analysis = self.node.fraud_detector.analyze_transaction(data)
            return jsonify(analysis), 200

        @self.app.route("/algo/status", methods=["GET"])
        def algo_status() -> Dict[str, Any]:
            """Get algorithmic features status."""
            if not ALGO_FEATURES_ENABLED:
                return jsonify({"enabled": False, "features": []})

            return jsonify({
                "enabled": True,
                "features": [
                    {
                        "name": "Fee Optimizer",
                        "description": "Statistical fee prediction using EMA",
                        "status": "active",
                        "transactions_analyzed": len(self.node.fee_optimizer.fee_history),
                        "confidence": min(100, len(self.node.fee_optimizer.fee_history) * 2),
                    },
                    {
                        "name": "Fraud Detector",
                        "description": "Pattern-based fraud detection",
                        "status": "active",
                        "addresses_tracked": len(self.node.fraud_detector.address_history),
                        "flagged_addresses": len(self.node.fraud_detector.flagged_addresses),
                    },
                ],
            })

    # ==================== SOCIAL RECOVERY ROUTES ====================

    def _setup_recovery_routes(self) -> None:
        """Setup social recovery routes."""

        @self.app.route("/recovery/setup", methods=["POST"])
        def setup_recovery() -> Tuple[Dict[str, Any], int]:
            """Set up guardians for a wallet."""
            data = request.json
            required_fields = ["owner_address", "guardians", "threshold"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.recovery_manager.setup_guardians(
                    owner_address=data["owner_address"],
                    guardian_addresses=data["guardians"],
                    threshold=int(data["threshold"]),
                    signature=data.get("signature"),
                )
                return jsonify(result), 200
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/request", methods=["POST"])
        def request_recovery() -> Tuple[Dict[str, Any], int]:
            """Initiate a recovery request."""
            data = request.json
            required_fields = ["owner_address", "new_address", "guardian_address"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.recovery_manager.initiate_recovery(
                    owner_address=data["owner_address"],
                    new_address=data["new_address"],
                    guardian_address=data["guardian_address"],
                    signature=data.get("signature"),
                )
                return jsonify(result), 200
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/vote", methods=["POST"])
        def vote_recovery() -> Tuple[Dict[str, Any], int]:
            """Guardian votes on a recovery request."""
            data = request.json
            required_fields = ["request_id", "guardian_address"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.recovery_manager.vote_recovery(
                    request_id=data["request_id"],
                    guardian_address=data["guardian_address"],
                    signature=data.get("signature"),
                )
                return jsonify(result), 200
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/status/<address>", methods=["GET"])
        def get_recovery_status(address: str) -> Tuple[Dict[str, Any], int]:
            """Get recovery status for an address."""
            try:
                status = self.node.recovery_manager.get_recovery_status(address)
                return jsonify({"success": True, "address": address, "status": status}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/cancel", methods=["POST"])
        def cancel_recovery() -> Tuple[Dict[str, Any], int]:
            """Cancel a pending recovery request."""
            data = request.json
            required_fields = ["request_id", "owner_address"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.recovery_manager.cancel_recovery(
                    request_id=data["request_id"],
                    owner_address=data["owner_address"],
                    signature=data.get("signature"),
                )
                return jsonify(result), 200
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/execute", methods=["POST"])
        def execute_recovery() -> Tuple[Dict[str, Any], int]:
            """Execute an approved recovery after waiting period."""
            data = request.json
            if "request_id" not in data:
                return jsonify({"error": "Missing request_id"}), 400

            try:
                result = self.node.recovery_manager.execute_recovery(
                    request_id=data["request_id"],
                    executor_address=data.get("executor_address")
                )
                return jsonify(result), 200
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": f"Server error: {str(e)}"}), 500

        @self.app.route("/recovery/config/<address>", methods=["GET"])
        def get_recovery_config(address: str) -> Tuple[Dict[str, Any], int]:
            """Get recovery configuration for an address."""
            try:
                config = self.node.recovery_manager.get_recovery_config(address)
                if config:
                    return jsonify({"success": True, "address": address, "config": config}), 200
                else:
                    return jsonify({"success": False, "message": "No recovery configuration found"}), 404
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/guardian/<address>", methods=["GET"])
        def get_guardian_duties(address: str) -> Tuple[Dict[str, Any], int]:
            """Get guardian duties for an address."""
            try:
                duties = self.node.recovery_manager.get_guardian_duties(address)
                return jsonify({"success": True, "duties": duties}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/requests", methods=["GET"])
        def get_recovery_requests() -> Tuple[Dict[str, Any], int]:
            """Get all recovery requests with optional status filter."""
            try:
                status_filter = request.args.get("status")
                requests_list = self.node.recovery_manager.get_all_requests(status=status_filter)
                return jsonify({
                    "success": True,
                    "count": len(requests_list),
                    "requests": requests_list
                }), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/stats", methods=["GET"])
        def get_recovery_stats() -> Tuple[Dict[str, Any], int]:
            """Get social recovery statistics."""
            try:
                stats = self.node.recovery_manager.get_stats()
                return jsonify({"success": True, "stats": stats}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ==================== GAMIFICATION ROUTES ====================

    def _setup_gamification_routes(self) -> None:
        """Setup gamification routes (airdrops, streaks, treasures, etc.)."""

        @self.app.route("/airdrop/winners", methods=["GET"])
        def get_airdrop_winners() -> Dict[str, Any]:
            """Get recent airdrop winners."""
            limit = request.args.get("limit", default=10, type=int)
            recent_airdrops = self.blockchain.airdrop_manager.get_recent_airdrops(limit)
            return jsonify({"success": True, "airdrops": recent_airdrops})

        @self.app.route("/airdrop/user/<address>", methods=["GET"])
        def get_user_airdrops(address: str) -> Dict[str, Any]:
            """Get airdrop history for specific address."""
            history = self.blockchain.airdrop_manager.get_user_airdrop_history(address)
            total_received = sum(a["amount"] for a in history)
            return jsonify({
                "success": True,
                "address": address,
                "total_airdrops": len(history),
                "total_received": total_received,
                "history": history,
            })

        @self.app.route("/mining/streaks", methods=["GET"])
        def get_mining_streaks() -> Dict[str, Any]:
            """Get mining streak leaderboard."""
            limit = request.args.get("limit", default=10, type=int)
            sort_by = request.args.get("sort_by", default="current_streak")
            leaderboard = self.blockchain.streak_tracker.get_leaderboard(limit, sort_by)
            return jsonify({"success": True, "leaderboard": leaderboard})

        @self.app.route("/mining/streak/<address>", methods=["GET"])
        def get_miner_streak(address: str) -> Tuple[Dict[str, Any], int]:
            """Get mining streak for specific address."""
            stats = self.blockchain.streak_tracker.get_miner_stats(address)
            if not stats:
                return jsonify({
                    "success": False,
                    "error": "No mining history found for this address"
                }), 404
            return jsonify({"success": True, "address": address, "stats": stats}), 200

        @self.app.route("/treasure/active", methods=["GET"])
        def get_active_treasures() -> Dict[str, Any]:
            """List all active (unclaimed) treasure hunts."""
            treasures = self.blockchain.treasure_manager.get_active_treasures()
            return jsonify({"success": True, "count": len(treasures), "treasures": treasures})

        @self.app.route("/treasure/create", methods=["POST"])
        def create_treasure() -> Tuple[Dict[str, Any], int]:
            """Create a new treasure hunt."""
            data = request.json
            required_fields = ["creator", "amount", "puzzle_type", "puzzle_data"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                treasure_id = self.blockchain.treasure_manager.create_treasure_hunt(
                    creator_address=data["creator"],
                    amount=float(data["amount"]),
                    puzzle_type=data["puzzle_type"],
                    puzzle_data=data["puzzle_data"],
                    hint=data.get("hint", ""),
                )
                return jsonify({
                    "success": True,
                    "treasure_id": treasure_id,
                    "message": "Treasure hunt created successfully",
                }), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/treasure/claim", methods=["POST"])
        def claim_treasure() -> Tuple[Dict[str, Any], int]:
            """Claim a treasure by solving the puzzle."""
            data = request.json
            required_fields = ["treasure_id", "claimer", "solution"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                from aixn.core.blockchain import Transaction

                success, amount = self.blockchain.treasure_manager.claim_treasure(
                    treasure_id=data["treasure_id"],
                    claimer_address=data["claimer"],
                    solution=data["solution"],
                )

                if success:
                    # Create transaction for claimed treasure
                    treasure_tx = Transaction("COINBASE", data["claimer"], amount, tx_type="treasure")
                    treasure_tx.txid = treasure_tx.calculate_hash()
                    self.blockchain.pending_transactions.append(treasure_tx)

                    return jsonify({
                        "success": True,
                        "amount": amount,
                        "message": "Treasure claimed successfully!",
                    }), 200
                else:
                    return jsonify({"success": False, "message": "Incorrect solution"}), 400

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/treasure/details/<treasure_id>", methods=["GET"])
        def get_treasure_details(treasure_id: str) -> Tuple[Dict[str, Any], int]:
            """Get details of a specific treasure hunt."""
            treasure = self.blockchain.treasure_manager.get_treasure_details(treasure_id)
            if not treasure:
                return jsonify({"error": "Treasure not found"}), 404
            return jsonify({"success": True, "treasure": treasure}), 200

        @self.app.route("/timecapsule/pending", methods=["GET"])
        def get_pending_timecapsules() -> Dict[str, Any]:
            """List all pending (locked) time capsules."""
            capsules = self.blockchain.timecapsule_manager.get_pending_capsules()
            return jsonify({"success": True, "count": len(capsules), "capsules": capsules})

        @self.app.route("/timecapsule/<address>", methods=["GET"])
        def get_user_timecapsules(address: str) -> Dict[str, Any]:
            """Get time capsules for a specific user."""
            capsules = self.blockchain.timecapsule_manager.get_user_capsules(address)
            return jsonify({
                "success": True,
                "address": address,
                "sent": capsules["sent"],
                "received": capsules["received"],
            })

        @self.app.route("/refunds/stats", methods=["GET"])
        def get_refund_stats() -> Dict[str, Any]:
            """Get overall fee refund statistics."""
            stats = self.blockchain.fee_refund_calculator.get_refund_stats()
            return jsonify({"success": True, "stats": stats})

        @self.app.route("/refunds/<address>", methods=["GET"])
        def get_user_refunds(address: str) -> Dict[str, Any]:
            """Get fee refund history for specific address."""
            history = self.blockchain.fee_refund_calculator.get_user_refund_history(address)
            total_refunded = sum(r["amount"] for r in history)
            return jsonify({
                "success": True,
                "address": address,
                "total_refunds": len(history),
                "total_refunded": total_refunded,
                "history": history,
            })

    # ==================== MINING BONUS ROUTES ====================

    def _setup_mining_bonus_routes(self) -> None:
        """Setup mining bonus routes."""

        @self.app.route("/mining/register", methods=["POST"])
        def register_miner() -> Tuple[Dict[str, Any], int]:
            """Register a new miner and check for early adopter bonus."""
            data = request.json
            if "address" not in data:
                return jsonify({"error": "Missing address field"}), 400

            try:
                result = self.node.bonus_manager.register_miner(data["address"])
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/achievements/<address>", methods=["GET"])
        def get_achievements(address: str) -> Tuple[Dict[str, Any], int]:
            """Check mining achievements for an address."""
            blocks_mined = request.args.get("blocks_mined", default=0, type=int)
            streak_days = request.args.get("streak_days", default=0, type=int)

            try:
                result = self.node.bonus_manager.check_achievements(address, blocks_mined, streak_days)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/claim-bonus", methods=["POST"])
        def claim_bonus() -> Tuple[Dict[str, Any], int]:
            """Claim a social bonus (tweet verification, discord join, etc.)."""
            data = request.json
            required_fields = ["address", "bonus_type"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.bonus_manager.claim_bonus(data["address"], data["bonus_type"])
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/referral/create", methods=["POST"])
        def create_referral_code() -> Tuple[Dict[str, Any], int]:
            """Create a referral code for a miner."""
            data = request.json
            if "address" not in data:
                return jsonify({"error": "Missing address field"}), 400

            try:
                result = self.node.bonus_manager.create_referral_code(data["address"])
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/referral/use", methods=["POST"])
        def use_referral_code() -> Tuple[Dict[str, Any], int]:
            """Use a referral code to register a new miner."""
            data = request.json
            required_fields = ["new_address", "referral_code"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.bonus_manager.use_referral_code(
                    data["new_address"],
                    data["referral_code"]
                )
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/user-bonuses/<address>", methods=["GET"])
        def get_user_bonuses(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all bonuses and rewards for a user."""
            try:
                result = self.node.bonus_manager.get_user_bonuses(address)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/leaderboard", methods=["GET"])
        def get_bonus_leaderboard() -> Tuple[Dict[str, Any], int]:
            """Get mining bonus leaderboard."""
            limit = request.args.get("limit", default=10, type=int)

            try:
                leaderboard = self.node.bonus_manager.get_leaderboard(limit)
                return jsonify({"success": True, "limit": limit, "leaderboard": leaderboard}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/stats", methods=["GET"])
        def get_mining_bonus_stats() -> Tuple[Dict[str, Any], int]:
            """Get mining bonus system statistics."""
            try:
                stats = self.node.bonus_manager.get_stats()
                return jsonify({"success": True, "stats": stats}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ==================== EXCHANGE ROUTES ====================

    def _setup_exchange_routes(self) -> None:
        """Setup exchange-related routes."""

        @self.app.route("/exchange/orders", methods=["GET"])
        def get_order_book() -> Tuple[Dict[str, Any], int]:
            """Get current order book (buy and sell orders)."""
            try:
                orders_file = os.path.join(get_base_dir(), "exchange_data", "orders.json")
                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        all_orders = json.load(f)
                else:
                    all_orders = {"buy": [], "sell": []}

                # Filter only open orders
                buy_orders = [o for o in all_orders.get("buy", []) if o["status"] == "open"]
                sell_orders = [o for o in all_orders.get("sell", []) if o["status"] == "open"]

                # Sort orders
                buy_orders.sort(key=lambda x: x["price"], reverse=True)
                sell_orders.sort(key=lambda x: x["price"])

                return jsonify({
                    "success": True,
                    "buy_orders": buy_orders[:20],
                    "sell_orders": sell_orders[:20],
                    "total_buy_orders": len(buy_orders),
                    "total_sell_orders": len(sell_orders),
                }), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/place-order", methods=["POST"])
        def place_order() -> Tuple[Dict[str, Any], int]:
            """Place a buy or sell order with balance verification."""
            data = request.json
            required_fields = ["address", "order_type", "price", "amount"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                # Validate order type
                if data["order_type"] not in ["buy", "sell"]:
                    return jsonify({"error": "Invalid order type"}), 400

                price = float(data["price"])
                amount = float(data["amount"])

                if price <= 0 or amount <= 0:
                    return jsonify({"error": "Price and amount must be positive"}), 400

                # Parse trading pair
                pair = data.get("pair", "AXN/USD")
                base_currency, quote_currency = pair.split("/")
                total_cost = price * amount

                user_address = data["address"]

                # Verify balance and lock funds
                if data["order_type"] == "buy":
                    balance_info = self.node.exchange_wallet_manager.get_balance(user_address, quote_currency)
                    if balance_info["available"] < total_cost:
                        return jsonify({
                            "success": False,
                            "error": f'Insufficient {quote_currency} balance. Need {total_cost:.2f}, have {balance_info["available"]:.2f}',
                        }), 400

                    if not self.node.exchange_wallet_manager.lock_for_order(user_address, quote_currency, total_cost):
                        return jsonify({"success": False, "error": "Failed to lock funds"}), 500
                else:  # sell
                    balance_info = self.node.exchange_wallet_manager.get_balance(user_address, base_currency)
                    if balance_info["available"] < amount:
                        return jsonify({
                            "success": False,
                            "error": f'Insufficient {base_currency} balance. Need {amount:.2f}, have {balance_info["available"]:.2f}',
                        }), 400

                    if not self.node.exchange_wallet_manager.lock_for_order(user_address, base_currency, amount):
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
                matched = self.node._match_orders(order, all_orders)

                # Get updated balances
                balances = self.node.exchange_wallet_manager.get_all_balances(user_address)

                return jsonify({
                    "success": True,
                    "order": order,
                    "matched": matched,
                    "balances": balances["available_balances"],
                    "message": f"{data['order_type'].capitalize()} order placed successfully",
                }), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/cancel-order", methods=["POST"])
        def cancel_order() -> Tuple[Dict[str, Any], int]:
            """Cancel an open order."""
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

                return jsonify({"success": True, "message": "Order cancelled successfully"}), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/my-orders/<address>", methods=["GET"])
        def get_my_orders(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all orders for a specific address."""
            try:
                orders_file = os.path.join(get_base_dir(), "exchange_data", "orders.json")
                if not os.path.exists(orders_file):
                    return jsonify({"success": True, "orders": []}), 200

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

                return jsonify({"success": True, "orders": user_orders}), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/trades", methods=["GET"])
        def get_recent_trades() -> Tuple[Dict[str, Any], int]:
            """Get recent executed trades."""
            limit = request.args.get("limit", default=50, type=int)

            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
                if not os.path.exists(trades_file):
                    return jsonify({"success": True, "trades": []}), 200

                with open(trades_file, "r") as f:
                    all_trades = json.load(f)

                all_trades.sort(key=lambda x: x["timestamp"], reverse=True)
                return jsonify({"success": True, "trades": all_trades[:limit]}), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # Add more exchange routes...
        self._setup_exchange_balance_routes()
        self._setup_exchange_stats_routes()
        self._setup_exchange_payment_routes()

    def _setup_exchange_balance_routes(self) -> None:
        """Setup exchange balance management routes."""

        @self.app.route("/exchange/deposit", methods=["POST"])
        def deposit_funds() -> Tuple[Dict[str, Any], int]:
            """Deposit funds into exchange wallet."""
            data = request.json
            required_fields = ["address", "currency", "amount"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.exchange_wallet_manager.deposit(
                    user_address=data["address"],
                    currency=data["currency"],
                    amount=float(data["amount"]),
                    deposit_type=data.get("deposit_type", "manual"),
                    tx_hash=data.get("tx_hash"),
                )
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/withdraw", methods=["POST"])
        def withdraw_funds() -> Tuple[Dict[str, Any], int]:
            """Withdraw funds from exchange wallet."""
            data = request.json
            required_fields = ["address", "currency", "amount", "destination"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.exchange_wallet_manager.withdraw(
                    user_address=data["address"],
                    currency=data["currency"],
                    amount=float(data["amount"]),
                    destination=data["destination"],
                )
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/balance/<address>", methods=["GET"])
        def get_user_balance(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all balances for a user."""
            try:
                balances = self.node.exchange_wallet_manager.get_all_balances(address)
                return jsonify({"success": True, "address": address, "balances": balances}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/balance/<address>/<currency>", methods=["GET"])
        def get_currency_balance(address: str, currency: str) -> Tuple[Dict[str, Any], int]:
            """Get balance for specific currency."""
            try:
                balance = self.node.exchange_wallet_manager.get_balance(address, currency)
                return jsonify({"success": True, "address": address, **balance}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/transactions/<address>", methods=["GET"])
        def get_transactions(address: str) -> Tuple[Dict[str, Any], int]:
            """Get transaction history for user."""
            try:
                limit = int(request.args.get("limit", 50))
                transactions = self.node.exchange_wallet_manager.get_transaction_history(address, limit)
                return jsonify({"success": True, "address": address, "transactions": transactions}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def _setup_exchange_stats_routes(self) -> None:
        """Setup exchange statistics routes."""

        @self.app.route("/exchange/price-history", methods=["GET"])
        def get_price_history() -> Tuple[Dict[str, Any], int]:
            """Get historical price data for charts."""
            timeframe = request.args.get("timeframe", default="24h", type=str)

            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
                if not os.path.exists(trades_file):
                    return jsonify({"success": True, "prices": [], "volumes": []}), 200

                with open(trades_file, "r") as f:
                    all_trades = json.load(f)

                # Filter by timeframe
                now = time.time()
                timeframe_seconds = {
                    "1h": 3600,
                    "24h": 86400,
                    "7d": 604800,
                    "30d": 2592000
                }.get(timeframe, 86400)

                cutoff_time = now - timeframe_seconds
                recent_trades = [t for t in all_trades if t["timestamp"] >= cutoff_time]

                # Process price data (simplified version)
                price_data = []
                volume_data = []

                if recent_trades:
                    recent_trades.sort(key=lambda x: x["timestamp"])
                    # Aggregate data here...

                return jsonify({
                    "success": True,
                    "timeframe": timeframe,
                    "prices": price_data,
                    "volumes": volume_data,
                }), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/stats", methods=["GET"])
        def get_exchange_stats() -> Tuple[Dict[str, Any], int]:
            """Get exchange statistics."""
            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
                orders_file = os.path.join(get_base_dir(), "exchange_data", "orders.json")

                stats = {
                    "current_price": 0.05,
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
                        stats["total_trades"] = len(all_trades)
                        stats["current_price"] = all_trades[-1]["price"]

                # Count active orders
                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        all_orders = json.load(f)

                    for order_type in ["buy", "sell"]:
                        stats["active_orders"] += len(
                            [o for o in all_orders.get(order_type, []) if o["status"] == "open"]
                        )

                return jsonify({"success": True, "stats": stats}), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def _setup_exchange_payment_routes(self) -> None:
        """Setup payment processing routes."""

        @self.app.route("/exchange/buy-with-card", methods=["POST"])
        def buy_with_card() -> Tuple[Dict[str, Any], int]:
            """Buy AXN with credit/debit card."""
            data = request.json
            required_fields = ["address", "usd_amount", "email"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                # Calculate purchase
                calc = self.node.payment_processor.calculate_purchase(data["usd_amount"])
                if not calc["success"]:
                    return jsonify(calc), 400

                # Process payment
                payment_result = self.node.payment_processor.process_card_payment(
                    user_address=data["address"],
                    usd_amount=data["usd_amount"],
                    card_token=data.get("card_token", "tok_test"),
                    email=data["email"],
                )

                if not payment_result["success"]:
                    return jsonify(payment_result), 400

                # Deposit AXN to exchange wallet
                deposit_result = self.node.exchange_wallet_manager.deposit(
                    user_address=data["address"],
                    currency="AXN",
                    amount=payment_result["axn_amount"],
                    deposit_type="credit_card",
                    tx_hash=payment_result["payment_id"],
                )

                return jsonify({
                    "success": True,
                    "payment": payment_result,
                    "deposit": deposit_result,
                    "message": f"Successfully purchased {payment_result['axn_amount']:.2f} AXN",
                }), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/payment-methods", methods=["GET"])
        def get_payment_methods() -> Tuple[Dict[str, Any], int]:
            """Get supported payment methods."""
            try:
                methods = self.node.payment_processor.get_supported_payment_methods()
                return jsonify({"success": True, "methods": methods}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/calculate-purchase", methods=["POST"])
        def calculate_purchase() -> Tuple[Dict[str, Any], int]:
            """Calculate AXN amount for USD purchase."""
            data = request.json
            if "usd_amount" not in data:
                return jsonify({"error": "Missing usd_amount"}), 400

            try:
                calc = self.node.payment_processor.calculate_purchase(data["usd_amount"])
                return jsonify(calc), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ==================== CRYPTO DEPOSIT ROUTES ====================

    def _setup_crypto_deposit_routes(self) -> None:
        """Setup crypto deposit routes."""

        @self.app.route("/exchange/crypto/generate-address", methods=["POST"])
        def generate_crypto_deposit_address() -> Tuple[Dict[str, Any], int]:
            """Generate unique deposit address for BTC/ETH/USDT."""
            data = request.json
            required_fields = ["user_address", "currency"]

            error = validate_required_fields(data, required_fields)
            if error:
                return jsonify({"error": error}), 400

            try:
                result = self.node.crypto_deposit_manager.generate_deposit_address(
                    user_address=data["user_address"],
                    currency=data["currency"]
                )
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/addresses/<address>", methods=["GET"])
        def get_crypto_deposit_addresses(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all crypto deposit addresses for user."""
            try:
                result = self.node.crypto_deposit_manager.get_user_deposit_addresses(address)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/pending-deposits", methods=["GET"])
        def get_pending_crypto_deposits() -> Tuple[Dict[str, Any], int]:
            """Get pending crypto deposits."""
            try:
                user_address = request.args.get("user_address")
                pending = self.node.crypto_deposit_manager.get_pending_deposits(user_address)
                return jsonify({
                    "success": True,
                    "pending_deposits": pending,
                    "count": len(pending)
                }), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/deposit-history/<address>", methods=["GET"])
        def get_crypto_deposit_history(address: str) -> Tuple[Dict[str, Any], int]:
            """Get confirmed crypto deposit history for user."""
            try:
                limit = int(request.args.get("limit", 50))
                history = self.node.crypto_deposit_manager.get_deposit_history(address, limit)
                return jsonify({
                    "success": True,
                    "address": address,
                    "deposits": history,
                    "count": len(history),
                }), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/stats", methods=["GET"])
        def get_crypto_deposit_stats() -> Tuple[Dict[str, Any], int]:
            """Get crypto deposit system statistics."""
            try:
                stats = self.node.crypto_deposit_manager.get_stats()
                return jsonify({"success": True, "stats": stats}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
