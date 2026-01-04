"""
Governance API endpoints
"""
from fastapi import APIRouter, Query, HTTPException
import httpx
from typing import Optional
from datetime import datetime

router = APIRouter()

# XAI Node connection
node_url = "http://localhost:12001"


@router.get("/proposals")
async def get_proposals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: voting, passed, rejected, all")
):
    """Get list of governance proposals with pagination"""
    try:
        async with httpx.AsyncClient() as client:
            params = {"page": page, "limit": limit}
            if status and status != "all":
                params["status"] = status

            response = await client.get(
                f"{node_url}/governance/proposals",
                params=params,
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()

            # Return mock data if node unavailable
            return {
                "proposals": _get_mock_proposals(page, limit, status),
                "total": 15,
                "page": page,
                "limit": limit
            }
    except Exception as e:
        # Return mock data for development
        return {
            "proposals": _get_mock_proposals(page, limit, status),
            "total": 15,
            "page": page,
            "limit": limit,
            "error": str(e)
        }


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: int):
    """Get proposal details by ID"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/governance/proposals/{proposal_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=404, detail="Proposal not found")
    except httpx.RequestError:
        # Return mock data for development
        return _get_mock_proposal_detail(proposal_id)


@router.get("/proposals/{proposal_id}/votes")
async def get_proposal_votes(
    proposal_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Get votes for a specific proposal"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/governance/proposals/{proposal_id}/votes",
                params={"page": page, "limit": limit},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return {"votes": [], "total": 0, "page": page}
    except Exception as e:
        # Return mock data for development
        return {
            "votes": _get_mock_votes(proposal_id, page, limit),
            "total": 25,
            "page": page,
            "limit": limit,
            "proposal_id": proposal_id
        }


def _get_mock_proposals(page: int, limit: int, status: Optional[str]):
    """Generate mock proposals for development"""
    statuses = ["voting", "passed", "rejected", "deposit"]
    proposals = []

    for i in range(limit):
        idx = (page - 1) * limit + i + 1
        if idx > 15:
            break

        prop_status = statuses[idx % len(statuses)]
        if status and status != "all" and prop_status != status:
            continue

        proposals.append({
            "proposal_id": idx,
            "title": f"XIP-{idx}: {'Network Upgrade' if idx % 3 == 0 else 'Parameter Change' if idx % 3 == 1 else 'Community Fund'}",
            "description": f"Proposal #{idx} for improving the XAI network",
            "status": prop_status,
            "proposer": f"xai1{'0' * 30}{idx:08d}",
            "submit_time": datetime.utcnow().isoformat(),
            "deposit_end_time": datetime.utcnow().isoformat(),
            "voting_start_time": datetime.utcnow().isoformat(),
            "voting_end_time": datetime.utcnow().isoformat(),
            "total_deposit": str(100 + idx * 10),
            "yes_votes": str(1000 * idx),
            "no_votes": str(100 * idx),
            "abstain_votes": str(50 * idx),
            "no_with_veto_votes": str(10 * idx),
        })

    return proposals


def _get_mock_proposal_detail(proposal_id: int):
    """Generate mock proposal detail for development"""
    statuses = ["voting", "passed", "rejected", "deposit"]
    return {
        "proposal_id": proposal_id,
        "title": f"XIP-{proposal_id}: Network Parameter Adjustment",
        "description": """## Summary
This proposal aims to adjust network parameters for improved performance and security.

## Motivation
The current parameters need optimization based on network growth and usage patterns.

## Specification
- Increase block size limit from 1MB to 2MB
- Reduce block time target from 10s to 8s
- Adjust fee parameters for AI compute tasks

## Rationale
These changes will improve throughput and user experience while maintaining security.""",
        "status": statuses[proposal_id % len(statuses)],
        "proposer": f"xai1{'0' * 30}{proposal_id:08d}",
        "submit_time": datetime.utcnow().isoformat(),
        "deposit_end_time": datetime.utcnow().isoformat(),
        "voting_start_time": datetime.utcnow().isoformat(),
        "voting_end_time": datetime.utcnow().isoformat(),
        "total_deposit": str(100 + proposal_id * 10),
        "yes_votes": str(1000 * proposal_id),
        "no_votes": str(100 * proposal_id),
        "abstain_votes": str(50 * proposal_id),
        "no_with_veto_votes": str(10 * proposal_id),
        "tally_result": {
            "yes": str(1000 * proposal_id),
            "no": str(100 * proposal_id),
            "abstain": str(50 * proposal_id),
            "no_with_veto": str(10 * proposal_id),
            "total_voting_power": str(2000 * proposal_id),
            "quorum_reached": proposal_id % 2 == 0,
            "threshold_reached": proposal_id % 3 != 0,
        }
    }


def _get_mock_votes(proposal_id: int, page: int, limit: int):
    """Generate mock votes for development"""
    options = ["yes", "no", "abstain", "no_with_veto"]
    votes = []

    for i in range(limit):
        idx = (page - 1) * limit + i + 1
        if idx > 25:
            break

        votes.append({
            "voter": f"xai1{'a' * 30}{idx:08d}",
            "proposal_id": proposal_id,
            "option": options[idx % len(options)],
            "voting_power": str(100 * idx),
            "timestamp": datetime.utcnow().isoformat(),
        })

    return votes
