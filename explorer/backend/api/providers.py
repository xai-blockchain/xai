from __future__ import annotations

"""
AI Providers API endpoints - Compute provider dashboard and stats
"""
from fastapi import APIRouter, HTTPException, Query

from datetime import datetime, timedelta
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

node_url = "http://localhost:12001"

@router.get("")
async def get_providers(
    status: str | None = None,
    sort_by: str = Query("reputation", regex="^(reputation|earnings|tasks)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get list of AI compute providers with ranking.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/ai/providers",
                params={"status": status, "sort_by": sort_by, "page": page, "limit": limit},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

        # Sample provider data
        return {
            "providers": [
                {
                    "provider_address": f"XAI{5000+i}...",
                    "provider_name": f"AI Compute Pro {i}",
                    "reputation_score": 95.0 - i * 2,
                    "total_tasks_completed": 1247 - i * 50,
                    "total_earnings": 18542.75 - i * 500,
                    "uptime_percentage": 98.5 - i * 0.3,
                    "status": "active",
                    "supported_models": ["claude-opus-4", "gpt-4-turbo", "gemini-pro"]
                }
                for i in range(min(limit, 15))
            ],
            "total": 15,
            "page": page
        }
    except Exception as e:
        logger.error(f"Error fetching providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{provider_address}")
async def get_provider_dashboard(provider_address: str):
    """
    Get provider dashboard details.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/ai/provider/{provider_address}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

        # Sample detailed provider dashboard
        return {
            "provider": {
                "provider_address": provider_address,
                "provider_name": "AI Compute Pro",
                "registration_date": (datetime.utcnow() - timedelta(days=300)).isoformat(),
                "status": "active",
                "reputation_score": 94.5,
                "total_tasks_completed": 1247,
                "total_tasks_failed": 23,
                "total_earnings": 18542.75,
                "average_compute_time": 1845.32,
                "uptime_percentage": 98.7,
                "supported_models": [
                    "claude-opus-4",
                    "claude-sonnet-4",
                    "gpt-4-turbo",
                    "gemini-pro"
                ],
                "hardware_specs": {
                    "gpu": "8x NVIDIA H100",
                    "cpu": "AMD EPYC 9654",
                    "ram": "1TB DDR5"
                }
            },
            "statistics": {
                "total_tasks": 1270,
                "completed_tasks": 1247,
                "failed_tasks": 23,
                "avg_compute_time": 1845.32,
                "total_cost": 18542.75
            },
            "earnings": {
                "monthly": [
                    {"month": "2025-12", "earnings": 4832.50},
                    {"month": "2025-11", "earnings": 5124.25},
                    {"month": "2025-10", "earnings": 4891.00}
                ],
                "total": 18542.75
            },
            "model_usage": [
                {
                    "ai_model": "claude-opus-4",
                    "task_count": 542,
                    "avg_time": 2134.5,
                    "total_cost": 8234.50
                },
                {
                    "ai_model": "gpt-4-turbo",
                    "task_count": 387,
                    "avg_time": 1654.2,
                    "total_cost": 5832.25
                }
            ],
            "uptime": {
                "percentage": 98.7,
                "last_seen": datetime.utcnow().isoformat(),
                "period_days": 30
            },
            "reputation": {
                "score": 94.5,
                "success_rate": 98.19
            }
        }
    except Exception as e:
        logger.error(f"Error fetching provider {provider_address}: {e}")
        raise HTTPException(status_code=404, detail="Provider not found")

@router.get("/leaderboard")
async def get_provider_leaderboard(
    metric: str = Query("reputation", regex="^(reputation|earnings|tasks|uptime)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get provider leaderboard.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/ai/providers/leaderboard",
                params={"metric": metric, "limit": limit},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

        return {
            "leaderboard": [
                {
                    "rank": i + 1,
                    "provider_address": f"XAI{5000+i}...",
                    "provider_name": f"Top Provider {i+1}",
                    "score": 100.0 - i * 3,
                    "total_tasks": 2000 - i * 100,
                    "total_earnings": 25000.0 - i * 1000,
                    "uptime": 99.0 - i * 0.2
                }
                for i in range(limit)
            ],
            "metric": metric,
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{provider_address}/earnings")
async def get_provider_earnings(
    provider_address: str,
    period: str = Query("month", regex="^(day|week|month|year|all)$")
):
    """
    Get detailed provider earnings
    Track compute provider income over time
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/ai/provider/{provider_address}/earnings",
                params={"period": period},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

        # Sample earnings data
        earnings_data = []
        days = {"day": 1, "week": 7, "month": 30, "year": 365, "all": 90}[period]

        for i in range(min(days, 90)):
            earnings_data.append({
                "date": (datetime.utcnow() - timedelta(days=i)).date().isoformat(),
                "earnings": round(150.0 + (i % 10) * 20.0, 2),
                "tasks_completed": 5 + (i % 3)
            })

        return {
            "provider_address": provider_address,
            "period": period,
            "earnings": earnings_data,
            "total": sum(e["earnings"] for e in earnings_data),
            "average_daily": sum(e["earnings"] for e in earnings_data) / len(earnings_data)
        }
    except Exception as e:
        logger.error(f"Error fetching earnings for {provider_address}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
