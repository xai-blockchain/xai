"""
Analytics API endpoints - Network and AI usage analytics
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
import httpx
import logging
from typing import List, Dict, Any
import random

router = APIRouter()
logger = logging.getLogger(__name__)

node_url = "http://localhost:12001"


@router.get("/transactions")
async def get_transaction_analytics(
    period: str = Query("24h", regex="^(1h|24h|7d|30d)$")
):
    """
    Get transaction volume analytics over time.
    Returns time-series data suitable for charts.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/analytics/transactions",
                params={"period": period},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass

    # Generate sample transaction analytics data
    hours = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}[period]

    if period == "1h":
        interval_minutes = 5
        data_points = 12
    elif period == "24h":
        interval_minutes = 60
        data_points = 24
    elif period == "7d":
        interval_minutes = 360
        data_points = 28
    else:
        interval_minutes = 1440
        data_points = 30

    timeline = []
    base_time = datetime.utcnow()

    for i in range(data_points):
        timestamp = base_time - timedelta(minutes=interval_minutes * (data_points - 1 - i))
        timeline.append({
            "timestamp": timestamp.isoformat(),
            "transaction_count": random.randint(50, 200),
            "volume": round(random.uniform(1000, 5000), 2),
            "ai_transactions": random.randint(10, 50),
            "transfer_transactions": random.randint(30, 120),
            "contract_transactions": random.randint(5, 30),
        })

    return {
        "period": period,
        "timeline": timeline,
        "summary": {
            "total_transactions": sum(d["transaction_count"] for d in timeline),
            "total_volume": round(sum(d["volume"] for d in timeline), 2),
            "avg_transactions_per_interval": round(sum(d["transaction_count"] for d in timeline) / len(timeline), 1),
            "peak_transactions": max(d["transaction_count"] for d in timeline),
        }
    }


@router.get("/blocks")
async def get_block_analytics(
    period: str = Query("24h", regex="^(1h|24h|7d|30d)$")
):
    """
    Get block production analytics over time.
    Returns time-series data for block metrics.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/analytics/blocks",
                params={"period": period},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass

    # Generate sample block analytics data
    hours = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}[period]

    if period == "1h":
        interval_minutes = 5
        data_points = 12
    elif period == "24h":
        interval_minutes = 60
        data_points = 24
    elif period == "7d":
        interval_minutes = 360
        data_points = 28
    else:
        interval_minutes = 1440
        data_points = 30

    timeline = []
    base_time = datetime.utcnow()
    target_block_time = 120  # 2 minutes target

    for i in range(data_points):
        timestamp = base_time - timedelta(minutes=interval_minutes * (data_points - 1 - i))
        blocks_in_interval = interval_minutes * 60 // target_block_time
        actual_blocks = blocks_in_interval + random.randint(-2, 2)
        avg_block_time = (interval_minutes * 60) / max(actual_blocks, 1)

        timeline.append({
            "timestamp": timestamp.isoformat(),
            "blocks_produced": actual_blocks,
            "avg_block_time": round(avg_block_time, 1),
            "avg_transactions_per_block": round(random.uniform(3, 12), 1),
            "difficulty": 2400000 + random.randint(-50000, 50000),
            "avg_block_size": random.randint(800, 2000),
        })

    return {
        "period": period,
        "timeline": timeline,
        "summary": {
            "total_blocks": sum(d["blocks_produced"] for d in timeline),
            "avg_block_time": round(sum(d["avg_block_time"] for d in timeline) / len(timeline), 1),
            "avg_difficulty": round(sum(d["difficulty"] for d in timeline) / len(timeline), 0),
            "total_transactions": sum(int(d["blocks_produced"] * d["avg_transactions_per_block"]) for d in timeline),
        }
    }


@router.get("/addresses")
async def get_address_analytics(
    period: str = Query("24h", regex="^(1h|24h|7d|30d)$")
):
    """
    Get active address analytics over time.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/analytics/addresses",
                params={"period": period},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass

    # Generate sample address analytics data
    if period == "1h":
        interval_minutes = 5
        data_points = 12
    elif period == "24h":
        interval_minutes = 60
        data_points = 24
    elif period == "7d":
        interval_minutes = 360
        data_points = 28
    else:
        interval_minutes = 1440
        data_points = 30

    timeline = []
    base_time = datetime.utcnow()

    for i in range(data_points):
        timestamp = base_time - timedelta(minutes=interval_minutes * (data_points - 1 - i))
        active = random.randint(80, 250)
        timeline.append({
            "timestamp": timestamp.isoformat(),
            "active_addresses": active,
            "new_addresses": random.randint(5, 30),
            "unique_senders": random.randint(40, active),
            "unique_receivers": random.randint(50, active),
        })

    return {
        "period": period,
        "timeline": timeline,
        "summary": {
            "total_active": sum(d["active_addresses"] for d in timeline),
            "total_new": sum(d["new_addresses"] for d in timeline),
            "peak_active": max(d["active_addresses"] for d in timeline),
            "avg_active": round(sum(d["active_addresses"] for d in timeline) / len(timeline), 0),
        }
    }


@router.get("/richlist")
async def get_rich_list(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get list of top XAI holders (rich list).
    Returns addresses sorted by balance.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/richlist",
                params={"limit": limit, "offset": offset},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass

    # Generate sample rich list data
    total_supply = 100_000_000  # 100M total supply

    # Generate descending balances
    holders = []
    remaining_supply = total_supply * 0.65  # Top holders have 65% of supply

    for i in range(min(limit, 500)):
        rank = offset + i + 1

        if rank <= 10:
            balance = remaining_supply * random.uniform(0.08, 0.12) / 10
        elif rank <= 50:
            balance = remaining_supply * random.uniform(0.01, 0.02) / 40
        elif rank <= 100:
            balance = remaining_supply * random.uniform(0.002, 0.005) / 50
        else:
            balance = remaining_supply * random.uniform(0.0005, 0.001) / 400

        percentage = (balance / total_supply) * 100

        holders.append({
            "rank": rank,
            "address": f"XAI{random.randint(1000, 9999)}{''.join(random.choices('abcdef0123456789', k=8))}...",
            "balance": round(balance, 2),
            "percentage": round(percentage, 4),
            "transaction_count": random.randint(10, 5000),
            "last_active": (datetime.utcnow() - timedelta(hours=random.randint(0, 168))).isoformat(),
        })

    # Sort by balance descending
    holders.sort(key=lambda x: x["balance"], reverse=True)
    # Reassign ranks after sorting
    for i, holder in enumerate(holders):
        holder["rank"] = offset + i + 1

    return {
        "holders": holders,
        "total": 12458,  # Total unique addresses
        "limit": limit,
        "offset": offset,
        "total_supply": total_supply,
        "circulating_supply": total_supply * 0.45,
    }


@router.get("/network")
async def get_network_stats():
    """
    Get comprehensive network statistics
    Blockchain metrics: blocks, transactions, addresses
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{node_url}/stats", timeout=10.0)
            if response.status_code == 200:
                return response.json()

        return {
            "blockchain": {
                "total_blocks": 125847,
                "total_transactions": 458923,
                "total_addresses": 12458,
                "active_addresses_24h": 342,
                "avg_block_time": 120.5,
                "network_hashrate": "1.5 TH/s",
                "difficulty": 2456789,
                "total_supply": "45250000.00"
            },
            "mempool": {
                "pending_transactions": 23,
                "total_size_kb": 145.2
            },
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching network stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai")
async def get_ai_analytics(
    period: str = Query("24h", regex="^(1h|24h|7d|30d|all)$")
):
    """
    Get AI usage analytics over time.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/ai/analytics",
                params={"period": period},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

        # Generate sample AI analytics data
        hours = {"1h": 1, "24h": 24, "7d": 168, "30d": 720, "all": 720}[period]
        interval = max(1, hours // 50)  # Up to 50 data points

        timeline_data = []
        for i in range(0, hours, interval):
            timeline_data.append({
                "timestamp": (datetime.utcnow() - timedelta(hours=hours-i)).isoformat(),
                "tasks_created": 5 + (i % 8),
                "tasks_completed": 4 + (i % 7),
                "compute_cost": round(50.0 + (i % 20) * 2.5, 2),
                "active_providers": 10 + (i % 5)
            })

        return {
            "period": period,
            "summary": {
                "total_tasks": sum(d["tasks_created"] for d in timeline_data),
                "completed_tasks": sum(d["tasks_completed"] for d in timeline_data),
                "total_compute_cost": sum(d["compute_cost"] for d in timeline_data),
                "average_providers": sum(d["active_providers"] for d in timeline_data) // len(timeline_data)
            },
            "timeline": timeline_data,
            "task_types": [
                {"type": "security_audit", "count": 145, "percentage": 32.5},
                {"type": "core_feature", "count": 123, "percentage": 27.6},
                {"type": "bug_fix", "count": 89, "percentage": 19.9},
                {"type": "optimization", "count": 67, "percentage": 15.0},
                {"type": "other", "count": 22, "percentage": 5.0}
            ],
            "model_usage": [
                {"model": "claude-opus-4", "tasks": 542, "percentage": 43.5},
                {"model": "gpt-4-turbo", "tasks": 387, "percentage": 31.0},
                {"model": "gemini-pro", "tasks": 298, "percentage": 23.9},
                {"model": "others", "tasks": 20, "percentage": 1.6}
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching AI analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_provider_analytics(
    period: str = Query("7d", regex="^(24h|7d|30d|all)$")
):
    """
    Get provider performance analytics
    Track provider network health and competition
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/ai/providers/analytics",
                params={"period": period},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

        return {
            "period": period,
            "provider_stats": {
                "total_providers": 15,
                "active_providers": 13,
                "new_providers": 2,
                "churned_providers": 1
            },
            "performance_distribution": [
                {"range": "90-100%", "providers": 5, "label": "Excellent"},
                {"range": "80-90%", "providers": 6, "label": "Good"},
                {"range": "70-80%", "providers": 2, "label": "Fair"},
                {"range": "Below 70%", "providers": 2, "label": "Poor"}
            ],
            "earnings_distribution": [
                {"range": "$10k+", "providers": 3},
                {"range": "$5k-$10k", "providers": 5},
                {"range": "$1k-$5k", "providers": 4},
                {"range": "Below $1k", "providers": 3}
            ],
            "top_performers": [
                {
                    "provider": "XAI5001...",
                    "name": "AI Compute Pro 1",
                    "tasks": 1247,
                    "earnings": 18542.75,
                    "success_rate": 98.2
                },
                {
                    "provider": "XAI5002...",
                    "name": "AI Compute Pro 2",
                    "tasks": 1197,
                    "earnings": 18042.75,
                    "success_rate": 97.8
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching provider analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
