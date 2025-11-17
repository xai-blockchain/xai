"""
Mining API Handler

Handles all mining-related API endpoints including:
- Start/stop mining
- Mining status and statistics
- Real-time mining updates via WebSocket
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, Tuple
from flask import Flask, jsonify, request
from prometheus_client import Gauge

logger = logging.getLogger(__name__)

miner_active_gauge = Gauge("xai_miner_active_count", "Number of miners currently running")


class MiningAPIHandler:
    """Handles all mining-related API endpoints."""

    def __init__(self, node: Any, app: Flask, broadcast_callback: callable):
        """
        Initialize Mining API Handler.

        Args:
            node: BlockchainNode instance
            app: Flask application instance
            broadcast_callback: Function to broadcast WebSocket messages
        """
        self.node = node
        self.app = app
        self.broadcast_ws = broadcast_callback

        # Mining state
        self.mining_threads: Dict[str, Dict[str, Any]] = {}  # miner_address -> thread info
        self.mining_stats: Dict[str, Dict[str, Any]] = {}  # miner_address -> stats

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all mining routes."""

        @self.app.route("/mining/start", methods=["POST"])
        def start_mining() -> Tuple[Dict[str, Any], int]:
            """Start continuous mining."""
            return self.start_mining_handler()

        @self.app.route("/mining/stop", methods=["POST"])
        def stop_mining() -> Tuple[Dict[str, Any], int]:
            """Stop mining."""
            return self.stop_mining_handler()

        @self.app.route("/mining/status", methods=["GET"])
        def mining_status() -> Tuple[Dict[str, Any], int]:
            """Get mining status."""
            return self.mining_status_handler()

    def start_mining_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle mining start request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json

        miner_address = data.get("miner_address")
        threads = data.get("threads", 1)
        intensity = data.get("intensity", "medium")

        if not miner_address:
            return jsonify({"error": "miner_address required"}), 400

        # Validate intensity
        intensity_levels = {"low": 1, "medium": 2, "high": 4}
        if intensity not in intensity_levels:
            return jsonify({"error": "intensity must be low, medium, or high"}), 400

        # Start mining thread
        if miner_address in self.mining_threads:
            return jsonify({"error": "Mining already active for this address"}), 400

        # Initialize stats
        self.mining_stats[miner_address] = {
            "started_at": time.time(),
            "blocks_mined": 0,
            "xai_earned": 0,
            "shares_submitted": 0,
            "shares_accepted": 0,
            "hashrate_history": [],
        }

        # Start mining
        self.node.is_mining = True
        mining_thread = threading.Thread(
            target=self._mining_worker,
            args=(miner_address, threads, intensity_levels[intensity]),
            daemon=True,
        )
        mining_thread.start()

        self.mining_threads[miner_address] = {
            "thread": mining_thread,
            "threads": threads,
            "intensity": intensity,
            "started_at": time.time(),
        }

        miner_active_gauge.set(len(self.mining_threads))

        # Broadcast to WebSocket clients
        self.broadcast_ws(
            {
                "channel": "mining",
                "event": "started",
                "data": {
                    "miner_address": miner_address,
                    "threads": threads,
                    "intensity": intensity,
                },
            }
        )

        return jsonify(
            {
                "success": True,
                "message": "Mining started",
                "miner_address": miner_address,
                "threads": threads,
                "intensity": intensity,
                "expected_hashrate": f"{threads * intensity_levels[intensity] * 100} MH/s",
            }
        ), 200

    def stop_mining_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle mining stop request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json
        miner_address = data.get("miner_address")

        if not miner_address or miner_address not in self.mining_threads:
            return jsonify({"error": "No active mining for this address"}), 400

        # Stop mining
        self.node.is_mining = False
        del self.mining_threads[miner_address]
        miner_active_gauge.set(len(self.mining_threads))

        # Get final stats
        stats = self.mining_stats.get(miner_address, {})
        duration = time.time() - stats.get("started_at", time.time())

        # Broadcast to WebSocket clients
        self.broadcast_ws(
            {
                "channel": "mining",
                "event": "stopped",
                "data": {
                    "miner_address": miner_address,
                    "total_blocks_mined": stats.get("blocks_mined", 0),
                    "total_xai_earned": stats.get("xai_earned", 0),
                },
            }
        )

        return jsonify(
            {
                "success": True,
                "message": "Mining stopped",
                "total_blocks_mined": stats.get("blocks_mined", 0),
                "total_xai_earned": stats.get("xai_earned", 0),
                "mining_duration": duration,
            }
        ), 200

    def mining_status_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle mining status request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        miner_address = request.args.get("address")

        if not miner_address:
            return jsonify({"error": "address parameter required"}), 400

        is_mining = miner_address in self.mining_threads
        stats = self.mining_stats.get(miner_address, {})

        if not is_mining:
            return jsonify({"is_mining": False, "miner_address": miner_address}), 200

        # Calculate hashrate
        recent_hashrates = stats.get("hashrate_history", [])[-10:]
        avg_hashrate = sum(recent_hashrates) / len(recent_hashrates) if recent_hashrates else 0

        return jsonify(
            {
                "is_mining": True,
                "miner_address": miner_address,
                "threads": self.mining_threads[miner_address]["threads"],
                "intensity": self.mining_threads[miner_address]["intensity"],
                "hashrate": f"{recent_hashrates[-1] if recent_hashrates else 0:.1f} MH/s",
                "avg_hashrate": f"{avg_hashrate:.1f} MH/s",
                "blocks_mined_today": stats.get("blocks_mined", 0),
                "xai_earned_today": stats.get("xai_earned", 0),
                "shares_submitted": stats.get("shares_submitted", 0),
                "shares_accepted": stats.get("shares_accepted", 0),
                "acceptance_rate": (
                    stats.get("shares_accepted", 0) / max(stats.get("shares_submitted", 1), 1)
                )
                * 100,
                "current_difficulty": self.node.blockchain.difficulty,
                "uptime": time.time() - stats.get("started_at", time.time()),
            }
        ), 200

    def _mining_worker(self, miner_address: str, threads: int, intensity: int) -> None:
        """
        Background mining worker.

        Args:
            miner_address: Address to receive mining rewards
            threads: Number of mining threads
            intensity: Mining intensity level
        """
        logger.info(
            f"Mining worker started for {miner_address} ({threads} threads, intensity {intensity})"
        )

        while self.node.is_mining and miner_address in self.mining_threads:
            try:
                # Mine a block
                if self.node.blockchain.pending_transactions:
                    block = self.node.blockchain.mine_pending_transactions(miner_address)

                    # Update stats
                    if miner_address in self.mining_stats:
                        self.mining_stats[miner_address]["blocks_mined"] += 1
                        self.mining_stats[miner_address][
                            "xai_earned"
                        ] += self.node.blockchain.block_reward
                        self.mining_stats[miner_address]["shares_accepted"] += 1

                    # Broadcast new block
                    self.broadcast_ws(
                        {
                            "channel": "blocks",
                            "event": "new_block",
                            "data": {
                                "index": block.index,
                                "hash": block.hash,
                                "miner": miner_address,
                                "reward": self.node.blockchain.block_reward,
                                "transactions": len(block.transactions),
                            },
                        }
                    )

                    logger.info(f"Block {block.index} mined by {miner_address}")

                # Calculate hashrate (simplified)
                hashrate = threads * intensity * 100
                if miner_address in self.mining_stats:
                    self.mining_stats[miner_address]["hashrate_history"].append(hashrate)
                    self.mining_stats[miner_address]["shares_submitted"] += 1

                # Broadcast mining update
                self.broadcast_ws(
                    {
                        "channel": "mining",
                        "event": "hashrate_update",
                        "data": {
                            "miner_address": miner_address,
                            "current_hashrate": f"{hashrate} MH/s",
                            "shares_accepted": self.mining_stats[miner_address]["shares_accepted"],
                            "timestamp": time.time(),
                        },
                    }
                )

                # Sleep based on intensity (lower = longer sleep)
                time.sleep(max(1, 5 - intensity))

            except Exception as e:
                logger.error(f"Mining error for {miner_address}: {e}")
                time.sleep(5)

        logger.info(f"Mining worker stopped for {miner_address}")
