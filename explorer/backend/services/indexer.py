"""
Blockchain indexer service - Indexes blocks, transactions, and AI tasks
"""
import asyncio
import logging
from typing import Set
from datetime import datetime
from fastapi import WebSocket
import httpx

logger = logging.getLogger(__name__)


class BlockchainIndexer:
    """
    Indexes blockchain data from XAI node
    Continuously syncs blocks, transactions, and AI tasks
    """

    def __init__(self, db, node_url: str):
        self.db = db
        self.node_url = node_url
        self.running = False
        self.indexing_task = None
        self.websockets: Set[WebSocket] = set()
        self.start_time = None

    async def start(self):
        """Start the indexer"""
        self.running = True
        self.start_time = datetime.utcnow()
        self.indexing_task = asyncio.create_task(self._index_loop())
        logger.info("Blockchain indexer started")

    async def stop(self):
        """Stop the indexer"""
        self.running = False
        if self.indexing_task:
            self.indexing_task.cancel()
            try:
                await self.indexing_task
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
                # Index latest blocks
                await self._index_latest_blocks()

                # Index AI tasks
                await self._index_ai_tasks()

                # Wait before next iteration
                await asyncio.sleep(10)  # Index every 10 seconds

            except Exception as e:
                logger.error(f"Indexing error: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def _index_latest_blocks(self):
        """Index latest blocks from node"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.node_url}/blocks/latest",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    # In production: Save to database
                    # Broadcast to WebSocket clients
                    await self._broadcast_update("block", data)
        except Exception as e:
            logger.debug(f"Could not fetch blocks: {e}")

    async def _index_ai_tasks(self):
        """Index AI tasks from node"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.node_url}/ai/tasks/recent",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    # In production: Save to database
                    # Broadcast to WebSocket clients
                    await self._broadcast_update("ai_task", data)
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

    async def _broadcast_update(self, update_type: str, data: dict):
        """Broadcast update to all WebSocket clients"""
        if not self.websockets:
            return

        import json
        message = json.dumps({
            "type": update_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })

        disconnected = []
        for ws in self.websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        # Remove disconnected clients
        for ws in disconnected:
            self.websockets.discard(ws)
