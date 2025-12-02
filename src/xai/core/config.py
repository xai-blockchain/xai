"""
XAI Blockchain Configuration

Supports testnet and mainnet with separate configurations.

SECURITY NOTICE:
- All secrets MUST be provided via environment variables
- Never commit secrets to version control
- Use different secrets for testnet vs mainnet
- Rotate secrets periodically
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets as secrets_module
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class NetworkType(Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


def _get_required_secret(env_var: str, network: str) -> str:
    """Get a required secret from environment, with mainnet enforcement.

    On mainnet, missing secrets raise ConfigurationError.
    On testnet, missing secrets generate a random value with a warning.
    """
    value = os.getenv(env_var, "").strip()
    if value:
        return value

    if network.lower() == "mainnet":
        raise ConfigurationError(
            f"CRITICAL: {env_var} environment variable required for mainnet. "
            f"Generate a secure secret: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    # Testnet: generate random secret and warn
    generated = secrets_module.token_hex(32)
    logger.warning(
        "Security: %s not set, using generated value for testnet. "
        "Set this environment variable for production.",
        env_var,
        extra={"event": "config.secret_generated", "env_var": env_var}
    )
    return generated


def _get_secret_with_default(env_var: str, default_generator=None) -> str:
    """Get a secret from environment, or generate one if not provided."""
    value = os.getenv(env_var, "").strip()
    if value:
        return value
    if default_generator:
        return default_generator()
    return secrets_module.token_hex(32)


# Get network type from environment variable
NETWORK = os.getenv("XAI_NETWORK", "testnet")  # Default to testnet for safety

FEATURE_FLAGS = {
    "vm": os.getenv("XAI_VM_ENABLED", "0").strip() == "1",
}

MAX_CONTRACT_GAS = int(os.getenv("XAI_MAX_CONTRACT_GAS", "20000000"))

# SECURITY: These secrets are required for production
# On mainnet, missing values will raise ConfigurationError
# On testnet, missing values will generate random secrets with warnings
WALLET_TRADE_PEER_SECRET = _get_required_secret("XAI_WALLET_TRADE_PEER_SECRET", NETWORK)
TIME_CAPSULE_MASTER_KEY = _get_required_secret("XAI_TIME_CAPSULE_MASTER_KEY", NETWORK)
PERSONAL_AI_WEBHOOK_URL = os.getenv("XAI_PERSONAL_AI_WEBHOOK_URL", "")
PERSONAL_AI_WEBHOOK_TIMEOUT = int(os.getenv("XAI_PERSONAL_AI_WEBHOOK_TIMEOUT", "5"))
WALLET_PASSWORD = os.getenv("XAI_WALLET_PASSWORD", "")
API_RATE_LIMIT = int(os.getenv("XAI_API_RATE_LIMIT", "120"))
API_RATE_WINDOW_SECONDS = int(os.getenv("XAI_API_RATE_WINDOW_SECONDS", "60"))
API_MAX_JSON_BYTES = int(os.getenv("XAI_API_MAX_JSON_BYTES", "1048576"))
API_KEY_STORE_PATH = os.getenv(
    "XAI_API_KEY_STORE",
    os.path.join(os.getcwd(), "secure_keys", "api_keys.json"),
)
API_PEER_SHARED_KEY = os.getenv("XAI_PEER_API_KEY", "").strip()
SECURITY_WEBHOOK_URL = os.getenv("XAI_SECURITY_WEBHOOK_URL", "").strip()
SECURITY_WEBHOOK_TOKEN = os.getenv("XAI_SECURITY_WEBHOOK_TOKEN", "").strip()
SECURITY_WEBHOOK_TIMEOUT = int(os.getenv("XAI_SECURITY_WEBHOOK_TIMEOUT", "5"))
SECURITY_WEBHOOK_QUEUE_PATH = os.getenv(
    "XAI_SECURITY_WEBHOOK_QUEUE", os.path.join(os.getcwd(), "data", "security_webhook_queue.json")
)
SECURITY_WEBHOOK_QUEUE_KEY = os.getenv("XAI_SECURITY_WEBHOOK_QUEUE_KEY", "").strip()
API_ADMIN_KEYS = [key.strip() for key in os.getenv("XAI_API_ADMIN_KEYS", "").split(",") if key.strip()]
API_ADMIN_TOKEN = os.getenv("XAI_API_ADMIN_TOKEN", "")
if API_ADMIN_TOKEN:
    API_ADMIN_KEYS.append(API_ADMIN_TOKEN)
API_AUTH_REQUIRED = bool(int(os.getenv("XAI_API_AUTH_REQUIRED", "0")))
API_AUTH_KEYS = [key.strip() for key in os.getenv("XAI_API_KEYS", "").split(",") if key.strip()]
LEDGER_DERIVATION_PATH = os.getenv("XAI_LEDGER_PATH", "44'/0'/0'/0/0")
# SECURITY: Embedded wallet salt must be unique per deployment
EMBEDDED_WALLET_SALT = _get_required_secret("XAI_EMBEDDED_SALT", NETWORK)
EMBEDDED_WALLET_DIR = os.getenv("XAI_EMBEDDED_DIR", os.path.join(os.getcwd(), "embedded_wallets"))
TRUSTED_PEER_PUBKEYS = [key.strip().lower() for key in os.getenv("XAI_TRUSTED_PEER_PUBKEYS", "").split(",") if key.strip()]
TRUSTED_PEER_CERT_FINGERPRINTS = [
    fp.strip().lower() for fp in os.getenv("XAI_TRUSTED_PEER_CERT_FPS", "").split(",") if fp.strip()
]
TRUSTED_PEER_PUBKEYS_FILE = os.getenv("XAI_TRUSTED_PEER_PUBKEYS_FILE", "").strip()
TRUSTED_PEER_CERT_FPS_FILE = os.getenv("XAI_TRUSTED_PEER_CERT_FPS_FILE", "").strip()
PEER_NONCE_TTL_SECONDS = int(os.getenv("XAI_PEER_NONCE_TTL_SECONDS", "300"))
PEER_REQUIRE_CLIENT_CERT = bool(int(os.getenv("XAI_PEER_REQUIRE_CLIENT_CERT", "0")))
P2P_DNS_SEEDS = [seed.strip() for seed in os.getenv("XAI_P2P_DNS_SEEDS", "").split(",") if seed.strip()]
P2P_BOOTSTRAP_NODES = [seed.strip() for seed in os.getenv("XAI_P2P_BOOTSTRAP_NODES", "").split(",") if seed.strip()]
P2P_MAX_MESSAGE_RATE = int(os.getenv("XAI_P2P_MAX_MESSAGE_RATE", "100"))
P2P_SECURITY_LOG_RATE = int(os.getenv("XAI_P2P_SECURITY_LOG_RATE", "20"))
P2P_MAX_BANDWIDTH_IN = int(os.getenv("XAI_P2P_MAX_BANDWIDTH_IN", str(1024 * 1024)))
P2P_MAX_BANDWIDTH_OUT = int(os.getenv("XAI_P2P_MAX_BANDWIDTH_OUT", str(1024 * 1024)))
P2P_CA_BUNDLE = os.getenv("XAI_P2P_CA_BUNDLE", os.getenv("XAI_PEER_CA_BUNDLE", "")).strip()
P2P_ENABLE_QUIC = bool(int(os.getenv("XAI_P2P_ENABLE_QUIC", "0")))
P2P_QUIC_DIAL_TIMEOUT = float(os.getenv("XAI_P2P_QUIC_DIAL_TIMEOUT", "1.0"))

SAFE_GENESIS_HASHES = {
    NetworkType.TESTNET: os.getenv(
        "XAI_TESTNET_GENESIS_HASH",
        "59b30b2d8525512cbd5715b24546d73b540ddb575d3778fdbdff02ba245a9141",
    ),
    NetworkType.MAINNET: os.getenv("XAI_MAINNET_GENESIS_HASH", ""),
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
    GENESIS_FILE = "genesis_testnet.json"
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
    BLOCKCHAIN_FILE = "blockchain_testnet.json"
    WALLET_DIR = "wallets_testnet"
    DATA_DIR = "data_testnet"

    # Faucet (testnet only)
    FAUCET_ENABLED = True
    FAUCET_AMOUNT = 100.0  # Free test XAI

    # Addresses (testnet prefix)
    ADDRESS_PREFIX = "TXAI"  # Testnet XAI
    TRADE_FEE_ADDRESS = "TXAITRADEFEE"
    FIAT_REENABLE_DATE = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    LEDGER_DERIVATION_PATH = LEDGER_DERIVATION_PATH
    FIAT_UNLOCK_GOVERNANCE_START = FIAT_UNLOCK_GOVERNANCE_START
    FIAT_UNLOCK_REQUIRED_VOTES = FIAT_UNLOCK_REQUIRED_VOTES
    FIAT_UNLOCK_SUPPORT_PERCENT = FIAT_UNLOCK_SUPPORT_PERCENT
    TRADE_FEE_PERCENT = 0.002
    TRADE_ORDER_EXPIRY = 3600
    # SECURITY: Lucky block seed should be unpredictable
    LUCKY_BLOCK_SEED = _get_required_secret("XAI_LUCKY_BLOCK_SEED", NETWORK)
    API_RATE_LIMIT = API_RATE_LIMIT
    API_RATE_WINDOW_SECONDS = API_RATE_WINDOW_SECONDS
    API_MAX_JSON_BYTES = API_MAX_JSON_BYTES
    API_KEY_STORE_PATH = API_KEY_STORE_PATH
    API_ADMIN_KEYS = API_ADMIN_KEYS
    API_AUTH_REQUIRED = API_AUTH_REQUIRED
    API_AUTH_KEYS = API_AUTH_KEYS
    PEER_API_KEY = API_PEER_SHARED_KEY
    PEER_TLS_REQUIRED = bool(int(os.getenv("XAI_PEER_TLS_REQUIRED", "0")))
    PEER_CA_BUNDLE = os.getenv("XAI_PEER_CA_BUNDLE", "").strip()
    PEER_NONCE_TTL_SECONDS = PEER_NONCE_TTL_SECONDS
    PEER_REQUIRE_CLIENT_CERT = PEER_REQUIRE_CLIENT_CERT
    TRUSTED_PEER_PUBKEYS = TRUSTED_PEER_PUBKEYS
    TRUSTED_PEER_CERT_FINGERPRINTS = TRUSTED_PEER_CERT_FINGERPRINTS
    TRUSTED_PEER_PUBKEYS_FILE = TRUSTED_PEER_PUBKEYS_FILE
    TRUSTED_PEER_CERT_FPS_FILE = TRUSTED_PEER_CERT_FPS_FILE
    P2P_DNS_SEEDS = P2P_DNS_SEEDS
    P2P_BOOTSTRAP_NODES = P2P_BOOTSTRAP_NODES
    P2P_MAX_MESSAGE_RATE = P2P_MAX_MESSAGE_RATE
    P2P_SECURITY_LOG_RATE = P2P_SECURITY_LOG_RATE
    P2P_MAX_BANDWIDTH_IN = P2P_MAX_BANDWIDTH_IN
    P2P_MAX_BANDWIDTH_OUT = P2P_MAX_BANDWIDTH_OUT
    P2P_CA_BUNDLE = P2P_CA_BUNDLE
    WALLET_TRADE_PEER_SECRET = WALLET_TRADE_PEER_SECRET

# Mempool limits
MEMPOOL_MAX_SIZE = int(os.getenv("XAI_MEMPOOL_MAX_SIZE", "10000"))
MEMPOOL_MAX_PER_SENDER = int(os.getenv("XAI_MEMPOOL_MAX_PER_SENDER", "100"))
MEMPOOL_MIN_FEE_RATE = float(os.getenv("XAI_MEMPOOL_MIN_FEE_RATE", "0.0000001"))
MEMPOOL_INVALID_TX_THRESHOLD = int(os.getenv("XAI_MEMPOOL_INVALID_TX_THRESHOLD", "3"))
MEMPOOL_INVALID_BAN_SECONDS = int(os.getenv("XAI_MEMPOOL_INVALID_BAN_SECONDS", "900"))
MEMPOOL_INVALID_WINDOW_SECONDS = int(os.getenv("XAI_MEMPOOL_INVALID_WINDOW_SECONDS", "900"))
MEMPOOL_ALERT_INVALID_DELTA = int(os.getenv("XAI_MEMPOOL_ALERT_INVALID_DELTA", "50"))
MEMPOOL_ALERT_BAN_DELTA = int(os.getenv("XAI_MEMPOOL_ALERT_BAN_DELTA", "10"))
MEMPOOL_ALERT_ACTIVE_BANS = int(os.getenv("XAI_MEMPOOL_ALERT_ACTIVE_BANS", "1"))
SECURITY_WEBHOOK_URL = SECURITY_WEBHOOK_URL
SECURITY_WEBHOOK_TOKEN = SECURITY_WEBHOOK_TOKEN
SECURITY_WEBHOOK_TIMEOUT = SECURITY_WEBHOOK_TIMEOUT
SECURITY_WEBHOOK_QUEUE_PATH = SECURITY_WEBHOOK_QUEUE_PATH
SECURITY_WEBHOOK_QUEUE_KEY = SECURITY_WEBHOOK_QUEUE_KEY
EMBEDDED_WALLET_SALT = EMBEDDED_WALLET_SALT
EMBEDDED_WALLET_DIR = EMBEDDED_WALLET_DIR
WALLET_TRADE_PEER_SECRET = WALLET_TRADE_PEER_SECRET
TIME_CAPSULE_MASTER_KEY = TIME_CAPSULE_MASTER_KEY
FEATURE_FLAGS = FEATURE_FLAGS
MAX_CONTRACT_GAS = MAX_CONTRACT_GAS

# Fast reset (testnet only)
ALLOW_CHAIN_RESET = True


class MainnetConfig:
    """Mainnet Configuration (production blockchain)"""

    # Network
    NETWORK_TYPE = NetworkType.MAINNET
    NETWORK_ID = 0x5841  # 'XA' in hex

    # Genesis
    GENESIS_FILE = "genesis_new.json"  # The real genesis with 22.4M premine
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
    BLOCKCHAIN_FILE = "blockchain.json"
    WALLET_DIR = "wallets"
    DATA_DIR = "data"

    # Faucet (disabled on mainnet)
    FAUCET_ENABLED = False
    FAUCET_AMOUNT = 0.0

    # Addresses (mainnet prefix)
    ADDRESS_PREFIX = "XAI"
    TRADE_FEE_ADDRESS = "XAITRADEFEE"
    FIAT_REENABLE_DATE = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    LEDGER_DERIVATION_PATH = LEDGER_DERIVATION_PATH
    FIAT_UNLOCK_GOVERNANCE_START = FIAT_UNLOCK_GOVERNANCE_START
    FIAT_UNLOCK_REQUIRED_VOTES = FIAT_UNLOCK_REQUIRED_VOTES
    FIAT_UNLOCK_SUPPORT_PERCENT = FIAT_UNLOCK_SUPPORT_PERCENT
    TRADE_FEE_PERCENT = 0.001
    TRADE_ORDER_EXPIRY = 3600
    # SECURITY: Lucky block seed - uses network-aware function
    # On mainnet, this will be enforced when Config is selected
    LUCKY_BLOCK_SEED = os.getenv("XAI_LUCKY_BLOCK_SEED", "")
    API_RATE_LIMIT = API_RATE_LIMIT
    API_RATE_WINDOW_SECONDS = API_RATE_WINDOW_SECONDS
    API_MAX_JSON_BYTES = API_MAX_JSON_BYTES
    API_KEY_STORE_PATH = API_KEY_STORE_PATH
    API_ADMIN_KEYS = API_ADMIN_KEYS
    API_AUTH_REQUIRED = API_AUTH_REQUIRED
    API_AUTH_KEYS = API_AUTH_KEYS
    PEER_API_KEY = API_PEER_SHARED_KEY
    SECURITY_WEBHOOK_URL = SECURITY_WEBHOOK_URL
    SECURITY_WEBHOOK_TOKEN = SECURITY_WEBHOOK_TOKEN
    SECURITY_WEBHOOK_TIMEOUT = SECURITY_WEBHOOK_TIMEOUT
    SECURITY_WEBHOOK_QUEUE_PATH = SECURITY_WEBHOOK_QUEUE_PATH
    SECURITY_WEBHOOK_QUEUE_KEY = SECURITY_WEBHOOK_QUEUE_KEY
    EMBEDDED_WALLET_SALT = EMBEDDED_WALLET_SALT
    EMBEDDED_WALLET_DIR = EMBEDDED_WALLET_DIR
    WALLET_TRADE_PEER_SECRET = WALLET_TRADE_PEER_SECRET
    TIME_CAPSULE_MASTER_KEY = TIME_CAPSULE_MASTER_KEY
    FEATURE_FLAGS = FEATURE_FLAGS
    MAX_CONTRACT_GAS = MAX_CONTRACT_GAS
    PEER_NONCE_TTL_SECONDS = PEER_NONCE_TTL_SECONDS
    PEER_REQUIRE_CLIENT_CERT = PEER_REQUIRE_CLIENT_CERT
    TRUSTED_PEER_PUBKEYS = TRUSTED_PEER_PUBKEYS
    TRUSTED_PEER_CERT_FINGERPRINTS = TRUSTED_PEER_CERT_FINGERPRINTS
    TRUSTED_PEER_PUBKEYS_FILE = TRUSTED_PEER_PUBKEYS_FILE
    TRUSTED_PEER_CERT_FPS_FILE = TRUSTED_PEER_CERT_FPS_FILE
    P2P_DNS_SEEDS = P2P_DNS_SEEDS
    P2P_BOOTSTRAP_NODES = P2P_BOOTSTRAP_NODES
    P2P_MAX_MESSAGE_RATE = P2P_MAX_MESSAGE_RATE
    P2P_SECURITY_LOG_RATE = P2P_SECURITY_LOG_RATE
    P2P_MAX_BANDWIDTH_IN = P2P_MAX_BANDWIDTH_IN
    P2P_MAX_BANDWIDTH_OUT = P2P_MAX_BANDWIDTH_OUT
    P2P_CA_BUNDLE = P2P_CA_BUNDLE

    # No reset on mainnet
    ALLOW_CHAIN_RESET = False


# Select config based on network
if NETWORK.lower() == "mainnet":
    Config = MainnetConfig
    # Enforce required secrets for mainnet
    _required_mainnet_secrets = [
        ("XAI_WALLET_TRADE_PEER_SECRET", WALLET_TRADE_PEER_SECRET),
        ("XAI_TIME_CAPSULE_MASTER_KEY", TIME_CAPSULE_MASTER_KEY),
        ("XAI_EMBEDDED_SALT", EMBEDDED_WALLET_SALT),
        ("XAI_LUCKY_BLOCK_SEED", MainnetConfig.LUCKY_BLOCK_SEED),
    ]
    for env_var, value in _required_mainnet_secrets:
        if not value or len(value) < 16:
            raise ConfigurationError(
                f"CRITICAL: {env_var} must be set to a secure value (min 16 chars) for mainnet. "
                f"Generate: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
else:
    Config = TestnetConfig

Config.SAFE_GENESIS_HASHES = SAFE_GENESIS_HASHES
Config.MEMPOOL_MIN_FEE_RATE = MEMPOOL_MIN_FEE_RATE
Config.MEMPOOL_INVALID_TX_THRESHOLD = MEMPOOL_INVALID_TX_THRESHOLD
Config.MEMPOOL_INVALID_BAN_SECONDS = MEMPOOL_INVALID_BAN_SECONDS
Config.MEMPOOL_INVALID_WINDOW_SECONDS = MEMPOOL_INVALID_WINDOW_SECONDS
Config.MEMPOOL_ALERT_INVALID_DELTA = MEMPOOL_ALERT_INVALID_DELTA
Config.MEMPOOL_ALERT_BAN_DELTA = MEMPOOL_ALERT_BAN_DELTA
Config.MEMPOOL_ALERT_ACTIVE_BANS = MEMPOOL_ALERT_ACTIVE_BANS
Config.P2P_QUIC_DIAL_TIMEOUT = P2P_QUIC_DIAL_TIMEOUT

# Wallet trade peers

WALLET_TRADE_PEERS = [
    peer.strip() for peer in os.getenv("XAI_WALLET_TRADE_PEERS", "").split(",") if peer.strip()
]

# Allow Config classes to expose the global peer list
Config.WALLET_TRADE_PEERS = WALLET_TRADE_PEERS

# Export config
__all__ = [
    "Config",
    "NetworkType",
    "TestnetConfig",
    "MainnetConfig",
    "WALLET_TRADE_PEERS",
    "WALLET_TRADE_PEER_SECRET",
    "TIME_CAPSULE_MASTER_KEY",
    "PERSONAL_AI_WEBHOOK_URL",
    "PERSONAL_AI_WEBHOOK_TIMEOUT",
    "WALLET_PASSWORD",
    "API_RATE_LIMIT",
    "API_RATE_WINDOW_SECONDS",
    "API_MAX_JSON_BYTES",
    "SAFE_GENESIS_HASHES",
]
