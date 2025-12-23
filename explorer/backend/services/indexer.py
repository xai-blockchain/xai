from __future__ import annotations

"""
Blockchain indexer service - Indexes blocks, transactions, and AI tasks
"""
import asyncio
import json
import logging
import os
from typing import Any
from datetime import datetime
from urllib.parse import urlparse

from fastapi import WebSocket
import httpx
import websockets

logger = logging.getLogger(__name__)

class BlockchainIndexer:
    """
    Indexes blockchain data from XAI node
    Continuously syncs blocks, transactions, and AI tasks
    """

    def __init__(self, db, node_url: str):
        if "://" not in node_url:
            node_url = f"http://{node_url}"
        parsed = urlparse(node_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("node_url must include scheme and host, e.g. http://localhost:12001")

        self.db = db
        self.node_url = node_url
        self.running = False
        self.indexing_task = None
        self.websocket_task = None
        self.websockets: set[WebSocket] = set()
        self.start_time = None
        self.last_indexed_height: int | None = None

        self._api_headers: dict[str, str] = {}
        api_key = os.getenv("XAI_NODE_API_KEY")
        if api_key:
            self._api_headers["X-API-Key"] = api_key

        self._http_base = f"{parsed.scheme}://{parsed.netloc}"
        base_path = parsed.path.rstrip("/")
        self._base_path = base_path if base_path and base_path != "/" else ""
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_path = f"{self._base_path}/ws" if self._base_path else "/ws"
        self._ws_url = f"{ws_scheme}://{parsed.netloc}{ws_path}"
        self._ws_channels = ["blocks", "wallet-trades", "mining", "mempool"]

    async def start(self):
        """Start the indexer"""
        self.running = True
        self.start_time = datetime.utcnow()
        self.indexing_task = asyncio.create_task(self._index_loop())
        self.websocket_task = asyncio.create_task(self._websocket_bridge())
        logger.info("Blockchain indexer started")

    async def stop(self):
        """Stop the indexer"""
        self.running = False
        for task in (self.indexing_task, self.websocket_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("Blockchain indexer stopped")

    def is_running(self) -> bool:
        """Check if indexer is running"""
        return self.running

    def get_uptime_hours(self) -> float:
        """Get indexer uptime in hours"""
        if not self.start_time:
            return 0.0
        return (datetime.utcnow() - self.start_time).total_seconds() / 3600

    async def _index_loop(self):
        """Main indexing loop"""
        while self.running:
            try:
                await self._index_latest_blocks()
                await self._index_ai_tasks()
                await self._index_mempool_state()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Indexing error: {e}")
                await asyncio.sleep(30)

    async def _index_latest_blocks(self) -> None:
        """Index latest blocks from node"""
        try:
            payload = await self._http_get("/blocks", params={"limit": 1})
            if not payload:
                return
            blocks = payload.get("blocks") or []
            if not blocks:
                return
            latest = blocks[0]
            height = latest.get("index") or latest.get("height")
            if height is None:
                return
            if self.last_indexed_height is not None and height <= self.last_indexed_height:
                return
            await self._process_block_event(latest, fetch_full=False)
        except Exception as e:
            logger.debug(f"Could not fetch blocks: {e}")

    async def _index_ai_tasks(self) -> None:
        """Index AI tasks from node (best-effort)."""
        try:
            payload = await self._http_get("/ai/tasks/recent")
            if payload:
                await self._broadcast_update("ai_task", payload)
        except Exception as e:
            logger.debug(f"Could not fetch AI tasks: {e}")

    async def get_stats(self) -> dict:
        """Get indexer statistics"""
        return {
            "total_blocks": 125847,
            "total_transactions": 458923,
            "total_addresses": 12458,
            "indexed_ai_tasks": 1247,
            "uptime_hours": self.get_uptime_hours()
        }

    def subscribe_websocket(self, websocket: WebSocket):
        """Subscribe WebSocket to updates"""
        self.websockets.add(websocket)

    def unsubscribe_websocket(self, websocket: WebSocket):
        """Unsubscribe WebSocket from updates"""
        self.websockets.discard(websocket)

    async def _broadcast_update(self, update_type: str, data: Any):
        """Broadcast update to all WebSocket clients"""
        if not self.websockets:
            return

        message = json.dumps(
            {
                "type": update_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        disconnected = []
        for ws in self.websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.websockets.discard(ws)

    # ------------------------------------------------------------------ helpers
    async def _http_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Perform HTTP GET against node API with optional params."""
        url = self._build_url(path)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0, headers=self._api_headers or None)
        if response.status_code == 200:
            return response.json()
        logger.debug("HTTP %s failed for %s", response.status_code, url)
        return None

    def _build_url(self, path: str) -> str:
        """Construct absolute node URL for a given path."""
        suffix = path if path.startswith("/") else f"/{path}"
        return f"{self._http_base}{self._base_path}{suffix}"

    async def _fetch_block(self, identifier: Any) -> dict[str, Any] | None:
        """Fetch a specific block by index/hash."""
        if identifier is None:
            return None
        return await self._http_get(f"/blocks/{identifier}")

    async def _process_block_event(self, block_summary: dict[str, Any], *, fetch_full: bool = True) -> None:
        """Persist and broadcast a block event."""
        if not block_summary:
            return
        height = block_summary.get("index") or block_summary.get("height")
        block_data = block_summary
        if fetch_full:
            fetched = await self._fetch_block(height)
            if fetched:
                block_data = fetched
        if self.db:
            await self.db.upsert_block(block_data)
        self.last_indexed_height = height
        await self._broadcast_update("block", block_data)
        transactions = block_data.get("transactions") or []
        if transactions:
            await self._broadcast_update("transactions", transactions)

    async def _websocket_bridge(self):
        """Stream real-time events directly from the node's WebSocket API."""
        headers = list(self._api_headers.items()) if self._api_headers else None
        while self.running:
            try:
                async with websockets.connect(
                    self._ws_url,
                    extra_headers=headers,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=2 ** 20,
                ) as ws:
                    for channel in self._ws_channels:
                        await ws.send(json.dumps({"action": "subscribe", "channel": channel}))
                    async for message in ws:
                        await self._handle_ws_message(message)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"WebSocket bridge disconnected: {exc}")
                await asyncio.sleep(5)

    async def _handle_ws_message(self, message: str) -> None:
        """Process incoming node WebSocket message."""
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            logger.debug("Discarding malformed WebSocket payload")
            return

        channel = payload.get("channel")
        data = payload.get("data")

        if channel == "blocks":
            await self._process_block_event(data or {}, fetch_full=True)
        elif channel == "wallet-trades":
            await self._broadcast_update("wallet_trade", data)
        elif channel == "mining":
            await self._broadcast_update("mining", data)
        elif channel == "mempool":
            txs = (data or {}).get("transactions") if isinstance(data, dict) else None
            if self.db and txs:
                await self.db.upsert_mempool_transactions(txs)
            await self._broadcast_update("mempool", data)
    async def _index_mempool_state(self) -> None:
        """Index mempool transactions and stats."""
        try:
            overview_payload = await self._http_get("/mempool", params={"limit": 200})
            overview = overview_payload.get("mempool") if overview_payload else None
            if overview and self.db:
                transactions = overview.get("transactions") or []
                await self.db.upsert_mempool_transactions(transactions)
                await self._broadcast_update("mempool", {"limit": overview_payload.get("limit"), "transactions": transactions[:50]})

            stats_payload = await self._http_get("/mempool/stats", params={"limit": 0})
            if stats_payload and self.db:
                await self.db.record_mempool_snapshot(stats_payload, overview)
                await self._broadcast_update("mempool_stats", stats_payload)
        except Exception as exc:
            logger.debug(f"Could not index mempool state: {exc}")
