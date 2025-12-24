"""Admin profiling and performance monitoring routes.

This module provides REST API endpoints for CPU and memory profiling,
allowing administrators to start/stop profilers and retrieve performance data.

Endpoints:
- GET /admin/profiling/status - Get profiling subsystem status
- POST /admin/profiling/memory/start - Start memory profiler
- POST /admin/profiling/memory/stop - Stop memory profiler
- POST /admin/profiling/memory/snapshot - Take memory snapshot
- POST /admin/profiling/cpu/start - Start CPU profiler
- POST /admin/profiling/cpu/stop - Stop CPU profiler
- GET /admin/profiling/cpu/hotspots - Get CPU hotspots
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from flask import request

from xai.performance.profiling import CPUProfiler, MemoryProfiler

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPIRoutes

logger = logging.getLogger(__name__)


def register_admin_profiling_routes(routes: "NodeAPIRoutes") -> None:
    """Register admin profiling endpoints.

    All routes require admin/operator authentication via _require_control_role().
    """
    app = routes.app

    def _memory_profiler() -> MemoryProfiler:
        profiler = getattr(routes, "memory_profiler", None)
        if not isinstance(profiler, MemoryProfiler):
            profiler = MemoryProfiler()
            routes.memory_profiler = profiler
        return profiler

    def _cpu_profiler() -> CPUProfiler:
        profiler = getattr(routes, "cpu_profiler", None)
        if not isinstance(profiler, CPUProfiler):
            profiler = CPUProfiler()
            routes.cpu_profiler = profiler
        return profiler

    @app.route("/admin/profiling/status", methods=["GET"])
    def admin_profiling_status() -> tuple[dict[str, Any], int]:
        """Return profiling subsystem status (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        memory = _memory_profiler()
        cpu = _cpu_profiler()
        memory_stats = memory.get_memory_stats() if memory.is_profiling else {}
        cpu_hotspots = cpu.get_hotspots(top_n=5) if cpu.profiler else []
        payload = {
            "memory": {
                "running": memory.is_profiling,
                "snapshot_count": len(memory.snapshots),
                "stats": memory_stats,
            },
            "cpu": {
                "running": cpu.is_profiling,
                "has_profiler": cpu.profiler is not None,
                "hotspots": cpu_hotspots,
            },
        }
        return routes._success_response(payload)

    @app.route("/admin/profiling/memory/start", methods=["POST"])
    def admin_memory_start() -> tuple[dict[str, Any], int]:
        """Start memory profiler (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error
        profiler = _memory_profiler()
        if profiler.is_profiling:
            return routes._success_response({"started": False, "message": "Memory profiler already running"})
        profiler.start()
        routes._log_event("admin_memory_profiler_start", {"snapshots": len(profiler.snapshots)}, severity="INFO")
        return routes._success_response({"started": True})

    @app.route("/admin/profiling/memory/stop", methods=["POST"])
    def admin_memory_stop() -> tuple[dict[str, Any], int]:
        """Stop memory profiler (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error
        profiler = _memory_profiler()
        if not profiler.is_profiling:
            return routes._success_response({"stopped": False, "message": "Memory profiler not running"})
        profiler.stop()
        routes._log_event("admin_memory_profiler_stop", {"snapshots": len(profiler.snapshots)}, severity="INFO")
        return routes._success_response({"stopped": True})

    @app.route("/admin/profiling/memory/snapshot", methods=["POST"])
    def admin_memory_snapshot() -> tuple[dict[str, Any], int]:
        """Take memory snapshot (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        profiler = _memory_profiler()
        if not profiler.is_profiling:
            return routes._error_response("Memory profiler not running", status=400, code="profiler_inactive")

        payload = request.get_json(silent=True) or {}
        top_n = int(payload.get("top_n") or 10)
        snapshot = profiler.take_snapshot(top_n=top_n)
        return routes._success_response(
            {
                "timestamp": snapshot.timestamp,
                "current_mb": snapshot.current_mb,
                "peak_mb": snapshot.peak_mb,
                "top_allocations": snapshot.top_allocations,
                "snapshot_count": len(profiler.snapshots),
            }
        )

    @app.route("/admin/profiling/cpu/start", methods=["POST"])
    def admin_cpu_start() -> tuple[dict[str, Any], int]:
        """Start CPU profiler (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        profiler = _cpu_profiler()
        if profiler.is_profiling:
            return routes._success_response({"started": False, "message": "CPU profiler already running"})
        profiler.start()
        routes._log_event("admin_cpu_profiler_start", {}, severity="INFO")
        return routes._success_response({"started": True})

    @app.route("/admin/profiling/cpu/stop", methods=["POST"])
    def admin_cpu_stop() -> tuple[dict[str, Any], int]:
        """Stop CPU profiler (admin only)."""
        auth_error = routes._require_control_role({"admin"})
        if auth_error:
            return auth_error

        profiler = _cpu_profiler()
        if not profiler.is_profiling:
            return routes._success_response({"stopped": False, "message": "CPU profiler not running"})
        profiler.stop()
        summary = profiler.get_stats(top_n=20)
        routes._log_event("admin_cpu_profiler_stop", {"summary_length": len(summary)}, severity="INFO")
        return routes._success_response({"stopped": True, "summary": summary})

    @app.route("/admin/profiling/cpu/hotspots", methods=["GET"])
    def admin_cpu_hotspots() -> tuple[dict[str, Any], int]:
        """Get CPU hotspots (admin/operator)."""
        auth_error = routes._require_control_role({"admin", "operator"})
        if auth_error:
            return auth_error

        profiler = _cpu_profiler()
        top_n = int(request.args.get("top", 10))
        hotspots = profiler.get_hotspots(top_n=top_n)
        return routes._success_response({"hotspots": hotspots, "running": profiler.is_profiling})
