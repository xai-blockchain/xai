from __future__ import annotations

"""
XAI Blockchain Explorer - FastAPI Backend
Production-grade API with AI-specific features
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
import logging
import os
from typing import Any

from api import blockchain, ai_tasks, providers, analytics, governance, staking
from services.indexer import BlockchainIndexer
from services.ai_service import AITaskService
from database.connection import Database
from security import APIAuthConfig, APIKeyAuthError, enforce_websocket_api_key, optional_dependencies

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
db: Database = None
indexer: BlockchainIndexer = None
ai_service: AITaskService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting XAI Blockchain Explorer...")

    global db, indexer, ai_service

    # Initialize database connection
    database_url = os.getenv("DATABASE_URL", "postgresql://xai:xai@localhost/xai_explorer")
    db = Database(database_url)
    await db.connect()
    logger.info("Database connected")
    await db.run_migrations()
    logger.info("Database migrations ensured")

    # Initialize blockchain indexer
    node_url = os.getenv("XAI_NODE_URL", "http://localhost:12001")
    indexer = BlockchainIndexer(db, node_url)
    await indexer.start()
    logger.info("Blockchain indexer started")

    # Initialize AI task service
    ai_service = AITaskService(db, node_url)
    await ai_service.start()
    logger.info("AI task service started")

    logger.info("XAI Blockchain Explorer started successfully!")

    yield

    # Shutdown
    logger.info("Shutting down XAI Blockchain Explorer...")

    if ai_service:
        await ai_service.stop()

    if indexer:
        await indexer.stop()

    if db:
        await db.disconnect()

    logger.info("XAI Blockchain Explorer stopped")

# Create FastAPI application
app = FastAPI(
    title="XAI Blockchain Explorer API",
    description="Production-grade blockchain explorer with AI compute features",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:12080,http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
auth_config = APIAuthConfig(
    require_api_key=os.getenv("EXPLORER_REQUIRE_API_KEY", "false").lower() == "true",
    key_file=os.getenv("EXPLORER_API_KEY_SECRET_PATH"),
)
route_dependencies = optional_dependencies(auth_config)
router_kwargs: dict[str, Any] = {}
if route_dependencies:
    # dependencies expects fastapi.Depends wrappers
    router_kwargs["dependencies"] = route_dependencies

app.include_router(blockchain.router, prefix="/api/v1", tags=["Blockchain"], **router_kwargs)
app.include_router(ai_tasks.router, prefix="/api/v1/ai", tags=["AI Tasks"], **router_kwargs)
app.include_router(providers.router, prefix="/api/v1/ai/providers", tags=["AI Providers"], **router_kwargs)
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"], **router_kwargs)
app.include_router(governance.router, prefix="/api/v1/governance", tags=["Governance"], **router_kwargs)
app.include_router(staking.router, prefix="/api/v1/staking", tags=["Staking"], **router_kwargs)

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "XAI Blockchain Explorer API",
        "version": "1.0.0",
        "description": "AI task explorer and blockchain analytics",
        "features": {
            "blockchain": ["blocks", "transactions", "addresses", "search"],
            "ai": [
                "task_explorer",
                "compute_providers",
                "model_comparison",
                "live_feed",
                "earnings_tracking"
            ],
            "governance": [
                "proposals",
                "voting",
                "tally"
            ],
            "staking": [
                "validators",
                "delegations",
                "rewards",
                "unbonding"
            ],
            "analytics": [
                "network_stats",
                "ai_usage_metrics",
                "provider_performance",
                "model_benchmarks"
            ],
            "realtime": ["websocket_blocks", "websocket_transactions", "websocket_ai_tasks"]
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "blockchain": "/api/v1/blocks",
            "ai_tasks": "/api/v1/ai/tasks",
            "providers": "/api/v1/ai/providers",
            "governance": "/api/v1/governance/proposals",
            "staking": "/api/v1/staking/validators",
            "websocket": "/api/v1/ws"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_healthy = await db.is_connected() if db else False

        # Check indexer status
        indexer_healthy = indexer.is_running() if indexer else False

        # Check AI service status
        ai_service_healthy = ai_service.is_running() if ai_service else False

        overall_healthy = db_healthy and indexer_healthy and ai_service_healthy

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "components": {
                "database": "connected" if db_healthy else "disconnected",
                "indexer": "running" if indexer_healthy else "stopped",
                "ai_service": "running" if ai_service_healthy else "stopped"
            },
            "timestamp": "2025-12-04T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-12-04T12:00:00Z"
            }
        )

# WebSocket endpoint for live updates
@app.websocket("/api/v1/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Universal WebSocket endpoint for live updates
    Sends: blocks, transactions, AI tasks
    """
    if auth_config.require_api_key:
        try:
            await enforce_websocket_api_key(websocket, auth_config)
        except APIKeyAuthError as exc:
            logger.warning("WebSocket authentication failed: %s", exc)
            return

    await websocket.accept()
    logger.info("WebSocket client connected to /live")

    try:
        # Subscribe to all update feeds
        if indexer:
            indexer.subscribe_websocket(websocket)

        if ai_service:
            ai_service.subscribe_websocket(websocket)

        # Keep connection alive
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")

            # Handle subscription changes
            elif data.startswith("subscribe:"):
                topic = data.split(":", 1)[1]
                logger.info(f"Client subscribed to: {topic}")

            elif data.startswith("unsubscribe:"):
                topic = data.split(":", 1)[1]
                logger.info(f"Client unsubscribed from: {topic}")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /live")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        # Unsubscribe from feeds
        if indexer:
            indexer.unsubscribe_websocket(websocket)

        if ai_service:
            ai_service.unsubscribe_websocket(websocket)

@app.get("/api/v1/mempool", dependencies=route_dependencies)
async def get_mempool(limit: int = 50):
    """Return recent mempool transactions and latest snapshot."""
    if not db:
        return JSONResponse(status_code=503, content={"error": "Database unavailable"})
    limit = max(1, min(limit, 200))
    transactions = await db.get_recent_mempool_transactions(limit)
    stats = await db.get_latest_mempool_stats()
    return {
        "transactions": jsonable_encoder(transactions),
        "stats": jsonable_encoder(stats),
        "limit": limit,
    }

@app.get("/api/v1/mempool/stats", dependencies=route_dependencies)
async def get_mempool_stats():
    """Return the most recent mempool congestion snapshot."""
    if not db:
        return JSONResponse(status_code=503, content={"error": "Database unavailable"})
    stats = await db.get_latest_mempool_stats()
    if not stats:
        return JSONResponse(status_code=404, content={"error": "No mempool data available"})
    return jsonable_encoder(stats)

@app.get("/api/v1/stats", dependencies=route_dependencies)
async def get_stats():
    """Get comprehensive statistics"""
    try:
        blockchain_stats = await indexer.get_stats() if indexer else {}
        ai_stats = await ai_service.get_stats() if ai_service else {}

        return {
            "blockchain": blockchain_stats,
            "ai": ai_stats,
            "explorer": {
                "uptime_hours": indexer.get_uptime_hours() if indexer else 0,
                "indexed_blocks": blockchain_stats.get("total_blocks", 0),
                "indexed_ai_tasks": ai_stats.get("total_tasks", 0)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch stats", "detail": str(e)}
        )

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting XAI Blockchain Explorer on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("RELOAD", "False").lower() == "true",
        log_level="info",
        access_log=True
    )
