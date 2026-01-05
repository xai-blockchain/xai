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
import json
import logging
import os
import secrets as secrets_module
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

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

# Node operation mode configuration
NODE_MODE = os.getenv("XAI_NODE_MODE", "full").strip().lower()
PRUNE_BLOCKS = int(os.getenv("XAI_PRUNE_BLOCKS", "0"))
CHECKPOINT_SYNC_ENABLED = bool(int(os.getenv("XAI_CHECKPOINT_SYNC", "1")))

# Pruning configuration
PRUNE_MODE = os.getenv("XAI_PRUNE_MODE", "none").strip().lower()
PRUNE_KEEP_BLOCKS = int(os.getenv("XAI_PRUNE_KEEP_BLOCKS", "1000"))
PRUNE_KEEP_DAYS = int(os.getenv("XAI_PRUNE_KEEP_DAYS", "30"))
PRUNE_AUTO = os.getenv("XAI_PRUNE_AUTO", "false").strip().lower() == "true"
PRUNE_ARCHIVE = os.getenv("XAI_PRUNE_ARCHIVE", "true").strip().lower() == "true"
PRUNE_ARCHIVE_PATH = os.getenv("XAI_PRUNE_ARCHIVE_PATH", "data/archive")
PRUNE_DISK_THRESHOLD_GB = float(os.getenv("XAI_PRUNE_DISK_THRESHOLD_GB", "50.0"))
PRUNE_MIN_FINALIZED_DEPTH = int(os.getenv("XAI_PRUNE_MIN_FINALIZED_DEPTH", "100"))
PRUNE_KEEP_HEADERS = os.getenv("XAI_PRUNE_KEEP_HEADERS", "true").strip().lower() == "true"

FEATURE_FLAGS = {
    "vm": os.getenv("XAI_VM_ENABLED", "0").strip() == "1",
}

# Peer diversity / ASN enforcement defaults
P2P_MAX_PEERS_PER_PREFIX = int(os.getenv("XAI_P2P_MAX_PEERS_PER_PREFIX", "8"))
P2P_MAX_PEERS_PER_ASN = int(os.getenv("XAI_P2P_MAX_PEERS_PER_ASN", "16"))
P2P_MAX_PEERS_PER_COUNTRY = int(os.getenv("XAI_P2P_MAX_PEERS_PER_COUNTRY", "48"))
P2P_DIVERSITY_PREFIX_LENGTH = int(os.getenv("XAI_P2P_DIVERSITY_PREFIX_LENGTH", "16"))
P2P_MIN_UNIQUE_PREFIXES = int(os.getenv("XAI_P2P_MIN_UNIQUE_PREFIXES", "5"))
P2P_MIN_UNIQUE_ASNS = int(os.getenv("XAI_P2P_MIN_UNIQUE_ASNS", "5"))
P2P_MIN_UNIQUE_COUNTRIES = int(os.getenv("XAI_P2P_MIN_UNIQUE_COUNTRIES", "5"))
P2P_MAX_UNKNOWN_GEO = int(os.getenv("XAI_P2P_MAX_UNKNOWN_GEO", "32"))
P2P_GEOIP_ENDPOINT = os.getenv("XAI_P2P_GEOIP_ENDPOINT", "https://ipinfo.io/{ip}/json").strip()
P2P_GEOIP_TIMEOUT = float(os.getenv("XAI_P2P_GEOIP_TIMEOUT", "2.5"))
P2P_GEOIP_CACHE_TTL = int(os.getenv("XAI_P2P_GEOIP_CACHE_TTL", "3600"))
P2P_CONNECTION_IDLE_TIMEOUT_SECONDS = int(os.getenv("XAI_P2P_IDLE_TIMEOUT_SECONDS", "900"))

MAX_CONTRACT_GAS = int(os.getenv("XAI_MAX_CONTRACT_GAS", "20000000"))

# SECURITY: These secrets are required for production
# On mainnet, missing values will raise ConfigurationError
# On testnet, missing values will generate random secrets with warnings
WALLET_TRADE_PEER_SECRET = _get_required_secret("XAI_WALLET_TRADE_PEER_SECRET", NETWORK)
TIME_CAPSULE_MASTER_KEY = _get_required_secret("XAI_TIME_CAPSULE_MASTER_KEY", NETWORK)
PERSONAL_AI_WEBHOOK_URL = os.getenv("XAI_PERSONAL_AI_WEBHOOK_URL", "")
PERSONAL_AI_WEBHOOK_TIMEOUT = int(os.getenv("XAI_PERSONAL_AI_WEBHOOK_TIMEOUT", "5"))
WALLET_PASSWORD = os.getenv("XAI_WALLET_PASSWORD", "")
EMERGENCY_PAUSER_ADDRESS = os.getenv("XAI_EMERGENCY_PAUSER", "0xAdmin").strip() or "0xAdmin"
EMERGENCY_CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("XAI_EMERGENCY_CIRCUIT_THRESHOLD", "3"))
EMERGENCY_CIRCUIT_BREAKER_TIMEOUT_SECONDS = int(os.getenv("XAI_EMERGENCY_CIRCUIT_TIMEOUT_SECONDS", "300"))

def _parse_origin_list(raw: str) -> list[str]:
    """Convert comma-separated origins into normalized list."""
    origins: list[str] = []
    for chunk in raw.split(","):
        origin = chunk.strip()
        if origin:
            origins.append(origin)
    return origins

API_RATE_LIMIT = int(os.getenv("XAI_API_RATE_LIMIT", "120"))
API_RATE_WINDOW_SECONDS = int(os.getenv("XAI_API_RATE_WINDOW_SECONDS", "60"))
API_MAX_JSON_BYTES = int(os.getenv("XAI_API_MAX_JSON_BYTES", "1048576"))

# Enhanced Rate Limiting Configuration (DDoS Protection)
# Categories: read (high), write (medium), sensitive (strict), admin (very strict)
RATE_LIMIT_ENABLED = bool(int(os.getenv("XAI_RATE_LIMIT_ENABLED", "1")))

# Read endpoints - higher limits (info queries, status checks)
RATE_LIMIT_READ_REQUESTS = int(os.getenv("XAI_RATE_LIMIT_READ", "300"))
RATE_LIMIT_READ_WINDOW = int(os.getenv("XAI_RATE_LIMIT_READ_WINDOW", "60"))

# Write endpoints - medium limits (transactions, state changes)
RATE_LIMIT_WRITE_REQUESTS = int(os.getenv("XAI_RATE_LIMIT_WRITE", "50"))
RATE_LIMIT_WRITE_WINDOW = int(os.getenv("XAI_RATE_LIMIT_WRITE_WINDOW", "60"))

# Sensitive endpoints - strict limits (faucet, auth, registration)
RATE_LIMIT_SENSITIVE_REQUESTS = int(os.getenv("XAI_RATE_LIMIT_SENSITIVE", "5"))
RATE_LIMIT_SENSITIVE_WINDOW = int(os.getenv("XAI_RATE_LIMIT_SENSITIVE_WINDOW", "300"))

# Admin endpoints - very strict limits
RATE_LIMIT_ADMIN_REQUESTS = int(os.getenv("XAI_RATE_LIMIT_ADMIN", "20"))
RATE_LIMIT_ADMIN_WINDOW = int(os.getenv("XAI_RATE_LIMIT_ADMIN_WINDOW", "60"))

# DDoS detection thresholds
RATE_LIMIT_DDOS_THRESHOLD = int(os.getenv("XAI_RATE_LIMIT_DDOS_THRESHOLD", "1000"))
RATE_LIMIT_DDOS_WINDOW = int(os.getenv("XAI_RATE_LIMIT_DDOS_WINDOW", "60"))
RATE_LIMIT_BLOCK_DURATION = int(os.getenv("XAI_RATE_LIMIT_BLOCK_DURATION", "3600"))

# Faucet specific limits (very strict to prevent abuse)
RATE_LIMIT_FAUCET_REQUESTS = int(os.getenv("XAI_RATE_LIMIT_FAUCET", "1"))
RATE_LIMIT_FAUCET_WINDOW = int(os.getenv("XAI_RATE_LIMIT_FAUCET_WINDOW", "86400"))
FAUCET_WALLET_FILE = os.getenv("XAI_FAUCET_WALLET_FILE", "").strip()
FAUCET_WALLET_PASSWORD = os.getenv("XAI_FAUCET_WALLET_PASSWORD", "").strip()
API_ALLOWED_ORIGINS = _parse_origin_list(os.getenv("XAI_API_ALLOWED_ORIGINS", ""))
API_KEY_STORE_PATH = os.getenv(
    "XAI_API_KEY_STORE",
    os.path.join(os.getcwd(), "secure_keys", "api_keys.json"),
)
API_KEY_DEFAULT_TTL_DAYS = int(os.getenv("XAI_API_KEY_DEFAULT_TTL_DAYS", "90"))
API_KEY_MAX_TTL_DAYS = int(os.getenv("XAI_API_KEY_MAX_TTL_DAYS", "365"))
API_KEY_ALLOW_PERMANENT = bool(int(os.getenv("XAI_API_KEY_ALLOW_PERMANENT", "0")))
API_PEER_SHARED_KEY = os.getenv("XAI_PEER_API_KEY", "").strip()
SECURITY_WEBHOOK_URL = os.getenv("XAI_SECURITY_WEBHOOK_URL", "").strip()
SECURITY_WEBHOOK_TOKEN = os.getenv("XAI_SECURITY_WEBHOOK_TOKEN", "").strip()
SECURITY_WEBHOOK_TIMEOUT = int(os.getenv("XAI_SECURITY_WEBHOOK_TIMEOUT", "5"))
SECURITY_WEBHOOK_QUEUE_PATH = os.getenv(
    "XAI_SECURITY_WEBHOOK_QUEUE", os.path.join(os.getcwd(), "data", "security_webhook_queue.json")
)
SECURITY_WEBHOOK_QUEUE_KEY = os.getenv("XAI_SECURITY_WEBHOOK_QUEUE_KEY", "").strip()
API_ADMIN_KEYS = [key.strip() for key in os.getenv("XAI_API_ADMIN_KEYS", "").split(",") if key.strip()]
API_OPERATOR_KEYS = [key.strip() for key in os.getenv("XAI_API_OPERATOR_KEYS", "").split(",") if key.strip()]
API_AUDITOR_KEYS = [key.strip() for key in os.getenv("XAI_API_AUDITOR_KEYS", "").split(",") if key.strip()]
API_ADMIN_TOKEN = os.getenv("XAI_API_ADMIN_TOKEN", "")
if API_ADMIN_TOKEN:
    API_ADMIN_KEYS.append(API_ADMIN_TOKEN)
API_AUTH_REQUIRED = bool(int(os.getenv("XAI_API_AUTH_REQUIRED", "1")))
API_AUTH_KEYS = [key.strip() for key in os.getenv("XAI_API_KEYS", "").split(",") if key.strip()]

# Thread-safe configuration lock for runtime modifications
_config_lock = threading.RLock()

_RUNTIME_MUTABLE_FIELDS: dict[str, tuple[str, Callable[[str], Any]]] = {
    "API_RATE_LIMIT": ("XAI_API_RATE_LIMIT", int),
    "API_RATE_WINDOW_SECONDS": ("XAI_API_RATE_WINDOW_SECONDS", int),
    "API_MAX_JSON_BYTES": ("XAI_API_MAX_JSON_BYTES", int),
    "API_ALLOWED_ORIGINS": ("XAI_API_ALLOWED_ORIGINS", _parse_origin_list),
}
_RUNTIME_INITIAL_VALUES = {key: globals()[key] for key in _RUNTIME_MUTABLE_FIELDS}

def reload_runtime(overrides: dict[str, str] | None = None) -> dict[str, Any]:
    """
    Reload selected runtime configuration values from environment.

    Thread-safe: Uses _config_lock to ensure atomic updates across all
    configuration sources (globals, TestnetConfig, MainnetConfig).

    Args:
        overrides: Optional mapping of env var -> value to apply for this reload

    Returns:
        Dictionary describing changed attributes and timestamp.

    Raises:
        ConfigurationError: If a provided override fails validation.
    """
    env = os.environ.copy()
    if overrides:
        env.update({key: str(value) for key, value in overrides.items()})

    changes: dict[str, dict[str, Any]] = {}

    # Validate all values before acquiring lock to minimize lock hold time
    pending_updates: list[tuple[str, Any, Any]] = []
    for attr, (env_var, parser) in _RUNTIME_MUTABLE_FIELDS.items():
        raw = env.get(env_var)
        if raw is None:
            continue
        try:
            new_value = parser(raw) if raw.strip() else _RUNTIME_INITIAL_VALUES[attr]
        except Exception as exc:  # pylint: disable=broad-except
            raise ConfigurationError(f"Invalid value for {env_var}: {exc}") from exc
        current_value = globals()[attr]
        if new_value != current_value:
            pending_updates.append((attr, current_value, new_value))

    # Apply all updates atomically under lock
    with _config_lock:
        for attr, old_value, new_value in pending_updates:
            globals()[attr] = new_value
            setattr(TestnetConfig, attr, new_value)
            setattr(MainnetConfig, attr, new_value)
            changes[attr] = {"old": old_value, "new": new_value}
        logger.info(
            "Configuration reloaded: %d changes",
            len(changes),
            extra={"event": "config.reload", "changes": list(changes.keys())}
        )

    return {
        "changed": changes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_runtime_config(attr: str) -> Any:
    """
    Thread-safe getter for runtime-mutable configuration values.

    Args:
        attr: Configuration attribute name (e.g., 'API_RATE_LIMIT')

    Returns:
        Current value of the configuration attribute.

    Raises:
        KeyError: If attr is not a runtime-mutable field.
    """
    if attr not in _RUNTIME_MUTABLE_FIELDS:
        raise KeyError(f"'{attr}' is not a runtime-mutable configuration field")
    with _config_lock:
        return globals()[attr]

def _parse_supported_versions(raw: str) -> list[str]:
    versions = [segment.strip() for segment in raw.split(",") if segment.strip()]
    return versions or ["v1"]

API_SUPPORTED_VERSIONS = _parse_supported_versions(os.getenv("XAI_API_VERSIONS", "v1,v2"))
API_DEFAULT_VERSION = os.getenv("XAI_API_DEFAULT_VERSION", "v2").strip() or API_SUPPORTED_VERSIONS[-1]
if API_DEFAULT_VERSION not in API_SUPPORTED_VERSIONS:
    API_DEFAULT_VERSION = API_SUPPORTED_VERSIONS[-1]

def _parse_int_list(raw: str) -> list[int]:
    values: list[int] = []
    for chunk in raw.split(","):
        entry = chunk.strip()
        if not entry:
            continue
        try:
            values.append(int(entry))
        except ValueError:
            continue
    return values

BLOCK_HEADER_VERSION = int(os.getenv("XAI_BLOCK_HEADER_VERSION", "1"))
_allowed_versions_env = os.getenv("XAI_BLOCK_HEADER_ALLOWED_VERSIONS", "")
BLOCK_HEADER_ALLOWED_VERSIONS = _parse_int_list(_allowed_versions_env)
if not BLOCK_HEADER_ALLOWED_VERSIONS:
    BLOCK_HEADER_ALLOWED_VERSIONS = [BLOCK_HEADER_VERSION]

def _parse_deprecations(raw: str) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for chunk in raw.split(","):
        entry = chunk.strip()
        if not entry:
            continue
        version, _, sunset = entry.partition("=")
        version = version.strip()
        if not version:
            continue
        info: dict[str, str] = {}
        if sunset.strip():
            info["sunset"] = sunset.strip()
        mapping[version] = info
    return mapping

API_DEPRECATED_VERSIONS = _parse_deprecations(
    os.getenv("XAI_API_VERSION_DEPRECATIONS", "v1=Wed, 01 Jan 2025 00:00:00 GMT")
)
API_VERSION_DOCS_URL = os.getenv(
    "XAI_API_VERSION_DOCS_URL",
    "https://github.com/xai-blockchain/xai/blob/main/docs/api/versioning.md",
).strip()
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

def _parse_deposit_sources(raw: str) -> dict[str, Any]:
    """Parse JSON object describing crypto deposit sources."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Invalid XAI_CRYPTO_DEPOSIT_SOURCES JSON: %s", exc)
        return {}
    if not isinstance(data, dict):
        logger.error("XAI_CRYPTO_DEPOSIT_SOURCES must be a JSON object mapping currency to config")
        return {}
    normalized: dict[str, Any] = {}
    for currency, cfg in data.items():
        if not isinstance(cfg, dict):
            continue
        normalized[currency.upper()] = cfg
    return normalized

CRYPTO_DEPOSIT_MONITOR_ENABLED = bool(int(os.getenv("XAI_CRYPTO_DEPOSIT_MONITOR_ENABLED", "0")))
CRYPTO_DEPOSIT_MONITOR_POLL_INTERVAL = int(os.getenv("XAI_CRYPTO_DEPOSIT_POLL_INTERVAL", "30"))
CRYPTO_DEPOSIT_MONITOR_POLL_JITTER = int(os.getenv("XAI_CRYPTO_DEPOSIT_POLL_JITTER", "5"))
CRYPTO_DEPOSIT_SOURCES = _parse_deposit_sources(os.getenv("XAI_CRYPTO_DEPOSIT_SOURCES", ""))
CRYPTO_DEPOSIT_MONITOR = {
    "ENABLED": CRYPTO_DEPOSIT_MONITOR_ENABLED,
    "POLL_INTERVAL": CRYPTO_DEPOSIT_MONITOR_POLL_INTERVAL,
    "JITTER_SECONDS": CRYPTO_DEPOSIT_MONITOR_POLL_JITTER,
    "SOURCES": CRYPTO_DEPOSIT_SOURCES,
}
PEER_NONCE_TTL_SECONDS = int(os.getenv("XAI_PEER_NONCE_TTL_SECONDS", "300"))
PEER_REQUIRE_CLIENT_CERT = bool(int(os.getenv("XAI_PEER_REQUIRE_CLIENT_CERT", "0")))
P2P_DNS_SEEDS = [seed.strip() for seed in os.getenv("XAI_P2P_DNS_SEEDS", "").split(",") if seed.strip()]
P2P_BOOTSTRAP_NODES = [seed.strip() for seed in os.getenv("XAI_P2P_BOOTSTRAP_NODES", "").split(",") if seed.strip()]
P2P_MAX_MESSAGE_RATE = int(os.getenv("XAI_P2P_MAX_MESSAGE_RATE", "100"))
P2P_SECURITY_LOG_RATE = int(os.getenv("XAI_P2P_SECURITY_LOG_RATE", "20"))
P2P_MAX_BANDWIDTH_IN = int(os.getenv("XAI_P2P_MAX_BANDWIDTH_IN", str(1024 * 1024)))
P2P_MAX_BANDWIDTH_OUT = int(os.getenv("XAI_P2P_MAX_BANDWIDTH_OUT", str(1024 * 1024)))
P2P_MAX_CONNECTIONS_PER_IP = int(os.getenv("XAI_P2P_MAX_CONNECTIONS_PER_IP", "50"))
P2P_PING_INTERVAL_SECONDS = int(os.getenv("XAI_P2P_PING_INTERVAL_SECONDS", "20"))
P2P_PING_TIMEOUT_SECONDS = int(os.getenv("XAI_P2P_PING_TIMEOUT_SECONDS", "20"))
P2P_CLOSE_TIMEOUT_SECONDS = int(os.getenv("XAI_P2P_CLOSE_TIMEOUT_SECONDS", "10"))
P2P_MONITOR_INTERVAL_SECONDS = int(os.getenv("XAI_P2P_MONITOR_INTERVAL_SECONDS", "30"))
P2P_MAX_RECONNECT_BACKOFF_SECONDS = int(os.getenv("XAI_P2P_MAX_RECONNECT_BACKOFF_SECONDS", "300"))
P2P_SYNC_INTERVAL_SECONDS = int(os.getenv("XAI_P2P_SYNC_INTERVAL_SECONDS", "30"))
P2P_CA_BUNDLE = os.getenv("XAI_P2P_CA_BUNDLE", os.getenv("XAI_PEER_CA_BUNDLE", "")).strip()
P2P_ENABLE_QUIC = bool(int(os.getenv("XAI_P2P_ENABLE_QUIC", "0")))
P2P_QUIC_DIAL_TIMEOUT = float(os.getenv("XAI_P2P_QUIC_DIAL_TIMEOUT", "1.0"))
P2P_POW_ENABLED = bool(int(os.getenv("XAI_P2P_POW_ENABLED", "1")))
P2P_POW_DIFFICULTY_BITS = int(os.getenv("XAI_P2P_POW_DIFFICULTY_BITS", "18"))
P2P_POW_MAX_ITERATIONS = int(os.getenv("XAI_P2P_POW_MAX_ITERATIONS", "250000"))
P2P_POW_REUSE_WINDOW_SECONDS = int(os.getenv("XAI_P2P_POW_REUSE_WINDOW_SECONDS", "600"))
PARTIAL_SYNC_ENABLED = bool(int(os.getenv("XAI_PARTIAL_SYNC_ENABLED", "1")))
P2P_PARTIAL_SYNC_ENABLED = bool(int(os.getenv("XAI_P2P_PARTIAL_SYNC_ENABLED", "1")))
P2P_PARTIAL_SYNC_MIN_DELTA = int(os.getenv("XAI_P2P_PARTIAL_SYNC_MIN_DELTA", "100"))
P2P_PARALLEL_SYNC_ENABLED = bool(int(os.getenv("XAI_P2P_PARALLEL_SYNC_ENABLED", "1")))
P2P_PARALLEL_SYNC_WORKERS = int(os.getenv("XAI_P2P_PARALLEL_SYNC_WORKERS", "4"))
P2P_PARALLEL_SYNC_CHUNK_SIZE = int(os.getenv("XAI_P2P_PARALLEL_SYNC_CHUNK_SIZE", "128"))
P2P_PARALLEL_SYNC_RETRY = int(os.getenv("XAI_P2P_PARALLEL_SYNC_RETRY", "2"))
P2P_PARALLEL_SYNC_PAGE_LIMIT = int(os.getenv("XAI_P2P_PARALLEL_SYNC_PAGE_LIMIT", "200"))

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
    FAUCET_WALLET_FILE = FAUCET_WALLET_FILE
    FAUCET_WALLET_PASSWORD = FAUCET_WALLET_PASSWORD

    # Addresses (testnet prefix - bech32-style)
    ADDRESS_PREFIX = "xaitest1"  # Testnet XAI (bech32-style)
    TRADE_FEE_ADDRESS = "xaitest1tradefeeaddr00000000000000"  # System trade fee address
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
    API_KEY_DEFAULT_TTL_DAYS = API_KEY_DEFAULT_TTL_DAYS
    API_KEY_MAX_TTL_DAYS = API_KEY_MAX_TTL_DAYS
    API_KEY_ALLOW_PERMANENT = API_KEY_ALLOW_PERMANENT
    API_ALLOWED_ORIGINS = API_ALLOWED_ORIGINS
    API_ADMIN_KEYS = API_ADMIN_KEYS
    EMERGENCY_PAUSER_ADDRESS = EMERGENCY_PAUSER_ADDRESS
    EMERGENCY_CIRCUIT_BREAKER_THRESHOLD = EMERGENCY_CIRCUIT_BREAKER_THRESHOLD
    EMERGENCY_CIRCUIT_BREAKER_TIMEOUT_SECONDS = EMERGENCY_CIRCUIT_BREAKER_TIMEOUT_SECONDS
    API_AUTH_REQUIRED = API_AUTH_REQUIRED
    API_AUTH_KEYS = API_AUTH_KEYS
    API_SUPPORTED_VERSIONS = API_SUPPORTED_VERSIONS
    API_DEFAULT_VERSION = API_DEFAULT_VERSION
    API_DEPRECATED_VERSIONS = API_DEPRECATED_VERSIONS
    API_VERSION_DOCS_URL = API_VERSION_DOCS_URL
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
    P2P_MAX_CONNECTIONS_PER_IP = P2P_MAX_CONNECTIONS_PER_IP
    P2P_PING_INTERVAL_SECONDS = P2P_PING_INTERVAL_SECONDS
    P2P_PING_TIMEOUT_SECONDS = P2P_PING_TIMEOUT_SECONDS
    P2P_CLOSE_TIMEOUT_SECONDS = P2P_CLOSE_TIMEOUT_SECONDS
    P2P_MONITOR_INTERVAL_SECONDS = P2P_MONITOR_INTERVAL_SECONDS
    P2P_MAX_RECONNECT_BACKOFF_SECONDS = P2P_MAX_RECONNECT_BACKOFF_SECONDS
    P2P_SYNC_INTERVAL_SECONDS = P2P_SYNC_INTERVAL_SECONDS
    P2P_CA_BUNDLE = P2P_CA_BUNDLE
    P2P_MAX_PEERS_PER_PREFIX = P2P_MAX_PEERS_PER_PREFIX
    P2P_MAX_PEERS_PER_ASN = P2P_MAX_PEERS_PER_ASN
    P2P_MAX_PEERS_PER_COUNTRY = P2P_MAX_PEERS_PER_COUNTRY
    P2P_MIN_UNIQUE_PREFIXES = P2P_MIN_UNIQUE_PREFIXES
    P2P_MIN_UNIQUE_ASNS = P2P_MIN_UNIQUE_ASNS
    P2P_MIN_UNIQUE_COUNTRIES = P2P_MIN_UNIQUE_COUNTRIES
    P2P_MAX_UNKNOWN_GEO = P2P_MAX_UNKNOWN_GEO
    P2P_GEOIP_ENDPOINT = P2P_GEOIP_ENDPOINT
    P2P_GEOIP_TIMEOUT = P2P_GEOIP_TIMEOUT
    P2P_GEOIP_CACHE_TTL = P2P_GEOIP_CACHE_TTL
    P2P_PARALLEL_SYNC_ENABLED = P2P_PARALLEL_SYNC_ENABLED
    P2P_PARALLEL_SYNC_WORKERS = P2P_PARALLEL_SYNC_WORKERS
    P2P_PARALLEL_SYNC_CHUNK_SIZE = P2P_PARALLEL_SYNC_CHUNK_SIZE
    P2P_PARALLEL_SYNC_RETRY = P2P_PARALLEL_SYNC_RETRY
    P2P_PARALLEL_SYNC_PAGE_LIMIT = P2P_PARALLEL_SYNC_PAGE_LIMIT
    P2P_POW_ENABLED = P2P_POW_ENABLED
    P2P_POW_DIFFICULTY_BITS = P2P_POW_DIFFICULTY_BITS
    P2P_POW_MAX_ITERATIONS = P2P_POW_MAX_ITERATIONS
    P2P_POW_REUSE_WINDOW_SECONDS = P2P_POW_REUSE_WINDOW_SECONDS
    BLOCK_HEADER_VERSION = BLOCK_HEADER_VERSION
    BLOCK_HEADER_ALLOWED_VERSIONS = BLOCK_HEADER_ALLOWED_VERSIONS
    WALLET_TRADE_PEER_SECRET = WALLET_TRADE_PEER_SECRET
    BLOCK_HEADER_VERSION = BLOCK_HEADER_VERSION
    BLOCK_HEADER_ALLOWED_VERSIONS = BLOCK_HEADER_ALLOWED_VERSIONS
    NODE_MODE = NODE_MODE
    PRUNE_BLOCKS = PRUNE_BLOCKS
    CHECKPOINT_SYNC_ENABLED = CHECKPOINT_SYNC_ENABLED
    PRUNE_MODE = PRUNE_MODE
    PRUNE_KEEP_BLOCKS = PRUNE_KEEP_BLOCKS
    PRUNE_KEEP_DAYS = PRUNE_KEEP_DAYS
    PRUNE_AUTO = PRUNE_AUTO
    PRUNE_ARCHIVE = PRUNE_ARCHIVE
    PRUNE_ARCHIVE_PATH = PRUNE_ARCHIVE_PATH
    PRUNE_DISK_THRESHOLD_GB = PRUNE_DISK_THRESHOLD_GB
    PRUNE_MIN_FINALIZED_DEPTH = PRUNE_MIN_FINALIZED_DEPTH
    PRUNE_KEEP_HEADERS = PRUNE_KEEP_HEADERS
    FEATURE_FLAGS = FEATURE_FLAGS
    MAX_CONTRACT_GAS = MAX_CONTRACT_GAS

    # Allow chain reset on testnet for development
    ALLOW_CHAIN_RESET = True

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
ATOMIC_SWAP_FEE_RATE = float(os.getenv("XAI_ATOMIC_SWAP_FEE_RATE", "0.0000005"))
ATOMIC_SWAP_UTXO_TX_SIZE = int(os.getenv("XAI_ATOMIC_SWAP_UTXO_TX_SIZE", "300"))
ATOMIC_SWAP_ETH_GAS_LIMIT = int(os.getenv("XAI_ATOMIC_SWAP_ETH_GAS_LIMIT", "200000"))
ATOMIC_SWAP_ETH_MAX_FEE_GWEI = float(os.getenv("XAI_ATOMIC_SWAP_ETH_MAX_FEE_GWEI", "60"))
ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI = float(os.getenv("XAI_ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI", "2"))
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
    FAUCET_WALLET_FILE = FAUCET_WALLET_FILE
    FAUCET_WALLET_PASSWORD = FAUCET_WALLET_PASSWORD

    # Addresses (mainnet prefix - bech32-style)
    ADDRESS_PREFIX = "xai1"  # Mainnet XAI (bech32-style)
    TRADE_FEE_ADDRESS = "xai1tradefeeaddr000000000000000000000000"  # System trade fee address
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
    API_KEY_DEFAULT_TTL_DAYS = API_KEY_DEFAULT_TTL_DAYS
    API_KEY_MAX_TTL_DAYS = API_KEY_MAX_TTL_DAYS
    API_KEY_ALLOW_PERMANENT = API_KEY_ALLOW_PERMANENT
    API_ALLOWED_ORIGINS = API_ALLOWED_ORIGINS
    API_ADMIN_KEYS = API_ADMIN_KEYS
    EMERGENCY_PAUSER_ADDRESS = EMERGENCY_PAUSER_ADDRESS
    EMERGENCY_CIRCUIT_BREAKER_THRESHOLD = EMERGENCY_CIRCUIT_BREAKER_THRESHOLD
    EMERGENCY_CIRCUIT_BREAKER_TIMEOUT_SECONDS = EMERGENCY_CIRCUIT_BREAKER_TIMEOUT_SECONDS
    API_AUTH_REQUIRED = API_AUTH_REQUIRED
    API_AUTH_KEYS = API_AUTH_KEYS
    API_SUPPORTED_VERSIONS = API_SUPPORTED_VERSIONS
    API_DEFAULT_VERSION = API_DEFAULT_VERSION
    API_DEPRECATED_VERSIONS = API_DEPRECATED_VERSIONS
    API_VERSION_DOCS_URL = API_VERSION_DOCS_URL
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
    P2P_MAX_CONNECTIONS_PER_IP = P2P_MAX_CONNECTIONS_PER_IP
    P2P_PING_INTERVAL_SECONDS = P2P_PING_INTERVAL_SECONDS
    P2P_PING_TIMEOUT_SECONDS = P2P_PING_TIMEOUT_SECONDS
    P2P_CLOSE_TIMEOUT_SECONDS = P2P_CLOSE_TIMEOUT_SECONDS
    P2P_MONITOR_INTERVAL_SECONDS = P2P_MONITOR_INTERVAL_SECONDS
    P2P_MAX_RECONNECT_BACKOFF_SECONDS = P2P_MAX_RECONNECT_BACKOFF_SECONDS
    P2P_SYNC_INTERVAL_SECONDS = P2P_SYNC_INTERVAL_SECONDS
    P2P_CA_BUNDLE = P2P_CA_BUNDLE
    P2P_MAX_PEERS_PER_PREFIX = P2P_MAX_PEERS_PER_PREFIX
    P2P_MAX_PEERS_PER_ASN = P2P_MAX_PEERS_PER_ASN
    P2P_MAX_PEERS_PER_COUNTRY = P2P_MAX_PEERS_PER_COUNTRY
    P2P_MIN_UNIQUE_PREFIXES = P2P_MIN_UNIQUE_PREFIXES
    P2P_MIN_UNIQUE_ASNS = P2P_MIN_UNIQUE_ASNS
    P2P_MIN_UNIQUE_COUNTRIES = P2P_MIN_UNIQUE_COUNTRIES
    P2P_MAX_UNKNOWN_GEO = P2P_MAX_UNKNOWN_GEO
    P2P_GEOIP_ENDPOINT = P2P_GEOIP_ENDPOINT
    P2P_GEOIP_TIMEOUT = P2P_GEOIP_TIMEOUT
    P2P_GEOIP_CACHE_TTL = P2P_GEOIP_CACHE_TTL
    P2P_PARALLEL_SYNC_ENABLED = P2P_PARALLEL_SYNC_ENABLED
    P2P_PARALLEL_SYNC_WORKERS = P2P_PARALLEL_SYNC_WORKERS
    P2P_PARALLEL_SYNC_CHUNK_SIZE = P2P_PARALLEL_SYNC_CHUNK_SIZE
    P2P_PARALLEL_SYNC_RETRY = P2P_PARALLEL_SYNC_RETRY
    P2P_PARALLEL_SYNC_PAGE_LIMIT = P2P_PARALLEL_SYNC_PAGE_LIMIT
    P2P_POW_ENABLED = P2P_POW_ENABLED
    P2P_POW_DIFFICULTY_BITS = P2P_POW_DIFFICULTY_BITS
    P2P_POW_MAX_ITERATIONS = P2P_POW_MAX_ITERATIONS
    P2P_POW_REUSE_WINDOW_SECONDS = P2P_POW_REUSE_WINDOW_SECONDS
    NODE_MODE = NODE_MODE
    PRUNE_BLOCKS = PRUNE_BLOCKS
    CHECKPOINT_SYNC_ENABLED = CHECKPOINT_SYNC_ENABLED
    PRUNE_MODE = PRUNE_MODE
    PRUNE_KEEP_BLOCKS = PRUNE_KEEP_BLOCKS
    PRUNE_KEEP_DAYS = PRUNE_KEEP_DAYS
    PRUNE_AUTO = PRUNE_AUTO
    PRUNE_ARCHIVE = PRUNE_ARCHIVE
    PRUNE_ARCHIVE_PATH = PRUNE_ARCHIVE_PATH
    PRUNE_DISK_THRESHOLD_GB = PRUNE_DISK_THRESHOLD_GB
    PRUNE_MIN_FINALIZED_DEPTH = PRUNE_MIN_FINALIZED_DEPTH
    PRUNE_KEEP_HEADERS = PRUNE_KEEP_HEADERS

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
Config.P2P_CONNECTION_IDLE_TIMEOUT_SECONDS = P2P_CONNECTION_IDLE_TIMEOUT_SECONDS
Config.ATOMIC_SWAP_FEE_RATE = ATOMIC_SWAP_FEE_RATE
Config.ATOMIC_SWAP_UTXO_TX_SIZE = ATOMIC_SWAP_UTXO_TX_SIZE
Config.ATOMIC_SWAP_ETH_GAS_LIMIT = ATOMIC_SWAP_ETH_GAS_LIMIT
Config.ATOMIC_SWAP_ETH_MAX_FEE_GWEI = ATOMIC_SWAP_ETH_MAX_FEE_GWEI
Config.ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI = ATOMIC_SWAP_ETH_PRIORITY_FEE_GWEI
Config.CRYPTO_DEPOSIT_MONITOR = CRYPTO_DEPOSIT_MONITOR
Config.FAUCET_WALLET_FILE = FAUCET_WALLET_FILE
Config.FAUCET_WALLET_PASSWORD = FAUCET_WALLET_PASSWORD

# Wallet trade peers

WALLET_TRADE_PEERS = [
    peer.strip() for peer in os.getenv("XAI_WALLET_TRADE_PEERS", "").split(",") if peer.strip()
]

# Allow Config classes to expose the global peer list
Config.WALLET_TRADE_PEERS = WALLET_TRADE_PEERS

# ============================================================================
# Pydantic Configuration Validation
# ============================================================================

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    from pydantic_settings import BaseSettings
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

if PYDANTIC_AVAILABLE:
    class NetworkSettings(BaseModel):
        """Validated network configuration."""
        network_type: str = Field(default="testnet", pattern=r"^(testnet|mainnet)$")
        node_mode: str = Field(default="full", pattern=r"^(full|light|archive)$")
        max_peers: int = Field(default=50, ge=1, le=1000)

        @field_validator("network_type")
        @classmethod
        def validate_network_type(cls, v: str) -> str:
            return v.lower()

    class APISettings(BaseModel):
        """Validated API configuration."""
        rate_limit: int = Field(default=120, ge=1, le=10000)
        rate_window_seconds: int = Field(default=60, ge=1, le=3600)
        max_json_bytes: int = Field(default=1048576, ge=1024, le=104857600)
        auth_required: bool = Field(default=False)

        @field_validator("rate_limit")
        @classmethod
        def validate_rate_limit(cls, v: int) -> int:
            if v < 1:
                raise ValueError("rate_limit must be at least 1")
            return v

    class P2PSettings(BaseModel):
        """Validated P2P configuration."""
        max_peers_per_prefix: int = Field(default=8, ge=1, le=100)
        max_peers_per_asn: int = Field(default=16, ge=1, le=200)
        ping_interval_seconds: int = Field(default=20, ge=5, le=300)
        ping_timeout_seconds: int = Field(default=20, ge=5, le=300)
        max_message_rate: int = Field(default=100, ge=1, le=10000)
        enable_quic: bool = Field(default=False)
        pow_enabled: bool = Field(default=True)
        pow_difficulty_bits: int = Field(default=18, ge=8, le=32)

    class SecuritySettings(BaseModel):
        """Validated security configuration."""
        emergency_pauser_address: str = Field(default="0xAdmin", min_length=1)
        circuit_breaker_threshold: int = Field(default=3, ge=1, le=100)
        circuit_breaker_timeout_seconds: int = Field(default=300, ge=60, le=86400)
        peer_nonce_ttl_seconds: int = Field(default=300, ge=60, le=3600)

    class ValidatedConfig(BaseModel):
        """Complete validated configuration model."""
        network: NetworkSettings = Field(default_factory=NetworkSettings)
        api: APISettings = Field(default_factory=APISettings)
        p2p: P2PSettings = Field(default_factory=P2PSettings)
        security: SecuritySettings = Field(default_factory=SecuritySettings)

        @classmethod
        def from_environment(cls) -> "ValidatedConfig":
            """Create validated config from current environment variables."""
            return cls(
                network=NetworkSettings(
                    network_type=NETWORK,
                    node_mode=NODE_MODE,
                ),
                api=APISettings(
                    rate_limit=API_RATE_LIMIT,
                    rate_window_seconds=API_RATE_WINDOW_SECONDS,
                    max_json_bytes=API_MAX_JSON_BYTES,
                    auth_required=API_AUTH_REQUIRED,
                ),
                p2p=P2PSettings(
                    max_peers_per_prefix=P2P_MAX_PEERS_PER_PREFIX,
                    max_peers_per_asn=P2P_MAX_PEERS_PER_ASN,
                    ping_interval_seconds=P2P_PING_INTERVAL_SECONDS,
                    ping_timeout_seconds=P2P_PING_TIMEOUT_SECONDS,
                    max_message_rate=P2P_MAX_MESSAGE_RATE,
                    enable_quic=P2P_ENABLE_QUIC,
                    pow_enabled=P2P_POW_ENABLED,
                    pow_difficulty_bits=P2P_POW_DIFFICULTY_BITS,
                ),
                security=SecuritySettings(
                    emergency_pauser_address=EMERGENCY_PAUSER_ADDRESS,
                    circuit_breaker_threshold=EMERGENCY_CIRCUIT_BREAKER_THRESHOLD,
                    circuit_breaker_timeout_seconds=EMERGENCY_CIRCUIT_BREAKER_TIMEOUT_SECONDS,
                    peer_nonce_ttl_seconds=PEER_NONCE_TTL_SECONDS,
                ),
            )

    def validate_config() -> tuple[bool, list[str]]:
        """
        Validate current configuration using Pydantic models.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: list[str] = []
        try:
            ValidatedConfig.from_environment()
        except Exception as e:
            errors.append(str(e))
        return len(errors) == 0, errors

else:
    # Fallback if Pydantic is not available
    def validate_config() -> tuple[bool, list[str]]:
        """Validate configuration (Pydantic not available, basic checks only)."""
        errors: list[str] = []
        if API_RATE_LIMIT < 1:
            errors.append("API_RATE_LIMIT must be at least 1")
        if API_RATE_WINDOW_SECONDS < 1:
            errors.append("API_RATE_WINDOW_SECONDS must be at least 1")
        if NETWORK.lower() not in ("testnet", "mainnet"):
            errors.append("NETWORK must be 'testnet' or 'mainnet'")
        return len(errors) == 0, errors


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
    "NODE_MODE",
    "PRUNE_BLOCKS",
    "CHECKPOINT_SYNC_ENABLED",
    "reload_runtime",
    "get_runtime_config",
    "validate_config",
    "PYDANTIC_AVAILABLE",
    # Enhanced rate limiting exports
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_READ_REQUESTS",
    "RATE_LIMIT_READ_WINDOW",
    "RATE_LIMIT_WRITE_REQUESTS",
    "RATE_LIMIT_WRITE_WINDOW",
    "RATE_LIMIT_SENSITIVE_REQUESTS",
    "RATE_LIMIT_SENSITIVE_WINDOW",
    "RATE_LIMIT_ADMIN_REQUESTS",
    "RATE_LIMIT_ADMIN_WINDOW",
    "RATE_LIMIT_DDOS_THRESHOLD",
    "RATE_LIMIT_DDOS_WINDOW",
    "RATE_LIMIT_BLOCK_DURATION",
    "RATE_LIMIT_FAUCET_REQUESTS",
    "RATE_LIMIT_FAUCET_WINDOW",
    "FAUCET_WALLET_FILE",
    "FAUCET_WALLET_PASSWORD",
]
