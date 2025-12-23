"""
Sync API routes for chunked state synchronization.

Provides endpoints for mobile/bandwidth-constrained clients to sync state
in small chunks with resume capability.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Any

from flask import Response, jsonify, request, send_file

if TYPE_CHECKING:
    from xai.core.node_api import NodeAPI

logger = logging.getLogger(__name__)

def register_sync_routes(node_api: 'NodeAPI') -> None:
    """
    Register chunked sync API routes.

    Endpoints:
    - GET /sync/snapshot/latest - Get latest snapshot metadata
    - GET /sync/snapshot/<id> - Get specific snapshot metadata
    - GET /sync/snapshot/<id>/chunks - List all chunks
    - GET /sync/snapshot/<id>/chunk/<index> - Download specific chunk
    - POST /sync/snapshot/resume - Resume interrupted sync
    - GET /sync/snapshots - List all available snapshots
    """

    @node_api.app.route("/api/v1/sync/checkpoint/manifest", methods=["GET"])
    @node_api.app.route("/sync/snapshot/latest", methods=["GET"])
    def get_latest_snapshot() -> tuple[dict[str, Any], int]:
        """
        Get metadata for the latest available snapshot.

        Aliases:
        - /api/v1/sync/checkpoint/manifest (v1 API)
        - /sync/snapshot/latest (legacy)

        Returns:
            JSON response with snapshot metadata or error
        """
        try:
            blockchain = getattr(node_api.node, "blockchain", None)
            if not blockchain:
                return jsonify({"error": "Blockchain not available"}), 503

            checkpoint_sync = getattr(blockchain, "checkpoint_sync_manager", None)
            if not checkpoint_sync or not checkpoint_sync.enable_chunked_sync:
                return jsonify({"error": "Chunked sync not enabled"}), 503

            # Get latest snapshot ID
            snapshot_id = checkpoint_sync.chunked_service.get_latest_snapshot_id()
            if not snapshot_id:
                return jsonify({"error": "No snapshots available"}), 404

            # Get metadata
            metadata = checkpoint_sync.chunked_service.get_snapshot_metadata(snapshot_id)
            if not metadata:
                return jsonify({"error": "Snapshot metadata not found"}), 404

            return jsonify({
                "status": "ok",
                "snapshot": metadata.to_dict(),
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to get latest snapshot",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/sync/snapshot/<snapshot_id>", methods=["GET"])
    def get_snapshot_metadata(snapshot_id: str) -> tuple[dict[str, Any], int]:
        """
        Get metadata for a specific snapshot.

        Args:
            snapshot_id: ID of the snapshot

        Returns:
            JSON response with snapshot metadata or error
        """
        try:
            blockchain = getattr(node_api.node, "blockchain", None)
            if not blockchain:
                return jsonify({"error": "Blockchain not available"}), 503

            checkpoint_sync = getattr(blockchain, "checkpoint_sync_manager", None)
            if not checkpoint_sync or not checkpoint_sync.enable_chunked_sync:
                return jsonify({"error": "Chunked sync not enabled"}), 503

            # Get metadata
            metadata = checkpoint_sync.chunked_service.get_snapshot_metadata(snapshot_id)
            if not metadata:
                return jsonify({"error": "Snapshot not found"}), 404

            return jsonify({
                "status": "ok",
                "snapshot": metadata.to_dict(),
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to get snapshot metadata",
                extra={
                    "snapshot_id": snapshot_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/api/v1/sync/checkpoint/<snapshot_id>/chunks", methods=["GET"])
    @node_api.app.route("/sync/snapshot/<snapshot_id>/chunks", methods=["GET"])
    def list_snapshot_chunks(snapshot_id: str) -> tuple[dict[str, Any], int]:
        """
        List all chunks for a snapshot.

        Aliases:
        - /api/v1/sync/checkpoint/{id}/chunks (v1 API)
        - /sync/snapshot/{id}/chunks (legacy)

        Args:
            snapshot_id: ID of the snapshot

        Returns:
            JSON response with list of chunk metadata
        """
        try:
            blockchain = getattr(node_api.node, "blockchain", None)
            if not blockchain:
                return jsonify({"error": "Blockchain not available"}), 503

            checkpoint_sync = getattr(blockchain, "checkpoint_sync_manager", None)
            if not checkpoint_sync or not checkpoint_sync.enable_chunked_sync:
                return jsonify({"error": "Chunked sync not enabled"}), 503

            # Get snapshot metadata
            metadata = checkpoint_sync.chunked_service.get_snapshot_metadata(snapshot_id)
            if not metadata:
                return jsonify({"error": "Snapshot not found"}), 404

            # Build chunk list with priority information
            chunks = []
            for i in range(metadata.total_chunks):
                priority = metadata.priority_map.get(i, None)
                chunks.append({
                    "chunk_index": i,
                    "priority": priority.value if priority else 2,
                    "url": f"/sync/snapshot/{snapshot_id}/chunk/{i}",
                })

            return jsonify({
                "status": "ok",
                "snapshot_id": snapshot_id,
                "total_chunks": metadata.total_chunks,
                "chunks": chunks,
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to list snapshot chunks",
                extra={
                    "snapshot_id": snapshot_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/api/v1/sync/checkpoint/<snapshot_id>/chunk/<int:chunk_index>", methods=["GET"])
    @node_api.app.route("/sync/snapshot/<snapshot_id>/chunk/<int:chunk_index>", methods=["GET"])
    def download_chunk(snapshot_id: str, chunk_index: int) -> Response:
        """
        Download a specific chunk with Range header support.

        Supports HTTP Range headers for partial downloads and resume capability.

        Aliases:
        - /api/v1/sync/checkpoint/{id}/chunk/{n} (v1 API)
        - /sync/snapshot/{id}/chunk/{n} (legacy)

        Args:
            snapshot_id: ID of the snapshot
            chunk_index: Index of the chunk to download

        Returns:
            Binary chunk data or JSON error
        """
        try:
            blockchain = getattr(node_api.node, "blockchain", None)
            if not blockchain:
                return jsonify({"error": "Blockchain not available"}), 503

            checkpoint_sync = getattr(blockchain, "checkpoint_sync_manager", None)
            if not checkpoint_sync or not checkpoint_sync.enable_chunked_sync:
                return jsonify({"error": "Chunked sync not enabled"}), 503

            # Get chunk
            chunk = checkpoint_sync.chunked_service.get_chunk(snapshot_id, chunk_index)
            if not chunk:
                return jsonify({"error": "Chunk not found"}), 404

            # Prepare binary response
            data = chunk.data
            total_size = len(data)

            # Handle Range header for partial downloads
            range_header = request.headers.get("Range")
            if range_header:
                # Parse range header: "bytes=start-end"
                try:
                    range_str = range_header.replace("bytes=", "")
                    start, end = range_str.split("-")
                    start = int(start) if start else 0
                    end = int(end) if end else total_size - 1

                    # Validate range
                    if start >= total_size or end >= total_size or start > end:
                        return Response(
                            "Invalid range",
                            status=416,
                            headers={"Content-Range": f"bytes */{total_size}"}
                        )

                    # Slice data
                    data = data[start:end+1]

                    # Build response with 206 Partial Content
                    response = Response(
                        io.BytesIO(data),
                        status=206,
                        mimetype="application/octet-stream",
                        direct_passthrough=True,
                    )
                    response.headers["Content-Range"] = f"bytes {start}-{end}/{total_size}"
                    response.headers["Content-Length"] = str(len(data))
                    response.headers["Accept-Ranges"] = "bytes"

                except (ValueError, IndexError) as e:
                    logger.warning(
                        "Invalid Range header",
                        extra={
                            "range_header": range_header,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                    return Response("Invalid range format", status=400)

            else:
                # Full chunk download
                response = Response(
                    io.BytesIO(data),
                    status=200,
                    mimetype="application/octet-stream",
                    direct_passthrough=True,
                )
                response.headers["Content-Length"] = str(total_size)
                response.headers["Accept-Ranges"] = "bytes"

            # Add chunk metadata headers
            response.headers["X-Chunk-Index"] = str(chunk.chunk_index)
            response.headers["X-Total-Chunks"] = str(chunk.total_chunks)
            response.headers["X-Chunk-Checksum"] = chunk.checksum
            response.headers["X-Compressed"] = "true" if chunk.compressed else "false"

            return response

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError, OSError, IOError) as e:
            logger.error(
                "Failed to download chunk",
                extra={
                    "snapshot_id": snapshot_id,
                    "chunk_index": chunk_index,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/sync/snapshot/resume", methods=["POST"])
    def resume_sync() -> tuple[dict[str, Any], int]:
        """
        Get resume information for an interrupted sync.

        Request body:
        {
            "snapshot_id": "height_12345_abcd1234"
        }

        Returns:
            JSON response with progress and remaining chunks
        """
        try:
            data = request.get_json()
            if not data or "snapshot_id" not in data:
                return jsonify({"error": "snapshot_id required"}), 400

            snapshot_id = data["snapshot_id"]

            blockchain = getattr(node_api.node, "blockchain", None)
            if not blockchain:
                return jsonify({"error": "Blockchain not available"}), 503

            checkpoint_sync = getattr(blockchain, "checkpoint_sync_manager", None)
            if not checkpoint_sync or not checkpoint_sync.enable_chunked_sync:
                return jsonify({"error": "Chunked sync not enabled"}), 503

            # Get sync progress
            progress = checkpoint_sync.chunked_service.get_sync_progress(snapshot_id)
            if not progress:
                return jsonify({
                    "error": "No sync progress found for this snapshot"
                }), 404

            return jsonify({
                "status": "ok",
                "snapshot_id": snapshot_id,
                "progress_percent": progress.progress_percent,
                "downloaded_chunks": list(progress.downloaded_chunks),
                "remaining_chunks": progress.remaining_chunks,
                "failed_chunks": list(progress.failed_chunks),
                "total_chunks": progress.total_chunks,
                "started_at": progress.started_at,
                "last_chunk_at": progress.last_chunk_at,
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to get sync progress",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/sync/snapshots", methods=["GET"])
    def list_snapshots() -> tuple[dict[str, Any], int]:
        """
        List all available snapshots.

        Returns:
            JSON response with list of snapshot metadata (sorted by height descending)
        """
        try:
            blockchain = getattr(node_api.node, "blockchain", None)
            if not blockchain:
                return jsonify({"error": "Blockchain not available"}), 503

            checkpoint_sync = getattr(blockchain, "checkpoint_sync_manager", None)
            if not checkpoint_sync or not checkpoint_sync.enable_chunked_sync:
                return jsonify({"error": "Chunked sync not enabled"}), 503

            snapshots = checkpoint_sync.list_available_snapshots()

            return jsonify({
                "status": "ok",
                "count": len(snapshots),
                "snapshots": snapshots,
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to list snapshots",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/api/v1/sync/progress", methods=["GET"])
    def get_sync_progress_v1() -> tuple[dict[str, Any], int]:
        """
        Get current sync progress for the client.

        Returns progress for:
        - Checkpoint/snapshot download
        - Verification
        - State application

        Returns:
            JSON response with sync progress details
        """
        try:
            blockchain = getattr(node_api.node, "blockchain", None)
            if not blockchain:
                return jsonify({"error": "Blockchain not available"}), 503

            checkpoint_sync = getattr(blockchain, "checkpoint_sync_manager", None)
            if not checkpoint_sync:
                return jsonify({"error": "Checkpoint sync not available"}), 503

            # Get checkpoint sync progress
            progress = checkpoint_sync.get_checkpoint_sync_progress()

            return jsonify({
                "status": "ok",
                "progress": progress,
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to get sync progress",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/api/v1/sync/headers/status", methods=["GET"])
    def get_header_sync_status() -> tuple[dict[str, Any], int]:
        """
        Get current header sync status.

        Returns:
            JSON response with sync status including:
            - sync_state: Current sync state (syncing, synced, stalled, idle)
            - current_height: Current blockchain height
            - target_height: Target height to sync to
            - is_syncing: Boolean indicating if actively syncing
        """
        try:
            # Get light client service
            light_client_service = getattr(node_api.node, "light_client_service", None)
            if not light_client_service:
                return jsonify({"error": "Light client service not available"}), 503

            # Get sync progress
            sync_progress = light_client_service.get_sync_progress()

            return jsonify({
                "status": "ok",
                "sync_state": sync_progress.sync_state,
                "current_height": sync_progress.current_height,
                "target_height": sync_progress.target_height,
                "is_syncing": sync_progress.sync_state in ["syncing", "stalled"],
                "checkpoint_sync_enabled": sync_progress.checkpoint_sync_enabled,
                "checkpoint_height": sync_progress.checkpoint_height,
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to get header sync status",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return jsonify({"error": "Internal server error"}), 500

    @node_api.app.route("/api/v1/sync/headers/progress", methods=["GET"])
    def get_header_sync_progress() -> tuple[dict[str, Any], int]:
        """
        Get detailed header synchronization progress.

        Returns:
            JSON response with header sync progress including:
            - current_height: Number of headers synced
            - target_height: Total headers to sync
            - sync_percentage: Progress percentage
            - estimated_time_remaining: Estimated completion time (seconds)
            - headers_per_second: Current sync speed
            - sync_state: Current sync state
            - started_at: When sync started (ISO format)
        """
        try:
            # Get light client service
            light_client_service = getattr(node_api.node, "light_client_service", None)
            if not light_client_service:
                return jsonify({"error": "Light client service not available"}), 503

            # Get sync progress
            sync_progress = light_client_service.get_sync_progress()

            return jsonify({
                "status": "ok",
                "current_height": sync_progress.current_height,
                "target_height": sync_progress.target_height,
                "sync_percentage": sync_progress.sync_percentage,
                "estimated_time_remaining": sync_progress.estimated_time_remaining,
                "headers_per_second": sync_progress.headers_per_second,
                "sync_state": sync_progress.sync_state,
                "started_at": sync_progress.started_at.isoformat(),
                "checkpoint_sync_enabled": sync_progress.checkpoint_sync_enabled,
                "checkpoint_height": sync_progress.checkpoint_height,
            }), 200

        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as e:
            logger.error(
                "Failed to get header sync progress",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return jsonify({"error": "Internal server error"}), 500
