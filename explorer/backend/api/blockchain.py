"""
Blockchain API endpoints
"""
from fastapi import APIRouter, Query, HTTPException
import httpx

router = APIRouter()

# XAI Node connection
node_url = "http://localhost:12001"


@router.get("/blocks")
async def get_blocks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get list of blocks with pagination"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/blocks",
                params={"page": page, "limit": limit},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return {"blocks": [], "total": 0, "page": page}
    except Exception as e:
        return {"blocks": [], "total": 0, "page": page, "error": str(e)}


@router.get("/blocks/{block_id}")
async def get_block(block_id: str):
    """Get block by height or hash"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{node_url}/block/{block_id}", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=404, detail="Block not found")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Node unavailable")


@router.get("/transactions/{txid}")
async def get_transaction(txid: str):
    """Get transaction by ID"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{node_url}/transaction/{txid}", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=404, detail="Transaction not found")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Node unavailable")


@router.get("/addresses/{address}")
async def get_address(address: str):
    """Get address information"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{node_url}/address/{address}", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            raise HTTPException(status_code=404, detail="Address not found")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Node unavailable")


@router.get("/search")
async def search(q: str = Query(..., min_length=1)):
    """Universal search for blocks, transactions, addresses"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{node_url}/search",
                params={"q": q},
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return {"results": [], "query": q}
    except Exception as e:
        return {"results": [], "query": q, "error": str(e)}
