"""
XAI Blockchain MCP Server

Provides Model Context Protocol tools for AI agents to interact with XAI blockchain.

Tools provided:
- get_balance: Query address balance
- get_block: Query block by height or hash
- get_transaction: Query transaction by ID
- get_chain_info: Get blockchain info (height, difficulty, etc.)
- create_transaction: Create and sign a transaction
- submit_transaction: Submit transaction to mempool
- get_utxos: Get UTXOs for an address
- estimate_fee: Estimate transaction fee

Usage:
    python -m xai.mcp.server --port 8765 --data-dir ~/.xai
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class XAIMCPServer:
    """
    MCP Server for XAI blockchain interaction.

    Implements the Model Context Protocol for AI agent tool calls.
    """

    def __init__(self, data_dir: str = "~/.xai"):
        """
        Initialize MCP server.

        Args:
            data_dir: Path to XAI blockchain data directory
        """
        import os
        self.data_dir = os.path.expanduser(data_dir)
        self._blockchain = None
        self._initialized = False

    def _ensure_blockchain(self) -> Any:
        """Lazy-load blockchain to avoid import issues."""
        if self._blockchain is None:
            from xai.core.blockchain import Blockchain
            self._blockchain = Blockchain(data_dir=self.data_dir)
            self._initialized = True
        return self._blockchain

    def get_tools(self) -> list[dict[str, Any]]:
        """Return list of available MCP tools."""
        return [
            {
                "name": "get_balance",
                "description": "Get the XAI balance for an address",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string", "description": "Wallet address"}
                    },
                    "required": ["address"]
                }
            },
            {
                "name": "get_block",
                "description": "Get block by height or hash",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "height": {"type": "integer", "description": "Block height"},
                        "hash": {"type": "string", "description": "Block hash"}
                    }
                }
            },
            {
                "name": "get_transaction",
                "description": "Get transaction details by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "txid": {"type": "string", "description": "Transaction ID"}
                    },
                    "required": ["txid"]
                }
            },
            {
                "name": "get_chain_info",
                "description": "Get blockchain info (height, difficulty, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_utxos",
                "description": "Get unspent transaction outputs for an address",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "address": {"type": "string", "description": "Wallet address"}
                    },
                    "required": ["address"]
                }
            },
            {
                "name": "estimate_fee",
                "description": "Estimate transaction fee",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tx_size_bytes": {"type": "integer", "description": "Transaction size in bytes", "default": 250}
                    }
                }
            },
            {
                "name": "get_mempool_info",
                "description": "Get mempool statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an MCP tool call.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result as dictionary
        """
        try:
            if name == "get_balance":
                return self._get_balance(arguments["address"])
            elif name == "get_block":
                return self._get_block(arguments.get("height"), arguments.get("hash"))
            elif name == "get_transaction":
                return self._get_transaction(arguments["txid"])
            elif name == "get_chain_info":
                return self._get_chain_info()
            elif name == "get_utxos":
                return self._get_utxos(arguments["address"])
            elif name == "estimate_fee":
                return self._estimate_fee(arguments.get("tx_size_bytes", 250))
            elif name == "get_mempool_info":
                return self._get_mempool_info()
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            logger.exception(f"Tool call failed: {name}")
            return {"error": str(e)}

    def _get_balance(self, address: str) -> dict[str, Any]:
        """Get balance for address."""
        bc = self._ensure_blockchain()
        balance = bc.get_balance(address)
        return {
            "address": address,
            "balance": balance,
            "unit": "XAI"
        }

    def _get_block(self, height: int | None, block_hash: str | None) -> dict[str, Any]:
        """Get block by height or hash."""
        bc = self._ensure_blockchain()

        if height is not None:
            if height < 0 or height >= len(bc.chain):
                return {"error": f"Block height {height} not found"}
            block = bc.chain[height]
        elif block_hash is not None:
            block = bc.get_block_by_hash(block_hash) if hasattr(bc, 'get_block_by_hash') else None
            if not block:
                return {"error": f"Block hash {block_hash} not found"}
        else:
            # Return latest block
            block = bc.chain[-1] if bc.chain else None
            if not block:
                return {"error": "No blocks in chain"}

        # Convert block to dict
        if hasattr(block, 'to_dict'):
            return block.to_dict()
        return {
            "index": getattr(block, 'index', None),
            "hash": getattr(block, 'hash', None),
            "previous_hash": getattr(block, 'previous_hash', None),
            "timestamp": getattr(block, 'timestamp', None),
            "transactions": len(getattr(block, 'transactions', [])),
        }

    def _get_transaction(self, txid: str) -> dict[str, Any]:
        """Get transaction by ID."""
        bc = self._ensure_blockchain()

        # Search in chain
        for block in bc.chain:
            for tx in getattr(block, 'transactions', []):
                if getattr(tx, 'txid', None) == txid:
                    if hasattr(tx, 'to_dict'):
                        return tx.to_dict()
                    return {"txid": txid, "found": True}

        # Check pending transactions
        for tx in getattr(bc, 'pending_transactions', []):
            if getattr(tx, 'txid', None) == txid:
                result = tx.to_dict() if hasattr(tx, 'to_dict') else {"txid": txid}
                result["status"] = "pending"
                return result

        return {"error": f"Transaction {txid} not found"}

    def _get_chain_info(self) -> dict[str, Any]:
        """Get blockchain info."""
        bc = self._ensure_blockchain()
        return {
            "height": len(bc.chain) - 1,
            "blocks": len(bc.chain),
            "difficulty": getattr(bc, 'difficulty', None),
            "pending_transactions": len(getattr(bc, 'pending_transactions', [])),
            "max_supply": getattr(bc, 'max_supply', 121000000),
        }

    def _get_utxos(self, address: str) -> dict[str, Any]:
        """Get UTXOs for address."""
        bc = self._ensure_blockchain()
        utxos = bc.utxo_manager.get_utxos_for_address(address)
        return {
            "address": address,
            "utxo_count": len(utxos),
            "utxos": utxos,
            "total_value": sum(u.get("amount", 0) for u in utxos)
        }

    def _estimate_fee(self, tx_size_bytes: int = 250) -> dict[str, Any]:
        """Estimate transaction fee."""
        # Simple fee estimation based on transaction size
        fee_rate = 0.00001  # XAI per byte
        estimated_fee = tx_size_bytes * fee_rate
        return {
            "tx_size_bytes": tx_size_bytes,
            "fee_rate": fee_rate,
            "estimated_fee": estimated_fee,
            "unit": "XAI"
        }

    def _get_mempool_info(self) -> dict[str, Any]:
        """Get mempool statistics."""
        bc = self._ensure_blockchain()
        pending = getattr(bc, 'pending_transactions', [])
        total_fees = sum(getattr(tx, 'fee', 0) for tx in pending)
        return {
            "size": len(pending),
            "total_fees": total_fees,
            "min_fee_rate": getattr(bc, 'min_fee_rate', 0.0),
        }


def create_mcp_server(data_dir: str = "~/.xai") -> XAIMCPServer:
    """Create and return an MCP server instance."""
    return XAIMCPServer(data_dir=data_dir)


async def run_stdio_server(server: XAIMCPServer) -> None:
    """Run MCP server over stdio (for Claude Code integration)."""
    import sys

    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break

            request = json.loads(line.strip())
            method = request.get("method")

            if method == "tools/list":
                response = {"tools": server.get_tools()}
            elif method == "tools/call":
                params = request.get("params", {})
                result = server.call_tool(params.get("name"), params.get("arguments", {}))
                response = {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            else:
                response = {"error": f"Unknown method: {method}"}

            print(json.dumps({"id": request.get("id"), "result": response}), flush=True)

        except json.JSONDecodeError:
            continue
        except KeyboardInterrupt:
            break


def main() -> None:
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(description="XAI Blockchain MCP Server")
    parser.add_argument("--data-dir", default="~/.xai", help="Blockchain data directory")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode")
    args = parser.parse_args()

    server = create_mcp_server(data_dir=args.data_dir)

    if args.stdio:
        asyncio.run(run_stdio_server(server))
    else:
        # Print available tools
        print("XAI MCP Server")
        print("Available tools:")
        for tool in server.get_tools():
            print(f"  - {tool['name']}: {tool['description']}")
        print("\nRun with --stdio for Claude Code integration")


if __name__ == "__main__":
    main()
