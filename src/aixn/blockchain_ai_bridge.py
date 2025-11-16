"""
Facade for blockchain AI bridge dependencies.

This module provides a simplified import path for the BlockchainAIBridge class,
acting as a facade to the core implementation. It allows users to import from
the top-level aixn package instead of navigating the internal structure.

Example:
    from aixn.blockchain_ai_bridge import BlockchainAIBridge
    # Instead of:
    # from src.aixn.core.blockchain_ai_bridge import BlockchainAIBridge
"""

from src.aixn.core.blockchain_ai_bridge import BlockchainAIBridge

__all__ = ["BlockchainAIBridge"]
