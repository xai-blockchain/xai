"""
XAI Smart Contract Standards.

This module provides standard contract implementations including:
- ERC20: Fungible token standard
- ERC721: Non-fungible token (NFT) standard
- ERC1155: Multi-token standard
- Proxy: Contract upgradability patterns (Transparent, UUPS, Beacon, Diamond)
- Account Abstraction: ERC-4337 smart accounts
- Factory contracts for deploying new tokens and proxies
"""

from .account_abstraction import (
    AccountFactory,
    EntryPoint,
    InvalidSignatureError,
    MalformedSignatureError,
    MissingPublicKeyError,
    MultiSigAccount,
    Paymaster,
    SessionKeyAccount,
    SessionKeyPermissions,
    SignatureError,
    SmartAccount,
    SocialRecoveryAccount,
    UserOperation,
)
from .erc20 import ERC20Factory, ERC20Token
from .erc721 import ERC721Factory, ERC721Token
from .erc1155 import ERC1155Token
from .proxy import (
    BeaconProxy,
    DiamondFacet,
    DiamondProxy,
    FacetCut,
    ProxyFactory,
    TransparentProxy,
    UpgradeableBeacon,
    UUPSImplementation,
    UUPSProxy,
)

__all__ = [
    # Token Standards
    "ERC20Token",
    "ERC20Factory",
    "ERC721Token",
    "ERC721Factory",
    "ERC1155Token",
    # Proxy Patterns
    "TransparentProxy",
    "UUPSProxy",
    "UUPSImplementation",
    "UpgradeableBeacon",
    "BeaconProxy",
    "DiamondProxy",
    "DiamondFacet",
    "FacetCut",
    "ProxyFactory",
    # Account Abstraction
    "UserOperation",
    "SmartAccount",
    "MultiSigAccount",
    "SocialRecoveryAccount",
    "SessionKeyAccount",
    "SessionKeyPermissions",
    "Paymaster",
    "EntryPoint",
    "AccountFactory",
    # Signature Exceptions
    "SignatureError",
    "MalformedSignatureError",
    "InvalidSignatureError",
    "MissingPublicKeyError",
]
