from __future__ import annotations

"""
Logging Standards and Configuration for XAI Blockchain

This module defines standardized logging levels and formats across the entire
XAI blockchain codebase. All modules should configure their loggers according
to these standards to ensure consistent, actionable logging output.

Usage:
    from xai.core.api.logging_standards import configure_module_logging

    logger = configure_module_logging(__name__, 'blockchain')
"""

import logging

# Module-level log level standards
# These define the default verbosity for each type of module
LOG_LEVELS: dict[str, str] = {
    # Core blockchain operations - INFO for tracking chain state
    "blockchain": "INFO",
    "consensus": "INFO",
    "validation": "INFO",
    "finality": "INFO",
    "checkpoints": "INFO",

    # Network operations - WARNING to reduce noise, ERROR for critical issues
    "network": "WARNING",
    "p2p": "WARNING",
    "peer_discovery": "WARNING",
    "node_connection": "WARNING",
    "eclipse_protector": "WARNING",

    # API and external interfaces - INFO for request tracking
    "api": "INFO",
    "api_routes": "INFO",
    "api_blueprints": "INFO",
    "websocket": "INFO",
    "rpc": "INFO",

    # Security - WARNING for suspicious activity, ERROR for breaches
    "security": "WARNING",
    "auth": "WARNING",
    "security_middleware": "WARNING",
    "security_validation": "WARNING",
    "encryption": "WARNING",
    "certificate_pinning": "WARNING",
    "zero_knowledge": "WARNING",
    "quantum_resistant": "WARNING",
    "hsm": "WARNING",
    "tss": "WARNING",

    # Wallet operations - WARNING to protect user privacy
    "wallet": "WARNING",
    "multisig_wallet": "WARNING",
    "hardware_wallet": "WARNING",
    "hd_wallet": "WARNING",
    "mnemonic": "WARNING",
    "offline_signing": "WARNING",

    # Virtual Machine - DEBUG for detailed execution traces
    "vm": "DEBUG",
    "evm": "DEBUG",
    "interpreter": "DEBUG",
    "executor": "DEBUG",

    # Smart contracts - INFO for deployment and execution
    "contracts": "INFO",
    "account_abstraction": "INFO",
    "erc20": "INFO",
    "erc721": "INFO",
    "erc1155": "INFO",
    "proxy": "INFO",

    # Mining operations - INFO for block production tracking
    "mining": "INFO",
    "mining_bonuses": "INFO",
    "mining_manager": "INFO",
    "proof_of_intelligence": "INFO",

    # DeFi operations - INFO for transaction tracking
    "defi": "INFO",
    "exchange": "INFO",
    "lending": "INFO",
    "staking": "INFO",
    "oracle": "INFO",
    "liquidity_mining": "INFO",
    "vesting": "INFO",

    # Governance - INFO for proposal tracking
    "governance": "INFO",
    "proposal_manager": "INFO",
    "voting": "INFO",

    # AI systems - INFO for AI operations
    "ai": "INFO",
    "ai_assistant": "INFO",
    "ai_trading": "INFO",
    "ai_safety": "INFO",
    "ai_governance": "INFO",

    # Monitoring and metrics - INFO for system health
    "monitoring": "INFO",
    "metrics": "INFO",
    "prometheus": "INFO",

    # Storage and persistence - WARNING to reduce I/O logging
    "storage": "WARNING",
    "persistence": "WARNING",
    "database": "WARNING",

    # Transaction processing - INFO for transaction lifecycle
    "transaction": "INFO",
    "transaction_validator": "INFO",
    "mempool": "INFO",
    "nonce_tracker": "INFO",

    # State management - INFO for state transitions
    "state": "INFO",
    "state_manager": "INFO",
    "utxo_manager": "INFO",

    # Recovery and error handling - WARNING for recovery attempts
    "recovery": "WARNING",
    "error_recovery": "WARNING",
    "error_detection": "WARNING",

    # CLI and user interfaces - INFO for user feedback
    "cli": "INFO",
    "explorer": "INFO",

    # Testing - DEBUG for detailed test output
    "test": "DEBUG",
    "benchmark": "DEBUG",
    "stress_test": "DEBUG",

    # Development tools - DEBUG
    "tools": "DEBUG",
    "scripts": "DEBUG",
}

# Default level for modules not in the map
DEFAULT_LOG_LEVEL = "INFO"

def get_module_category(module_name: str) -> str | None:
    """
    Determine the category for a module name.

    Args:
        module_name: Full module path (e.g., 'xai.core.blockchain')

    Returns:
        Category name or None if no match
    """
    # Handle xai.core.vm.evm.interpreter -> evm/interpreter
    parts = module_name.split('.')

    # Try exact matches first
    for part in reversed(parts):
        if part in LOG_LEVELS:
            return part

    # Try partial matches (e.g., api_routes matches api)
    for part in reversed(parts):
        for category in LOG_LEVELS.keys():
            if category in part or part in category:
                return category

    return None

def get_log_level(module_name: str, override: str | None = None) -> str:
    """
    Get the appropriate log level for a module.

    Args:
        module_name: Full module path (e.g., 'xai.core.blockchain')
        override: Optional override level (e.g., from environment variable)

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if override:
        return override.upper()

    category = get_module_category(module_name)
    if category:
        return LOG_LEVELS[category]

    return DEFAULT_LOG_LEVEL

def configure_module_logging(
    module_name: str,
    category: str | None = None,
    override_level: str | None = None,
) -> logging.Logger:
    """
    Configure and return a logger for a module with standardized settings.

    Args:
        module_name: The module's __name__ (e.g., 'xai.core.blockchain')
        category: Optional category override (e.g., 'blockchain')
        override_level: Optional level override (e.g., 'DEBUG')

    Returns:
        Configured logger instance

    Example:
        logger = configure_module_logging(__name__, 'blockchain')
    """
    logger = logging.getLogger(module_name)

    # Determine log level
    if category:
        level_str = LOG_LEVELS.get(category, DEFAULT_LOG_LEVEL)
    else:
        level_str = get_log_level(module_name, override_level)

    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    return logger

def get_all_module_categories() -> dict[str, str]:
    """
    Get a mapping of all module categories to their log levels.

    Returns:
        Dictionary mapping category name to log level
    """
    return LOG_LEVELS.copy()

def set_category_level(category: str, level: str) -> None:
    """
    Dynamically update the log level for a category.

    Args:
        category: Category name (e.g., 'blockchain')
        level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if category in LOG_LEVELS:
        LOG_LEVELS[category] = level.upper()
    else:
        raise ValueError(f"Unknown category: {category}")

# Structured logging field standards
STANDARD_FIELDS = {
    # Error context
    "error_type": "Exception class name",
    "error": "Error message string",
    "function": "Function where error occurred",
    "module": "Module where error occurred",

    # Transaction context
    "txid": "Transaction ID",
    "tx_hash": "Transaction hash",
    "from_address": "Sender address",
    "to_address": "Recipient address",
    "amount": "Transaction amount",

    # Block context
    "block_index": "Block height/index",
    "block_hash": "Block hash",
    "block_time": "Block timestamp",

    # Network context
    "peer_id": "Peer identifier",
    "peer_address": "Peer network address",
    "connection_id": "Connection identifier",

    # API context
    "endpoint": "API endpoint path",
    "method": "HTTP method",
    "status_code": "HTTP status code",
    "request_id": "Request identifier",
    "user_address": "Authenticated user address",

    # Performance context
    "duration": "Operation duration in seconds",
    "operation": "Operation name",
    "count": "Item count",
    "size": "Data size in bytes",
}

def get_standard_fields() -> dict[str, str]:
    """
    Get the standard structured logging field names and their descriptions.

    Returns:
        Dictionary mapping field name to description
    """
    return STANDARD_FIELDS.copy()
