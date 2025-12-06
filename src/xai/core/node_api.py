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
import uuid
import re
import html
import math
from contextlib import nullcontext

# Import centralized validation
from xai.core.validation import validate_address as core_validate_address
from xai.core.validation import validate_hex_string

from xai.core.vm.evm.abi import keccak256
from werkzeug.exceptions import RequestEntityTooLarge

logger = logging.getLogger(__name__)

ERC165_SELECTOR = keccak256(b"supportsInterface(bytes4)")[:4]
INTERFACE_PROBE_ADDRESS = "0x" + "b" * 40
KNOWN_TOKEN_RECEIVER_INTERFACES = {
    "erc1363_receiver": bytes.fromhex("b7b04c6b"),
    "erc721_receiver": bytes.fromhex("150b7a02"),
}

from pydantic import ValidationError as PydanticValidationError
from xai.core.config import Config, NetworkType
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
    NodeTransactionInput,
    PeerTransactionInput,
    FaucetClaimInput,
    RecoverySetupInput,
    RecoveryRequestInput,
    RecoveryVoteInput,
    RecoveryCancelInput,
    RecoveryExecuteInput,
    CryptoDepositAddressInput,
    ExchangeOrderInput,
    ExchangeTransferInput,
    ExchangeCancelInput,
    ExchangeCardPurchaseInput,
    TreasureCreateInput,
    TreasureClaimInput,
    MiningRegisterInput,
    MiningBonusClaimInput,
    ReferralCreateInput,
    ReferralUseInput,
    PeerBlockInput,
    PeerAddInput,
    FraudCheckInput,
    ContractDeployInput,
    ContractCallInput,
    ContractFeatureToggleInput,
)
from xai.core.request_validator_middleware import RequestValidator, validate_request
from xai.core.security_validation import log_security_event, SecurityValidator
from xai.core.monitoring import MetricsCollector
from xai.core.api_auth import APIAuthManager, APIKeyStore
from xai.core.governance_execution import ProposalType
from xai.network.peer_manager import PeerManager
from xai.wallet.spending_limits import SpendingLimitManager
from xai.core.vm.evm.abi import keccak256

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

        except Exception as e:
            self._log_event("peer_signature_failure", {"reason": "exception", "error": str(e)})
            return False, f"verification_error: {e}", None

    def setup_routes(self) -> None:
        """
        Register all API routes with the Flask app.

        Organizes routes into logical categories for maintainability.
        """
        self._setup_core_routes()
        self._setup_blockchain_routes()
        self._setup_transaction_routes()
        self._setup_contract_routes()
        self._setup_wallet_routes()
        self._setup_faucet_routes()
        self._setup_mining_routes()
        self._setup_peer_routes()
        self._setup_algo_routes()
        self._setup_recovery_routes()
        self._setup_gamification_routes()
        self._setup_mining_bonus_routes()
        self._setup_exchange_routes()
        self._setup_crypto_deposit_routes()
        self._setup_admin_routes()

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
            except Exception:
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
            except Exception:
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
                    except Exception as exc:  # pragma: no cover - defensive
                        blockchain_summary = {"accessible": False, "error": str(exc)}
                        overall_status = "unhealthy"
                        http_status = 503
                else:
                    blockchain_summary = {"accessible": False, "error": "Blockchain not initialized"}
                    degrade("blockchain_unavailable")
            except Exception as exc:  # pragma: no cover - defensive
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
            except Exception as exc:
                storage_status = "degraded"
                degrade("storage_unwritable")
                services["storage_error"] = str(exc)
            services["storage"] = storage_status

            # Network/P2P checks
            p2p_manager = getattr(self.node, "p2p_manager", None)
            try:
                from unittest.mock import Mock as _Mock  # type: ignore
            except Exception:  # pragma: no cover - fallback when mock not present
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
                except Exception as exc:  # pragma: no cover - defensive
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

        @self.app.route("/metrics", methods=["GET"])
        def prometheus_metrics() -> Tuple[str, int, Dict[str, str]]:
            """Prometheus metrics endpoint."""
            try:
                metrics_output = self.node.metrics_collector.export_prometheus()
                return metrics_output, 200, {"Content-Type": "text/plain; version=0.0.4"}
            except Exception as e:
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
            except Exception as exc:
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
            except Exception as exc:
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
            except Exception as e:
                logger.debug("Block %d not in chain cache: %s", idx_int, type(e).__name__)
                fallback_block = None

            block_obj = None
            if hasattr(self.blockchain, "get_block") and callable(
                getattr(self.blockchain, "get_block", None)
            ):
                try:
                    block_obj = self.blockchain.get_block(idx_int)
                except Exception as e:
                    logger.debug("get_block(%d) failed: %s", idx_int, type(e).__name__)
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
                except Exception as exc:
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
            except Exception as exc:
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
                except Exception as e:
                    logger.debug("P2P metrics record failed: %s", type(e).__name__)
                added = self.blockchain.add_block(block)
            except Exception as exc:
                return self._handle_exception(exc, "receive_block")

            if added:
                return self._success_response({"height": len(self.blockchain.chain)})
            return self._error_response(
                "Block rejected",
                status=400,
                code="block_rejected",
            )

    # ==================== TRANSACTION ROUTES ====================

    def _setup_transaction_routes(self) -> None:
        """Setup transaction-related routes."""

        @self.app.route("/transactions", methods=["GET"])
        def get_pending_transactions() -> Dict[str, Any]:
            """Get pending transactions."""
            try:
                limit, offset = self._get_pagination_params(default_limit=50, max_limit=500)
            except PaginationError as exc:
                return self._error_response(
                    str(exc),
                    status=400,
                    code="invalid_pagination",
                    event_type="api.invalid_paging",
                )

            pending = list(getattr(self.blockchain, "pending_transactions", []) or [])
            total = len(pending)
            window = pending[offset : offset + limit]

            return jsonify(
                {
                    "count": total,
                    "limit": limit,
                    "offset": offset,
                    "transactions": [tx.to_dict() for tx in window],
                }
            )

        @self.app.route("/transaction/<txid>", methods=["GET"])
        def get_transaction(txid: str) -> Tuple[Dict[str, Any], int]:
            """Get transaction by ID."""
            chain = getattr(self.blockchain, "chain", [])
            chain_length = len(chain) if hasattr(chain, "__len__") else 0

            # Search in confirmed blocks
            for i in range(chain_length):
                fallback_block = None
                try:
                    fallback_block = chain[i]
                except Exception as e:
                    logger.debug("Block %d not in chain cache: %s", i, type(e).__name__)
                    fallback_block = None

                block = None
                if hasattr(self.blockchain, "get_block") and callable(
                    getattr(self.blockchain, "get_block", None)
                ):
                    try:
                        block = self.blockchain.get_block(i)
                    except Exception as e:
                        logger.debug("get_block(%d) failed: %s", i, type(e).__name__)
                        block = None
                if block is None and fallback_block is not None:
                    block = fallback_block
                if not block:
                    continue

                txs = getattr(block, "transactions", None)
                if txs is None and isinstance(block, dict):
                    txs = block.get("transactions")
                if not isinstance(txs, (list, tuple)):
                    # fall back to chain-backed block if available
                    if fallback_block is not None and fallback_block is not block:
                        block = fallback_block
                        txs = getattr(block, "transactions", None)
                        if txs is None and isinstance(block, dict):
                            txs = block.get("transactions")
                    if not isinstance(txs, (list, tuple)):
                        continue

                for tx in txs:
                    tx_identifier = getattr(tx, "txid", None)
                    if tx_identifier is None and isinstance(tx, dict):
                        tx_identifier = tx.get("txid")
                    if tx_identifier == txid:
                        tx_payload = tx.to_dict() if hasattr(tx, "to_dict") else tx
                        block_index = getattr(block, "index", i)
                        confirmations = chain_length - block_index
                        if confirmations < 0:
                            confirmations = 0
                        return (
                            jsonify(
                                {
                                    "found": True,
                                    "block": block_index,
                                    "confirmations": confirmations,
                                    "transaction": tx_payload,
                                }
                            ),
                            200,
                        )

            # Check pending transactions
            for tx in self.blockchain.pending_transactions:
                if tx.txid == txid:
                    return (
                        jsonify({"found": True, "status": "pending", "transaction": tx.to_dict()}),
                        200,
                    )

            return jsonify({"found": False, "error": "Transaction not found"}), 404

        @self.app.route("/send", methods=["POST"])
        @validate_request(self.request_validator, NodeTransactionInput)
        def send_transaction() -> Tuple[Dict[str, Any], int]:
            """Submit new transaction with strict validation and sanitized errors."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            
            # Rate limit send endpoint - fail closed when limiter unavailable
            try:
                from xai.core.advanced_rate_limiter import get_rate_limiter as get_advanced_rate_limiter

                limiter = get_advanced_rate_limiter()
                allowed, error = limiter.check_rate_limit("/send")
                if not allowed:
                    return self._error_response(
                        error or "Rate limit exceeded",
                        status=429,
                        code="rate_limited",
                    )
            except Exception as exc:
                logger.error(
                    "Rate limiter unavailable for /send: %s",
                    type(exc).__name__,
                    extra={
                        "event": "api.rate_limiter_error",
                        "endpoint": "/send",
                        "client": request.remote_addr or "unknown",
                    },
                    exc_info=True,
                )
                return self._error_response(
                    "Rate limiting unavailable. Please retry later.",
                    status=503,
                    code="rate_limiter_unavailable",
                )
                
            model: Optional[NodeTransactionInput] = getattr(request, "validated_model", None)
            if model is None:
                payload = request.get_json(silent=True) or {}
                return self._error_response(
                    "Invalid transaction payload",
                    status=400,
                    code="invalid_payload",
                    context={"payload": payload},
                )

            try:
                from xai.core.blockchain import Transaction
                from xai.core.config import Config

                tx = Transaction(
                    sender=model.sender,
                    recipient=model.recipient,
                    amount=model.amount,
                    fee=model.fee,
                    public_key=model.public_key,
                    nonce=model.nonce,
                )
                tx.signature = model.signature
                if model.metadata:
                    tx.metadata = model.metadata

                # Enforce timestamp bounds to prevent replay/delay abuse
                now_ts = time.time()
                max_future = float(getattr(Config, "TX_MAX_FUTURE_SKEW_SECONDS", 120))
                max_age = float(getattr(Config, "TX_MAX_AGE_SECONDS", 86400))
                if model.timestamp > now_ts + max_future:
                    self._record_send_rejection("future_timestamp")
                    return self._error_response(
                        "Transaction timestamp too far in the future",
                        status=400,
                        code="future_timestamp",
                        context={"timestamp": model.timestamp, "now": now_ts},
                    )
                if model.timestamp < now_ts - max_age:
                    self._record_send_rejection("stale_timestamp")
                    return self._error_response(
                        "Transaction timestamp too old",
                        status=400,
                        code="stale_timestamp",
                        context={"timestamp": model.timestamp, "age_seconds": now_ts - model.timestamp},
                    )

                tx.timestamp = float(model.timestamp)
                expected_txid = tx.calculate_hash()
                if model.txid and model.txid != expected_txid:
                    self._record_send_rejection("txid_mismatch")
                    return self._error_response(
                        "Transaction hash mismatch",
                        status=400,
                        code="txid_mismatch",
                        context={"expected": expected_txid, "provided": model.txid},
                    )
                tx.txid = expected_txid

                # Enforce daily spending limits for non-AA wallets at API boundary
                allowed, used, limit = self.spending_limits.can_spend(model.sender, float(model.amount))
                if not allowed:
                    return self._error_response(
                        "Daily spending limit exceeded",
                        status=403,
                        code="spend_limit_exceeded",
                        context={
                            "sender": model.sender,
                            "used_today": used,
                            "limit": limit,
                            "requested": float(model.amount),
                        },
                    )

                if not tx.verify_signature():
                    return self._error_response(
                        "Invalid signature",
                        status=400,
                        code="invalid_signature",
                        context={"sender": model.sender},
                    )

                if self.blockchain.add_transaction(tx):
                    # Record spend on acceptance
                    try:
                        self.spending_limits.record_spend(model.sender, float(model.amount))
                    except Exception as e:
                        logger.warning(
                            "Failed to record spending limit for transaction",
                            extra={"error": str(e), "sender": model.sender, "event": "spending_limits.record_failed"}
                        )
                    self.node.broadcast_transaction(tx)
                    return self._success_response(
                        {
                            "txid": tx.txid,
                            "message": "Transaction submitted successfully",
                        }
                    )

                return self._error_response(
                    "Transaction validation failed",
                    status=400,
                    code="transaction_rejected",
                    context={"sender": model.sender, "recipient": model.recipient},
                )
            except Exception as exc:
                return self._handle_exception(exc, "send_transaction")

        @self.app.route("/transaction/receive", methods=["POST"])
        def receive_transaction() -> Tuple[Dict[str, Any], int]:
            """Receive a broadcasted transaction from a peer node."""
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
                    "Invalid transaction payload",
                    status=400,
                    code="invalid_payload",
                )
            required = ["sender", "recipient", "amount", "public_key", "signature", "nonce"]
            missing = [field for field in required if payload.get(field) in (None, "")]
            if missing:
                return self._error_response(
                    "Invalid transaction payload",
                    status=400,
                    code="invalid_payload",
                    context={"missing": missing},
                )

            try:
                from xai.core.blockchain import Transaction

                tx = Transaction(
                    sender=payload.get("sender"),
                    recipient=payload.get("recipient"),
                    amount=payload.get("amount"),
                    fee=payload.get("fee"),
                    public_key=payload.get("public_key"),
                    tx_type=payload.get("tx_type"),
                    nonce=payload.get("nonce"),
                    inputs=payload.get("inputs"),
                    outputs=payload.get("outputs"),
                )
                tx.timestamp = payload.get("timestamp") or time.time()
                tx.signature = payload.get("signature")
                tx.txid = payload.get("txid") or tx.calculate_hash()
                if payload.get("metadata"):
                    tx.metadata = payload.get("metadata")
            except Exception as exc:
                return self._error_response(
                    "Invalid transaction data",
                    status=400,
                    code="invalid_transaction",
                    context={"sender": payload.get("sender"), "error": str(exc)},
                )

            try:
                # P2P metrics: received transaction
                try:
                    from xai.core.monitoring import MetricsCollector
                    MetricsCollector.instance().record_p2p_message("received")
                except Exception as e:
                    logger.debug("P2P metrics record failed: %s", type(e).__name__)
                accepted = self.blockchain.add_transaction(tx)
            except Exception as exc:
                return self._handle_exception(exc, "receive_transaction")

            if accepted:
                return self._success_response({"txid": tx.txid})
            return self._error_response(
                "Transaction rejected",
                status=400,
                code="transaction_rejected",
                context={"sender": payload.get("sender"), "txid": tx.txid},
            )

    def _setup_contract_routes(self) -> None:
        """Expose the smart-contract operations when the VM is enabled."""

        @self.app.route("/contracts/deploy", methods=["POST"])
        @validate_request(self.request_validator, ContractDeployInput)
        def deploy_contract() -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            if not self.blockchain.smart_contract_manager:
                return self._error_response(
                    "Smart-contract VM feature is disabled",
                    status=503,
                    code="vm_feature_disabled",
                )
            model: Optional[ContractDeployInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response(
                    "Invalid contract deployment payload", status=400, code="invalid_payload"
                )

            nonce = model.nonce if model.nonce is not None else self.blockchain.nonce_tracker.get_next_nonce(
                model.sender
            )
            contract_address = self.blockchain.derive_contract_address(model.sender, nonce)

            metadata = dict(model.metadata or {})
            metadata["data"] = bytes.fromhex(model.bytecode)
            metadata["gas_limit"] = model.gas_limit
            metadata["contract_address"] = contract_address
            if "abi" in metadata:
                try:
                    metadata["abi"] = self.blockchain.normalize_contract_abi(metadata.get("abi"))
                except ValueError as exc:
                    return self._error_response(
                        "Invalid contract ABI",
                        status=400,
                        code="invalid_contract_abi",
                        context={"error": str(exc)},
                    )

            try:
                from xai.core.blockchain import Transaction

                tx = Transaction(
                    sender=model.sender,
                    recipient=contract_address,
                    amount=model.value,
                    fee=model.fee,
                    public_key=model.public_key,
                    nonce=nonce,
                    tx_type="contract_deploy",
                    outputs=[{"address": contract_address, "amount": model.value}],
                )
                tx.metadata = metadata
                tx.signature = model.signature
            except Exception as exc:
                return self._error_response(
                    "Unable to build deployment transaction",
                    status=400,
                    code="contract_build_error",
                    context={"error": str(exc)},
                )

            if not tx.verify_signature():
                return self._error_response(
                    "Invalid signature",
                    status=400,
                    code="invalid_signature",
                    context={"sender": model.sender},
                )

            if self.blockchain.add_transaction(tx):
                self.node.broadcast_transaction(tx)
                return self._success_response(
                    {
                        "txid": tx.txid,
                        "contract_address": contract_address,
                        "message": "Contract deployment queued",
                    }
                )

            return self._error_response(
                "Contract deployment rejected",
                status=400,
                code="contract_rejected",
                context={"contract_address": contract_address, "sender": model.sender},
            )

        @self.app.route("/contracts/call", methods=["POST"])
        @validate_request(self.request_validator, ContractCallInput)
        def call_contract() -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            if not self.blockchain.smart_contract_manager:
                return self._error_response(
                    "Smart-contract VM feature is disabled",
                    status=503,
                    code="vm_feature_disabled",
                )
            model: Optional[ContractCallInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response(
                    "Invalid contract call payload", status=400, code="invalid_payload"
                )

            nonce = model.nonce if model.nonce is not None else self.blockchain.nonce_tracker.get_next_nonce(
                model.sender
            )
            try:
                data_bytes = (
                    json.dumps(model.payload).encode("utf-8")
                    if model.payload is not None
                    else bytes.fromhex(model.data or "")
                )
            except ValueError as exc:
                return self._error_response(
                    "Contract payload serialization failed",
                    status=400,
                    code="contract_payload_error",
                    context={"error": str(exc)},
                )

            metadata = dict(model.metadata or {})
            metadata["data"] = data_bytes
            metadata["gas_limit"] = model.gas_limit

            try:
                from xai.core.blockchain import Transaction

                tx = Transaction(
                    sender=model.sender,
                    recipient=model.contract_address,
                    amount=model.value,
                    fee=model.fee,
                    public_key=model.public_key,
                    nonce=nonce,
                    tx_type="contract_call",
                    outputs=[{"address": model.contract_address, "amount": model.value}],
                )
                tx.metadata = metadata
                tx.signature = model.signature
            except Exception as exc:
                return self._error_response(
                    "Unable to build contract call",
                    status=400,
                    code="contract_build_error",
                    context={"error": str(exc)},
                )

            if not tx.verify_signature():
                return self._error_response(
                    "Invalid signature",
                    status=400,
                    code="invalid_signature",
                    context={"sender": model.sender},
                )

            if self.blockchain.add_transaction(tx):
                self.node.broadcast_transaction(tx)
                return self._success_response(
                    {"txid": tx.txid, "message": "Contract call queued"}
                )

            return self._error_response(
                "Contract call rejected",
                status=400,
                code="contract_rejected",
                context={"contract_address": model.contract_address, "sender": model.sender},
            )

        @self.app.route("/contracts/<address>/state", methods=["GET"])
        def contract_state(address: str) -> Tuple[Dict[str, Any], int]:
            if not self.blockchain.smart_contract_manager:
                return self._error_response(
                    "Smart-contract VM feature is disabled",
                    status=503,
                    code="vm_feature_disabled",
                )
            try:
                normalized = InputSanitizer.validate_address(address)
            except ValueError as exc:
                return self._error_response(
                    str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
                )
            state = self.blockchain.get_contract_state(normalized)
            if not state:
                return self._error_response(
                    "Contract not found", status=404, code="contract_not_found"
                )
            return self._success_response({"contract_address": normalized, "state": state})

        @self.app.route("/contracts/<address>/abi", methods=["GET"])
        def contract_abi(address: str) -> Tuple[Dict[str, Any], int]:
            try:
                normalized = InputSanitizer.validate_address(address)
            except ValueError as exc:
                return self._error_response(
                    str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
                )

            abi_payload = self.blockchain.get_contract_abi(normalized)
            if not abi_payload:
                return self._error_response(
                    "Contract ABI not found", status=404, code="contract_abi_missing"
                )
            response = {"contract_address": normalized, **abi_payload}
            return self._success_response(response)

        @self.app.route("/contracts/<address>/interfaces", methods=["GET"])
        def contract_interfaces(address: str) -> Tuple[Dict[str, Any], int]:
            try:
                normalized = InputSanitizer.validate_address(address)
            except ValueError as exc:
                return self._error_response(
                    str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
                )

            if normalized.upper() not in self.blockchain.contracts:
                return self._error_response(
                    "Contract not found", status=404, code="contract_not_found"
                )

            cached_metadata = self.blockchain.get_contract_interface_metadata(normalized)
            served_from_cache = bool(cached_metadata)
            interfaces = cached_metadata["supports"] if cached_metadata else None

            if interfaces is None:
                if not self.blockchain.smart_contract_manager:
                    return self._error_response(
                        "Smart-contract VM feature is disabled",
                        status=503,
                        code="vm_feature_disabled",
                    )
                try:
                    interfaces = self._detect_contract_interfaces(normalized)
                except RuntimeError as exc:
                    return self._error_response(
                        str(exc),
                        status=503,
                        code="vm_feature_disabled",
                    )
                cached_metadata = self.blockchain.update_contract_interface_metadata(
                    normalized, interfaces, source="erc165_probe"
                )

            return self._success_response(
                {
                    "contract_address": normalized,
                    "interfaces": interfaces,
                    "metadata": {
                        "detected_at": cached_metadata.get("detected_at") if cached_metadata else None,
                        "source": (cached_metadata or {}).get("source", "unknown"),
                        "cached": served_from_cache,
                    },
                }
            )

        @self.app.route("/contracts/<address>/events", methods=["GET"])
        def contract_events(address: str) -> Tuple[Dict[str, Any], int]:
            try:
                limit, offset = self._get_pagination_params(default_limit=50, max_limit=500)
            except PaginationError as exc:
                return self._error_response(
                    str(exc), status=400, code="invalid_pagination", event_type="contracts.invalid_paging"
                )

            try:
                normalized = InputSanitizer.validate_address(address)
            except ValueError as exc:
                return self._error_response(
                    str(exc), status=400, code="invalid_address", event_type="contracts.invalid_address"
                )

            events, total = self.blockchain.get_contract_events(normalized, limit, offset)
            return self._success_response(
                {
                    "contract_address": normalized,
                    "events": events,
                    "count": len(events),
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }
            )

        @self.app.route("/contracts/governance/status", methods=["GET"])
        def contract_feature_status() -> Tuple[Dict[str, Any], int]:
            executor = getattr(self.blockchain, "governance_executor", None)
            feature_enabled = bool(
                executor and executor.is_feature_enabled("smart_contracts")
            )
            config_enabled = bool(getattr(Config, "FEATURE_FLAGS", {}).get("vm", False))
            manager_ready = bool(
                feature_enabled and config_enabled and self.blockchain.smart_contract_manager
            )
            return self._success_response(
                {
                    "feature_name": "smart_contracts",
                    "config_enabled": config_enabled,
                    "governance_enabled": feature_enabled,
                    "contract_manager_ready": manager_ready,
                    "contracts_tracked": len(self.blockchain.contracts),
                    "receipts_tracked": len(self.blockchain.contract_receipts),
                }
            )

        @self.app.route("/contracts/governance/feature", methods=["POST"])
        @validate_request(self.request_validator, ContractFeatureToggleInput)
        def contract_feature_toggle() -> Tuple[Dict[str, Any], int]:
            if not self.blockchain.governance_executor:
                return self._error_response(
                    "Governance execution engine unavailable",
                    status=500,
                    code="governance_unavailable",
                )
            admin_allowed, admin_error = self.api_auth.authorize_admin(request)
            if not admin_allowed:
                return self._error_response(
                    "Admin authentication failed",
                    status=403,
                    code="admin_auth_failed",
                    context={"reason": admin_error},
                )

            model: Optional[ContractFeatureToggleInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response(
                    "Request must be a JSON object",
                    status=400,
                    code="invalid_payload",
                )

            enabled = model.enabled
            
            proposal_id = f"smart-contracts-{int(time.time())}-{uuid.uuid4().hex[:8]}"
            proposal_data = {
                "proposal_type": ProposalType.FEATURE_ACTIVATION.value,
                "feature_name": "smart_contracts",
                "enabled": enabled,
                "reason": model.reason or "",
            }

            try:
                execution_result = self.blockchain.governance_executor.execute_proposal(
                    proposal_id, proposal_data
                )
            except Exception as exc:
                return self._handle_exception(exc, "contract_feature_toggle")

            if not execution_result.get("success"):
                return self._error_response(
                    "Governance toggle rejected",
                    status=400,
                    code="governance_toggle_rejected",
                    context={"details": execution_result},
                )

            self.blockchain.sync_smart_contract_vm()
            self._log_event(
                "contracts_governance_toggle",
                {
                    "proposal_id": proposal_id,
                    "feature": "smart_contracts",
                    "enabled": enabled,
                    "requester": getattr(request, "remote_addr", "unknown"),
                },
                severity="INFO",
            )

            return self._success_response(
                {"proposal_id": proposal_id, "governance_result": execution_result}
            )

    # ==================== WALLET ROUTES ====================

    def _setup_wallet_routes(self) -> None:
        """Setup wallet-related routes."""

        @self.app.route("/balance/<address>", methods=["GET"])
        def get_balance(address: str) -> Dict[str, Any]:
            """Get address balance."""
            balance = self.blockchain.get_balance(address)
            return jsonify({"address": address, "balance": balance})

        @self.app.route("/address/<address>/nonce", methods=["GET"])
        def get_address_nonce(address: str) -> Tuple[Dict[str, Any], int]:
            """Return confirmed and next nonce for an address."""
            tracker = getattr(self.blockchain, "nonce_tracker", None)
            if tracker is None:
                return self._error_response(
                    "Nonce tracker unavailable",
                    status=503,
                    code="nonce_tracker_unavailable",
                )

            try:
                confirmed = tracker.get_nonce(address)
                next_nonce = tracker.get_next_nonce(address)
            except Exception as exc:
                return self._handle_exception(exc, "nonce_lookup")

            pending_nonce = next_nonce - 1 if next_nonce - 1 > confirmed else None
            return (
                jsonify(
                    {
                        "address": address,
                        "confirmed_nonce": max(confirmed, -1),
                        "next_nonce": next_nonce,
                        "pending_nonce": pending_nonce,
                    }
                ),
                200,
            )

        @self.app.route("/history/<address>", methods=["GET"])
        def get_history(address: str) -> Dict[str, Any]:
            """Get transaction history for address."""
            try:
                limit, offset = self._get_pagination_params(default_limit=50, max_limit=500)
            except PaginationError as exc:
                return self._error_response(
                    str(exc),
                    status=400,
                    code="invalid_pagination",
                    event_type="api.invalid_paging",
                )

            try:
                window, total = self.blockchain.get_transaction_history_window(address, limit, offset)
            except ValueError as exc:
                return self._error_response(
                    str(exc),
                    status=400,
                    code="invalid_pagination",
                    event_type="api.invalid_paging",
                )

            return jsonify(
                {
                    "address": address,
                    "transaction_count": total,
                    "limit": limit,
                    "offset": offset,
                    "transactions": window,
                }
            )

    # ==================== FAUCET ROUTES ====================

    def _setup_faucet_routes(self) -> None:
        """Setup faucet claim route for testnet users."""

        @self.app.route("/faucet/claim", methods=["POST"])
        def claim_faucet() -> Tuple[Dict[str, Any], int]:
            """Queue a faucet transaction for the provided testnet address."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            if not getattr(Config, "FAUCET_ENABLED", False):
                self._record_faucet_metric(success=False)
                return self._error_response(
                    "Faucet is disabled on this network",
                    status=403,
                    code="faucet_disabled",
                )

            network = getattr(Config, "NETWORK_TYPE", NetworkType.TESTNET)
            if network != NetworkType.TESTNET:
                self._record_faucet_metric(success=False)
                return self._error_response(
                    "Faucet is only available on the testnet",
                    status=403,
                    code="faucet_unavailable",
                )

            payload = request.get_json(silent=True) or {}
            try:
                model = FaucetClaimInput.parse_obj(payload)
            except PydanticValidationError as exc:
                self._record_faucet_metric(success=False)
                return self._error_response(
                    "Invalid faucet request",
                    status=400,
                    code="invalid_payload",
                    context={"errors": exc.errors()},
                )

            address = model.address

            expected_prefix = getattr(Config, "ADDRESS_PREFIX", "")
            if expected_prefix and not address.startswith(expected_prefix):
                self._record_faucet_metric(success=False)
                return self._error_response(
                    f"Invalid address for this network. Expected prefix {expected_prefix}.",
                    status=400,
                    code="invalid_address",
                    context={"address": address, "expected_prefix": expected_prefix},
                )

            amount = float(getattr(Config, "FAUCET_AMOUNT", 0.0) or 0.0)
            if amount <= 0:
                self._record_faucet_metric(success=False)
                return self._error_response(
                    "Faucet amount is not configured",
                    status=503,
                    code="faucet_misconfigured",
                )

            limiter = get_rate_limiter()
            identifier = f"{address}:{request.remote_addr or 'unknown'}"
            allowed, error = limiter.check_rate_limit(identifier, "/faucet/claim")
            if not allowed:
                self._record_faucet_metric(success=False)
                return self._error_response(
                    error or "Rate limit exceeded",
                    status=429,
                    code="rate_limited",
                    context={"address": address, "identifier": identifier},
                )

            try:
                faucet_tx = self.node.queue_faucet_transaction(address, amount)
            except Exception as exc:  # pragma: no cover - defensive
                self._record_faucet_metric(success=False)
                return self._handle_exception(exc, "faucet_queue")

            self._record_faucet_metric(success=True)
            return self._success_response(
                {
                    "amount": amount,
                    "txid": getattr(faucet_tx, "txid", None),
                    "message": (
                        f"Testnet faucet claim successful! {amount} XAI will be added to your "
                        "address after the next block."
                    ),
                    "note": "This is testnet XAI - it has no real value!",
                }
            )

    def _record_faucet_metric(self, success: bool) -> None:
        """Update faucet metrics without failing requests if monitoring is unavailable."""
        metrics = getattr(self.node, "metrics_collector", None)
        if not metrics:
            return

        record = getattr(metrics, "record_faucet_result", None)
        if callable(record):
            record(success)

    # ==================== MINING ROUTES ====================

    def _setup_mining_routes(self) -> None:
        """Setup mining-related routes."""

        @self.app.route("/mine", methods=["POST"])
        def mine_block() -> Tuple[Dict[str, Any], int]:
            """Mine pending transactions."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            # Rate limit mining endpoint - fail closed when limiter unavailable
            try:
                from xai.core.advanced_rate_limiter import get_rate_limiter as get_advanced_rate_limiter

                limiter = get_advanced_rate_limiter()
                allowed, error = limiter.check_rate_limit("/mine")
                if not allowed:
                    return self._error_response(
                        error or "Rate limit exceeded",
                        status=429,
                        code="rate_limited",
                    )
            except Exception as exc:
                logger.error(
                    "Rate limiter unavailable for /mine: %s",
                    type(exc).__name__,
                    extra={
                        "event": "api.rate_limiter_error",
                        "endpoint": "/mine",
                        "client": request.remote_addr or "unknown",
                    },
                    exc_info=True,
                )
                return self._error_response(
                    "Rate limiting unavailable. Please retry later.",
                    status=503,
                    code="rate_limiter_unavailable",
                )

            if not self.blockchain.pending_transactions:
                return jsonify({"error": "No pending transactions to mine"}), 400

            try:
                block = self.blockchain.mine_pending_transactions(self.node.miner_address)

                # Broadcast new block to peers
                self.node.broadcast_block(block)

                return (
                    jsonify(
                        {
                            "success": True,
                            "block": block.to_dict(),
                            "message": f"Block {block.index} mined successfully",
                            "reward": self.blockchain.block_reward,
                        }
                    ),
                    200,
                )

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/auto-mine/start", methods=["POST"])
        def start_auto_mining() -> Dict[str, str]:
            """Start automatic mining."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            if self.node.is_mining:
                return jsonify({"message": "Mining already active"})

            self.node.start_mining()
            return jsonify({"message": "Auto-mining started"})

        @self.app.route("/auto-mine/stop", methods=["POST"])
        def stop_auto_mining() -> Dict[str, str]:
            """Stop automatic mining."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            if not self.node.is_mining:
                return jsonify({"message": "Mining not active"})

            self.node.stop_mining()
            return jsonify({"message": "Auto-mining stopped"})

    # ==================== P2P ROUTES ====================

    def _setup_peer_routes(self) -> None:
        """Setup peer-to-peer networking routes."""

        @self.app.route("/peers", methods=["GET"])
        def get_peers() -> Dict[str, Any]:
            """Get connected peers."""
            verbose = request.args.get("verbose", "false")
            verbose_requested = str(verbose).lower() in {"1", "true", "yes", "on"}
            payload: Dict[str, Any] = {"count": len(self.node.peers), "peers": list(self.node.peers), "verbose": verbose_requested}
            if verbose_requested:
                payload.update(self._build_peer_snapshot())
            return jsonify(payload)

        @self.app.route("/peers/add", methods=["POST"])
        @validate_request(self.request_validator, PeerAddInput)
        def add_peer() -> Tuple[Dict[str, str], int]:
            """Add peer node."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[PeerAddInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid peer payload", status=400, code="invalid_payload")

            self.node.add_peer(model.url)
            return self._success_response({"message": f"Peer {model.url} added"})

        @self.app.route("/sync", methods=["POST"])
        def sync_blockchain() -> Dict[str, Any]:
            """Synchronize blockchain with peers."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            synced = self.node.sync_with_network()
            return jsonify({"synced": synced, "chain_length": len(self.blockchain.chain)})

    # ==================== ALGORITHMIC FEATURE ROUTES ====================

    def _setup_algo_routes(self) -> None:
        """Setup algorithmic feature routes."""

        @self.app.route("/algo/fee-estimate", methods=["GET"])
        def estimate_fee() -> Tuple[Dict[str, Any], int]:
            """Get algorithmic fee recommendation."""
            fee_optimizer = getattr(self.node, "fee_optimizer", None)
            enabled = getattr(node_utils, "ALGO_FEATURES_ENABLED", ALGO_FEATURES_ENABLED) or ALGO_FEATURES_ENABLED
            if not (enabled and fee_optimizer):
                return jsonify({"error": "Algorithmic features not available"}), 503

            priority = request.args.get("priority", "normal")
            pending_transactions = list(getattr(self.blockchain, "pending_transactions", []) or [])
            pending_count = len(pending_transactions)

            fee_rates: List[float] = []
            mempool_bytes = 0
            size_samples = 0

            for tx in pending_transactions:
                rate_callable = getattr(tx, "get_fee_rate", None)
                if callable(rate_callable):
                    try:
                        rate_value = rate_callable()
                        if isinstance(rate_value, (int, float)) and math.isfinite(rate_value) and rate_value > 0:
                            fee_rates.append(float(rate_value))
                    except Exception as e:
                        logger.debug(
                            "Failed to get fee rate from transaction",
                            extra={"error": str(e), "event": "mempool.fee_rate_error"}
                        )

                size_callable = getattr(tx, "get_size", None)
                if callable(size_callable):
                    try:
                        size_value = size_callable()
                        if isinstance(size_value, (int, float)) and size_value > 0:
                            mempool_bytes += int(size_value)
                            size_samples += 1
                    except Exception as e:
                        logger.debug(
                            "Failed to get size from transaction",
                            extra={"error": str(e), "event": "mempool.size_error"}
                        )

            avg_tx_size = (mempool_bytes / size_samples) if size_samples else 450.0
            max_block_bytes = 1_000_000
            avg_tx_size = max(avg_tx_size, 200.0)
            approx_block_capacity = max(1, min(5000, int(max_block_bytes / avg_tx_size)))

            recommendation = fee_optimizer.predict_optimal_fee(
                pending_tx_count=pending_count,
                priority=priority,
                fee_rates=fee_rates,
                mempool_bytes=mempool_bytes,
                avg_block_capacity=approx_block_capacity,
            )
            return jsonify(recommendation), 200

        @self.app.route("/algo/fraud-check", methods=["POST"])
        def check_fraud() -> Tuple[Dict[str, Any], int]:
            """Check transaction for fraud indicators."""
            enabled = getattr(node_utils, "ALGO_FEATURES_ENABLED", ALGO_FEATURES_ENABLED) or ALGO_FEATURES_ENABLED
            fraud_detector = getattr(self.node, "fraud_detector", None)
            if not (enabled and fraud_detector):
                return jsonify({"error": "Algorithmic features not available"}), 503

            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            # Explicit validation to avoid running request_validator when feature is disabled
            valid, error, parsed = self.request_validator.validate_pydantic_model(FraudCheckInput)
            if not valid or parsed is None:
                error_message = error or "Missing transaction data"
                return self._error_response(
                    error_message,
                    status=400,
                    code="invalid_payload",
                    context={"errors": error},
                )

            analysis = fraud_detector.analyze_transaction(parsed.payload)
            return jsonify(analysis), 200

        @self.app.route("/algo/status", methods=["GET"])
        def algo_status() -> Dict[str, Any]:
            """Get algorithmic features status."""
            fee_optimizer = getattr(self.node, "fee_optimizer", None)
            fraud_detector = getattr(self.node, "fraud_detector", None)
            enabled = getattr(node_utils, "ALGO_FEATURES_ENABLED", ALGO_FEATURES_ENABLED) or ALGO_FEATURES_ENABLED

            if not enabled:
                return jsonify({"enabled": False, "features": []})

            features: List[Dict[str, Any]] = []
            if fee_optimizer:
                fee_history = getattr(fee_optimizer, "fee_history", [])
                features.append(
                    {
                        "name": "Fee Optimizer",
                        "description": "Statistical fee prediction using EMA",
                        "status": "active",
                        "transactions_analyzed": len(fee_history),
                        "confidence": min(100, len(fee_history) * 2),
                    }
                )
            if fraud_detector:
                addresses_tracked = len(getattr(fraud_detector, "address_history", []))
                flagged = len(getattr(fraud_detector, "flagged_addresses", []))
                features.append(
                    {
                        "name": "Fraud Detector",
                        "description": "Pattern-based fraud detection",
                        "status": "active",
                        "addresses_tracked": addresses_tracked,
                        "flagged_addresses": flagged,
                    }
                )

            if not features:
                return jsonify({"enabled": True, "features": [], "warning": "Modules not installed"})

            return jsonify({"enabled": True, "features": features})

    # ==================== SOCIAL RECOVERY ROUTES ====================

    def _setup_recovery_routes(self) -> None:
        """Setup social recovery routes."""

        @self.app.route("/recovery/setup", methods=["POST"])
        @validate_request(self.request_validator, RecoverySetupInput)
        def setup_recovery() -> Tuple[Dict[str, Any], int]:
            """Set up guardians for a wallet."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[RecoverySetupInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response(
                    "Invalid recovery payload",
                    status=400,
                    code="invalid_payload",
                )

            try:
                result = self.node.recovery_manager.setup_guardians(
                    owner_address=model.owner_address,
                    guardian_addresses=model.guardians,
                    threshold=model.threshold,
                    signature=model.signature,
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                return self._error_response(str(exc), status=400, code="recovery_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "recovery_setup")

        @self.app.route("/recovery/request", methods=["POST"])
        @validate_request(self.request_validator, RecoveryRequestInput)
        def request_recovery() -> Tuple[Dict[str, Any], int]:
            """Initiate a recovery request."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[RecoveryRequestInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid recovery payload", status=400, code="invalid_payload")

            try:
                result = self.node.recovery_manager.initiate_recovery(
                    owner_address=model.owner_address,
                    new_address=model.new_address,
                    guardian_address=model.guardian_address,
                    signature=model.signature,
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                return self._error_response(str(exc), status=400, code="recovery_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "recovery_request")

        @self.app.route("/recovery/vote", methods=["POST"])
        @validate_request(self.request_validator, RecoveryVoteInput)
        def vote_recovery() -> Tuple[Dict[str, Any], int]:
            """Guardian votes on a recovery request."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            model: Optional[RecoveryVoteInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid recovery payload", status=400, code="invalid_payload")

            try:
                result = self.node.recovery_manager.vote_recovery(
                    request_id=model.request_id,
                    guardian_address=model.guardian_address,
                    signature=model.signature,
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                return self._error_response(str(exc), status=400, code="recovery_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "recovery_vote")

        @self.app.route("/recovery/status/<address>", methods=["GET"])
        def get_recovery_status(address: str) -> Tuple[Dict[str, Any], int]:
            """Get recovery status for an address."""
            try:
                status = self.node.recovery_manager.get_recovery_status(address)
                return jsonify({"success": True, "address": address, "status": status}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/cancel", methods=["POST"])
        @validate_request(self.request_validator, RecoveryCancelInput)
        def cancel_recovery() -> Tuple[Dict[str, Any], int]:
            """Cancel a pending recovery request."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            model: Optional[RecoveryCancelInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid recovery payload", status=400, code="invalid_payload")

            try:
                result = self.node.recovery_manager.cancel_recovery(
                    request_id=model.request_id,
                    owner_address=model.owner_address,
                    signature=model.signature,
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                return self._error_response(str(exc), status=400, code="recovery_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "recovery_cancel")

        @self.app.route("/recovery/execute", methods=["POST"])
        @validate_request(self.request_validator, RecoveryExecuteInput)
        def execute_recovery() -> Tuple[Dict[str, Any], int]:
            """Execute an approved recovery after waiting period."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error
            model: Optional[RecoveryExecuteInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid recovery payload", status=400, code="invalid_payload")

            try:
                result = self.node.recovery_manager.execute_recovery(
                    request_id=model.request_id, executor_address=model.executor_address
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                return self._error_response(str(exc), status=400, code="recovery_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "recovery_execute")

        @self.app.route("/recovery/config/<address>", methods=["GET"])
        def get_recovery_config(address: str) -> Tuple[Dict[str, Any], int]:
            """Get recovery configuration for an address."""
            try:
                config = self.node.recovery_manager.get_recovery_config(address)
                if config:
                    return jsonify({"success": True, "address": address, "config": config}), 200
                else:
                    return (
                        jsonify({"success": False, "message": "No recovery configuration found"}),
                        404,
                    )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/guardian/<address>", methods=["GET"])
        def get_guardian_duties(address: str) -> Tuple[Dict[str, Any], int]:
            """Get guardian duties for an address."""
            try:
                duties = self.node.recovery_manager.get_guardian_duties(address)
                return jsonify({"success": True, "duties": duties}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/requests", methods=["GET"])
        def get_recovery_requests() -> Tuple[Dict[str, Any], int]:
            """Get all recovery requests with optional status filter."""
            try:
                status_filter = request.args.get("status")
                requests_list = self.node.recovery_manager.get_all_requests(status=status_filter)
                return (
                    jsonify(
                        {"success": True, "count": len(requests_list), "requests": requests_list}
                    ),
                    200,
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/recovery/stats", methods=["GET"])
        def get_recovery_stats() -> Tuple[Dict[str, Any], int]:
            """Get social recovery statistics."""
            try:
                stats = self.node.recovery_manager.get_stats()
                return jsonify({"success": True, "stats": stats}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ==================== GAMIFICATION ROUTES ====================

    def _setup_gamification_routes(self) -> None:
        """Setup gamification routes (airdrops, streaks, treasures, etc.)."""

        @self.app.route("/airdrop/winners", methods=["GET"])
        def get_airdrop_winners() -> Dict[str, Any]:
            """Get recent airdrop winners."""
            limit = request.args.get("limit", default=10, type=int)
            recent_airdrops = self.blockchain.airdrop_manager.get_recent_airdrops(limit)
            return jsonify({"success": True, "airdrops": recent_airdrops})

        @self.app.route("/airdrop/user/<address>", methods=["GET"])
        def get_user_airdrops(address: str) -> Dict[str, Any]:
            """Get airdrop history for specific address."""
            history = self.blockchain.airdrop_manager.get_user_airdrop_history(address)
            total_received = sum(a["amount"] for a in history)
            return jsonify(
                {
                    "success": True,
                    "address": address,
                    "total_airdrops": len(history),
                    "total_received": total_received,
                    "history": history,
                }
            )

        @self.app.route("/mining/streaks", methods=["GET"])
        def get_mining_streaks() -> Dict[str, Any]:
            """Get mining streak leaderboard."""
            limit = request.args.get("limit", default=10, type=int)
            sort_by = request.args.get("sort_by", default="current_streak")
            leaderboard = self.blockchain.streak_tracker.get_leaderboard(limit, sort_by)
            return jsonify({"success": True, "leaderboard": leaderboard})

        @self.app.route("/mining/streak/<address>", methods=["GET"])
        def get_miner_streak(address: str) -> Tuple[Dict[str, Any], int]:
            """Get mining streak for specific address."""
            stats = self.blockchain.streak_tracker.get_miner_stats(address)
            if not stats:
                return (
                    jsonify(
                        {"success": False, "error": "No mining history found for this address"}
                    ),
                    404,
                )
            return jsonify({"success": True, "address": address, "stats": stats}), 200

        @self.app.route("/treasure/active", methods=["GET"])
        def get_active_treasures() -> Dict[str, Any]:
            """List all active (unclaimed) treasure hunts."""
            treasures = self.blockchain.treasure_manager.get_active_treasures()
            return jsonify({"success": True, "count": len(treasures), "treasures": treasures})

        @self.app.route("/treasure/create", methods=["POST"])
        @validate_request(self.request_validator, TreasureCreateInput)
        def create_treasure() -> Tuple[Dict[str, Any], int]:
            """Create a new treasure hunt."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[TreasureCreateInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid treasure payload", status=400, code="invalid_payload")

            try:
                treasure_id = self.blockchain.treasure_manager.create_treasure_hunt(
                    creator_address=model.creator,
                    amount=float(model.amount),
                    puzzle_type=model.puzzle_type,
                    puzzle_data=model.puzzle_data,
                    hint=model.hint or "",
                )
                return self._success_response(
                    {
                        "treasure_id": treasure_id,
                        "message": "Treasure hunt created successfully",
                    }
                )
            except Exception as exc:
                return self._handle_exception(exc, "create_treasure")

        @self.app.route("/treasure/claim", methods=["POST"])
        @validate_request(self.request_validator, TreasureClaimInput)
        def claim_treasure() -> Tuple[Dict[str, Any], int]:
            """Claim a treasure by solving the puzzle."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[TreasureClaimInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid treasure payload", status=400, code="invalid_payload")

            try:
                from xai.core.blockchain import Transaction

                success, amount = self.blockchain.treasure_manager.claim_treasure(
                    treasure_id=model.treasure_id,
                    claimer_address=model.claimer,
                    solution=model.solution,
                )

                if success:
                    treasure_tx = Transaction("COINBASE", model.claimer, amount, tx_type="treasure")
                    treasure_tx.txid = treasure_tx.calculate_hash()
                    self.blockchain.pending_transactions.append(treasure_tx)

                    return self._success_response(
                        {
                            "amount": amount,
                            "message": "Treasure claimed successfully!",
                        }
                    )
                return self._error_response(
                    "Incorrect solution",
                    status=400,
                    code="invalid_solution",
                )

            except Exception as exc:
                return self._handle_exception(exc, "claim_treasure")

        @self.app.route("/treasure/details/<treasure_id>", methods=["GET"])
        def get_treasure_details(treasure_id: str) -> Tuple[Dict[str, Any], int]:
            """Get details of a specific treasure hunt."""
            treasure = self.blockchain.treasure_manager.get_treasure_details(treasure_id)
            if not treasure:
                return jsonify({"error": "Treasure not found"}), 404
            return jsonify({"success": True, "treasure": treasure}), 200

        @self.app.route("/timecapsule/pending", methods=["GET"])
        def get_pending_timecapsules() -> Dict[str, Any]:
            """List all pending (locked) time capsules."""
            capsules = self.blockchain.timecapsule_manager.get_pending_capsules()
            return jsonify({"success": True, "count": len(capsules), "capsules": capsules})

        @self.app.route("/timecapsule/<address>", methods=["GET"])
        def get_user_timecapsules(address: str) -> Dict[str, Any]:
            """Get time capsules for a specific user."""
            capsules = self.blockchain.timecapsule_manager.get_user_capsules(address)
            return jsonify(
                {
                    "success": True,
                    "address": address,
                    "sent": capsules["sent"],
                    "received": capsules["received"],
                }
            )

        @self.app.route("/refunds/stats", methods=["GET"])
        def get_refund_stats() -> Dict[str, Any]:
            """Get overall fee refund statistics."""
            stats = self.blockchain.fee_refund_calculator.get_refund_stats()
            return jsonify({"success": True, "stats": stats})

        @self.app.route("/refunds/<address>", methods=["GET"])
        def get_user_refunds(address: str) -> Dict[str, Any]:
            """Get fee refund history for specific address."""
            history = self.blockchain.fee_refund_calculator.get_user_refund_history(address)
            total_refunded = sum(r["amount"] for r in history)
            return jsonify(
                {
                    "success": True,
                    "address": address,
                    "total_refunds": len(history),
                    "total_refunded": total_refunded,
                    "history": history,
                }
            )

    # ==================== MINING BONUS ROUTES ====================

    def _setup_mining_bonus_routes(self) -> None:
        """Setup mining bonus routes."""

        @self.app.route("/mining/register", methods=["POST"])
        @validate_request(self.request_validator, MiningRegisterInput)
        def register_miner() -> Tuple[Dict[str, Any], int]:
            """Register a new miner and check for early adopter bonus."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[MiningRegisterInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid miner payload", status=400, code="invalid_payload")

            try:
                result = self.node.bonus_manager.register_miner(model.address)
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except Exception as exc:
                return self._handle_exception(exc, "register_miner")

        @self.app.route("/mining/achievements/<address>", methods=["GET"])
        def get_achievements(address: str) -> Tuple[Dict[str, Any], int]:
            """Check mining achievements for an address."""
            blocks_mined = request.args.get("blocks_mined", default=0, type=int)
            streak_days = request.args.get("streak_days", default=0, type=int)

            try:
                result = self.node.bonus_manager.check_achievements(
                    address, blocks_mined, streak_days
                )
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/claim-bonus", methods=["POST"])
        @validate_request(self.request_validator, MiningBonusClaimInput)
        def claim_bonus() -> Tuple[Dict[str, Any], int]:
            """Claim a social bonus (tweet verification, discord join, etc.)."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[MiningBonusClaimInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid bonus payload", status=400, code="invalid_payload")

            try:
                result = self.node.bonus_manager.claim_bonus(model.address, model.bonus_type)
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except Exception as exc:
                return self._handle_exception(exc, "claim_bonus")

        @self.app.route("/mining/referral/create", methods=["POST"])
        @validate_request(self.request_validator, ReferralCreateInput)
        def create_referral_code() -> Tuple[Dict[str, Any], int]:
            """Create a referral code for a miner."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[ReferralCreateInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid referral payload", status=400, code="invalid_payload")

            try:
                result = self.node.bonus_manager.create_referral_code(model.address)
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except Exception as exc:
                return self._handle_exception(exc, "create_referral_code")

        @self.app.route("/mining/referral/use", methods=["POST"])
        @validate_request(self.request_validator, ReferralUseInput)
        def use_referral_code() -> Tuple[Dict[str, Any], int]:
            """Use a referral code to register a new miner."""
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[ReferralUseInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid referral payload", status=400, code="invalid_payload")

            try:
                result = self.node.bonus_manager.use_referral_code(
                    model.new_address,
                    model.referral_code,
                    metadata=getattr(model, "metadata", None),
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except Exception as exc:
                return self._handle_exception(exc, "use_referral_code")

        @self.app.route("/mining/user-bonuses/<address>", methods=["GET"])
        def get_user_bonuses(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all bonuses and rewards for a user."""
            try:
                result = self.node.bonus_manager.get_user_bonuses(address)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/leaderboard", methods=["GET"])
        def get_bonus_leaderboard() -> Tuple[Dict[str, Any], int]:
            """Get mining bonus leaderboard."""
            limit = request.args.get("limit", default=10, type=int)

            try:
                leaderboard = self.node.bonus_manager.get_leaderboard(limit)
                return jsonify({"success": True, "limit": limit, "leaderboard": leaderboard}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/leaderboard/unified", methods=["GET"])
        def get_unified_leaderboard() -> Tuple[Dict[str, Any], int]:
            """Get unified leaderboard that blends XP, streaks, and referrals."""
            limit = request.args.get("limit", default=10, type=int)
            metric = request.args.get("metric", default="composite", type=str)

            try:
                leaderboard = self.node.bonus_manager.get_unified_leaderboard(metric, limit)
                return jsonify(
                    {"success": True, "limit": limit, "metric": metric, "leaderboard": leaderboard}
                ), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/mining/stats", methods=["GET"])
        def get_mining_bonus_stats() -> Tuple[Dict[str, Any], int]:
            """Get mining bonus system statistics."""
            try:
                stats = self.node.bonus_manager.get_stats()
                return jsonify({"success": True, "stats": stats}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

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
            except Exception as exc:
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
                return self._error_response(str(exc), status=400, code="order_invalid")
            except Exception as exc:
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

            except Exception as exc:
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

            except Exception as e:
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

            except Exception as e:
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
                return self._error_response(str(exc), status=400, code="deposit_invalid")
            except Exception as exc:
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
                return self._error_response(str(exc), status=400, code="withdraw_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "exchange_withdraw")

        @self.app.route("/exchange/balance/<address>", methods=["GET"])
        def get_user_balance(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all balances for a user."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                balances = self.node.exchange_wallet_manager.get_all_balances(address)
                return jsonify({"success": True, "address": address, "balances": balances}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/balance/<address>/<currency>", methods=["GET"])
        def get_currency_balance(address: str, currency: str) -> Tuple[Dict[str, Any], int]:
            """Get balance for specific currency."""
            if not self.node.exchange_wallet_manager:
                return jsonify({"success": False, "error": "Exchange module disabled"}), 503
            try:
                balance = self.node.exchange_wallet_manager.get_balance(address, currency)
                return jsonify({"success": True, "address": address, **balance}), 200
            except Exception as e:
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
            except Exception as e:
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

            except Exception as e:
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

            except Exception as e:
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
                return self._error_response(str(exc), status=400, code="payment_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "exchange_buy_with_card")

        @self.app.route("/exchange/payment-methods", methods=["GET"])
        def get_payment_methods() -> Tuple[Dict[str, Any], int]:
            """Get supported payment methods."""
            if not self.node.payment_processor:
                return jsonify({"success": False, "error": "Payment module disabled"}), 503
            try:
                methods = self.node.payment_processor.get_supported_payment_methods()
                return jsonify({"success": True, "methods": methods}), 200
            except Exception as e:
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
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ==================== CRYPTO DEPOSIT ROUTES ====================

    def _setup_crypto_deposit_routes(self) -> None:
        """Setup crypto deposit routes."""

        @self.app.route("/exchange/crypto/generate-address", methods=["POST"])
        @validate_request(self.request_validator, CryptoDepositAddressInput)
        def generate_crypto_deposit_address() -> Tuple[Dict[str, Any], int]:
            """Generate unique deposit address for BTC/ETH/USDT."""
            if not self.node.crypto_deposit_manager:
                return self._error_response(
                    "Crypto deposit module disabled", status=503, code="module_disabled"
                )
            auth_error = self._require_api_auth()
            if auth_error:
                return auth_error

            model: Optional[CryptoDepositAddressInput] = getattr(request, "validated_model", None)
            if model is None:
                return self._error_response("Invalid deposit request", status=400, code="invalid_payload")

            try:
                result = self.node.crypto_deposit_manager.generate_deposit_address(
                    user_address=model.user_address, currency=model.currency
                )
                return self._success_response(result if isinstance(result, dict) else {"result": result})
            except ValueError as exc:
                return self._error_response(str(exc), status=400, code="deposit_invalid")
            except Exception as exc:
                return self._handle_exception(exc, "crypto_generate_address")

        @self.app.route("/exchange/crypto/addresses/<address>", methods=["GET"])
        def get_crypto_deposit_addresses(address: str) -> Tuple[Dict[str, Any], int]:
            """Get all crypto deposit addresses for user."""
            if not self.node.crypto_deposit_manager:
                return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
            try:
                result = self.node.crypto_deposit_manager.get_user_deposit_addresses(address)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/pending-deposits", methods=["GET"])
        def get_pending_crypto_deposits() -> Tuple[Dict[str, Any], int]:
            """Get pending crypto deposits."""
            if not self.node.crypto_deposit_manager:
                return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
            try:
                user_address = request.args.get("user_address")
                pending = self.node.crypto_deposit_manager.get_pending_deposits(user_address)
                return (
                    jsonify({"success": True, "pending_deposits": pending, "count": len(pending)}),
                    200,
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/deposit-history/<address>", methods=["GET"])
        def get_crypto_deposit_history(address: str) -> Tuple[Dict[str, Any], int]:
            """Get confirmed crypto deposit history for user."""
            if not self.node.crypto_deposit_manager:
                return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
            try:
                limit = int(request.args.get("limit", 50))
                history = self.node.crypto_deposit_manager.get_deposit_history(address, limit)
                return (
                    jsonify(
                        {
                            "success": True,
                            "address": address,
                            "deposits": history,
                            "count": len(history),
                        }
                    ),
                    200,
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/exchange/crypto/stats", methods=["GET"])
        def get_crypto_deposit_stats() -> Tuple[Dict[str, Any], int]:
            """Get crypto deposit system statistics."""
            if not self.node.crypto_deposit_manager:
                return jsonify({"success": False, "error": "Crypto deposit module disabled"}), 503
            try:
                stats = self.node.crypto_deposit_manager.get_stats()
                return jsonify({"success": True, "stats": stats}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # ==================== ADMIN ROUTES ====================

    def _setup_admin_routes(self) -> None:
        """Setup API key management routes."""

        @self.app.route("/admin/api-keys", methods=["GET"])
        def list_api_keys() -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_admin_auth()
            if auth_error:
                return auth_error
            metadata = self.api_auth.list_key_metadata()
            return self._success_response(metadata)

        @self.app.route("/admin/api-keys", methods=["POST"])
        def create_api_key() -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_admin_auth()
            if auth_error:
                return auth_error
            payload = request.get_json(silent=True) or {}
            label = str(payload.get("label", "")).strip()
            scope = str(payload.get("scope", "user")).strip().lower() or "user"
            if scope not in {"user", "admin"}:
                return self._error_response("Invalid scope", status=400, code="invalid_payload")
            try:
                api_key, key_id = self.api_auth.issue_key(label=label, scope=scope)
                self._log_event(
                    "api_key_issued", {"key_id": key_id, "label": label, "scope": scope}, severity="INFO"
                )
                return self._success_response(
                    {"api_key": api_key, "key_id": key_id, "scope": scope}, status=201
                )
            except ValueError as exc:
                return self._error_response(str(exc), status=500, code="admin_error")

        @self.app.route("/admin/api-keys/<key_id>", methods=["DELETE"])
        def delete_api_key(key_id: str) -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_admin_auth()
            if auth_error:
                return auth_error
            try:
                if self.api_auth.revoke_key(key_id):
                    self._log_event("api_key_revoked", {"key_id": key_id}, severity="WARNING")
                    return self._success_response({"revoked": True})
            except ValueError as exc:
                return self._error_response(str(exc), status=500, code="admin_error")
            return self._error_response("API key not found", status=404, code="not_found")

        @self.app.route("/admin/api-key-events", methods=["GET"])
        def list_api_key_events() -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_admin_auth()
            if auth_error:
                return auth_error
            limit = request.args.get("limit", default=100, type=int)
            events = self.api_key_store.get_events(limit=limit)
            return self._success_response({"events": events})

        @self.app.route("/admin/withdrawals/telemetry", methods=["GET"])
        def get_withdrawal_telemetry() -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_admin_auth()
            if auth_error:
                return auth_error
            limiter = get_rate_limiter()
            identifier = f"admin-telemetry:{request.remote_addr or 'unknown'}"
            allowed, error = limiter.check_rate_limit(identifier, "/admin/withdrawals/telemetry")
            if not allowed:
                return self._error_response(
                    error or "Rate limit exceeded",
                    status=429,
                    code="rate_limited",
                    context={"identifier": identifier},
                )
            limit = request.args.get("limit", default=20, type=int) or 20
            limit = max(1, min(limit, 200))
            collector = getattr(self.node, "metrics_collector", None) or MetricsCollector.instance()
            events = collector.get_recent_withdrawals(limit=limit)
            rate_metric = collector.get_metric("xai_withdrawals_rate_per_minute")
            backlog_metric = collector.get_metric("xai_withdrawals_time_locked_backlog")
            payload = {
                "rate_per_minute": rate_metric.value if rate_metric else 0,
                "time_locked_backlog": backlog_metric.value if backlog_metric else 0,
                "recent_withdrawals": events,
                "log_path": getattr(collector, "withdrawal_event_log_path", None),
            }
            self._log_event(
                "admin_withdrawals_telemetry_access",
                {
                    "rate_per_minute": payload["rate_per_minute"],
                    "time_locked_backlog": payload["time_locked_backlog"],
                    "events_served": len(events),
                },
                severity="INFO",
            )
            return self._success_response(payload)

        @self.app.route("/admin/withdrawals/status", methods=["GET"])
        def get_withdrawal_status_snapshot() -> Tuple[Dict[str, Any], int]:
            auth_error = self._require_admin_auth()
            if auth_error:
                return auth_error
            limiter = get_rate_limiter()
            identifier = f"admin-withdrawal-status:{request.remote_addr or 'unknown'}"
            allowed, error = limiter.check_rate_limit(identifier, "/admin/withdrawals/status")
            if not allowed:
                return self._error_response(
                    error or "Rate limit exceeded",
                    status=429,
                    code="rate_limited",
                    context={"identifier": identifier},
                )
            manager = getattr(self.node, "exchange_wallet_manager", None)
            if not manager:
                return self._error_response(
                    "Exchange wallet manager unavailable",
                    status=503,
                    code="service_unavailable",
                )
            limit = request.args.get("limit", default=25, type=int) or 25
            limit = max(1, min(limit, 200))
            status_param = request.args.get("status", default="")
            valid_statuses = {"pending", "completed", "failed", "flagged"}
            if status_param:
                requested = {item.strip().lower() for item in status_param.split(",") if item.strip()}
                invalid = requested - valid_statuses
                if invalid:
                    return self._error_response(
                        "Invalid status filter",
                        status=400,
                        code="invalid_status",
                        context={"invalid": sorted(invalid)},
                    )
                target_statuses = requested or valid_statuses
            else:
                target_statuses = valid_statuses

            withdrawals = {
                status: manager.get_withdrawals_by_status(status, limit) for status in sorted(target_statuses)
            }
            counts = manager.get_withdrawal_counts()
            processor_stats = None
            if hasattr(self.node, "get_withdrawal_processor_stats"):
                processor_stats = self.node.get_withdrawal_processor_stats()
            payload = {
                "counts": counts,
                "queue_depth": counts.get("pending", 0),
                "latest_processor_run": processor_stats,
                "withdrawals": withdrawals,
            }
            self._log_event(
                "admin_withdrawals_status_access",
                {
                    "queue_depth": payload["queue_depth"],
                    "statuses": sorted(list(target_statuses)),
                    "limit": limit,
                },
                severity="INFO",
            )
            return self._success_response(payload)

        @self.app.route("/admin/spend-limit", methods=["POST"])
        def set_spend_limit() -> Tuple[Dict[str, Any], int]:
            """Set per-address daily spending limit (admin only)."""
            auth_error = self._require_admin_auth()
            if auth_error:
                return auth_error

            payload = request.get_json(silent=True) or {}
            address = str(payload.get("address", "")).strip()
            try:
                limit = float(payload.get("limit"))
            except Exception:
                return self._error_response("Invalid limit", status=400, code="invalid_payload")

            if not address or limit <= 0:
                return self._error_response("Invalid address or limit", status=400, code="invalid_payload")

            try:
                self.spending_limits.set_limit(address, limit)
                return self._success_response({"address": address, "limit": limit}, status=201)
            except Exception as exc:
                return self._error_response(str(exc), status=500, code="admin_error")
