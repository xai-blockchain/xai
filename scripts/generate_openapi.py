#!/usr/bin/env python3
"""
Generate the OpenAPI specification for the XAI node API.

The API surface is intentionally large, so this script keeps the canonical
definition in one place and renders a deterministic YAML file that can be
served to SDK/CLI/documentation tooling.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "docs" / "api" / "openapi.yaml"


def ref_schema(name: str) -> Dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def ref_param(name: str) -> Dict[str, str]:
    return {"$ref": f"#/components/parameters/{name}"}


def json_request(schema: str, description: Optional[str] = None, required: bool = True) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "required": required,
        "content": {
            "application/json": {
                "schema": ref_schema(schema),
            }
        },
    }
    if description:
        body["description"] = description
    return body


def success_response(
    schema: Dict[str, Any], description: str = "Request succeeded"
) -> Dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": schema,
            }
        },
    }


def error_response(description: str = "Error response") -> Dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": ref_schema("ErrorResponse"),
            }
        },
    }


def build_spec() -> Dict[str, Any]:
    spec: Dict[str, Any] = OrderedDict()
    spec["openapi"] = "3.0.3"
    spec["info"] = OrderedDict(
        {
            "title": "XAI Blockchain API",
            "version": "1.1.0",
            "description": (
                "Production REST API for the XAI blockchain node.\n\n"
                "All endpoints require authenticated transport in production. "
                "Use the summaries and schemas in this document to integrate "
                "wallets, explorers, trading engines, and operational tooling."
            ),
            "contact": {"name": "XAI Support", "url": "https://xai-blockchain.io"},
            "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        }
    )
    spec["servers"] = [
        {"url": "http://localhost:12080", "description": "Local development"},
        {"url": "https://testnet-api.xai-blockchain.io", "description": "Testnet"},
        {"url": "https://api.xai-blockchain.io", "description": "Production"},
    ]

    tags = [
        ("Core", "Node metadata, health, and statistics"),
        ("Mempool", "Transaction mempool inspection"),
        ("Blockchain", "Blocks, transactions, and state queries"),
        ("Contracts", "Smart-contract execution and metadata"),
        ("Wallet", "Balance, history, faucet, and nonce helpers"),
        ("Mining", "Mining orchestration and performance"),
        ("P2P", "Peer management and sync"),
        ("Algo", "AI-assisted fee estimation and fraud checks"),
        ("Recovery", "Social recovery and guardian coordination"),
        ("Gamification", "Airdrops, streaks, treasure hunts, and refunds"),
        ("Mining Bonus", "XP, achievements, referrals, and leaderboards"),
        ("Exchange", "Order book, settlements, and fiat ramps"),
        ("Crypto Deposits", "BTC/ETH/USDT deposit helpers"),
        ("Admin", "Operational controls, API keys, and spending limits"),
    ]
    spec["tags"] = [{"name": name, "description": desc} for name, desc in tags]

    paths: Dict[str, Any] = OrderedDict()

    def add_operation(
        path: str,
        method: str,
        *,
        tags: List[str],
        summary: str,
        description: str,
        response_schema: Dict[str, Any],
        parameters: Optional[List[Dict[str, Any]]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        security: Optional[List[Dict[str, Any]]] = None,
        additional_errors: Optional[List[str]] = None,
    ) -> None:
        operation: Dict[str, Any] = OrderedDict()
        operation["tags"] = tags
        operation["summary"] = summary
        operation["description"] = description
        if parameters:
            operation["parameters"] = parameters
        if request_body:
            operation["requestBody"] = request_body
        responses: Dict[str, Any] = OrderedDict()
        responses["200"] = success_response(response_schema)
        default_errors = ["400", "500"]
        for code in default_errors:
            responses[code] = error_response()
        if additional_errors:
            for code in additional_errors:
                responses[code] = error_response()
        operation["responses"] = responses
        if security is not None:
            operation["security"] = security
        paths.setdefault(path, OrderedDict())[method.lower()] = operation

    # Helper schemas for reuse
    def success_with(properties: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "default": True},
                **properties,
            },
            "required": ["success"],
        }

    def message_response(example: str = "") -> Dict[str, Any]:
        schema = success_with({"message": {"type": "string"}})
        if example:
            schema["properties"]["message"]["example"] = example
        return schema

    # Core endpoints
    add_operation(
        "/",
        "GET",
        tags=["Core"],
        summary="Get node overview",
        description="Returns status metadata, build information, and discovered API endpoints.",
        response_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "online"},
                "node": {"type": "string", "example": "AXN Full Node"},
                "version": {"type": "string", "example": "1.0.0"},
                "algorithmic_features": {"type": "boolean"},
                "endpoints": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["status", "node", "version"],
        },
        security=[],
    )

    add_operation(
        "/health",
        "GET",
        tags=["Core"],
        summary="Health check",
        description="Operational readiness probe with blockchain, storage, and peer diagnostics.",
        response_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "healthy"},
                "timestamp": {"type": "number", "format": "float"},
                "blockchain": {"type": "object"},
                "services": {"type": "object"},
                "network": {"type": "object"},
                "backlog": {"type": "object"},
                "error": {"type": "string"},
            },
            "required": ["status", "timestamp"],
        },
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/checkpoint/provenance",
        "GET",
        tags=["Core"],
        summary="List checkpoint provenance",
        description="Surfaces the latest deterministic checkpoints used for accelerated sync.",
        response_schema=success_with(
            {"provenance": {"type": "array", "items": {"type": "object"}}}
        ),
        security=[],
    )

    paths["/metrics"] = {
        "get": {
            "tags": ["Core"],
            "summary": "Prometheus metrics",
            "description": "Raw text exposition compatible with Prometheus scrapers.",
            "responses": {
                "200": {
                    "description": "Metrics stream",
                    "content": {"text/plain": {"schema": {"type": "string"}}},
                },
                "500": {
                    "description": "Exporter failure",
                    "content": {"text/plain": {"schema": {"type": "string"}}},
                },
            },
            "security": [],
        }
    }

    add_operation(
        "/stats",
        "GET",
        tags=["Core"],
        summary="Node statistics",
        description="Returns chain height, peer count, mining status, and uptime metrics.",
        response_schema=success_with({"stats": {"type": "object"}}),
        security=[],
    )

    # Mempool endpoints
    add_operation(
        "/mempool",
        "GET",
        tags=["Mempool"],
        summary="Get mempool snapshot",
        description="Lists pending transactions and queue sizing metadata.",
        parameters=[ref_param("LimitParam")],
        response_schema=success_with(
            {
                "limit": {"type": "integer"},
                "mempool": {"type": "object"},
            }
        ),
        security=[],
    )

    add_operation(
        "/mempool/stats",
        "GET",
        tags=["Mempool"],
        summary="Get mempool pressure indicators",
        description="Returns congestion, fee percentiles, and pressure heuristics.",
        parameters=[ref_param("LimitParam")],
        response_schema=success_with(
            {
                "timestamp": {"type": "number"},
                "fees": {"type": "object"},
                "pressure": {"type": "object"},
                "transactions_returned": {"type": "integer"},
            }
        ),
        security=[],
    )

    # Blockchain endpoints
    add_operation(
        "/blocks",
        "GET",
        tags=["Blockchain"],
        summary="List blocks",
        description="Returns the latest blocks with pagination.",
        parameters=[ref_param("LimitParam"), ref_param("OffsetParam")],
        response_schema=success_with(
            {
                "total": {"type": "integer"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
                "blocks": {"type": "array", "items": ref_schema("Block")},
            }
        ),
        security=[],
    )

    add_operation(
        "/blocks/{index}",
        "GET",
        tags=["Blockchain"],
        summary="Get block by index",
        description="Fetch a block using its height/index with cache-friendly headers.",
        parameters=[ref_param("BlockIndexParam")],
        response_schema=ref_schema("Block"),
        security=[],
        additional_errors=["404"],
    )

    add_operation(
        "/block/{block_hash}",
        "GET",
        tags=["Blockchain"],
        summary="Get block by hash",
        description="Fetch a block using its canonical hash.",
        parameters=[ref_param("BlockHashParam")],
        response_schema=ref_schema("Block"),
        security=[],
        additional_errors=["404"],
    )

    add_operation(
        "/block/receive",
        "POST",
        tags=["Blockchain"],
        summary="Accept peer block",
        description="Receives a block envelope signed by a peer and attempts to add it to the chain.",
        request_body=json_request("PeerBlockInput"),
        response_schema=success_with({"height": {"type": "integer"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/transactions",
        "GET",
        tags=["Blockchain"],
        summary="List pending transactions",
        description="Returns the mempool contents in deterministic order.",
        parameters=[ref_param("LimitParam"), ref_param("OffsetParam")],
        response_schema=success_with(
            {
                "count": {"type": "integer"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
                "transactions": {"type": "array", "items": ref_schema("Transaction")},
            }
        ),
        security=[],
    )

    add_operation(
        "/transaction/{txid}",
        "GET",
        tags=["Blockchain"],
        summary="Get transaction by ID",
        description="Searches confirmed blocks and the mempool for the provided transaction ID.",
        parameters=[ref_param("TransactionIdParam")],
        response_schema=success_with(
            {
                "found": {"type": "boolean"},
                "block": {"type": "integer"},
                "confirmations": {"type": "integer"},
                "transaction": ref_schema("Transaction"),
            }
        ),
        security=[],
        additional_errors=["404"],
    )

    add_operation(
        "/send",
        "POST",
        tags=["Blockchain"],
        summary="Broadcast transaction",
        description="Validates, enqueues, and broadcasts a signed transaction.",
        request_body=json_request("NodeTransactionInput"),
        response_schema=success_with({"txid": {"type": "string"}}),
        additional_errors=["401", "403", "429"],
    )

    add_operation(
        "/transaction/receive",
        "POST",
        tags=["Blockchain"],
        summary="Accept peer transaction",
        description="Receives a signed peer transaction envelope and attempts to add it to the mempool.",
        request_body=json_request("PeerTransactionInput"),
        response_schema=success_with({"txid": {"type": "string"}}),
        additional_errors=["401"],
    )

    # Contracts
    add_operation(
        "/contracts/deploy",
        "POST",
        tags=["Contracts"],
        summary="Deploy smart contract",
        description="Queues a contract deployment transaction and returns the derived address.",
        request_body=json_request("ContractDeployInput"),
        response_schema=success_with(
            {
                "txid": {"type": "string"},
                "contract_address": {"type": "string"},
            }
        ),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/contracts/call",
        "POST",
        tags=["Contracts"],
        summary="Execute smart contract call",
        description="Queues a call transaction against an existing contract.",
        request_body=json_request("ContractCallInput"),
        response_schema=success_with({"txid": {"type": "string"}}),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/contracts/{address}/state",
        "GET",
        tags=["Contracts"],
        summary="Read contract state",
        description="Retrieves the stored state for a contract build.",
        parameters=[ref_param("ContractAddressParam")],
        response_schema=success_with({"contract_address": {"type": "string"}, "state": {"type": "object"}}),
        additional_errors=["404", "503"],
    )

    add_operation(
        "/contracts/{address}/abi",
        "GET",
        tags=["Contracts"],
        summary="Get contract ABI",
        description="Returns the ABI metadata registered for the contract.",
        parameters=[ref_param("ContractAddressParam")],
        response_schema=success_with({"contract_address": {"type": "string"}, "abi": {"type": "array"}}),
        additional_errors=["404"],
    )

    add_operation(
        "/contracts/{address}/interfaces",
        "GET",
        tags=["Contracts"],
        summary="Detect supported interfaces",
        description="Runs ERC-165 probes and reports supported receiver interfaces.",
        parameters=[ref_param("ContractAddressParam")],
        response_schema=success_with(
            {
                "contract_address": {"type": "string"},
                "interfaces": {"type": "object"},
                "metadata": {"type": "object"},
            }
        ),
        additional_errors=["404", "503"],
    )

    add_operation(
        "/contracts/{address}/events",
        "GET",
        tags=["Contracts"],
        summary="List contract events",
        description="Returns indexed events emitted by the contract.",
        parameters=[ref_param("ContractAddressParam"), ref_param("LimitParam"), ref_param("OffsetParam")],
        response_schema=success_with(
            {
                "contract_address": {"type": "string"},
                "events": {"type": "array", "items": {"type": "object"}},
                "count": {"type": "integer"},
                "total": {"type": "integer"},
            }
        ),
    )

    add_operation(
        "/contracts/governance/status",
        "GET",
        tags=["Contracts"],
        summary="Smart-contract feature status",
        description="Reports governance flags plus runtime readiness for the VM.",
        response_schema=success_with(
            {
                "feature_name": {"type": "string"},
                "config_enabled": {"type": "boolean"},
                "governance_enabled": {"type": "boolean"},
                "contract_manager_ready": {"type": "boolean"},
                "contracts_tracked": {"type": "integer"},
            }
        ),
    )

    add_operation(
        "/contracts/governance/feature",
        "POST",
        tags=["Contracts"],
        summary="Toggle smart-contract execution",
        description="Administrative endpoint that executes a governance instruction to enable or disable the VM.",
        request_body=json_request("ContractFeatureToggleInput"),
        response_schema=success_with({"proposal_id": {"type": "string"}, "governance_result": {"type": "object"}}),
        additional_errors=["401", "403", "503"],
    )

    # Wallet helpers
    add_operation(
        "/balance/{address}",
        "GET",
        tags=["Wallet"],
        summary="Get balance",
        description="Returns the spendable balance for an address.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"address": {"type": "string"}, "balance": {"type": "number"}}),
        security=[],
    )

    add_operation(
        "/address/{address}/nonce",
        "GET",
        tags=["Wallet"],
        summary="Get address nonce",
        description="Reports the confirmed and next nonce for transaction construction.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with(
            {
                "address": {"type": "string"},
                "confirmed_nonce": {"type": "integer"},
                "next_nonce": {"type": "integer"},
                "pending_nonce": {"type": "integer", "nullable": True},
            }
        ),
        security=[],
    )

    add_operation(
        "/history/{address}",
        "GET",
        tags=["Wallet"],
        summary="Get address history",
        description="Transaction history window for an address.",
        parameters=[ref_param("AddressPathParam"), ref_param("LimitParam"), ref_param("OffsetParam")],
        response_schema=success_with(
            {
                "address": {"type": "string"},
                "transaction_count": {"type": "integer"},
                "transactions": {"type": "array", "items": {"type": "object"}},
            }
        ),
        security=[],
    )

    add_operation(
        "/faucet/claim",
        "POST",
        tags=["Wallet"],
        summary="Claim testnet faucet",
        description="Queues a faucet transfer on test networks.",
        request_body=json_request("FaucetClaimInput"),
        response_schema=success_with({"amount": {"type": "number"}, "txid": {"type": "string"}}),
        additional_errors=["401", "403", "429", "503"],
    )

    # Mining routes
    add_operation(
        "/mine",
        "POST",
        tags=["Mining"],
        summary="Mine pending transactions",
        description="Forces immediate mining and broadcasts the resulting block.",
        response_schema=success_with({"block": ref_schema("Block"), "reward": {"type": "number"}}),
        additional_errors=["401", "429"],
    )

    add_operation(
        "/auto-mine/start",
        "POST",
        tags=["Mining"],
        summary="Start auto mining",
        description="Turns on background mining threads.",
        response_schema=message_response("Auto-mining started"),
        additional_errors=["401"],
    )

    add_operation(
        "/auto-mine/stop",
        "POST",
        tags=["Mining"],
        summary="Stop auto mining",
        description="Terminates background mining threads.",
        response_schema=message_response("Auto-mining stopped"),
        additional_errors=["401"],
    )

    # P2P
    add_operation(
        "/peers",
        "GET",
        tags=["P2P"],
        summary="List peers",
        description="Shows connected peers and optional verbose metadata.",
        parameters=[ref_param("VerboseParam")],
        response_schema=success_with(
            {
                "count": {"type": "integer"},
                "peers": {"type": "array", "items": {"type": "string"}},
                "verbose": {"type": "boolean"},
            }
        ),
        security=[],
    )

    add_operation(
        "/peers/add",
        "POST",
        tags=["P2P"],
        summary="Add peer",
        description="Registers a peer URL and attempts to connect.",
        request_body=json_request("PeerAddInput"),
        response_schema=message_response("Peer added"),
        additional_errors=["401"],
    )

    add_operation(
        "/sync",
        "POST",
        tags=["P2P"],
        summary="Synchronize with network",
        description="Triggers the sync coordinator to fetch blocks from peers.",
        response_schema=success_with({"synced": {"type": "boolean"}, "chain_length": {"type": "integer"}}),
        additional_errors=["401"],
    )

    # Algorithmic features
    add_operation(
        "/algo/fee-estimate",
        "GET",
        tags=["Algo"],
        summary="Fee recommendation",
        description="Predicts recommended fee rates given mempool pressure and requested priority.",
        parameters=[
            {
                "name": "priority",
                "in": "query",
                "schema": {"type": "string", "enum": ["slow", "normal", "priority"]},
                "required": False,
            }
        ],
        response_schema=success_with({"recommended": {"type": "object"}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/algo/fraud-check",
        "POST",
        tags=["Algo"],
        summary="Fraud analysis",
        description="Runs the AI-powered fraud detector on a transaction payload.",
        request_body=json_request("FraudCheckInput"),
        response_schema=success_with({"analysis": {"type": "object"}}),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/algo/status",
        "GET",
        tags=["Algo"],
        summary="Algorithmic feature status",
        description="Reports enabled modules such as fee optimizer and fraud detector.",
        response_schema=success_with(
            {
                "enabled": {"type": "boolean"},
                "features": {"type": "array", "items": {"type": "object"}},
            }
        ),
        security=[],
    )

    # Recovery routes definition will be appended later after building helper functions
    recovery_endpoints = [
        (
            "/recovery/setup",
            "POST",
            "Configure guardians",
            "Registers guardians and the signature threshold for an address.",
            "RecoverySetupInput",
        ),
        (
            "/recovery/request",
            "POST",
            "Initiate recovery",
            "Guardian starts a recovery flow to move control to a new address.",
            "RecoveryRequestInput",
        ),
        (
            "/recovery/vote",
            "POST",
            "Guardian vote",
            "Guardian vote on an existing recovery request.",
            "RecoveryVoteInput",
        ),
        (
            "/recovery/cancel",
            "POST",
            "Cancel recovery",
            "Owner cancels a pending recovery.",
            "RecoveryCancelInput",
        ),
        (
            "/recovery/execute",
            "POST",
            "Execute recovery",
            "Executes the approved recovery after the safety delay.",
            "RecoveryExecuteInput",
        ),
    ]

    for path, method, summary, description, schema_name in recovery_endpoints:
        add_operation(
            path,
            method,
            tags=["Recovery"],
            summary=summary,
            description=description,
            request_body=json_request(schema_name),
            response_schema=success_with({"result": {"type": "object"}}),
            additional_errors=["401"],
        )

    recovery_gets = [
        (
            "/recovery/status/{address}",
            "Recovery status",
            "Returns active recovery status for an address.",
            ["Recovery"],
            [
                ref_param("AddressPathParam"),
            ],
        ),
        (
            "/recovery/config/{address}",
            "Recovery config",
            "Returns guardian configuration for an address.",
            ["Recovery"],
            [ref_param("AddressPathParam")],
        ),
        (
            "/recovery/guardian/{address}",
            "Guardian duties",
            "Lists guardian responsibilities for an address.",
            ["Recovery"],
            [ref_param("AddressPathParam")],
        ),
    ]

    for path, summary, description, tags_list, params in recovery_gets:
        add_operation(
            path,
            "GET",
            tags=tags_list,
            summary=summary,
            description=description,
            parameters=params,
            response_schema=success_with({"data": {"type": "object"}}),
            security=[],
        )

    add_operation(
        "/recovery/requests",
        "GET",
        tags=["Recovery"],
        summary="List recovery requests",
        description="Lists pending recovery requests optionally filtered by status.",
        parameters=[
            {
                "name": "status",
                "in": "query",
                "schema": {"type": "string"},
                "required": False,
            }
        ],
        response_schema=success_with({"count": {"type": "integer"}, "requests": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/recovery/stats",
        "GET",
        tags=["Recovery"],
        summary="Recovery statistics",
        description="Aggregate statistics for the guardian and recovery system.",
        response_schema=success_with({"stats": {"type": "object"}}),
        security=[],
    )

    # Gamification & progression endpoints
    add_operation(
        "/airdrop/winners",
        "GET",
        tags=["Gamification"],
        summary="List airdrop winners",
        description="Leaderboard of the most recent airdrop winners.",
        parameters=[ref_param("LimitParam")],
        response_schema=success_with({"airdrops": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/airdrop/user/{address}",
        "GET",
        tags=["Gamification"],
        summary="Get user airdrops",
        description="Historical airdrop data for the provided address.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with(
            {
                "address": {"type": "string"},
                "total_airdrops": {"type": "integer"},
                "history": {"type": "array", "items": {"type": "object"}},
            }
        ),
        security=[],
    )

    add_operation(
        "/mining/streaks",
        "GET",
        tags=["Gamification"],
        summary="Mining streak leaderboard",
        description="Returns the longest and most recent mining streaks.",
        parameters=[
            ref_param("LimitParam"),
            {
                "name": "sort_by",
                "in": "query",
                "schema": {"type": "string", "default": "current_streak"},
            },
        ],
        response_schema=success_with({"leaderboard": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/mining/streak/{address}",
        "GET",
        tags=["Gamification"],
        summary="Address mining streak",
        description="Returns streak statistics for a specific miner.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"address": {"type": "string"}, "stats": {"type": "object"}}),
        security=[],
        additional_errors=["404"],
    )

    add_operation(
        "/treasure/active",
        "GET",
        tags=["Gamification"],
        summary="List active treasures",
        description="Returns all currently unclaimed treasure hunts.",
        response_schema=success_with({"count": {"type": "integer"}, "treasures": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/treasure/create",
        "POST",
        tags=["Gamification"],
        summary="Create treasure hunt",
        description="Creates a new treasure hunt by locking a bounty behind a puzzle.",
        request_body=json_request("TreasureCreateInput"),
        response_schema=success_with({"treasure_id": {"type": "string"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/treasure/claim",
        "POST",
        tags=["Gamification"],
        summary="Claim treasure",
        description="Validates the puzzle solution and rewards the claimer.",
        request_body=json_request("TreasureClaimInput"),
        response_schema=success_with({"amount": {"type": "number"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/treasure/details/{treasure_id}",
        "GET",
        tags=["Gamification"],
        summary="Treasure details",
        description="Returns the metadata for a treasure hunt.",
        parameters=[ref_param("TreasureIdParam")],
        response_schema=success_with({"treasure": {"type": "object"}}),
        security=[],
        additional_errors=["404"],
    )

    add_operation(
        "/timecapsule/pending",
        "GET",
        tags=["Gamification"],
        summary="Pending time capsules",
        description="Lists time capsules that are still locked.",
        response_schema=success_with({"count": {"type": "integer"}, "capsules": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/timecapsule/{address}",
        "GET",
        tags=["Gamification"],
        summary="Address time capsules",
        description="Returns sent and received time capsules for an address.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"address": {"type": "string"}, "sent": {"type": "array"}, "received": {"type": "array"}}),
        security=[],
    )

    add_operation(
        "/refunds/stats",
        "GET",
        tags=["Gamification"],
        summary="Refund statistics",
        description="Aggregated fee refund metrics.",
        response_schema=success_with({"stats": {"type": "object"}}),
        security=[],
    )

    add_operation(
        "/refunds/{address}",
        "GET",
        tags=["Gamification"],
        summary="Address refund history",
        description="Lists the refunds that an address has received.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"address": {"type": "string"}, "history": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    # Mining bonus routes
    add_operation(
        "/mining/register",
        "POST",
        tags=["Mining Bonus"],
        summary="Register miner",
        description="Registers a miner for XP/bonus tracking.",
        request_body=json_request("MiningRegisterInput"),
        response_schema=success_with({"result": {"type": "object"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/mining/achievements/{address}",
        "GET",
        tags=["Mining Bonus"],
        summary="Get achievements",
        description="Returns unlocked achievements and progress for an address.",
        parameters=[
            ref_param("AddressPathParam"),
            {
                "name": "blocks_mined",
                "in": "query",
                "schema": {"type": "integer", "minimum": 0},
            },
            {
                "name": "streak_days",
                "in": "query",
                "schema": {"type": "integer", "minimum": 0},
            },
        ],
        response_schema=success_with({"achievements": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/mining/claim-bonus",
        "POST",
        tags=["Mining Bonus"],
        summary="Claim social bonus",
        description="Claims a configured mining bonus such as social campaigns.",
        request_body=json_request("MiningBonusClaimInput"),
        response_schema=success_with({"result": {"type": "object"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/mining/referral/create",
        "POST",
        tags=["Mining Bonus"],
        summary="Create referral code",
        description="Generates a referral code for a miner.",
        request_body=json_request("ReferralCreateInput"),
        response_schema=success_with({"result": {"type": "object"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/mining/referral/use",
        "POST",
        tags=["Mining Bonus"],
        summary="Redeem referral code",
        description="Registers a new miner using an existing referral code.",
        request_body=json_request("ReferralUseInput"),
        response_schema=success_with({"result": {"type": "object"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/mining/user-bonuses/{address}",
        "GET",
        tags=["Mining Bonus"],
        summary="List user bonuses",
        description="Returns all XP, streak, and referral bonuses tied to an address.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"bonuses": {"type": "object"}}),
        security=[],
    )

    add_operation(
        "/mining/leaderboard",
        "GET",
        tags=["Mining Bonus"],
        summary="Bonus leaderboard",
        description="Returns the top addresses ranked by configured bonus metrics.",
        parameters=[ref_param("LimitParam")],
        response_schema=success_with({"leaderboard": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/mining/leaderboard/unified",
        "GET",
        tags=["Mining Bonus"],
        summary="Unified leaderboard",
        description="Aggregated leaderboard blending XP, streaks, and referrals.",
        parameters=[
            ref_param("LimitParam"),
            {
                "name": "metric",
                "in": "query",
                "schema": {"type": "string", "default": "composite"},
            },
        ],
        response_schema=success_with({"leaderboard": {"type": "array", "items": {"type": "object"}}}),
        security=[],
    )

    add_operation(
        "/mining/stats",
        "GET",
        tags=["Mining Bonus"],
        summary="Mining bonus stats",
        description="System-wide statistics for the bonus engine.",
        response_schema=success_with({"stats": {"type": "object"}}),
        security=[],
    )

    # Exchange routes
    add_operation(
        "/exchange/orders",
        "GET",
        tags=["Exchange"],
        summary="Order book snapshot",
        description="Returns the top of book for both sides.",
        response_schema=success_with(
            {
                "buy_orders": {"type": "array", "items": {"type": "object"}},
                "sell_orders": {"type": "array", "items": {"type": "object"}},
            }
        ),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/place-order",
        "POST",
        tags=["Exchange"],
        summary="Place order",
        description="Creates a limit order and optionally matches immediately.",
        request_body=json_request("ExchangeOrderInput"),
        response_schema=success_with({"order": {"type": "object"}, "matched": {"type": "array", "items": {"type": "object"}}}),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/exchange/cancel-order",
        "POST",
        tags=["Exchange"],
        summary="Cancel order",
        description="Cancels an open order and unlocks funds.",
        request_body=json_request("ExchangeCancelInput"),
        response_schema=message_response("Order cancelled successfully"),
        additional_errors=["401", "503", "404"],
    )

    add_operation(
        "/exchange/my-orders/{address}",
        "GET",
        tags=["Exchange"],
        summary="List user orders",
        description="Returns the order history for an address.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"orders": {"type": "array", "items": {"type": "object"}}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/trades",
        "GET",
        tags=["Exchange"],
        summary="Recent trades",
        description="Returns recently executed trades.",
        parameters=[ref_param("LimitParam")],
        response_schema=success_with({"trades": {"type": "array", "items": {"type": "object"}}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/deposit",
        "POST",
        tags=["Exchange"],
        summary="Deposit funds",
        description="Credits an exchange wallet via manual or automated deposit.",
        request_body=json_request("ExchangeTransferInput"),
        response_schema=success_with({"result": {"type": "object"}}),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/exchange/withdraw",
        "POST",
        tags=["Exchange"],
        summary="Withdraw funds",
        description="Initiates a withdrawal from the exchange wallet.",
        request_body=json_request("ExchangeTransferInput"),
        response_schema=success_with({"result": {"type": "object"}}),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/exchange/balance/{address}",
        "GET",
        tags=["Exchange"],
        summary="All balances",
        description="Returns all currency balances (available and locked) for an address.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"balances": {"type": "object"}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/balance/{address}/{currency}",
        "GET",
        tags=["Exchange"],
        summary="Currency balance",
        description="Returns the balance for a single currency.",
        parameters=[ref_param("AddressPathParam"), ref_param("CurrencyParam")],
        response_schema=success_with({"available": {"type": "number"}, "locked": {"type": "number"}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/transactions/{address}",
        "GET",
        tags=["Exchange"],
        summary="Exchange transactions",
        description="Returns transfers and fills for an address.",
        parameters=[ref_param("AddressPathParam"), ref_param("LimitParam")],
        response_schema=success_with({"transactions": {"type": "array", "items": {"type": "object"}}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/price-history",
        "GET",
        tags=["Exchange"],
        summary="Price history",
        description="Returns charting data for the requested timeframe.",
        parameters=[
            {
                "name": "timeframe",
                "in": "query",
                "schema": {"type": "string", "default": "24h"},
            }
        ],
        response_schema=success_with({"prices": {"type": "array"}, "volumes": {"type": "array"}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/stats",
        "GET",
        tags=["Exchange"],
        summary="Exchange stats",
        description="Returns market statistics such as current price, volume, and open interest.",
        response_schema=success_with({"stats": {"type": "object"}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/buy-with-card",
        "POST",
        tags=["Exchange"],
        summary="Buy AXN with card",
        description="Processes a credit/debit card payment and credits AXN.",
        request_body=json_request("ExchangeCardPurchaseInput"),
        response_schema=success_with({"payment": {"type": "object"}, "deposit": {"type": "object"}}),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/exchange/payment-methods",
        "GET",
        tags=["Exchange"],
        summary="Supported payment methods",
        description="Lists enabled card/payment rails.",
        response_schema=success_with({"methods": {"type": "array", "items": {"type": "object"}}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/calculate-purchase",
        "POST",
        tags=["Exchange"],
        summary="Estimate purchase amount",
        description="Returns the AXN amount and fees for a USD purchase.",
        request_body=json_request("PurchaseEstimateRequest"),
        response_schema=success_with({"estimate": {"type": "object"}}),
        additional_errors=["503"],
    )

    # Crypto deposit routes
    add_operation(
        "/exchange/crypto/generate-address",
        "POST",
        tags=["Crypto Deposits"],
        summary="Generate deposit address",
        description="Creates a unique BTC/ETH/USDT deposit address for the user.",
        request_body=json_request("CryptoDepositAddressInput"),
        response_schema=success_with({"address": {"type": "string"}, "currency": {"type": "string"}}),
        additional_errors=["401", "503"],
    )

    add_operation(
        "/exchange/crypto/addresses/{address}",
        "GET",
        tags=["Crypto Deposits"],
        summary="List user deposit addresses",
        description="Returns the crypto deposit addresses issued to the user.",
        parameters=[ref_param("AddressPathParam")],
        response_schema=success_with({"addresses": {"type": "array", "items": {"type": "object"}}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/crypto/pending-deposits",
        "GET",
        tags=["Crypto Deposits"],
        summary="Pending crypto deposits",
        description="Returns pending deposits optionally filtered by user.",
        parameters=[
            {
                "name": "user_address",
                "in": "query",
                "schema": {"type": "string"},
            }
        ],
        response_schema=success_with({"pending_deposits": {"type": "array", "items": {"type": "object"}}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/crypto/deposit-history/{address}",
        "GET",
        tags=["Crypto Deposits"],
        summary="Deposit history",
        description="Returns confirmed crypto deposits for the user.",
        parameters=[ref_param("AddressPathParam"), ref_param("LimitParam")],
        response_schema=success_with({"deposits": {"type": "array", "items": {"type": "object"}}}),
        security=[],
        additional_errors=["503"],
    )

    add_operation(
        "/exchange/crypto/stats",
        "GET",
        tags=["Crypto Deposits"],
        summary="Crypto deposit stats",
        description="Returns aggregated metrics for the crypto deposit system.",
        response_schema=success_with({"stats": {"type": "object"}}),
        security=[],
        additional_errors=["503"],
    )

    # Admin routes
    add_operation(
        "/admin/api-keys",
        "GET",
        tags=["Admin"],
        summary="List API keys",
        description="Returns metadata about issued API keys.",
        response_schema=success_with({"keys": {"type": "array", "items": {"type": "object"}}}),
        additional_errors=["401"],
    )

    add_operation(
        "/admin/api-keys",
        "POST",
        tags=["Admin"],
        summary="Create API key",
        description="Issues an API key with user or admin scope.",
        request_body=json_request("ApiKeyCreateRequest"),
        response_schema=success_with({"api_key": {"type": "string"}, "key_id": {"type": "string"}}),
        additional_errors=["401"],
    )

    add_operation(
        "/admin/api-keys/{key_id}",
        "DELETE",
        tags=["Admin"],
        summary="Revoke API key",
        description="Revokes an API key by ID.",
        parameters=[{"name": "key_id", "in": "path", "required": True, "schema": {"type": "string"}}],
        response_schema=success_with({"revoked": {"type": "boolean"}}),
        additional_errors=["401", "404"],
    )

    add_operation(
        "/admin/api-key-events",
        "GET",
        tags=["Admin"],
        summary="API key events",
        description="Returns recent API key audit events.",
        parameters=[ref_param("LimitParam")],
        response_schema=success_with({"events": {"type": "array", "items": {"type": "object"}}}),
        additional_errors=["401"],
    )

    add_operation(
        "/admin/withdrawals/telemetry",
        "GET",
        tags=["Admin"],
        summary="Withdrawal telemetry",
        description="Returns live withdrawal metrics for ops teams.",
        parameters=[ref_param("LimitParam")],
        response_schema=success_with({"recent_withdrawals": {"type": "array", "items": {"type": "object"}}}),
        additional_errors=["401", "429"],
    )

    add_operation(
        "/admin/withdrawals/status",
        "GET",
        tags=["Admin"],
        summary="Withdrawal status snapshot",
        description="Returns withdrawals grouped by status plus queue depth.",
        parameters=[
            ref_param("LimitParam"),
            {
                "name": "status",
                "in": "query",
                "schema": {"type": "string"},
            },
        ],
        response_schema=success_with({"withdrawals": {"type": "object"}}),
        additional_errors=["401", "429", "503"],
    )

    add_operation(
        "/admin/spend-limit",
        "POST",
        tags=["Admin"],
        summary="Set spending limit",
        description="Sets the per-address daily spending limit enforced by the API.",
        request_body=json_request("SpendLimitRequest"),
        response_schema=success_with({"address": {"type": "string"}, "limit": {"type": "number"}}),
        additional_errors=["401"],
    )

    spec["paths"] = paths

    # Shared parameter definitions
    parameters = {
        "LimitParam": {
            "name": "limit",
            "in": "query",
            "required": False,
            "schema": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 50},
            "description": "Maximum number of records to return.",
        },
        "OffsetParam": {
            "name": "offset",
            "in": "query",
            "required": False,
            "schema": {"type": "integer", "minimum": 0, "default": 0},
            "description": "Pagination offset.",
        },
        "VerboseParam": {
            "name": "verbose",
            "in": "query",
            "required": False,
            "schema": {"type": "boolean", "default": False},
            "description": "When true include detailed peer metadata.",
        },
        "AddressPathParam": {
            "name": "address",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        },
        "BlockIndexParam": {
            "name": "index",
            "in": "path",
            "required": True,
            "schema": {"type": "integer", "minimum": 0},
        },
        "BlockHashParam": {
            "name": "block_hash",
            "in": "path",
            "required": True,
            "schema": {"type": "string", "pattern": "^[0-9a-fA-Fx]+$"},
        },
        "ContractAddressParam": {
            "name": "address",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        },
        "TransactionIdParam": {
            "name": "txid",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        },
        "TreasureIdParam": {
            "name": "treasure_id",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        },
        "CurrencyParam": {
            "name": "currency",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        },
    }

    # Schema definitions for request bodies and shared payloads
    schemas: Dict[str, Any] = {
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "default": False},
                "error": {"type": "string"},
                "code": {"type": "string"},
            },
        },
        "Transaction": {
            "type": "object",
            "properties": {
                "txid": {"type": "string"},
                "sender": {"type": "string"},
                "recipient": {"type": "string"},
                "amount": {"type": "number"},
                "fee": {"type": "number"},
                "nonce": {"type": "integer"},
                "timestamp": {"type": "number"},
            },
        },
        "Block": {
            "type": "object",
            "properties": {
                "index": {"type": "integer"},
                "timestamp": {"type": "number"},
                "previous_hash": {"type": "string"},
                "hash": {"type": "string"},
                "merkle_root": {"type": "string"},
                "transactions": {"type": "array", "items": {"$ref": "#/components/schemas/Transaction"}},
            },
        },
        "NodeTransactionInput": {
            "type": "object",
            "required": ["sender", "recipient", "amount", "fee", "public_key", "nonce", "timestamp", "signature"],
            "properties": {
                "sender": {"type": "string"},
                "recipient": {"type": "string"},
                "amount": {"type": "number"},
                "fee": {"type": "number"},
                "public_key": {"type": "string"},
                "nonce": {"type": "integer"},
                "timestamp": {"type": "number"},
                "signature": {"type": "string"},
                "txid": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
        "PeerTransactionInput": {
            "type": "object",
            "required": ["sender", "recipient", "amount", "public_key", "signature", "nonce"],
            "properties": {
                "sender": {"type": "string"},
                "recipient": {"type": "string"},
                "amount": {"type": "number"},
                "fee": {"type": "number"},
                "public_key": {"type": "string"},
                "tx_type": {"type": "string"},
                "nonce": {"type": "integer"},
                "inputs": {"type": "array", "items": {"type": "object"}},
                "outputs": {"type": "array", "items": {"type": "object"}},
                "timestamp": {"type": "number"},
                "signature": {"type": "string"},
                "txid": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
        "PeerBlockInput": {
            "type": "object",
            "required": ["header", "transactions"],
            "properties": {
                "header": {"type": "object"},
                "transactions": {"type": "array", "items": {"type": "object"}},
            },
        },
        "ContractDeployInput": {
            "type": "object",
            "required": ["sender", "bytecode", "gas_limit", "public_key", "signature"],
            "properties": {
                "sender": {"type": "string"},
                "bytecode": {"type": "string"},
                "gas_limit": {"type": "integer"},
                "value": {"type": "number"},
                "fee": {"type": "number"},
                "public_key": {"type": "string"},
                "nonce": {"type": "integer"},
                "signature": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
        "ContractCallInput": {
            "type": "object",
            "required": ["sender", "contract_address", "gas_limit", "public_key", "signature"],
            "properties": {
                "sender": {"type": "string"},
                "contract_address": {"type": "string"},
                "payload": {"type": "object"},
                "data": {"type": "string"},
                "gas_limit": {"type": "integer"},
                "value": {"type": "number"},
                "fee": {"type": "number"},
                "public_key": {"type": "string"},
                "nonce": {"type": "integer"},
                "signature": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
        "ContractFeatureToggleInput": {
            "type": "object",
            "required": ["enabled"],
            "properties": {
                "enabled": {"type": "boolean"},
                "reason": {"type": "string"},
            },
        },
        "FaucetClaimInput": {
            "type": "object",
            "required": ["address"],
            "properties": {"address": {"type": "string"}},
        },
        "PeerAddInput": {
            "type": "object",
            "required": ["url"],
            "properties": {"url": {"type": "string"}},
        },
        "FraudCheckInput": {
            "type": "object",
            "required": ["payload"],
            "properties": {"payload": {"type": "object"}},
        },
        "RecoverySetupInput": {
            "type": "object",
            "required": ["owner_address", "guardians", "threshold", "signature"],
            "properties": {
                "owner_address": {"type": "string"},
                "guardians": {"type": "array", "items": {"type": "string"}},
                "threshold": {"type": "integer"},
                "signature": {"type": "string"},
            },
        },
        "RecoveryRequestInput": {
            "type": "object",
            "required": ["owner_address", "new_address", "guardian_address", "signature"],
            "properties": {
                "owner_address": {"type": "string"},
                "new_address": {"type": "string"},
                "guardian_address": {"type": "string"},
                "signature": {"type": "string"},
            },
        },
        "RecoveryVoteInput": {
            "type": "object",
            "required": ["request_id", "guardian_address", "signature"],
            "properties": {
                "request_id": {"type": "string"},
                "guardian_address": {"type": "string"},
                "signature": {"type": "string"},
            },
        },
        "RecoveryCancelInput": {
            "type": "object",
            "required": ["request_id", "owner_address", "signature"],
            "properties": {
                "request_id": {"type": "string"},
                "owner_address": {"type": "string"},
                "signature": {"type": "string"},
            },
        },
        "RecoveryExecuteInput": {
            "type": "object",
            "required": ["request_id", "executor_address"],
            "properties": {
                "request_id": {"type": "string"},
                "executor_address": {"type": "string"},
            },
        },
        "TreasureCreateInput": {
            "type": "object",
            "required": ["creator", "amount", "puzzle_type", "puzzle_data"],
            "properties": {
                "creator": {"type": "string"},
                "amount": {"type": "number"},
                "puzzle_type": {"type": "string"},
                "puzzle_data": {"type": "object"},
                "hint": {"type": "string"},
            },
        },
        "TreasureClaimInput": {
            "type": "object",
            "required": ["treasure_id", "claimer", "solution"],
            "properties": {
                "treasure_id": {"type": "string"},
                "claimer": {"type": "string"},
                "solution": {"type": "string"},
            },
        },
        "MiningRegisterInput": {"type": "object", "required": ["address"], "properties": {"address": {"type": "string"}}},
        "MiningBonusClaimInput": {
            "type": "object",
            "required": ["address", "bonus_type"],
            "properties": {
                "address": {"type": "string"},
                "bonus_type": {"type": "string"},
            },
        },
        "ReferralCreateInput": {"type": "object", "required": ["address"], "properties": {"address": {"type": "string"}}},
        "ReferralUseInput": {
            "type": "object",
            "required": ["new_address", "referral_code"],
            "properties": {
                "new_address": {"type": "string"},
                "referral_code": {"type": "string"},
                "metadata": {"type": "object"},
            },
        },
        "ExchangeOrderInput": {
            "type": "object",
            "required": ["address", "order_type", "pair", "price", "amount"],
            "properties": {
                "address": {"type": "string"},
                "order_type": {"type": "string"},
                "pair": {"type": "string"},
                "price": {"type": "number"},
                "amount": {"type": "number"},
            },
        },
        "ExchangeCancelInput": {
            "type": "object",
            "required": ["order_id"],
            "properties": {"order_id": {"type": "string"}},
        },
        "ExchangeTransferInput": {
            "type": "object",
            "required": ["from_address", "to_address", "currency", "amount"],
            "properties": {
                "from_address": {"type": "string"},
                "to_address": {"type": "string"},
                "currency": {"type": "string"},
                "amount": {"type": "number"},
                "destination": {"type": "string"},
            },
        },
        "ExchangeCardPurchaseInput": {
            "type": "object",
            "required": ["from_address", "to_address", "usd_amount", "email", "card_id", "user_id", "payment_token"],
            "properties": {
                "from_address": {"type": "string"},
                "to_address": {"type": "string"},
                "usd_amount": {"type": "number"},
                "email": {"type": "string"},
                "card_id": {"type": "string"},
                "user_id": {"type": "string"},
                "payment_token": {"type": "string"},
            },
        },
        "CryptoDepositAddressInput": {
            "type": "object",
            "required": ["user_address", "currency"],
            "properties": {
                "user_address": {"type": "string"},
                "currency": {"type": "string"},
            },
        },
        "ApiKeyCreateRequest": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "scope": {"type": "string", "enum": ["user", "admin"], "default": "user"},
            },
        },
        "SpendLimitRequest": {
            "type": "object",
            "required": ["address", "limit"],
            "properties": {
                "address": {"type": "string"},
                "limit": {"type": "number"},
            },
        },
        "PurchaseEstimateRequest": {
            "type": "object",
            "required": ["usd_amount"],
            "properties": {
                "usd_amount": {"type": "number"},
            },
        },
    }

    spec["components"] = {
        "parameters": parameters,
        "schemas": schemas,
        "securitySchemes": {
            "api_key": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
            "bearer_auth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        },
    }

    spec["security"] = [{"api_key": []}, {"bearer_auth": []}]

    return spec


def ordered(obj: Any) -> Any:
    if isinstance(obj, OrderedDict):
        return {key: ordered(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [ordered(item) for item in obj]
    return obj


def main() -> None:
    spec = build_spec()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(ordered(spec), handle, sort_keys=False)


if __name__ == "__main__":
    main()
