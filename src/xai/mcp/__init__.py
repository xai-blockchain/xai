"""
XAI Blockchain MCP Server

Model Context Protocol server for AI agent interaction with XAI blockchain.
Provides tools for querying blockchain state and submitting transactions.
"""

from xai.mcp.server import XAIMCPServer, create_mcp_server

__all__ = ["XAIMCPServer", "create_mcp_server"]
