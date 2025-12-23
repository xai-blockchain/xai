"""
XAI Blockchain Python SDK

A comprehensive SDK for interacting with the XAI blockchain platform.

Example:
    >>> from xai_sdk import XAIClient
    >>> client = XAIClient(api_key="your-api-key")
    >>> wallet = client.wallet.create()
    >>> print(wallet.address)
"""

from .client import XAIClient
from .exceptions import (
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ValidationError,
    XAIError,
)
from .models import (
    Block,
    MiningStatus,
    Proposal,
    Transaction,
    Wallet,
)

__version__ = "1.0.0"
__author__ = "XAI Team"

__all__ = [
    "XAIClient",
    "Wallet",
    "Transaction",
    "Block",
    "Proposal",
    "MiningStatus",
    "XAIError",
    "AuthenticationError",
    "RateLimitError",
    "NetworkError",
    "ValidationError",
]
