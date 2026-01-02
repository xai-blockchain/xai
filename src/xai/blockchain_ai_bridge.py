"""
Facade for blockchain AI bridge dependencies.

This module provides a simplified import path for the BlockchainAIBridge class,
acting as a facade to the core implementation. It allows users to import from
the top-level xai package instead of navigating the internal structure.

Example:
    from xai.blockchain_ai_bridge import BlockchainAIBridge
    # Instead of:
    # from xai.core.blockchain_ai_bridge import BlockchainAIBridge
"""

from xai.core.blockchain_ai_bridge import BlockchainAIBridge

__all__ = ["BlockchainAIBridge"]
