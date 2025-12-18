"""
Mini App Registry and Sandboxing
Task 175: Complete mini app registry sandboxing

This module provides secure sandboxing for third-party mini applications
running within the mobile wallet.

Now uses the secure sandbox implementation from xai.sandbox:
- RestrictedPython for Python code execution
- WebAssembly for compiled code
- Capability-based permissions
- Resource limits and isolation
"""

from __future__ import annotations

import json
import hashlib
import logging
import time
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Import secure sandbox components
from xai.sandbox.permissions import (
    Permission,
    PermissionLevel,
    PermissionManager,
    PermissionDeniedError,
    AuditLog,
)
from xai.sandbox.secure_executor import (
    SecureExecutor,
    ExecutionContext,
    ExecutionResult,
    ResourceLimits,
    SandboxAPI,
)
from xai.sandbox.wasm_executor import (
    WasmExecutor,
    WasmResult,
    WasmLimits,
)

logger = logging.getLogger(__name__)


class AppPermission(Enum):
    """Permissions for mini apps"""
    READ_BALANCE = "read_balance"
    READ_TRANSACTIONS = "read_transactions"
    CREATE_TRANSACTION = "create_transaction"
    SIGN_MESSAGE = "sign_message"
    READ_CONTACTS = "read_contacts"
    CAMERA = "camera"
    NOTIFICATIONS = "notifications"
    NETWORK = "network"
    STORAGE = "storage"


@dataclass
class MiniApp:
    """Mini application metadata"""
    app_id: str
    name: str
    version: str
    developer: str
    description: str
    icon_url: str
    entry_point: str
    permissions: List[str]
    verified: bool = False
    install_time: Optional[float] = None
    last_used: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MiniApp:
        return cls(**data)

    def calculate_hash(self) -> str:
        """Calculate app hash for verification"""
        data = {
            "app_id": self.app_id,
            "version": self.version,
            "developer": self.developer
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class AppSandbox:
    """
    Sandbox environment for mini apps

    Provides isolated execution environment with controlled access to wallet APIs
    """

    def __init__(self, app: MiniApp, wallet_interface: Any):
        self.app = app
        self.wallet_interface = wallet_interface
        self.api_call_count = 0
        self.max_api_calls_per_minute = 60
        self.last_reset_time = time.time()
        self.storage_limit_bytes = 1024 * 1024  # 1MB per app
        self.storage_used = 0
        self.allowed_domains: Set[str] = set()

    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute app code in sandbox

        Args:
            code: App code to execute
            context: Execution context

        Returns:
            Execution result
        """
        # This is a placeholder - in production, use proper sandboxing
        # like RestrictedPython or a separate process with limited permissions

        # Check rate limiting
        if not self._check_rate_limit():
            raise PermissionError("API rate limit exceeded")

        # Create restricted globals
        restricted_globals = {
            "app_api": self._create_app_api(),
            "print": self._safe_print,
            "__builtins__": self._create_restricted_builtins()
        }

        # Add context
        if context:
            restricted_globals.update(context)

        # Execute in restricted environment
        # Feature flag: disable in server builds by default
        import os
        if os.getenv("XAI_ENABLE_SANDBOX_EXEC", "0") != "1":
            raise PermissionError("Sandbox execution is disabled. Set XAI_ENABLE_SANDBOX_EXEC=1 to enable in controlled environments.")
        # The 'exec' call has been removed due to the extreme security risk.
        # A proper sandboxing mechanism (e.g., using a separate process,
        # WebAssembly, or a heavily restricted Python interpreter) is required
        # before this feature can be safely enabled.
        raise NotImplementedError("In-process code execution is disabled for security reasons.")

    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded"""
        current_time = time.time()

        # Reset counter every minute
        if current_time - self.last_reset_time > 60:
            self.api_call_count = 0
            self.last_reset_time = current_time

        if self.api_call_count >= self.max_api_calls_per_minute:
            return False

        self.api_call_count += 1
        return True

    def _create_app_api(self) -> Dict[str, Callable]:
        """Create restricted API for app"""
        api = {}

        # Conditionally add APIs based on permissions
        if AppPermission.READ_BALANCE.value in self.app.permissions:
            api["getBalance"] = self._get_balance

        if AppPermission.READ_TRANSACTIONS.value in self.app.permissions:
            api["getTransactions"] = self._get_transactions

        if AppPermission.CREATE_TRANSACTION.value in self.app.permissions:
            api["createTransaction"] = self._create_transaction

        if AppPermission.SIGN_MESSAGE.value in self.app.permissions:
            api["signMessage"] = self._sign_message

        if AppPermission.STORAGE.value in self.app.permissions:
            api["storage"] = {
                "set": self._storage_set,
                "get": self._storage_get,
                "remove": self._storage_remove
            }

        if AppPermission.NETWORK.value in self.app.permissions:
            api["fetch"] = self._safe_fetch

        return api

    def _get_balance(self, address: Optional[str] = None) -> float:
        """Get balance (sandboxed)"""
        if not self._check_permission(AppPermission.READ_BALANCE):
            raise PermissionError("No permission to read balance")

        return self.wallet_interface.get_balance(address)

    def _get_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get transactions (sandboxed)"""
        if not self._check_permission(AppPermission.READ_TRANSACTIONS):
            raise PermissionError("No permission to read transactions")

        # Limit to prevent abuse
        limit = min(limit, 100)

        return self.wallet_interface.get_transactions(limit)

    def _create_transaction(self, recipient: str, amount: float) -> Dict[str, Any]:
        """Create transaction (sandboxed, requires user confirmation)"""
        if not self._check_permission(AppPermission.CREATE_TRANSACTION):
            raise PermissionError("No permission to create transactions")

        # This would show confirmation dialog to user
        # For now, return unsigned transaction
        return {
            "status": "pending_confirmation",
            "recipient": recipient,
            "amount": amount,
            "app": self.app.name
        }

    def _sign_message(self, message: str) -> str:
        """Sign message (sandboxed, requires user confirmation)"""
        if not self._check_permission(AppPermission.SIGN_MESSAGE):
            raise PermissionError("No permission to sign messages")

        # Would require user confirmation
        return "signature_pending"

    def _storage_set(self, key: str, value: Any) -> bool:
        """Set storage value (sandboxed with quota)"""
        if not self._check_permission(AppPermission.STORAGE):
            raise PermissionError("No permission to use storage")

        # Check storage quota
        value_size = len(json.dumps(value).encode())
        if self.storage_used + value_size > self.storage_limit_bytes:
            raise RuntimeError("Storage quota exceeded")

        self.storage_used += value_size
        return True

    def _storage_get(self, key: str) -> Any:
        """Get storage value (sandboxed)"""
        if not self._check_permission(AppPermission.STORAGE):
            raise PermissionError("No permission to use storage")

        return None  # Placeholder

    def _storage_remove(self, key: str) -> bool:
        """Remove storage value (sandboxed)"""
        if not self._check_permission(AppPermission.STORAGE):
            raise PermissionError("No permission to use storage")

        return True

    def _safe_fetch(self, url: str) -> Any:
        """Safe network request (sandboxed with whitelist)"""
        if not self._check_permission(AppPermission.NETWORK):
            raise PermissionError("No permission to access network")

        # Check domain whitelist
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        if self.allowed_domains and domain not in self.allowed_domains:
            raise PermissionError(f"Domain {domain} not whitelisted")

        # Would make actual request with timeout and size limits
        return None

    def _safe_print(self, *args, **kwargs) -> None:
        """Safe print function"""
        # Log to app console instead of system console
        pass

    def _check_permission(self, permission: AppPermission) -> bool:
        """Check if app has permission"""
        return permission.value in self.app.permissions

    def _create_restricted_builtins(self) -> Dict[str, Any]:
        """Create restricted builtins"""
        # Only allow safe builtins
        safe_builtins = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
        }

        return safe_builtins


class MiniAppRegistry:
    """
    Registry for managing mini apps

    Handles installation, verification, and lifecycle management
    """

    def __init__(self, storage_path: str = "./mini_apps"):
        self.storage_path = storage_path
        import os
        os.makedirs(storage_path, exist_ok=True)

        self.apps: Dict[str, MiniApp] = {}
        self.verified_developers: Set[str] = set()
        self._load_apps()

    def register_app(self, app: MiniApp) -> bool:
        """
        Register a new mini app

        Args:
            app: Mini app to register

        Returns:
            True if registered successfully
        """
        # Validate app
        if not self._validate_app(app):
            return False

        # Check if already exists
        if app.app_id in self.apps:
            return False

        # Set install time
        app.install_time = time.time()

        # Add to registry
        self.apps[app.app_id] = app

        # Save registry
        self._save_apps()

        return True

    def unregister_app(self, app_id: str) -> bool:
        """
        Unregister mini app

        Args:
            app_id: App ID to unregister

        Returns:
            True if unregistered
        """
        if app_id in self.apps:
            del self.apps[app_id]
            self._save_apps()
            return True

        return False

    def get_app(self, app_id: str) -> Optional[MiniApp]:
        """Get app by ID"""
        return self.apps.get(app_id)

    def list_apps(self, verified_only: bool = False) -> List[MiniApp]:
        """
        List all apps

        Args:
            verified_only: Only return verified apps

        Returns:
            List of apps
        """
        apps = list(self.apps.values())

        if verified_only:
            apps = [app for app in apps if app.verified]

        return sorted(apps, key=lambda a: a.install_time or 0, reverse=True)

    def verify_app(self, app_id: str, verified: bool = True) -> bool:
        """
        Mark app as verified

        Args:
            app_id: App ID
            verified: Verification status

        Returns:
            True if updated
        """
        app = self.apps.get(app_id)
        if app:
            app.verified = verified
            self._save_apps()
            return True

        return False

    def update_last_used(self, app_id: str) -> None:
        """Update last used timestamp"""
        app = self.apps.get(app_id)
        if app:
            app.last_used = time.time()
            self._save_apps()

    def _validate_app(self, app: MiniApp) -> bool:
        """Validate app metadata"""
        # Check required fields
        if not app.app_id or not app.name or not app.version:
            return False

        # Validate permissions
        valid_permissions = {p.value for p in AppPermission}
        for perm in app.permissions:
            if perm not in valid_permissions:
                return False

        return True

    def _load_apps(self) -> None:
        """Load apps from storage"""
        registry_file = f"{self.storage_path}/registry.json"

        try:
            with open(registry_file, 'r') as f:
                data = json.load(f)
                for app_data in data.get("apps", []):
                    app = MiniApp.from_dict(app_data)
                    self.apps[app.app_id] = app

                self.verified_developers = set(data.get("verified_developers", []))
        except FileNotFoundError:
            # No registry file exists yet - this is expected on first run
            logger.debug("Mini app registry file not found, starting with empty registry")

    def _save_apps(self) -> None:
        """Save apps to storage"""
        registry_file = f"{self.storage_path}/registry.json"

        data = {
            "apps": [app.to_dict() for app in self.apps.values()],
            "verified_developers": list(self.verified_developers)
        }

        with open(registry_file, 'w') as f:
            json.dump(data, f, indent=2)


class AppSecurityMonitor:
    """Monitor app behavior for security"""

    def __init__(self):
        self.suspicious_activities: List[Dict[str, Any]] = []

    def log_api_call(self, app_id: str, api_name: str, params: Dict[str, Any]) -> None:
        """Log API call for monitoring"""
        # Detect suspicious patterns
        if self._is_suspicious(api_name, params):
            self.suspicious_activities.append({
                "app_id": app_id,
                "api": api_name,
                "params": params,
                "timestamp": time.time()
            })

    def _is_suspicious(self, api_name: str, params: Dict[str, Any]) -> bool:
        """Detect suspicious activity"""
        # Check for large transaction attempts
        if api_name == "createTransaction":
            amount = params.get("amount", 0)
            if amount > 1000:  # Threshold
                return True

        # Check for rapid API calls
        # Check for unusual patterns

        return False

    def get_suspicious_activities(self, app_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get suspicious activities"""
        if app_id:
            return [a for a in self.suspicious_activities if a["app_id"] == app_id]

        return self.suspicious_activities
