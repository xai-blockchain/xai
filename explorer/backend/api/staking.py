"""
Staking API endpoints
"""
from fastapi import APIRouter, Query, HTTPException
import httpx
from typing import Optional
from datetime import datetime

router = APIRouter()

# XAI Node connection
node_url = "http://localhost:12001"


@router.get("/pool")
async def get_staking_pool():
    """Get staking pool information"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/staking/pool",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

            # Return mock data if node unavailable
            return _get_mock_staking_pool()
    except Exception as e:
        # Return mock data for development
        return {**_get_mock_staking_pool(), "error": str(e)}


@router.get("/delegations/{address}")
async def get_delegations(
    address: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get delegations for an address"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/staking/delegations/{address}",
                params={"page": page, "limit": limit},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

            return {
                "delegations": _get_mock_delegations(address, page, limit),
                "total": 5,
                "page": page,
                "address": address
            }
    except Exception as e:
        return {
            "delegations": _get_mock_delegations(address, page, limit),
            "total": 5,
            "page": page,
            "address": address,
            "error": str(e)
        }


@router.get("/rewards/{address}")
async def get_rewards(address: str):
    """Get staking rewards for an address"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/staking/rewards/{address}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

            return _get_mock_rewards(address)
    except Exception as e:
        return {**_get_mock_rewards(address), "error": str(e)}


@router.get("/unbonding/{address}")
async def get_unbonding(address: str):
    """Get unbonding delegations for an address"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/staking/unbonding/{address}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

            return _get_mock_unbonding(address)
    except Exception as e:
        return {**_get_mock_unbonding(address), "error": str(e)}


@router.get("/validators")
async def get_validators(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, jailed, all"),
    sort_by: Optional[str] = Query("voting_power", description="Sort by: voting_power, commission, name")
):
    """Get list of validators with pagination"""
    try:
        async with httpx.AsyncClient() as client:
            params = {"page": page, "limit": limit}
            if status and status != "all":
                params["status"] = status
            if sort_by:
                params["sort_by"] = sort_by

            response = await client.get(
                f"{node_url}/staking/validators",
                params=params,
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

            return {
                "validators": _get_mock_validators(page, limit, status),
                "total": 30,
                "page": page,
                "limit": limit
            }
    except Exception as e:
        return {
            "validators": _get_mock_validators(page, limit, status),
            "total": 30,
            "page": page,
            "limit": limit,
            "error": str(e)
        }


@router.get("/validators/{address}")
async def get_validator(address: str):
    """Get validator details by address"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/staking/validators/{address}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=404, detail="Validator not found")
    except httpx.RequestError:
        # Return mock data for development
        return _get_mock_validator_detail(address)


@router.get("/validators/{address}/delegators")
async def get_validator_delegators(
    address: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Get delegators for a specific validator"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/staking/validators/{address}/delegators",
                params={"page": page, "limit": limit},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

            return {
                "delegators": _get_mock_delegators_for_validator(address, page, limit),
                "total": 100,
                "page": page,
                "validator": address
            }
    except Exception as e:
        return {
            "delegators": _get_mock_delegators_for_validator(address, page, limit),
            "total": 100,
            "page": page,
            "validator": address,
            "error": str(e)
        }


def _get_mock_staking_pool():
    """Generate mock staking pool data"""
    return {
        "bonded_tokens": "50000000000000",
        "not_bonded_tokens": "25000000000000",
        "total_supply": "100000000000000",
        "bonded_ratio": 0.6667,
        "inflation_rate": 0.05,
        "annual_provisions": "5000000000000",
        "community_pool": "1000000000000"
    }


def _get_mock_delegations(address: str, page: int, limit: int):
    """Generate mock delegations for an address"""
    delegations = []
    for i in range(min(limit, 5)):
        idx = (page - 1) * limit + i + 1
        delegations.append({
            "delegator_address": address,
            "validator_address": f"xaivaloper1{'v' * 30}{idx:08d}",
            "validator_name": f"Validator #{idx}",
            "shares": str(1000 * idx),
            "balance": str(1000 * idx),
            "rewards": str(10 * idx),
        })
    return delegations


def _get_mock_rewards(address: str):
    """Generate mock rewards data"""
    return {
        "address": address,
        "total_rewards": "1234.567890",
        "rewards_by_validator": [
            {
                "validator_address": f"xaivaloper1{'v' * 30}00000001",
                "validator_name": "Validator #1",
                "reward": "500.123456"
            },
            {
                "validator_address": f"xaivaloper1{'v' * 30}00000002",
                "validator_name": "Validator #2",
                "reward": "734.444434"
            }
        ]
    }


def _get_mock_unbonding(address: str):
    """Generate mock unbonding data"""
    return {
        "address": address,
        "unbonding_delegations": [
            {
                "validator_address": f"xaivaloper1{'v' * 30}00000003",
                "validator_name": "Validator #3",
                "entries": [
                    {
                        "creation_height": 12345,
                        "completion_time": datetime.utcnow().isoformat(),
                        "initial_balance": "1000",
                        "balance": "1000"
                    }
                ]
            }
        ],
        "total_unbonding": "1000"
    }


def _get_mock_validators(page: int, limit: int, status: Optional[str]):
    """Generate mock validators for development"""
    statuses = ["active", "active", "active", "inactive", "jailed"]
    validators = []

    for i in range(limit):
        idx = (page - 1) * limit + i + 1
        if idx > 30:
            break

        val_status = statuses[idx % len(statuses)]
        if status and status != "all" and val_status != status:
            continue

        validators.append({
            "operator_address": f"xaivaloper1{'v' * 30}{idx:08d}",
            "consensus_pubkey": f"xaivalconspub1{'p' * 40}{idx:08d}",
            "moniker": f"Validator {idx}" if idx > 3 else ["XAI Foundation", "Genesis Validator", "Community Node"][idx - 1],
            "website": f"https://validator{idx}.example.com",
            "details": f"Professional validator service #{idx}",
            "status": val_status,
            "jailed": val_status == "jailed",
            "tokens": str(10000000 - idx * 100000),
            "delegator_shares": str(10000000 - idx * 100000),
            "voting_power": str(10000000 - idx * 100000),
            "voting_power_percentage": round((10000000 - idx * 100000) / 50000000 * 100, 2),
            "commission_rate": round(0.05 + (idx % 10) * 0.01, 2),
            "commission_max_rate": 0.20,
            "commission_max_change_rate": 0.01,
            "min_self_delegation": "1",
            "uptime_percentage": round(99.9 - (idx % 5) * 0.1, 2),
            "rank": idx
        })

    return validators


def _get_mock_validator_detail(address: str):
    """Generate mock validator detail for development"""
    # Extract index from address for consistent mock data
    idx = int(address[-8:]) if address[-8:].isdigit() else 1

    return {
        "operator_address": address,
        "consensus_pubkey": f"xaivalconspub1{'p' * 40}{idx:08d}",
        "moniker": f"Validator {idx}",
        "identity": f"ABC123{idx}",
        "website": f"https://validator{idx}.example.com",
        "security_contact": f"security@validator{idx}.example.com",
        "details": f"Professional validator service #{idx} providing secure and reliable validation services for the XAI network.",
        "status": "active",
        "jailed": False,
        "tokens": str(10000000 - idx * 100000),
        "delegator_shares": str(10000000 - idx * 100000),
        "voting_power": str(10000000 - idx * 100000),
        "voting_power_percentage": round((10000000 - idx * 100000) / 50000000 * 100, 2),
        "commission": {
            "rate": round(0.05 + (idx % 10) * 0.01, 2),
            "max_rate": 0.20,
            "max_change_rate": 0.01,
            "update_time": datetime.utcnow().isoformat()
        },
        "min_self_delegation": "1",
        "self_delegation": str(1000000),
        "delegator_count": 100 + idx * 10,
        "uptime": {
            "uptime_percentage": round(99.9 - (idx % 5) * 0.1, 2),
            "missed_blocks_counter": idx * 2,
            "signed_blocks_window": 10000,
            "start_height": 1
        },
        "slashing": {
            "slash_events": [],
            "total_slashed": "0"
        },
        "rank": idx,
        "created_at": datetime.utcnow().isoformat()
    }


def _get_mock_delegators_for_validator(validator_address: str, page: int, limit: int):
    """Generate mock delegators for a validator"""
    delegators = []
    for i in range(limit):
        idx = (page - 1) * limit + i + 1
        if idx > 100:
            break

        delegators.append({
            "delegator_address": f"xai1{'d' * 30}{idx:08d}",
            "shares": str(10000 - idx * 50),
            "balance": str(10000 - idx * 50),
        })

    return delegators
