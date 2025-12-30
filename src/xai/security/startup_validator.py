"""
XAI Security Startup Validator

Validates that no insecure debug configurations are enabled in production.
This module should be called at the start of any production node.

CRITICAL: Debug bypasses in production are a severe security vulnerability.
"""

import logging
import os
import sys
from typing import NamedTuple

logger = logging.getLogger(__name__)


class SecurityBypass(NamedTuple):
    """Represents a security bypass configuration."""
    env_var: str
    description: str
    severity: str  # "critical" or "warning"


# List of dangerous debug environment variables
DANGEROUS_BYPASSES = [
    SecurityBypass(
        env_var="XAI_P2P_DISABLE_SIGNATURE_VERIFY",
        description="Allows nodes to skip signature verification on P2P messages",
        severity="critical"
    ),
    SecurityBypass(
        env_var="XAI_P2P_DISABLE_SSL",
        description="Disables TLS/SSL encryption on P2P connections",
        severity="critical"
    ),
    SecurityBypass(
        env_var="XAI_DISABLE_TX_VALIDATION",
        description="Disables transaction validation",
        severity="critical"
    ),
    SecurityBypass(
        env_var="XAI_SKIP_BLOCK_VALIDATION",
        description="Skips block validation checks",
        severity="critical"
    ),
]

WARNING_BYPASSES = [
    SecurityBypass(
        env_var="XAI_P2P_DISABLE_SECURITY_EVENTS",
        description="Silences security event logging",
        severity="warning"
    ),
]


def is_production_mode() -> bool:
    """
    Check if the node is running in production mode.

    Production mode is determined by:
    1. XAI_PRODUCTION_MODE=1 or XAI_PRODUCTION_MODE=true
    2. XAI_NETWORK=mainnet
    3. Running in a Docker container with production image

    Returns:
        True if production mode is detected
    """
    # Explicit production mode flag
    prod_mode = os.getenv("XAI_PRODUCTION_MODE", "0").lower()
    if prod_mode in {"1", "true", "yes", "on", "production"}:
        return True

    # Network type detection
    network = os.getenv("XAI_NETWORK", "").lower()
    if network in {"mainnet", "main", "production"}:
        return True

    # Docker production detection
    if os.path.exists("/.dockerenv"):
        docker_env = os.getenv("XAI_DOCKER_ENV", "").lower()
        if docker_env in {"production", "prod", "mainnet"}:
            return True

    return False


def is_bypass_enabled(env_var: str) -> bool:
    """Check if a specific bypass environment variable is enabled."""
    value = os.getenv(env_var, "0").lower()
    return value in {"1", "true", "yes", "on"}


def validate_security_configuration(
    fail_on_critical: bool = True,
    warn_on_advisory: bool = True
) -> bool:
    """
    Validate that no dangerous security bypasses are enabled.

    In production mode, this will raise an exception and refuse to start
    if any critical bypasses are detected.

    Args:
        fail_on_critical: If True, raise exception on critical bypasses in production
        warn_on_advisory: If True, log warnings for advisory bypasses

    Returns:
        True if configuration is secure, False otherwise

    Raises:
        SecurityConfigurationError: If critical bypass detected in production
    """
    production = is_production_mode()
    is_secure = True
    critical_issues = []
    warnings = []

    # Check dangerous bypasses
    for bypass in DANGEROUS_BYPASSES:
        if is_bypass_enabled(bypass.env_var):
            msg = f"CRITICAL: {bypass.env_var} is enabled - {bypass.description}"
            critical_issues.append(msg)
            logger.critical(msg)
            is_secure = False

    # Check warning bypasses
    for bypass in WARNING_BYPASSES:
        if is_bypass_enabled(bypass.env_var):
            msg = f"WARNING: {bypass.env_var} is enabled - {bypass.description}"
            warnings.append(msg)
            if warn_on_advisory:
                logger.warning(msg)

    # In production, fail on critical issues
    if production and critical_issues and fail_on_critical:
        error_msg = (
            "SECURITY ERROR: Cannot start node in production mode with "
            f"security bypasses enabled:\n" + "\n".join(critical_issues)
        )
        logger.critical(error_msg)
        raise SecurityConfigurationError(error_msg)

    # Log summary
    if is_secure:
        logger.info("Security configuration validated: no dangerous bypasses detected")
    else:
        if not production:
            logger.warning(
                "Security bypasses detected in non-production mode. "
                "This would fail in production."
            )

    return is_secure


class SecurityConfigurationError(Exception):
    """Raised when insecure configuration is detected in production."""
    pass


def enforce_production_security() -> None:
    """
    Enforce security requirements for production deployments.

    This should be called at the very start of node initialization.
    Will exit with error code 1 if security requirements are not met.
    """
    try:
        validate_security_configuration(fail_on_critical=True, warn_on_advisory=True)
    except SecurityConfigurationError as e:
        print(f"\n{'='*60}", file=sys.stderr)
        print("SECURITY ERROR: NODE STARTUP BLOCKED", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print(f"\nTo fix: Remove the dangerous environment variables.", file=sys.stderr)
        print("If this is development, set XAI_PRODUCTION_MODE=0", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        sys.exit(1)


def get_security_status() -> dict:
    """
    Get current security configuration status.

    Returns:
        Dictionary with security status information
    """
    production = is_production_mode()
    critical_enabled = []
    warnings_enabled = []

    for bypass in DANGEROUS_BYPASSES:
        if is_bypass_enabled(bypass.env_var):
            critical_enabled.append(bypass.env_var)

    for bypass in WARNING_BYPASSES:
        if is_bypass_enabled(bypass.env_var):
            warnings_enabled.append(bypass.env_var)

    return {
        "production_mode": production,
        "is_secure": len(critical_enabled) == 0,
        "critical_bypasses_enabled": critical_enabled,
        "warning_bypasses_enabled": warnings_enabled,
        "total_bypasses": len(critical_enabled) + len(warnings_enabled),
    }
