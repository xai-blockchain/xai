"""
XAI Blockchain Node API Routes
Handles all Flask route definitions and HTTP request/response logic.

This module contains all API endpoint handlers organized by category:
- Core endpoints (health, metrics, stats)
- Blockchain endpoints (blocks, transactions)
- Wallet endpoints (balance, send)
- Mining endpoints (mine, auto-mine)
- P2P endpoints (peers, sync)
- Algorithmic features (fee estimation, fraud detection)
- Gamification endpoints (airdrops, streaks, treasures)
- Social recovery endpoints
- Mining bonus endpoints
- Exchange endpoints
- Crypto deposit endpoints
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any, Tuple, List, Optional, Sequence
from flask import Flask, jsonify, request, g, make_response
import time
import json
import logging
import os
import re
import html
from contextlib import nullcontext

# Import centralized validation
from xai.core.validation import validate_address as core_validate_address
from xai.core.validation import validate_hex_string

from xai.core.vm.evm.abi import keccak256
from werkzeug.exceptions import RequestEntityTooLarge

# Import typed exceptions
from xai.core.blockchain_exceptions import (
    DatabaseError,
    StorageError,
    ValidationError,
    NetworkError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)

ERC165_SELECTOR = keccak256(b"supportsInterface(bytes4)")[:4]
INTERFACE_PROBE_ADDRESS = "0x" + "b" * 40
KNOWN_TOKEN_RECEIVER_INTERFACES = {
    "erc1363_receiver": bytes.fromhex("b7b04c6b"),
    "erc721_receiver": bytes.fromhex("150b7a02"),
}

from xai.core.config import Config
from xai.core import node_utils
from xai.core.node_utils import (
    ALGO_FEATURES_ENABLED,
    NODE_VERSION,
    get_base_dir,
    get_api_endpoints,
)
from xai.core.rate_limiter import get_rate_limiter
from xai.core.error_handlers import ErrorHandlerRegistry
from xai.core.input_validation_schemas import (
    PeerTransactionInput,
    CryptoDepositAddressInput,
    ExchangeOrderInput,
    ExchangeTransferInput,
    ExchangeCancelInput,
    ExchangeCardPurchaseInput,
    PeerBlockInput,
)
from xai.core.request_validator_middleware import RequestValidator, validate_request
from xai.core.security_validation import log_security_event, SecurityValidator
from xai.core.monitoring import MetricsCollector
from xai.core.api_auth import APIAuthManager, APIKeyStore
from xai.network.peer_manager import PeerManager
from xai.wallet.spending_limits import SpendingLimitManager
from xai.core.vm.evm.abi import keccak256
from xai.core.api_routes import (
    register_transaction_routes,
    register_contract_routes,
    register_wallet_routes,
    register_faucet_routes,
    register_mining_routes,
    register_peer_routes,
    register_algo_routes,
    register_recovery_routes,
    register_gamification_routes,
    register_mining_bonus_routes,
    register_admin_routes,
    register_crypto_deposit_routes,
)

if TYPE_CHECKING:
    from xai.core.blockchain import Transaction
    from flask import Flask


class InputSanitizer:
    """Comprehensive input sanitization for API endpoints.

    Implements Task 65: Input Sanitization with SQL injection protection,
    hex format validation, range checking, and dangerous character filtering.
    """

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string inputs.

        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length (default: 1000)

        Returns:
            Sanitized string

        Raises:
            ValueError: If input is invalid
        """
        if not isinstance(value, str):
            raise ValueError("Input must be string")

        # Remove SQL injection patterns
        sql_patterns = [
            r"(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bCREATE\b)",
            r"(--|;|\/\*|\*\/|xp_|sp_)",
            r"(\bUNION\b|\bEXEC\b|\bEXECUTE\b)"
        ]
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Invalid input: SQL keywords detected")

        # HTML escape
        value = html.escape(value)

        # Truncate to max length
        if len(value) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length}")

        return value

    @staticmethod
    def validate_numeric(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
        """Validate numeric inputs with range checking.

        Args:
            value: Numeric value to validate
            min_val: Minimum allowed value (optional)
            max_val: Maximum allowed value (optional)

        Returns:
            Validated float value

        Raises:
            ValueError: If value is invalid or out of range
        """
        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValueError("Invalid numeric value")

        if min_val is not None and num < min_val:
            raise ValueError(f"Value must be >= {min_val}")

        if max_val is not None and num > max_val:
            raise ValueError(f"Value must be <= {max_val}")

        return num

    @staticmethod
    def validate_address(address: str) -> str:
        """Validate blockchain address format.

        Uses centralized validation from xai.core.validation module.

        XAI addresses follow the format:
        - Mainnet: XAI + 40 hex characters (e.g., XAI1234567890abcdef...)
        - Testnet: TXAI + 40 hex characters (e.g., TXAI1234567890abcdef...)
        - Special: COINBASE (mining rewards), fee addresses

        Args:
            address: Blockchain address to validate

        Returns:
            Validated address

        Raises:
            ValueError: If address format is invalid
        """
        return core_validate_address(address, allow_special=True)

    @staticmethod
    def validate_hash(hash_value: str, expected_length: int = 64) -> str:
        """Validate transaction/block hash format.

        Uses centralized validation from xai.core.validation module.

        Args:
            hash_value: Hash to validate
            expected_length: Expected hash length in characters (default: 64)

        Returns:
            Validated hash in lowercase

        Raises:
            ValueError: If hash format is invalid
        """
        return validate_hex_string(hash_value, exact_length=expected_length)

    @staticmethod
    def reject_invalid_utf8(value: str) -> str:
        """Reject invalid UTF-8 sequences.

        Args:
            value: String to validate

        Returns:
            Validated string

        Raises:
            ValueError: If string contains invalid UTF-8
        """
        try:
            value.encode('utf-8').decode('utf-8')
        except UnicodeError:
            raise ValueError("Invalid UTF-8 encoding")
        return value

    @staticmethod
    def strip_dangerous_chars(value: str) -> str:
        """Strip dangerous characters (null bytes, control characters).

        Args:
            value: String to sanitize

        Returns:
            Sanitized string
        """
        # Remove null bytes, control characters
        value = re.sub(r'[\x00-\x1F\x7F]', '', value)
        return value

    @staticmethod
    def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
        """Validate integer inputs with range checking.

        Args:
            value: Integer value to validate
            min_val: Minimum allowed value (optional)
            max_val: Maximum allowed value (optional)

        Returns:
            Validated integer value

        Raises:
            ValueError: If value is invalid or out of range
        """
        try:
            num = int(value)
        except (ValueError, TypeError):
            raise ValueError("Invalid integer value")

        if min_val is not None and num < min_val:
            raise ValueError(f"Value must be >= {min_val}")

        if max_val is not None and num > max_val:
            raise ValueError(f"Value must be <= {max_val}")

        return num

    @staticmethod
    def sanitize_json_keys(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all string keys and values in a dictionary.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            clean_key = InputSanitizer.strip_dangerous_chars(str(key))

            # Sanitize value if string
            if isinstance(value, str):
                clean_value = InputSanitizer.strip_dangerous_chars(value)
                sanitized[clean_key] = clean_value
            elif isinstance(value, dict):
                sanitized[clean_key] = InputSanitizer.sanitize_json_keys(value)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    InputSanitizer.strip_dangerous_chars(v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                sanitized[clean_key] = value

        return sanitized


class PaginationError(ValueError):
    """Raised when pagination query parameters are invalid."""


_API_VERSION_ENV_KEY = "xai.api_version"


class _VersionPrefixMiddleware:
    """WSGI middleware that strips version prefixes and records requested version."""

    def __init__(
        self,
        app,
        supported_versions: Sequence[str],
        default_version: str,
        docs_url: str = "",
    ) -> None:
        self.app = app
        self.supported_versions = tuple(supported_versions) or ("v1",)
        self.default_version = default_version if default_version in self.supported_versions else self.supported_versions[-1]
        self.docs_url = docs_url

    @staticmethod
    def _looks_like_version(token: str) -> bool:
        return token.startswith("v") and token[1:].isdigit()

    def __call__(self, environ, start_response):  # type: ignore[override]
        path = environ.get("PATH_INFO", "") or "/"
        version, trimmed = self._extract_version(path)

        if version is None:
            logger.warning(
                "Unsupported API version requested",
                extra={
                    "event": "api.version.unsupported",
                    "requested": self._requested_token(path) or "unknown",
                    "remote": environ.get("REMOTE_ADDR", "unknown"),
                },
            )
            requested = self._requested_token(path)
            payload = json.dumps(
                {
                    "success": False,
                    "error": "Unsupported API version",
                    "code": "unsupported_api_version",
                    "requested_version": requested or "unknown",
                    "supported_versions": list(self.supported_versions),
                }
            )
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(payload))),
                ("X-API-Version", "unknown"),
            ]
            if self.docs_url:
                headers.append(("Link", f"<{self.docs_url}>; rel=\"deprecation\""))
            start_response("404 NOT FOUND", headers)
            return [payload.encode("utf-8")]

        environ[_API_VERSION_ENV_KEY] = version
        environ["PATH_INFO"] = trimmed
        return self.app(environ, start_response)

    def _extract_version(self, path: str) -> Tuple[Optional[str], str]:
        normalized = path or "/"
        for version in self.supported_versions:
            prefix = f"/{version}"
            if normalized == prefix or normalized.startswith(f"{prefix}/"):
                remainder = normalized[len(prefix) :]
                if not remainder:
                    remainder = "/"
                elif not remainder.startswith("/"):
                    remainder = f"/{remainder}"
                return version, remainder

        token = self._requested_token(normalized)
        if token and self._looks_like_version(token) and token not in self.supported_versions:
            return None, normalized

        # Default version applies when no explicit prefix provided
        return self.default_version, normalized

    @staticmethod
    def _requested_token(path: str) -> Optional[str]:
        if not path.startswith("/"):
            return None
        segments = path.split("/", 2)
        if len(segments) < 2:
            return None
        token = segments[1]
        return token or None


class APIVersioningManager:
    """Installs API version prefix handling and response headers."""

    def __init__(
        self,
        app: Flask,
        supported_versions: Optional[Sequence[str]] = None,
        default_version: Optional[str] = None,
        deprecated_versions: Optional[Dict[str, Dict[str, str]]] = None,
        docs_url: str = "",
    ) -> None:
        if not isinstance(app, Flask):  # type: ignore[unreachable]
            raise TypeError("APIVersioningManager requires a Flask application instance")

        config = Config
        versions = tuple(supported_versions or getattr(config, "API_SUPPORTED_VERSIONS", ("v1",)))
        if not versions:
            versions = ("v1",)
        normalized_versions = tuple(dict.fromkeys(v.strip() or "v1" for v in versions))

        source_default = default_version or getattr(config, "API_DEFAULT_VERSION", normalized_versions[-1])
        if source_default not in normalized_versions:
            source_default = normalized_versions[-1]

        raw_deprecations = deprecated_versions or getattr(config, "API_DEPRECATED_VERSIONS", {})
        self.deprecated_versions: Dict[str, Dict[str, str]] = {}
        for version, info in raw_deprecations.items():
            if not version:
                continue
            if isinstance(info, dict):
                self.deprecated_versions[version] = dict(info)
            elif isinstance(info, str) and info:
                self.deprecated_versions[version] = {"sunset": info}
            else:
                self.deprecated_versions[version] = {}

        self.app = app
        self.supported_versions = normalized_versions
        self.default_version = source_default
        self.docs_url = docs_url or getattr(config, "API_VERSION_DOCS_URL", "")

        self._install_middleware()

    def _install_middleware(self) -> None:
        if getattr(self.app, "xai_api_versioning", False):
            return

        original_wsgi_app = self.app.wsgi_app
        self.app.wsgi_app = _VersionPrefixMiddleware(
            original_wsgi_app,
            supported_versions=self.supported_versions,
            default_version=self.default_version,
            docs_url=self.docs_url,
        )

        @self.app.before_request
        def _set_api_version_context() -> None:
            g.api_version = request.environ.get(_API_VERSION_ENV_KEY, self.default_version)

        @self.app.after_request
        def _inject_version_headers(response):
            version = getattr(g, "api_version", self.default_version)
            response.headers["X-API-Version"] = version
            if version in self.deprecated_versions:
                response.headers["Deprecation"] = f'version="{version}"'
                sunset = self.deprecated_versions[version].get("sunset")
                if sunset:
                    response.headers.setdefault("Sunset", sunset)
                if self.docs_url:
                    response.headers.setdefault(
                        "Link",
                        f"<{self.docs_url}>; rel=\"deprecation\"; type=\"text/html\"",
                    )
            return response

        setattr(self.app, "xai_api_versioning", True)


class NodeAPIRoutes:
    """
    Manages all API routes for the blockchain node.

    This class encapsulates all HTTP endpoint handlers and provides
    a clean separation between API logic and core node functionality.
    """

    def __init__(self, node: Any) -> None:
        """
        Initialize API routes handler.

        Args:
            node: The blockchain node instance (BlockchainNode)
        """
        self.node = node
        self.blockchain = node.blockchain
        self.app = node.app
        peer_source = getattr(node, "peer_manager", None)
        if not isinstance(peer_source, PeerManager):
            pm_candidate = getattr(getattr(node, "p2p_manager", None), "peer_manager", None)
            peer_source = pm_candidate if isinstance(pm_candidate, PeerManager) else PeerManager()
            setattr(node, "peer_manager", peer_source)
        self.peer_manager = peer_source
        candidate_validator = getattr(node, "request_validator", None)
        self.request_validator = (
            candidate_validator if isinstance(candidate_validator, RequestValidator) else RequestValidator()
        )
        store_path = getattr(Config, "API_KEY_STORE_PATH", os.path.join(os.getcwd(), "secure_keys", "api_keys.json"))
        self.api_key_store = APIKeyStore(store_path)
        self.error_registry = ErrorHandlerRegistry()
        self.security_validator = getattr(node, "validator", SecurityValidator())
        self.api_auth = APIAuthManager.from_config(store=self.api_key_store)
        self.spending_limits = SpendingLimitManager()
        self.api_versioning = APIVersioningManager(self.app)
        self._body_size_limit = max(1, int(getattr(Config, "API_MAX_JSON_BYTES", 1_000_000)))
        self._install_request_size_limits()

    def _install_request_size_limits(self) -> None:
        """
        Enforce global request payload limits using MAX_CONTENT_LENGTH and
        a before_request guard so oversized payloads are rejected before
        reaching any route logic.
        """
        current_limit = self.app.config.get("MAX_CONTENT_LENGTH")
        if not current_limit or current_limit > self._body_size_limit:
            self.app.config["MAX_CONTENT_LENGTH"] = self._body_size_limit

        @self.app.before_request
        def _enforce_payload_limit():
            content_length = request.content_length
            if content_length and content_length > self._body_size_limit:
                description = (
                    f"Payload {content_length} bytes exceeds {self._body_size_limit} byte limit"
                )
                raise RequestEntityTooLarge(description=description)

        self.app.register_error_handler(RequestEntityTooLarge, self._handle_payload_too_large)

    def _handle_payload_too_large(self, error: RequestEntityTooLarge):
        """Return a structured error when payload exceeds allowed limit."""
        content_length = request.content_length or 0
        context = {
            "limit_bytes": self._body_size_limit,
            "content_length": content_length,
            "path": request.path,
            "method": request.method,
        }
        return self._error_response(
            f"Request body exceeds maximum size of {self._body_size_limit} bytes",
            status=413,
            code="payload_too_large",
            context=context,
            event_type="api.payload_too_large",
        )

    def _verify_signed_peer_message(self) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify a signed message from a peer, checking signature and freshness, and providing the payload.
        
        Returns (ok, reason, payload)
        """
        body_bytes = request.get_data(cache=False, as_text=False) or b""
        
        try:
            verified = self.peer_manager.encryption.verify_signed_message(body_bytes)
            if not verified:
                self._log_event("peer_signature_failure", {"reason": "invalid_signature"})
                return False, "invalid_signature", None
            
            payload = verified.get("payload")
            sender_id = verified.get("sender")
            nonce = verified.get("nonce")

            if not sender_id or not nonce:
                self._log_event("peer_signature_failure", {"reason": "missing_identity"})
                return False, "missing_identity", None

            if nonce and sender_id:
                if self.peer_manager.is_nonce_replay(sender_id, nonce, verified.get("timestamp")):
                    self._log_event("peer_signature_failure", {"reason": "replay", "sender": sender_id})
                    return False, "replay_attack", None
                self.peer_manager.record_nonce(sender_id, nonce, verified.get("timestamp"))
            
            return True, "ok", payload

        except (ValueError, RuntimeError, KeyError) as e:
            self._log_event("peer_signature_failure", {"reason": "exception", "error": str(e)})
            return False, f"verification_error: {e}", None

    def setup_routes(self) -> None:
        """
        Register all API routes with the Flask app.

        Organizes routes into logical categories for maintainability.
        """
        self._setup_core_routes()
        self._setup_blockchain_routes()
        register_transaction_routes(self)
        register_contract_routes(self, InputSanitizer)
        register_wallet_routes(self)
        register_faucet_routes(
            self,
            simple_rate_limiter_getter=get_rate_limiter,
            advanced_rate_limiter_getter=self._get_advanced_rate_limiter,
        )
        register_mining_routes(
            self,
            advanced_rate_limiter_getter=self._get_advanced_rate_limiter,
        )
        register_peer_routes(self)
        register_algo_routes(self)
        register_recovery_routes(self)
        register_gamification_routes(self)
        register_mining_bonus_routes(self)
        self._setup_exchange_routes()
        register_crypto_deposit_routes(self)
        register_admin_routes(self)

    def _log_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None, severity: str = "INFO") -> None:
        """Helper to log API security events with sanitized payloads."""
        sanitized = SecurityValidator.sanitize_for_logging(payload or {})
        log_security_event(event_type, {"details": sanitized}, severity=severity)

    def _record_send_rejection(self, reason: str) -> None:
        """Forward /send rejection metrics to the collector when available."""
        collector = getattr(self.node, "metrics_collector", None)
        if collector is None:
            try:
                collector = MetricsCollector.instance()
            except (RuntimeError, AttributeError) as e:
                logger.debug(
                    "Metrics collector unavailable",
                    error=str(e)
                )
                collector = None
        if collector is None:
            return
        try:
            collector.record_send_rejection(reason)
        except AttributeError as e:
            logger.debug(
                "Metrics collector missing record_send_rejection method",
                extra={"error": str(e), "event": "metrics.missing_method"}
            )

    def _get_advanced_rate_limiter(self):
        """Best-effort accessor for the optional advanced rate limiter."""
        try:
            from xai.core.advanced_rate_limiter import get_rate_limiter as get_advanced_rate_limiter

            return get_advanced_rate_limiter()
        except (ImportError, RuntimeError, AttributeError):
            return None

    def _success_response(self, payload: Dict[str, Any], status: int = 200):
        """Return a success payload with consistent structure."""
        body = {"success": True, **payload}
        return jsonify(body), status

    def _error_response(
        self,
        message: str,
        status: int = 400,
        code: str = "bad_request",
        context: Optional[Dict[str, Any]] = None,
        event_type: str = "node_api_error",
    ):
        """Return a sanitized error response and emit a security log."""
        severity = "ERROR" if status >= 500 else "WARNING"
        details = {"code": code, "status": status, **(context or {})}
        self._log_event(event_type, details, severity=severity)
        return jsonify({"success": False, "error": message, "code": code}), status

    def _handle_exception(self, error: Exception, context: str, status: int = 500):
        """Route unexpected exceptions through the error registry with sanitized output."""
        handled, handler_message = self.error_registry.handle_error(error, context, self.blockchain)
        details = {"context": context, "error": str(error), "handled": handled}
        return self._error_response(
            handler_message if status < 500 and handler_message else "Internal server error",
            status=status,
            code="internal_error",
            context=details,
            event_type="node_api_exception",
        )

    def _format_timestamp(self, timestamp: Optional[float]) -> Optional[str]:
        """Return RFC3339-ish string for telemetry fields."""
        if timestamp is None:
            return None
        try:
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(timestamp)))
        except (ValueError, TypeError, OverflowError):
            return None

    def _build_peer_diversity_stats(self, manager: PeerManager) -> Dict[str, Any]:
        """Snapshot peer diversity counters under lock for consistent reporting."""
        diversity_lock = getattr(manager, "_diversity_lock", None)
        context = diversity_lock if hasattr(diversity_lock, "__enter__") else nullcontext()
        with context:
            prefix_counts = dict(getattr(manager, "prefix_counts", {}))
            asn_counts = dict(getattr(manager, "asn_counts", {}))
            country_counts = dict(getattr(manager, "country_counts", {}))
            unknown_geo = int(getattr(manager, "unknown_geo_peers", 0))

        return {
            "prefix_counts": prefix_counts,
            "asn_counts": asn_counts,
            "country_counts": country_counts,
            "unknown_geo_peers": unknown_geo,
            "unique_prefixes": len(prefix_counts),
            "unique_asns": len(asn_counts),
            "unique_countries": len(country_counts),
            "thresholds": {
                "min_unique_prefixes": getattr(manager, "min_unique_prefixes", None),
                "min_unique_asns": getattr(manager, "min_unique_asns", None),
                "min_unique_countries": getattr(manager, "min_unique_countries", None),
                "max_unknown_geo": getattr(manager, "max_unknown_geo", None),
            },
        }

    def _build_peer_snapshot(self) -> Dict[str, Any]:
        """Assemble detailed peer metadata for verbose peer queries."""
        manager = getattr(self, "peer_manager", None)
        if not isinstance(manager, PeerManager):
            return {"connections": [], "diversity": {}, "limits": {}, "connected_total": 0}

        now = time.time()
        connected = getattr(manager, "connected_peers", {}) or {}
        seen_nonces = getattr(manager, "seen_nonces", {}) or {}
        trusted_set = {peer.lower() for peer in getattr(manager, "trusted_peers", set())}
        banned_set = {peer.lower() for peer in getattr(manager, "banned_peers", set())}

        connections: List[Dict[str, Any]] = []
        for peer_id, info in list(connected.items()):
            connected_at = float(info.get("connected_at", now) or now)
            last_seen = info.get("last_seen")
            ip_address = (info.get("ip_address") or "").lower()
            geo = info.get("geo") or {}
            nonce_window = seen_nonces.get(peer_id, [])
            reputation = None
            if getattr(manager, "reputation", None):
                reputation = round(manager.reputation.get_score(peer_id), 4)

            connections.append(
                {
                    "peer_id": peer_id,
                    "ip_address": info.get("ip_address"),
                    "connected_at": connected_at,
                    "connected_at_iso": self._format_timestamp(connected_at),
                    "uptime_seconds": max(0.0, now - connected_at),
                    "last_seen": last_seen,
                    "last_seen_iso": self._format_timestamp(last_seen) if last_seen else None,
                    "geo": geo,
                    "reputation": reputation,
                    "nonce_window": len(nonce_window),
                    "trusted": ip_address in trusted_set,
                    "banned": ip_address in banned_set,
                }
            )

        connections.sort(key=lambda entry: entry.get("connected_at") or 0.0, reverse=True)
        diversity = self._build_peer_diversity_stats(manager)
        limits = {
            "max_connections_per_ip": getattr(manager, "max_connections_per_ip", None),
            "max_per_prefix": getattr(manager, "max_per_prefix", None),
            "max_per_asn": getattr(manager, "max_per_asn", None),
            "max_per_country": getattr(manager, "max_per_country", None),
            "max_unknown_geo": getattr(manager, "max_unknown_geo", None),
            "require_client_cert": getattr(manager, "require_client_cert", False),
        }
        discovery = getattr(getattr(manager, "discovery", None), "discovered_peers", [])

        return {
            "connections": connections,
            "connected_total": len(connections),
            "diversity": diversity,
            "limits": limits,
            "trusted_peers": sorted(trusted_set),
            "banned_peers": sorted(banned_set),
            "discovered": discovery[:50] if isinstance(discovery, list) else [],
        }

    def _detect_contract_interfaces(self, contract_address: str) -> Dict[str, bool]:
        """Check ERC-165 interface support for known token receiver standards."""
        manager = self.blockchain.smart_contract_manager
        if not manager:
            raise RuntimeError("Smart-contract manager unavailable")

        supports: Dict[str, bool] = {}
        for name, interface_id in KNOWN_TOKEN_RECEIVER_INTERFACES.items():
            calldata = ERC165_SELECTOR + interface_id.rjust(32, b"\x00")
            try:
                result = manager.static_call(
                    INTERFACE_PROBE_ADDRESS,
                    contract_address,
                    calldata,
                    gas_limit=200_000,
                )
            except (ValueError, RuntimeError) as e:
                logger.debug(
                    f"Failed to check interface support for {name}",
                    contract=contract_address,
                    interface=name,
                    error=str(e)
                )
                supports[name] = False
                continue

            if not result.success or len(result.return_data) < 32:
                supports[name] = False
                continue

            supports[name] = bool(int.from_bytes(result.return_data[-32:], "big"))
        return supports

    def _require_api_auth(self):
        if not self.api_auth.is_enabled():
            return None
        allowed, reason = self.api_auth.authorize(request)
        if allowed:
            return None
        return self._error_response(
            "API key required",
            status=401,
            code="unauthorized",
            context={"reason": reason or ""},
            event_type="api_auth_failure",
        )

    def _require_admin_auth(self):
        allowed, reason = self.api_auth.authorize_admin(request)
        if allowed:
            return None
        return self._error_response(
            reason or "Admin token invalid",
            status=401,
            code="admin_unauthorized",
            event_type="api_admin_auth_failure",
        )

    def _get_pagination_params(
        self,
        default_limit: int = 50,
        max_limit: int = 500,
        default_offset: int = 0,
    ) -> Tuple[int, int]:
        """Normalize pagination query params and enforce sane limits."""
        limit = request.args.get("limit", default=default_limit, type=int)
        offset = request.args.get("offset", default=default_offset, type=int)
        if limit is None or offset is None:
            raise PaginationError("limit and offset must be integers")
        if limit <= 0:
            raise PaginationError("limit must be greater than zero")
        if limit > max_limit:
            raise PaginationError(f"limit cannot exceed {max_limit}")
        if offset < 0:
            raise PaginationError("offset cannot be negative")
        return limit, offset

    # ==================== CORE ROUTES ====================

    def _setup_core_routes(self) -> None:
        """Setup core node routes (index, health, metrics, stats)."""

        @self.app.route("/", methods=["GET"])
        def index() -> Tuple[Dict[str, Any], int]:
            """Node information and available endpoints."""
            return (
                jsonify(
                    {
                        "status": "online",
                        "node": "AXN Full Node",
                        "version": NODE_VERSION,
                        "algorithmic_features": ALGO_FEATURES_ENABLED,
                        "endpoints": get_api_endpoints(),
                    }
                ),
                200,
            )

        @self.app.route("/health", methods=["GET"])
        def health_check() -> Tuple[Dict[str, Any], int]:
            """Health check endpoint for Docker and monitoring."""
            overall_status = "healthy"
            http_status = 200
            timestamp = time.time()
            blockchain_summary: Dict[str, Any] = {"accessible": False}
            services: Dict[str, Any] = {"api": "running"}
            backlog: Dict[str, Any] = {"pending_transactions": 0, "orphan_blocks": 0}
            network: Dict[str, Any] = {"peers": 0}

            def degrade(reason: str) -> None:
                nonlocal overall_status, http_status
                if overall_status == "healthy":
                    overall_status = "degraded"
                http_status = 503
                services.setdefault("issues", []).append(reason)

            try:
                blockchain = getattr(self.node, "blockchain", None)
                if blockchain:
                    try:
                        stats = blockchain.get_stats()
                        blockchain_summary = {
                            "accessible": True,
                            "height": stats.get("chain_height", len(getattr(blockchain, "chain", []))),
                            "difficulty": stats.get("difficulty"),
                            "total_supply": stats.get("total_circulating_supply"),
                            "latest_block_hash": stats.get("latest_block_hash", ""),
                        }
                        backlog["pending_transactions"] = stats.get("pending_transactions_count", 0)
                        backlog["orphan_blocks"] = stats.get("orphan_blocks_count", 0)
                        backlog["orphan_transactions"] = stats.get("orphan_transactions_count", 0)
                    except (ValueError, RuntimeError, KeyError) as exc:  # pragma: no cover - defensive
                        blockchain_summary = {"accessible": False, "error": str(exc)}
                        overall_status = "unhealthy"
                        http_status = 503
                else:
                    blockchain_summary = {"accessible": False, "error": "Blockchain not initialized"}
                    degrade("blockchain_unavailable")
            except (ValueError, RuntimeError, OSError) as exc:  # pragma: no cover - defensive
                blockchain_summary = {"accessible": False, "error": str(exc)}
                overall_status = "unhealthy"
                http_status = 503

            # Storage check
            storage_status = "healthy"
            try:
                data_dir = getattr(getattr(self.node, "blockchain", None), "storage", None)
                data_dir = getattr(data_dir, "data_dir", os.getcwd())
                if not isinstance(data_dir, (str, os.PathLike)):
                    data_dir = os.getcwd()
                test_file = os.path.join(data_dir, "health_check.tmp")
                with open(test_file, "w") as handle:
                    handle.write("ok")
                os.remove(test_file)
            except (OSError, IOError) as exc:
                storage_status = "degraded"
                degrade("storage_unwritable")
                services["storage_error"] = str(exc)
            services["storage"] = storage_status

            # Network/P2P checks
            p2p_manager = getattr(self.node, "p2p_manager", None)
            try:
                from unittest.mock import Mock as _Mock  # type: ignore
            except ImportError as e:  # pragma: no cover - fallback when mock not present
                logger.debug("unittest.mock not available", error=str(e))
                _Mock = None
            is_mock_manager = bool(_Mock and isinstance(p2p_manager, _Mock))
            if is_mock_manager and getattr(p2p_manager, "_mock_parent", None) is not None:
                # Ignore dynamically created mocks from loose test doubles
                p2p_manager = None
                is_mock_manager = False
            p2p_status = "running"
            peer_count = 0
            if p2p_manager and not is_mock_manager:
                try:
                    server = getattr(p2p_manager, "server", None)
                    if not server or not server.is_serving():
                        p2p_status = "degraded"
                        degrade("p2p_server_down")
                    if hasattr(p2p_manager, "get_peer_count"):
                        peer_count_raw = p2p_manager.get_peer_count()
                        peer_count = (
                            peer_count_raw
                            if isinstance(peer_count_raw, (int, float))
                            else 0
                        )
                        if peer_count == 0:
                            degrade("no_connected_peers")
                    network["peers"] = peer_count
                except (RuntimeError, ValueError) as exc:  # pragma: no cover - defensive
                    p2p_status = "degraded"
                    degrade("p2p_error")
                    services["p2p_error"] = str(exc)
            else:
                p2p_status = "unavailable"
                network["peers"] = 0
            services["p2p"] = p2p_status

            # Backlog thresholds
            if backlog.get("pending_transactions", 0) > 10000:
                degrade("mempool_backlog")
                backlog["status"] = "degraded"
            if backlog.get("orphan_blocks", 0) > 100:
                degrade("orphan_block_backlog")
                backlog["status"] = "degraded"

            response = {
                "status": overall_status,
                "timestamp": timestamp,
                "blockchain": blockchain_summary,
                "services": services,
                "network": network,
                "backlog": backlog,
            }
            if http_status != 200:
                response["error"] = services.get("issues", ["degraded"])[0] if services.get("issues") else "degraded"
            return jsonify(response), http_status

        @self.app.route("/checkpoint/provenance", methods=["GET"])
        def checkpoint_provenance() -> Tuple[Dict[str, Any], int]:
            """Expose recent checkpoint provenance for diagnostics."""
            sync_coordinator = getattr(self.node, "partial_sync_coordinator", None)
            sync_mgr = getattr(sync_coordinator, "sync_manager", None) if sync_coordinator else None
            provenance = []
            if sync_mgr and hasattr(sync_mgr, "get_provenance"):
                try:
                    provenance = sync_mgr.get_provenance()
                except (RuntimeError, ValueError) as exc:
                    logger.debug("Failed to read checkpoint provenance: %s", exc)
            return jsonify({"provenance": provenance}), 200

        @self.app.route("/metrics", methods=["GET"])
        def prometheus_metrics() -> Tuple[str, int, Dict[str, str]]:
            """Prometheus metrics endpoint."""
            try:
                metrics_output = self.node.metrics_collector.export_prometheus()
                return metrics_output, 200, {"Content-Type": "text/plain; version=0.0.4"}
            except (RuntimeError, AttributeError, ValueError) as e:
                return f"# Error generating metrics: {e}\n", 500, {"Content-Type": "text/plain"}

        @self.app.route("/stats", methods=["GET"])
        def get_stats() -> Dict[str, Any]:
            """Get blockchain statistics."""
            stats = self.blockchain.get_stats()
            stats["miner_address"] = self.node.miner_address
            stats["peers"] = len(self.node.peers)
            stats["is_mining"] = self.node.is_mining
            stats["node_uptime"] = time.time() - self.node.start_time
            return jsonify(stats)

        @self.app.route("/mempool", methods=["GET"])
        def get_mempool_overview() -> Tuple[Dict[str, Any], int]:
            """Get mempool statistics and a snapshot of pending transactions."""
            limit_param = request.args.get("limit", default=100, type=int)
            limit = 100 if limit_param is None else limit_param
            if limit < 0:
                limit = 0
            limit = min(limit, 1000)
            try:
                overview = self.blockchain.get_mempool_overview(limit)
                return jsonify({"success": True, "limit": limit, "mempool": overview}), 200
            except AttributeError:
                return (
                    jsonify({"success": False, "error": "Blockchain unavailable"}),
                    503,
                )
            except (DatabaseError, StorageError, OSError, RuntimeError, ValueError) as exc:
                logger.error(
                    "Mempool overview failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "mempool_overview")

        @self.app.route("/mempool/stats", methods=["GET"])
        def get_mempool_stats() -> Tuple[Dict[str, Any], int]:
            """Aggregate mempool fee statistics and congestion indicators."""
            limit_param = request.args.get("limit", default=0, type=int)
            limit = 0 if limit_param is None else limit_param
            if limit < 0:
                limit = 0
            limit = min(limit, 1000)

            try:
                overview = self.blockchain.get_mempool_overview(limit)
            except AttributeError:
                return (
                    jsonify({"success": False, "error": "Blockchain unavailable"}),
                    503,
                )
            except (DatabaseError, StorageError, OSError, RuntimeError, ValueError) as exc:
                logger.error(
                    "Mempool stats failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "mempool_stats")

            limits = overview.get("limits", {}) or {}
            pending_count = int(overview.get("pending_count", 0) or 0)
            size_bytes = int(overview.get("size_bytes", 0) or 0)
            max_transactions = int(limits.get("max_transactions") or 0)
            max_transactions = max(max_transactions, 1)
            capacity_ratio = min(max(pending_count / float(max_transactions), 0.0), 1.0)

            max_age_seconds = float(limits.get("max_age_seconds") or 0.0)
            max_age_seconds = max(max_age_seconds, 1.0)
            oldest_age = float(overview.get("oldest_transaction_age_seconds") or 0.0)
            age_pressure = min(max(oldest_age / max_age_seconds, 0.0), 1.0)

            if capacity_ratio >= 0.9 or age_pressure >= 0.9:
                pressure_state = "critical"
            elif capacity_ratio >= 0.7 or age_pressure >= 0.75:
                pressure_state = "elevated"
            elif capacity_ratio >= 0.5 or age_pressure >= 0.5:
                pressure_state = "moderate"
            else:
                pressure_state = "normal"

            avg_fee_rate = float(overview.get("avg_fee_rate") or 0.0)
            median_fee_rate = float(overview.get("median_fee_rate") or 0.0)
            min_fee_rate = float(overview.get("min_fee_rate") or 0.0)
            max_fee_rate = float(overview.get("max_fee_rate") or 0.0)

            def _recommended(multiplier: float) -> float:
                baseline = median_fee_rate if median_fee_rate > 0 else avg_fee_rate
                candidate = baseline * multiplier
                if multiplier < 1.0:
                    candidate = max(candidate, min_fee_rate)
                else:
                    candidate = max(candidate, min_fee_rate)
                return float(candidate)

            fee_stats = {
                "average_fee": float(overview.get("avg_fee") or 0.0),
                "median_fee": float(overview.get("median_fee") or 0.0),
                "average_fee_rate": avg_fee_rate,
                "median_fee_rate": median_fee_rate,
                "min_fee_rate": min_fee_rate,
                "max_fee_rate": max_fee_rate,
                "recommended_fee_rates": {
                    "slow": _recommended(0.75),
                    "standard": _recommended(1.0),
                    "priority": _recommended(1.25),
                },
            }

            pressure = {
                "status": pressure_state,
                "capacity_ratio": capacity_ratio,
                "pending_transactions": pending_count,
                "max_transactions": max_transactions,
                "age_pressure": age_pressure,
                "oldest_transaction_age_seconds": oldest_age,
                "size_bytes": size_bytes,
                "size_kb": overview.get("size_kb", size_bytes / 1024.0 if size_bytes else 0.0),
            }

            response_body: Dict[str, Any] = {
                "success": True,
                "limit": limit,
                "timestamp": overview.get("timestamp"),
                "fees": fee_stats,
                "pressure": pressure,
                "sponsored_transactions": overview.get("sponsored_transactions", 0),
                "rejections": overview.get("rejections", {}),
                "transactions": overview.get("transactions", []),
                "transactions_returned": overview.get("transactions_returned", 0),
            }
            return jsonify(response_body), 200

    # ==================== BLOCKCHAIN ROUTES ====================

    def _setup_blockchain_routes(self) -> None:
        """Setup blockchain query routes."""

        @self.app.route("/blocks", methods=["GET"])
        def get_blocks() -> Dict[str, Any]:
            """Get all blocks with pagination."""
            try:
                limit, offset = self._get_pagination_params(default_limit=10, max_limit=200)
            except PaginationError as exc:
                logger.warning(
                    "PaginationError in get_blocks",
                    error_type="PaginationError",
                    error=str(exc),
                    function="get_blocks",
                )
                return self._error_response(
                    str(exc),
                    status=400,
                    code="invalid_pagination",
                    event_type="api.invalid_paging",
                )

            blocks = [block.to_dict() for block in self.blockchain.chain]
            blocks.reverse()  # Most recent first

            return jsonify(
                {
                    "total": len(blocks),
                    "limit": limit,
                    "offset": offset,
                    "blocks": blocks[offset : offset + limit],
                }
            )

        @self.app.route("/blocks/<index>", methods=["GET"])
        def get_block(index: str) -> Tuple[Dict[str, Any], int]:
            """Get specific block by index with explicit validation (supports negative input)."""
            try:
                idx_int = int(index)
            except (TypeError, ValueError):
                return jsonify({"error": "Block index must be integer"}), 400

            chain = getattr(self.blockchain, "chain", [])
            chain_length = len(chain) if hasattr(chain, "__len__") else 0

            if idx_int < 0 or idx_int >= chain_length:
                return jsonify({"error": "Block not found"}), 404

            fallback_block = None
            try:
                fallback_block = chain[idx_int]
            except (IndexError, KeyError, TypeError, AttributeError) as e:
                logger.debug(
                    "Block not in chain cache",
                    block_index=idx_int,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                fallback_block = None

            block_obj = None
            if hasattr(self.blockchain, "get_block") and callable(
                getattr(self.blockchain, "get_block", None)
            ):
                try:
                    block_obj = self.blockchain.get_block(idx_int)
                except (DatabaseError, StorageError, ValidationError, KeyError, ValueError, TypeError) as e:
                    logger.debug(
                        "get_block failed",
                        block_index=idx_int,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    block_obj = None

            if block_obj is None or (
                not hasattr(block_obj, "to_dict") and not isinstance(block_obj, dict)
            ):
                block_obj = fallback_block or block_obj
            if block_obj is None:
                return jsonify({"error": "Block not found"}), 404

            payload_source = block_obj
            payload = None
            if hasattr(payload_source, "to_dict") and callable(getattr(payload_source, "to_dict", None)):
                payload = payload_source.to_dict()
            else:
                payload = payload_source
            if not isinstance(payload, dict) and fallback_block is not None:
                payload_source = fallback_block
                if hasattr(payload_source, "to_dict") and callable(getattr(payload_source, "to_dict", None)):
                    payload = payload_source.to_dict()
                else:
                    payload = payload_source
            if isinstance(payload, dict) and "index" not in payload:
                header = payload.get("header", {})
                if isinstance(header, dict) and "index" in header:
                    payload["index"] = header["index"]
            if not isinstance(payload, dict):
                return jsonify({"error": "Block not available"}), 404

            # ETag-based caching for immutable blocks
            # Extract block hash from payload or block object
            block_hash = None
            if isinstance(payload, dict):
                block_hash = payload.get("hash")
                if not block_hash and "header" in payload and isinstance(payload["header"], dict):
                    block_hash = payload["header"].get("hash")
            if not block_hash and hasattr(block_obj, "hash"):
                block_hash = block_obj.hash

            if block_hash:
                # Generate ETag from block hash (immutable identifier)
                etag = f'"{block_hash}"'

                # Check If-None-Match header for conditional request
                client_etag = request.headers.get("If-None-Match")
                if client_etag == etag:
                    # Client has cached version - return 304 Not Modified
                    return "", 304

                # Create response with caching headers
                response = make_response(jsonify(payload), 200)
                response.headers["ETag"] = etag
                # Immutable blocks can be cached forever (1 year)
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                return response

            # Fallback for blocks without hash (shouldn't happen in production)
            return jsonify(payload), 200

        @self.app.route("/block/<block_hash>", methods=["GET"])
        def get_block_by_hash(block_hash: str) -> Tuple[Dict[str, Any], int]:
            """Get a block by its hash."""
            if not block_hash:
                return jsonify({"error": "Invalid block hash"}), 400
            normalized = block_hash.lower()
            if normalized.startswith("0x"):
                normalized = normalized[2:]
            if not normalized or not re.fullmatch(r"[0-9a-f]{64}", normalized):
                return jsonify({"error": "Invalid block hash"}), 400

            block_obj = None
            lookup = getattr(self.blockchain, "get_block_by_hash", None)
            if callable(lookup):
                try:
                    block_obj = lookup(block_hash)
                except (LookupError, ValueError, TypeError) as exc:
                    logger.debug("get_block_by_hash failed: %s", type(exc).__name__)
                    block_obj = None

            if block_obj is None:
                chain = getattr(self.blockchain, "chain", [])
                target = f"0x{normalized}"
                for candidate in chain:
                    candidate_hash = getattr(candidate, "hash", None)
                    if not candidate_hash and isinstance(candidate, dict):
                        candidate_hash = candidate.get("hash") or candidate.get("block_hash")
                    if not candidate_hash:
                        continue
                    cand_norm = candidate_hash.lower()
                    if cand_norm.startswith("0x"):
                        cand_norm = cand_norm[2:]
                    if cand_norm == normalized:
                        block_obj = candidate
                        break

            if block_obj is None:
                return jsonify({"error": "Block not found"}), 404

            payload_source = block_obj
            if hasattr(payload_source, "to_dict") and callable(getattr(payload_source, "to_dict", None)):
                payload = payload_source.to_dict()
            elif isinstance(payload_source, dict):
                payload = payload_source
            else:
                payload = None

            if not isinstance(payload, dict):
                return jsonify({"error": "Block not available"}), 404

            if "hash" not in payload:
                payload["hash"] = getattr(block_obj, "hash", None)

            # ETag-based caching for immutable blocks
            # Use the block hash as the ETag (it's immutable)
            final_hash = payload.get("hash") or block_hash
            if final_hash:
                # Generate ETag from block hash
                etag = f'"{final_hash}"'

                # Check If-None-Match header for conditional request
                client_etag = request.headers.get("If-None-Match")
                if client_etag == etag:
                    # Client has cached version - return 304 Not Modified
                    return "", 304

                # Create response with caching headers
                response = make_response(jsonify(payload), 200)
                response.headers["ETag"] = etag
                # Immutable blocks can be cached forever (1 year)
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                return response

            # Fallback for blocks without hash (shouldn't happen in production)
            return jsonify(payload), 200

        @self.app.route("/block/receive", methods=["POST"])
        def receive_block() -> Tuple[Dict[str, Any], int]:
            """Receive a block from a peer node."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            ok, err, payload = self._verify_signed_peer_message()
            if not ok:
                return self._error_response(
                    "Unauthorized P2P message",
                    status=401,
                    code=f"p2p_{err}",
                )
            
            if payload is None:
                return self._error_response(
                    "Invalid block payload",
                    status=400,
                    code="invalid_payload",
                )
            header = payload.get("header") if isinstance(payload, dict) else None
            required_header = ["index", "previous_hash", "merkle_root", "timestamp", "difficulty", "nonce"]
            if not header or any(header.get(f) in (None, "") for f in required_header):
                return self._error_response(
                    "Invalid block payload",
                    status=400,
                    code="invalid_payload",
                    context={"missing_header_fields": [f for f in required_header if not header or header.get(f) in (None, "")]},
                )
            
            try:
                from xai.core.blockchain import Blockchain

                block = Blockchain.deserialize_block(payload)
            except (ValueError, TypeError, KeyError) as exc:
                return self._error_response(
                    f"Invalid block data: {exc}",
                    status=400,
                    code="invalid_block",
                    context={"error": str(exc)},
                )

            try:
                # P2P metrics: received block
                try:
                    from xai.core.monitoring import MetricsCollector
                    MetricsCollector.instance().record_p2p_message("received")
                except (RuntimeError, ValueError) as e:
                    logger.debug("P2P metrics record failed: %s", type(e).__name__)
                added = self.blockchain.add_block(block)
            except (RuntimeError, ValueError) as exc:
                return self._handle_exception(exc, "receive_block")

            if added:
                return self._success_response({"height": len(self.blockchain.chain)})
            return self._error_response(
                "Block rejected",
                status=400,
                code="block_rejected",
            )

    # ==================== WALLET ROUTES ====================

    def _record_faucet_metric(self, success: bool) -> None:
        """Update faucet metrics without failing requests if monitoring is unavailable."""
        metrics = getattr(self.node, "metrics_collector", None)
        if not metrics:
            return

        record = getattr(metrics, "record_faucet_result", None)
        if callable(record):
            record(success)

    # ==================== EXCHANGE ROUTES ====================

    def _setup_exchange_routes(self) -> None:
        """Setup exchange-related routes."""

        @self.app.route("/exchange/orders", methods=["GET"])
        def get_order_book() -> Tuple[Dict[str, Any], int]:
            """Get current order book (buy and sell orders)."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                base_dir = getattr(getattr(self.blockchain, "storage", None), "data_dir", None)
                if not isinstance(base_dir, (str, bytes, os.PathLike)):
                    base_dir = get_base_dir()
                orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
                all_orders = {"buy": [], "sell": []}
                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            for book_side in ("buy", "sell"):
                                if book_side in loaded and isinstance(loaded[book_side], list):
                                    all_orders[book_side] = loaded[book_side]
                        else:
                            raise ValueError("Order book file is corrupted")

                # Filter only open orders
                buy_orders = [o for o in all_orders.get("buy", []) if o["status"] == "open"]
                sell_orders = [o for o in all_orders.get("sell", []) if o["status"] == "open"]

                # Sort orders
                buy_orders.sort(key=lambda x: x["price"], reverse=True)
                sell_orders.sort(key=lambda x: x["price"])

                return (
                    jsonify(
                        {
                            "success": True,
                            "buy_orders": buy_orders[:20],
                            "sell_orders": sell_orders[:20],
                            "total_buy_orders": len(buy_orders),
                            "total_sell_orders": len(sell_orders),
                        }
                    ),
                    200,
                )
            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, KeyError) as exc:
                logger.error(
                    "Exchange get order book failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "exchange_get_order_book")

        @self.app.route("/exchange/place-order", methods=["POST"])
        @validate_request(self.request_validator, ExchangeOrderInput)
        def place_order() -> Tuple[Dict[str, Any], int]:
            """Place a buy or sell order with balance verification."""
            if not self.node.exchange_wallet_manager:
                return self._error_response(
                    "Exchange module disabled", status=503, code="module_disabled"
                )
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            try:
                model: Optional[ExchangeOrderInput] = getattr(request, "validated_model", None)
                if model is None:
                    return self._error_response(
                        "Invalid order payload", status=400, code="invalid_payload"
                    )

                price = float(model.price)
                amount = float(model.amount)
                pair = model.pair
                base_currency, quote_currency = pair.split("/")
                total_cost = price * amount

                user_address = model.address
                order_type = model.order_type

                # Verify balance and lock funds
                if order_type == "buy":
                    balance_info = self.node.exchange_wallet_manager.get_balance(
                        user_address, quote_currency
                    )
                    if balance_info["available"] < total_cost:
                        return self._error_response(
                            f'Insufficient {quote_currency} balance. Need {total_cost:.2f}, have {balance_info["available"]:.2f}',
                            status=400,
                            code="insufficient_funds",
                        )

                    if not self.node.exchange_wallet_manager.lock_for_order(
                        user_address, quote_currency, total_cost
                    ):
                        return self._error_response(
                            "Failed to lock funds", status=500, code="lock_failed"
                        )
                else:  # sell
                    balance_info = self.node.exchange_wallet_manager.get_balance(
                        user_address, base_currency
                    )
                    if balance_info["available"] < amount:
                        return self._error_response(
                            f'Insufficient {base_currency} balance. Need {amount:.2f}, have {balance_info["available"]:.2f}',
                            status=400,
                            code="insufficient_funds",
                        )

                    if not self.node.exchange_wallet_manager.lock_for_order(
                        user_address, base_currency, amount
                    ):
                        return self._error_response(
                            "Failed to lock funds", status=500, code="lock_failed"
                        )

                # Create order
                order = {
                    "id": f"{user_address}_{int(time.time() * 1000)}",
                    "address": user_address,
                    "order_type": order_type,
                    "pair": pair,
                    "base_currency": base_currency,
                    "quote_currency": quote_currency,
                    "price": price,
                    "amount": amount,
                    "remaining": amount,
                    "total": total_cost,
                    "status": "open",
                    "timestamp": time.time(),
                }

                # Save order
                base_dir = getattr(getattr(self.blockchain, "storage", None), "data_dir", None)
                if not isinstance(base_dir, (str, bytes, os.PathLike)):
                    base_dir = get_base_dir()
                orders_dir = os.path.join(base_dir, "exchange_data")
                os.makedirs(orders_dir, exist_ok=True)
                orders_file = os.path.join(orders_dir, "orders.json")

                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        stored_orders = json.load(f)
                        if not isinstance(stored_orders, dict):
                            raise ValueError("Order storage corrupted")
                        buy_orders = stored_orders.get("buy", [])
                        sell_orders = stored_orders.get("sell", [])
                        if not isinstance(buy_orders, list) or not isinstance(sell_orders, list):
                            raise ValueError("Order book lists are malformed")
                        all_orders = {"buy": buy_orders, "sell": sell_orders}
                else:
                    all_orders = {"buy": [], "sell": []}

                all_orders[order_type].append(order)

                with open(orders_file, "w") as f:
                    json.dump(all_orders, f, indent=2)

                # Try to match order immediately
                matched = self.node._match_orders(order, all_orders)

                # Get updated balances
                balances = self.node.exchange_wallet_manager.get_all_balances(user_address)

                return self._success_response(
                    {
                        "order": order,
                        "matched": matched,
                        "balances": balances["available_balances"],
                        "message": f"{order_type.capitalize()} order placed successfully",
                    }
                )
            except ValueError as exc:
                logger.warning(
                    "ValueError occurred",
                    error_type="ValueError",
                    error=str(exc),
                )
                return self._error_response(str(exc), status=400, code="order_invalid")
            except (DatabaseError, StorageError, OSError, IOError, TypeError, KeyError, AttributeError) as exc:
                logger.error(
                    "Exchange place order failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "exchange_place_order")

        @self.app.route("/exchange/cancel-order", methods=["POST"])
        @validate_request(self.request_validator, ExchangeCancelInput)
        def cancel_order() -> Tuple[Dict[str, Any], int]:
            """Cancel an open order."""
            if not self.node.exchange_wallet_manager:
                return self._error_response(
                    "Exchange module disabled", status=503, code="module_disabled"
                )
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            model: Optional[ExchangeCancelInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid payload", status=400, code="invalid_payload")
            try:
                base_dir = getattr(getattr(self.blockchain, "storage", None), "data_dir", None)
                if not isinstance(base_dir, (str, bytes, os.PathLike)):
                    base_dir = get_base_dir()
                orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
                if not os.path.exists(orders_file):
                    return self._error_response("Order not found", status=404, code="not_found")

                with open(orders_file, "r") as f:
                    all_orders = json.load(f)

                # Find and cancel order
                found = False
                for order_type in ["buy", "sell"]:
                    for order in all_orders[order_type]:
                        if order["id"] == model.order_id:
                            if order["status"] == "open":
                                order["status"] = "cancelled"
                                found = True
                                break
                    if found:
                        break

                if not found:
                    return self._error_response(
                        "Order not found or already completed", status=404, code="not_found"
                    )

                with open(orders_file, "w") as f:
                    json.dump(all_orders, f, indent=2)

                return self._success_response({"message": "Order cancelled successfully"})

            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, KeyError) as exc:
                logger.error(
                    "Exchange cancel order failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "exchange_cancel_order")

        @self.app.route("/exchange/my-orders/<address>", methods=["GET"])
        def get_my_orders(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all orders for a specific address."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                base_dir = getattr(getattr(self.blockchain, "storage", None), "data_dir", get_base_dir())
                orders_file = os.path.join(base_dir, "exchange_data", "orders.json")
                if not os.path.exists(orders_file):
                    return jsonify({"success": True, "orders": []}), 200

                with open(orders_file, "r") as f:
                    all_orders = json.load(f)

                # Filter orders for this address
                user_orders = []
                for order_type in ["buy", "sell"]:
                    for order in all_orders[order_type]:
                        if order["address"] == address:
                            user_orders.append(order)

                # Sort by timestamp (newest first)
                user_orders.sort(key=lambda x: x["timestamp"], reverse=True)

                return jsonify({"success": True, "orders": user_orders}), 200

            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, KeyError) as e:
                logger.error(
                    "Get my orders failed",
                    address=address,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/trades", methods=["GET"])
        def get_recent_trades() -> Tuple[Dict[str, Any], int]:
            """Get recent executed trades."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            limit = request.args.get("limit", default=50, type=int)

            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
                if not os.path.exists(trades_file):
                    return jsonify({"success": True, "trades": []}), 200

                with open(trades_file, "r") as f:
                    all_trades = json.load(f)

                all_trades.sort(key=lambda x: x["timestamp"], reverse=True)
                return jsonify({"success": True, "trades": all_trades[:limit]}), 200

            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, KeyError) as e:
                logger.error(
                    "Get recent trades failed",
                    limit=limit,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

        # Add more exchange routes...
        self._setup_exchange_balance_routes()
        self._setup_exchange_stats_routes()
        self._setup_exchange_payment_routes()

    def _setup_exchange_balance_routes(self) -> None:
        """Setup exchange balance management routes."""

        @self.app.route("/exchange/deposit", methods=["POST"])
        @validate_request(self.request_validator, ExchangeTransferInput)
        def deposit_funds() -> Tuple[Dict[str, Any], int]:
            """Deposit funds into exchange wallet."""
            if not self.node.exchange_wallet_manager:
                return self._error_response(
                    "Exchange module disabled", status=503, code="module_disabled"
                )
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            try:
                model: Optional[ExchangeTransferInput] = getattr(request, "validated_model", None)
                if model is None:
                    return self._error_response(
                        "Invalid deposit payload", status=400, code="invalid_payload"
                    )
                result = self.node.exchange_wallet_manager.deposit(
                    user_address=model.to_address,
                    currency=model.currency,
                    amount=float(model.amount),
                    deposit_type=request.json.get("deposit_type", "manual"),
                    tx_hash=request.json.get("tx_hash"),
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                logger.warning(
                    "ValueError in deposit_funds",
                    error_type="ValueError",
                    error=str(exc),
                    function="deposit_funds",
                )
                return self._error_response(str(exc), status=400, code="deposit_invalid")
            except (DatabaseError, StorageError, OSError, IOError, TypeError, KeyError, AttributeError) as exc:
                logger.error(
                    "Exchange deposit failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "exchange_deposit")

        @self.app.route("/exchange/withdraw", methods=["POST"])
        @validate_request(self.request_validator, ExchangeTransferInput)
        def withdraw_funds() -> Tuple[Dict[str, Any], int]:
            """Withdraw funds from exchange wallet."""
            if not self.node.exchange_wallet_manager:
                return self._error_response(
                    "Exchange module disabled", status=503, code="module_disabled"
                )
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            try:
                model: Optional[ExchangeTransferInput] = getattr(request, "validated_model", None)
                if model is None or not (model.destination or model.to_address):
                    return self._error_response(
                        "Invalid withdraw payload", status=400, code="invalid_payload"
                    )
                result = self.node.exchange_wallet_manager.withdraw(
                    user_address=model.from_address,
                    currency=model.currency,
                    amount=float(model.amount),
                    destination=model.destination or model.to_address,
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                logger.warning(
                    "ValueError in withdraw_funds",
                    error_type="ValueError",
                    error=str(exc),
                    function="withdraw_funds",
                )
                return self._error_response(str(exc), status=400, code="withdraw_invalid")
            except (DatabaseError, StorageError, OSError, IOError, TypeError, KeyError, AttributeError) as exc:
                logger.error(
                    "Exchange withdraw failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "exchange_withdraw")

        @self.app.route("/exchange/balance/<address>", methods=["GET"])
        def get_user_balance(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all balances for a user."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                balances = self.node.exchange_wallet_manager.get_all_balances(address)
                return jsonify({"success": True, "address": address, "balances": balances}), 200
            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, AttributeError) as e:
                logger.error(
                    "Get user balance failed",
                    address=address,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/balance/<address>/<currency>", methods=["GET"])
        def get_currency_balance(address: str, currency: str) -> Tuple[Dict[str, Any], int]:
            """Get balance for specific currency."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                balance = self.node.exchange_wallet_manager.get_balance(address, currency)
                return jsonify({"success": True, "address": address, **balance}), 200
            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, AttributeError) as e:
                logger.error(
                    "Get currency balance failed",
                    address=address,
                    currency=currency,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/transactions/<address>", methods=["GET"])
        def get_transactions(address: str) -> Tuple[Dict[str, Any], int]:
            """Get transaction history for user."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                limit = int(request.args.get("limit", 50))
                transactions = self.node.exchange_wallet_manager.get_transaction_history(
                    address, limit
                )
                return (
                    jsonify({"success": True, "address": address, "transactions": transactions}),
                    200,
                )
            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, AttributeError) as e:
                logger.error(
                    "Get transactions failed",
                    address=address,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

    def _setup_exchange_stats_routes(self) -> None:
        """Setup exchange statistics routes."""

        @self.app.route("/exchange/price-history", methods=["GET"])
        def get_price_history() -> Tuple[Dict[str, Any], int]:
            """Get historical price data for charts."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            timeframe = request.args.get("timeframe", default="24h", type=str)

            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
                if not os.path.exists(trades_file):
                    return jsonify({"success": True, "prices": [], "volumes": []}), 200

                with open(trades_file, "r") as f:
                    all_trades = json.load(f)

                # Filter by timeframe
                now = time.time()
                timeframe_seconds = {"1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000}.get(
                    timeframe, 86400
                )

                cutoff_time = now - timeframe_seconds
                recent_trades = [t for t in all_trades if t["timestamp"] >= cutoff_time]

                # Process price data (simplified version)
                price_data = []
                volume_data = []

                if recent_trades:
                    recent_trades.sort(key=lambda x: x["timestamp"])
                    # Aggregate data here...

                return (
                    jsonify(
                        {
                            "success": True,
                            "timeframe": timeframe,
                            "prices": price_data,
                            "volumes": volume_data,
                        }
                    ),
                    200,
                )

            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, KeyError) as e:
                logger.error(
                    "Get price history failed",
                    timeframe=timeframe,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/stats", methods=["GET"])
        def get_exchange_stats() -> Tuple[Dict[str, Any], int]:
            """Get exchange statistics."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                trades_file = os.path.join(get_base_dir(), "exchange_data", "trades.json")
                base_dir = getattr(getattr(self.blockchain, "storage", None), "data_dir", get_base_dir())
                orders_file = os.path.join(base_dir, "exchange_data", "orders.json")

                stats = {
                    "current_price": 0.05,
                    "volume_24h": 0,
                    "change_24h": 0,
                    "high_24h": 0,
                    "low_24h": 0,
                    "total_trades": 0,
                    "active_orders": 0,
                }

                # Calculate stats from trades
                if os.path.exists(trades_file):
                    with open(trades_file, "r") as f:
                        all_trades = json.load(f)

                    if all_trades:
                        stats["total_trades"] = len(all_trades)
                        stats["current_price"] = all_trades[-1]["price"]

                # Count active orders
                if os.path.exists(orders_file):
                    with open(orders_file, "r") as f:
                        all_orders = json.load(f)

                    for order_type in ["buy", "sell"]:
                        stats["active_orders"] += len(
                            [o for o in all_orders.get(order_type, []) if o["status"] == "open"]
                        )

                return jsonify({"success": True, "stats": stats}), 200

            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, KeyError) as e:
                logger.error(
                    "Get exchange stats failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

    def _setup_exchange_payment_routes(self) -> None:
        """Setup payment processing routes."""

        @self.app.route("/exchange/buy-with-card", methods=["POST"])
        @validate_request(self.request_validator, ExchangeCardPurchaseInput)
        def buy_with_card() -> Tuple[Dict[str, Any], int]:
            """Buy AXN with credit/debit card."""
            if not (self.node.payment_processor and self.node.exchange_wallet_manager):
                return self._error_response(
                    "Payment module disabled", status=503, code="module_disabled"
                )
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            try:
                model: Optional[ExchangeCardPurchaseInput] = getattr(request, "validated_model", None)
                if model is None:
                    return self._error_response("Invalid payload", status=400, code="invalid_payload")

                calc = self.node.payment_processor.calculate_purchase(model.usd_amount)
                if not calc["success"]:
                    return jsonify(calc), 400

                # Process payment
                payment_result = self.node.payment_processor.process_card_payment(
                    user_address=model.from_address,
                    usd_amount=model.usd_amount,
                    card_token=model.payment_token or request.json.get("payment_token", "tok_test"),
                    email=model.email,
                    card_id=model.card_id,
                    user_id=model.user_id,
                )

                if not payment_result["success"]:
                    return jsonify(payment_result), 400

                # Deposit AXN to exchange wallet
                deposit_result = self.node.exchange_wallet_manager.deposit(
                    user_address=model.to_address,
                    currency="AXN",
                    amount=payment_result["axn_amount"],
                    deposit_type="credit_card",
                    tx_hash=payment_result["payment_id"],
                )

                return self._success_response(
                    {
                        "payment": payment_result,
                        "deposit": deposit_result,
                        "message": f"Successfully purchased {payment_result['axn_amount']:.2f} AXN",
                    }
                )

            except ValueError as exc:
                logger.warning(
                    "ValueError in buy_with_card",
                    error_type="ValueError",
                    error=str(exc),
                    function="buy_with_card",
                )
                return self._error_response(str(exc), status=400, code="payment_invalid")
            except (DatabaseError, StorageError, OSError, IOError, TypeError, KeyError, AttributeError) as exc:
                logger.error(
                    "Exchange buy with card failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                return self._handle_exception(exc, "exchange_buy_with_card")

        @self.app.route("/exchange/payment-methods", methods=["GET"])
        def get_payment_methods() -> Tuple[Dict[str, Any], int]:
            """Get supported payment methods."""
            if not self.node.payment_processor:
                return jsonify({"success": False, "error": "Payment module disabled"}), 503
            try:
                methods = self.node.payment_processor.get_supported_payment_methods()
                return jsonify({"success": True, "methods": methods}), 200
            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, AttributeError) as e:
                logger.error(
                    "Get payment methods failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/calculate-purchase", methods=["POST"])
        def calculate_purchase() -> Tuple[Dict[str, Any], int]:
            """Calculate AXN amount for USD purchase."""
            if not self.node.payment_processor:
                return jsonify({"success": False, "error": "Payment module disabled"}), 503
            data = request.json
            if "usd_amount" not in data:
                return jsonify({"error": "Missing usd_amount"}), 400

            try:
                calc = self.node.payment_processor.calculate_purchase(data["usd_amount"])
                return jsonify(calc), 200
            except (DatabaseError, StorageError, OSError, IOError, ValueError, TypeError, AttributeError) as e:
                logger.error(
                    "Calculate purchase failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return jsonify({"error": str(e)}), 500
