"""
XAI Core Blockchain Module

This module contains the refactored blockchain components extracted from the
monolithic blockchain.py file.
"""

from xai.core.blockchain_components.block import Block
from xai.core.blockchain_components.consensus_mixin import BlockchainConsensusMixin
from xai.core.blockchain_components.mempool_mixin import BlockchainMempoolMixin
from xai.core.blockchain_components.mining_mixin import BlockchainMiningMixin

__all__ = [
    "Block",
    "BlockchainConsensusMixin",
    "BlockchainMempoolMixin",
    "BlockchainMiningMixin",
]
