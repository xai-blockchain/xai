from __future__ import annotations

"""
Mobile Telemetry API Handler

Handles mobile-specific telemetry endpoints:
- POST /api/v1/telemetry/mobile - Submit telemetry data
- GET /api/v1/telemetry/mobile/summary - Get aggregated stats (admin only)
- GET /api/v1/telemetry/mobile/optimize - Get optimization recommendations
"""

import logging
import time
from typing import Any

from flask import Flask, jsonify, request

from xai.mobile.network_optimizer import ConnectionType, NetworkOptimizer
from xai.mobile.telemetry import MobileTelemetryCollector, TelemetryEvent

logger = logging.getLogger(__name__)

class MobileTelemetryAPIHandler:
    """Handles all mobile telemetry API endpoints."""

    def __init__(
        self,
        node: Any,
        app: Flask,
        api_auth: Any | None = None
    ):
        """
        Initialize Mobile Telemetry API Handler.

        Args:
            node: BlockchainNode instance
            app: Flask application instance
            api_auth: Optional API authentication handler
        """
        self.node = node
        self.app = app
        self.api_auth = api_auth

        # Initialize telemetry collector and optimizer
        self.telemetry_collector = MobileTelemetryCollector(
            max_events=10000
        )
        self.network_optimizer = NetworkOptimizer(
            enable_compression=True,
            max_queue_size=1000
        )

        # Register routes
        self._register_routes()

        logger.info("Mobile Telemetry API Handler initialized")

    def _register_routes(self) -> None:
        """Register all mobile telemetry routes."""

        @self.app.route("/api/v1/telemetry/mobile", methods=["POST"])
        def submit_telemetry() -> tuple[dict[str, Any], int]:
            """Submit mobile telemetry data."""
            return self.submit_telemetry_handler()

        @self.app.route("/api/v1/telemetry/mobile/summary", methods=["GET"])
        def get_telemetry_summary() -> tuple[dict[str, Any], int]:
            """Get aggregated telemetry summary (admin only)."""
            return self.get_telemetry_summary_handler()

        @self.app.route("/api/v1/telemetry/mobile/optimize", methods=["POST"])
        def get_optimization_recommendations() -> tuple[dict[str, Any], int]:
            """Get network optimization recommendations."""
            return self.get_optimization_handler()

        @self.app.route("/api/v1/telemetry/mobile/queue", methods=["GET"])
        def get_offline_queue_status() -> tuple[dict[str, Any], int]:
            """Get offline transaction queue status."""
            return self.get_queue_status_handler()

        @self.app.route("/api/v1/telemetry/mobile/stats", methods=["GET"])
        def get_telemetry_stats() -> tuple[dict[str, Any], int]:
            """Get telemetry statistics (public)."""
            return self.get_stats_handler()

    def submit_telemetry_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle telemetry submission from mobile clients.

        Expected payload:
        {
            "events": [
                {
                    "event_type": "sync|api_call|transaction|resource_snapshot",
                    "timestamp": 1234567890.0,
                    "client_id": "anon_device_id",
                    "bytes_sent": 1024,
                    "bytes_received": 2048,
                    "duration_ms": 150,
                    "latency_ms": 50,
                    "connection_type": "wifi|cellular|offline",
                    "battery_level_start": 95.0,
                    "battery_level_end": 94.8,
                    "memory_mb": 128.5,
                    "storage_mb": 512.0,
                    "signal_strength": 4,
                    "metadata": {}
                }
            ]
        }

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.json

        if not data or 'events' not in data:
            return jsonify({"error": "events array required"}), 400

        events = data['events']
        if not isinstance(events, list):
            return jsonify({"error": "events must be an array"}), 400

        if len(events) > 1000:
            return jsonify({"error": "Maximum 1000 events per request"}), 400

        # Process events
        processed = 0
        failed = 0

        for event_data in events:
            try:
                # Validate required fields
                if not all(k in event_data for k in ['event_type', 'timestamp', 'client_id']):
                    failed += 1
                    continue

                # Create event
                event = TelemetryEvent.from_dict(event_data)

                # Record event
                if self.telemetry_collector.record_event(event):
                    processed += 1
                else:
                    failed += 1

            except Exception as e:
                logger.warning(f"Failed to process telemetry event: {e}")
                failed += 1

        # Get optimization recommendations for response
        recommendations = {}
        if events:
            # Use most recent event for network profile
            latest = events[-1]
            if 'connection_type' in latest and 'latency_ms' in latest:
                profile = self.network_optimizer.update_network_profile(
                    connection_type=latest.get('connection_type', 'unknown'),
                    signal_strength=latest.get('signal_strength', 3),
                    latency_ms=latest.get('latency_ms', 100),
                    is_metered=latest.get('connection_type') == 'cellular'
                )
                recommendations = {
                    'bandwidth_mode': profile.recommended_mode().value,
                    'recommended_batch_size': profile.recommended_batch_size(),
                    'use_compression': profile.recommended_mode().value in ['low', 'minimal', 'optimized']
                }

        return jsonify({
            "success": True,
            "processed": processed,
            "failed": failed,
            "total": len(events),
            "recommendations": recommendations
        }), 200

    def get_telemetry_summary_handler(self) -> tuple[dict[str, Any], int]:
        """
        Get aggregated telemetry summary (admin only).

        Query parameters:
        - hours: Time window in hours (default: 24)
        - event_type: Filter by event type
        - connection_type: Filter by connection type

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        # Check admin authentication if available
        if self.api_auth:
            auth_result = self.api_auth.require_admin(request)
            if auth_result is not None:
                return auth_result

        # Parse query parameters
        hours = request.args.get('hours', type=int)
        event_type = request.args.get('event_type')
        connection_type = request.args.get('connection_type')

        # Get statistics
        try:
            stats = self.telemetry_collector.get_stats(
                time_window_hours=hours,
                event_type=event_type,
                connection_type=connection_type
            )

            # Get bandwidth breakdown
            bandwidth_by_op = self.telemetry_collector.get_bandwidth_by_operation()

            # Get battery impact
            battery_by_op = self.telemetry_collector.get_battery_impact_by_operation()

            # Get performance trends
            trends = self.telemetry_collector.get_performance_trends(
                hours=hours or 24,
                bucket_size_minutes=60
            )

            summary = {
                "success": True,
                "statistics": stats.to_dict(),
                "bandwidth_by_operation": bandwidth_by_op,
                "battery_by_operation": battery_by_op,
                "performance_trends": trends,
                "filters": {
                    "time_window_hours": hours,
                    "event_type": event_type,
                    "connection_type": connection_type
                }
            }

            return jsonify(summary), 200

        except Exception as e:
            logger.error(f"Failed to get telemetry summary: {e}")
            return jsonify({"error": "Failed to generate summary"}), 500

    def get_optimization_handler(self) -> tuple[dict[str, Any], int]:
        """
        Get network optimization recommendations.

        Expected payload:
        {
            "connection_type": "wifi|cellular|offline",
            "signal_strength": 0-5,
            "latency_ms": 50.0,
            "bandwidth_kbps": 5000.0,
            "is_metered": false,
            "operation": "sync|transactions|blocks"
        }

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.json

        # Validate required fields
        if 'connection_type' not in data or 'latency_ms' not in data:
            return jsonify({
                "error": "connection_type and latency_ms required"
            }), 400

        # Update network profile
        profile = self.network_optimizer.update_network_profile(
            connection_type=data['connection_type'],
            signal_strength=data.get('signal_strength', 3),
            latency_ms=data['latency_ms'],
            estimated_bandwidth_kbps=data.get('bandwidth_kbps'),
            is_metered=data.get('is_metered', False)
        )

        # Get operation-specific recommendations
        operation = data.get('operation', 'sync')
        batch_size = self.network_optimizer.get_recommended_batch_size(operation)
        bandwidth_mode = self.network_optimizer.get_bandwidth_mode()

        # Optimize sync parameters
        base_params = {
            'batch_size': 50,
            'poll_interval': 30,
            'include_full_blocks': True,
            'include_tx_details': True
        }
        optimized_params = self.network_optimizer.optimize_sync_params(base_params)

        return jsonify({
            "success": True,
            "network_profile": profile.to_dict(),
            "bandwidth_mode": bandwidth_mode.value,
            "recommended_batch_size": batch_size,
            "optimized_sync_params": optimized_params,
            "quality_score": profile.quality_score(),
            "recommendations": {
                "use_compression": bandwidth_mode.value in ['low', 'minimal', 'optimized'],
                "reduce_polling": bandwidth_mode.value in ['low', 'minimal'],
                "queue_offline": profile.connection_type == ConnectionType.OFFLINE
            }
        }), 200

    def get_queue_status_handler(self) -> tuple[dict[str, Any], int]:
        """
        Get offline transaction queue status.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        status = self.network_optimizer.get_queue_status()
        return jsonify({
            "success": True,
            "queue": status
        }), 200

    def get_stats_handler(self) -> tuple[dict[str, Any], int]:
        """
        Get public telemetry statistics (limited view).

        Query parameters:
        - hours: Time window in hours (default: 24)

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        hours = request.args.get('hours', type=int, default=24)

        # Limit time window for public endpoint
        if hours > 168:  # 1 week
            hours = 168

        try:
            # Get overall statistics
            stats = self.telemetry_collector.get_stats(time_window_hours=hours)

            # Return limited view for public
            public_stats = {
                "success": True,
                "time_window_hours": hours,
                "event_count": stats.event_count,
                "avg_latency_ms": round(stats.avg_latency_ms, 2),
                "latency_percentiles": {
                    "p50": round(stats.latency_p50, 2),
                    "p95": round(stats.latency_p95, 2),
                    "p99": round(stats.latency_p99, 2)
                },
                "connection_type_distribution": stats.connection_types,
                "event_type_distribution": stats.event_types
            }

            return jsonify(public_stats), 200

        except Exception as e:
            logger.error(f"Failed to get telemetry stats: {e}")
            return jsonify({"error": "Failed to generate stats"}), 500

    def get_telemetry_collector(self) -> MobileTelemetryCollector:
        """Get telemetry collector instance"""
        return self.telemetry_collector

    def get_network_optimizer(self) -> NetworkOptimizer:
        """Get network optimizer instance"""
        return self.network_optimizer
