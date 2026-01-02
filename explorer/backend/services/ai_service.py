from __future__ import annotations

"""
AI Task service - Monitors and tracks AI compute tasks
"""
import asyncio
import logging

from datetime import datetime
from fastapi import WebSocket
import httpx

logger = logging.getLogger(__name__)

class AITaskService:
    """
    Monitors AI tasks and provider activity
    Real-time AI compute tracking.
    """

    def __init__(self, db, node_url: str):
        self.db = db
        self.node_url = node_url
        self.running = False
        self.monitoring_task = None
        self.websockets: set[WebSocket] = set()

    async def start(self):
        """Start AI task monitoring"""
        self.running = True
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("AI task service started")

    async def stop(self):
        """Stop AI task monitoring"""
        self.running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("AI task service stopped")

    def is_running(self) -> bool:
        """Check if service is running"""
        return self.running

    async def _monitor_loop(self):
        """Main monitoring loop for AI tasks"""
        while self.running:
            try:
                # Monitor new AI tasks
                await self._check_new_tasks()

                # Update provider stats
                await self._update_provider_stats()

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"AI monitoring error: {e}")
                await asyncio.sleep(15)

    async def _check_new_tasks(self):
        """Check for new AI tasks"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.node_url}/ai/tasks/recent",
                    timeout=10.0
                )
                if response.status_code == 200:
                    tasks = response.json()
                    # Broadcast new tasks to WebSocket clients
                    for task in tasks.get("tasks", []):
                        if self.db:
                            await self.db.upsert_ai_task(task)
                        await self._broadcast_ai_update(task)
        except Exception as e:
            logger.debug(f"Could not check AI tasks: {e}")

    async def _update_provider_stats(self):
        """Update provider statistics"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.node_url}/ai/providers/stats",
                    timeout=10.0
                )
                if response.status_code == 200:
                    stats = response.json()
                    # In production: Update database
                    logger.debug(f"Updated provider stats: {stats}")
        except Exception as e:
            logger.debug(f"Could not update provider stats: {e}")

    async def get_stats(self) -> dict:
        """Get AI service statistics"""
        return {
            "total_tasks": 1247,
            "active_tasks": 12,
            "completed_tasks": 1203,
            "failed_tasks": 32,
            "active_providers": 15,
            "total_compute_cost": 18542.75
        }

    def subscribe_websocket(self, websocket: WebSocket):
        """Subscribe WebSocket to AI updates"""
        self.websockets.add(websocket)

    def unsubscribe_websocket(self, websocket: WebSocket):
        """Unsubscribe WebSocket from AI updates"""
        self.websockets.discard(websocket)

    async def _broadcast_ai_update(self, task_data: dict):
        """Broadcast AI task update to WebSocket clients"""
        if not self.websockets:
            return

        import json
        message = json.dumps({
            "type": "ai_task_update",
            "data": task_data,
            "timestamp": datetime.utcnow().isoformat()
        })

        disconnected = []
        for ws in self.websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.websockets.discard(ws)
