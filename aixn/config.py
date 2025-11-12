"""
XAI Blockchain Configuration

Supports testnet and mainnet with separate configurations.
"""

import os
from datetime import datetime, timezone
from enum import Enum

class NetworkType(Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"

# Get network type from environment variable
NETWORK = os.getenv('XAI_NETWORK', 'testnet')  # Default to testnet for safety

WALLET_TRADE_PEER_SECRET = os.getenv("XAI_WALLET_TRADE_PEER_SECRET", "xai-peer-secret")
TIME_CAPSULE_MASTER_KEY = os.getenv("XAI_TIME_CAPSULE_MASTER_KEY", "xai-timecapsule-secret")
PERSONAL_AI_WEBHOOK_URL = os.getenv("XAI_PERSONAL_AI_WEBHOOK_URL", "")
PERSONAL_AI_WEBHOOK_TIMEOUT = int(os.getenv("XAI_PERSONAL_AI_WEBHOOK_TIMEOUT", "5"))
WALLET_PASSWORD = os.getenv("XAI_WALLET_PASSWORD", "")
API_RATE_LIMIT = int(os.getenv("XAI_API_RATE_LIMIT", "120"))
API_RATE_WINDOW_SECONDS = int(os.getenv("XAI_API_RATE_WINDOW_SECONDS", "60"))
API_MAX_JSON_BYTES = int(os.getenv("XAI_API_MAX_JSON_BYTES", "1048576"))
LEDGER_DERIVATION_PATH = os.getenv("XAI_LEDGER_PATH", "44'/0'/0'/0/0")
EMBEDDED_WALLET_SALT = os.getenv("XAI_EMBEDDED_SALT", "embedded-salt")
EMBEDDED_WALLET_DIR = os.getenv("XAI_EMBEDDED_DIR", os.path.join(os.getcwd(), "embedded_wallets"))

SAFE_GENESIS_HASHES = {
    NetworkType.TESTNET: os.getenv(
        "XAI_TESTNET_GENESIS_HASH", "59b30b2d8525512cbd5715b24546d73b540ddb575d3778fdbdff02ba245a9141"
    ),
    NetworkType.MAINNET: os.getenv("XAI_MAINNET_GENESIS_HASH", "")
}

# Governance unlock controls
FIAT_UNLOCK_GOVERNANCE_START = datetime(2026, 3, 12, 0, 0, 0, tzinfo=timezone.utc)
FIAT_UNLOCK_REQUIRED_VOTES = 5
FIAT_UNLOCK_SUPPORT_PERCENT = 0.66



class TestnetConfig:
    """Testnet Configuration (for local testing before mainnet)"""

    # Network
    NETWORK_TYPE = NetworkType.TESTNET
    NETWORK_ID = 0xABCD  # Different from mainnet

    # Genesis
    GENESIS_FILE = 'genesis_testnet.json'
    GENESIS_TIMESTAMP = 1704067200.0  # Can reset for testing

    # Supply (smaller for testing)
    MAX_SUPPLY = 121000000.0
    INITIAL_BLOCK_REWARD = 12.0
    HALVING_INTERVAL = 262800  # 1 year

    # Mining (easier difficulty for testing)
    INITIAL_DIFFICULTY = 2  # Lower than mainnet (4)
    BLOCK_TIME_TARGET = 120  # 2 minutes

    # Ports (different from mainnet)
    DEFAULT_PORT = 18545  # Testnet port
    DEFAULT_RPC_PORT = 18546

    # Files (separate from mainnet)
    BLOCKCHAIN_FILE = 'blockchain_testnet.json'
    WALLET_DIR = 'wallets_testnet'
    DATA_DIR = 'data_testnet'

    # Faucet (testnet only)
    FAUCET_ENABLED = True
    FAUCET_AMOUNT = 100.0  # Free test XAI

    # Addresses (testnet prefix)
    ADDRESS_PREFIX = 'TXAI'  # Testnet XAI
    TRADE_FEE_ADDRESS = 'TXAITRADEFEE'
    FIAT_REENABLE_DATE = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    LEDGER_DERIVATION_PATH = LEDGER_DERIVATION_PATH
    FIAT_UNLOCK_GOVERNANCE_START = FIAT_UNLOCK_GOVERNANCE_START
    FIAT_UNLOCK_REQUIRED_VOTES = FIAT_UNLOCK_REQUIRED_VOTES
    FIAT_UNLOCK_SUPPORT_PERCENT = FIAT_UNLOCK_SUPPORT_PERCENT
    TRADE_FEE_PERCENT = 0.002
    TRADE_ORDER_EXPIRY = 3600
    LUCKY_BLOCK_SEED = os.getenv('XAI_LUCKY_BLOCK_SEED', 'testnet-default-seed')
    API_RATE_LIMIT = API_RATE_LIMIT
    API_RATE_WINDOW_SECONDS = API_RATE_WINDOW_SECONDS
    API_MAX_JSON_BYTES = API_MAX_JSON_BYTES
    EMBEDDED_WALLET_SALT = EMBEDDED_WALLET_SALT
    EMBEDDED_WALLET_DIR = EMBEDDED_WALLET_DIR

    # Fast reset (testnet only)
    ALLOW_CHAIN_RESET = True

class MainnetConfig:
    """Mainnet Configuration (production blockchain)"""

    # Network
    NETWORK_TYPE = NetworkType.MAINNET
    NETWORK_ID = 0x5841  # 'XA' in hex

    # Genesis
    GENESIS_FILE = 'genesis_new.json'  # The real genesis with 22.4M premine
    GENESIS_TIMESTAMP = 1704067200.0

    # Supply (121M cap - Bitcoin tribute)
    MAX_SUPPLY = 121000000.0
    INITIAL_BLOCK_REWARD = 12.0
    HALVING_INTERVAL = 262800  # 1 year

    # Mining
    INITIAL_DIFFICULTY = 4  # Production difficulty
    BLOCK_TIME_TARGET = 120  # 2 minutes

    # Ports
    DEFAULT_PORT = 8545
    DEFAULT_RPC_PORT = 8546

    # Files
    BLOCKCHAIN_FILE = 'blockchain.json'
    WALLET_DIR = 'wallets'
    DATA_DIR = 'data'

    # Faucet (disabled on mainnet)
    FAUCET_ENABLED = False
    FAUCET_AMOUNT = 0.0

    # Addresses (mainnet prefix)
    ADDRESS_PREFIX = 'AIXN'
    TRADE_FEE_ADDRESS = 'AIXNTRADEFEE'
    FIAT_REENABLE_DATE = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    LEDGER_DERIVATION_PATH = LEDGER_DERIVATION_PATH
    FIAT_UNLOCK_GOVERNANCE_START = FIAT_UNLOCK_GOVERNANCE_START
    FIAT_UNLOCK_REQUIRED_VOTES = FIAT_UNLOCK_REQUIRED_VOTES
    FIAT_UNLOCK_SUPPORT_PERCENT = FIAT_UNLOCK_SUPPORT_PERCENT
    TRADE_FEE_PERCENT = 0.001
    TRADE_ORDER_EXPIRY = 3600
    LUCKY_BLOCK_SEED = os.getenv('XAI_LUCKY_BLOCK_SEED', 'mainnet-default-seed')
    API_RATE_LIMIT = API_RATE_LIMIT
    API_RATE_WINDOW_SECONDS = API_RATE_WINDOW_SECONDS
    API_MAX_JSON_BYTES = API_MAX_JSON_BYTES
    EMBEDDED_WALLET_SALT = EMBEDDED_WALLET_SALT
    EMBEDDED_WALLET_DIR = EMBEDDED_WALLET_DIR

    # No reset on mainnet
    ALLOW_CHAIN_RESET = False

# Select config based on network
if NETWORK.lower() == 'mainnet':
    Config = MainnetConfig
else:
    Config = TestnetConfig

Config.SAFE_GENESIS_HASHES = SAFE_GENESIS_HASHES

# Wallet trade peers

WALLET_TRADE_PEERS = [
    peer.strip() for peer in os.getenv('XAI_WALLET_TRADE_PEERS', '').split(',')
    if peer.strip()
]

# Allow Config classes to expose the global peer list
Config.WALLET_TRADE_PEERS = WALLET_TRADE_PEERS

# Export config
__all__ = [
    'Config',
    'NetworkType',
    'TestnetConfig',
    'MainnetConfig',
    'WALLET_TRADE_PEERS',
    'WALLET_TRADE_PEER_SECRET',
    'TIME_CAPSULE_MASTER_KEY',
    'PERSONAL_AI_WEBHOOK_URL',
    'PERSONAL_AI_WEBHOOK_TIMEOUT',
    'WALLET_PASSWORD',
    'API_RATE_LIMIT',
    'API_RATE_WINDOW_SECONDS',
    'API_MAX_JSON_BYTES',
    'SAFE_GENESIS_HASHES',
]
