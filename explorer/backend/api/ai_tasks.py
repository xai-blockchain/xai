from __future__ import annotations

"""
AI tasks API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException, Depends

from datetime import datetime, timedelta
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# XAI Node connection
node_url = "http://localhost:12001"

@router.get("/tasks")
async def get_ai_tasks(
    status: str | None = None,
    task_type: str | None = None,
    ai_model: str | None = None,
    provider: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get list of AI tasks with filtering and pagination.
    """
    try:
        # In production, this queries the database
        # For now, generate sample data from XAI node or mock
        tasks = []

        # Try to get from XAI node
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{node_url}/ai/tasks",
                    params={
                        "status": status,
                        "task_type": task_type,
                        "ai_model": ai_model,
                        "provider": provider,
                        "page": page,
                        "limit": limit
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch from node: {e}")

        # Return sample data for demonstration
        return {
            "tasks": [
                {
                    "task_id": f"task_{i}",
                    "task_type": "security_audit" if i % 3 == 0 else "core_feature",
                    "complexity": "complex" if i % 2 == 0 else "moderate",
                    "status": "completed" if i % 4 != 0 else "in_progress",
                    "provider_address": f"XAI{1000+i}...",
                    "ai_model": ["claude-opus-4", "gpt-4-turbo", "gemini-pro"][i % 3],
                    "cost_estimate": round(10.5 + i * 0.3, 2),
                    "actual_cost": round(9.8 + i * 0.28, 2) if i % 4 != 0 else None,
                    "compute_time_seconds": 1800 + i * 50 if i % 4 != 0 else None,
                    "created_at": (datetime.utcnow() - timedelta(hours=i)).isoformat()
                }
                for i in range(20)
            ],
            "total": 156,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error fetching AI tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/{task_id}")
async def get_ai_task_detail(task_id: str):
    """
    Get detailed information about a specific AI task
    Shows complete task lifecycle, results, and compute metrics
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{node_url}/ai/task/{task_id}", timeout=10.0)
            if response.status_code == 200:
                return response.json()

        # Return sample detailed task
        return {
            "task_id": task_id,
            "task_type": "security_audit",
            "complexity": "critical",
            "priority": "critical",
            "status": "completed",
            "requester_address": "XAI1abcd...",
            "provider_address": "XAI5efgh...",
            "ai_model": "claude-opus-4",
            "estimated_tokens": 180000,
            "actual_tokens": 165432,
            "cost_estimate": 13.50,
            "actual_cost": 12.41,
            "started_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "completed_at": (datetime.utcnow() - timedelta(minutes=30)).isoformat(),
            "compute_time_seconds": 1902,
            "result_hash": "7f3d92abc...",
            "result_data": {
                "vulnerabilities_found": 3,
                "critical_issues": 1,
                "recommendations": 8,
                "security_score": 87.5
            },
            "created_at": (datetime.utcnow() - timedelta(hours=3)).isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching AI task {task_id}: {e}")
        raise HTTPException(status_code=404, detail="Task not found")

@router.get("/models")
async def get_ai_models():
    """
    Get AI model statistics and performance comparison.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{node_url}/ai/models", timeout=10.0)
            if response.status_code == 200:
                return response.json()

        # Return sample model stats
        return {
            "models": [
                {
                    "model_name": "claude-opus-4",
                    "provider": "anthropic",
                    "total_tasks": 542,
                    "success_rate": 98.5,
                    "average_compute_time": 2134.5,
                    "average_cost": 15.18,
                    "quality_score": 94.2,
                    "last_used": datetime.utcnow().isoformat()
                },
                {
                    "model_name": "gpt-4-turbo",
                    "provider": "openai",
                    "total_tasks": 387,
                    "success_rate": 96.8,
                    "average_compute_time": 1654.2,
                    "average_cost": 15.07,
                    "quality_score": 91.5,
                    "last_used": datetime.utcnow().isoformat()
                },
                {
                    "model_name": "gemini-pro",
                    "provider": "google",
                    "total_tasks": 298,
                    "success_rate": 95.3,
                    "average_compute_time": 1823.8,
                    "average_cost": 12.45,
                    "quality_score": 88.7,
                    "last_used": datetime.utcnow().isoformat()
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching AI models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_ai_stats():
    """
    Get overall AI usage statistics
    Network-wide AI compute metrics
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{node_url}/ai/stats", timeout=10.0)
            if response.status_code == 200:
                return response.json()

        return {
            "total_tasks": 1247,
            "completed_tasks": 1203,
            "active_tasks": 12,
            "failed_tasks": 32,
            "total_compute_hours": 623.5,
            "total_cost": 18542.75,
            "active_providers": 15,
            "models_in_use": 8,
            "average_task_time": 1798.3,
            "success_rate": 96.5
        }
    except Exception as e:
        logger.error(f"Error fetching AI stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
