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

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# Import secure sandbox components
from xai.sandbox.permissions import (
    AuditLog,
    Permission,
    PermissionDeniedError,
    PermissionLevel,
    PermissionManager,
)
from xai.sandbox.secure_executor import (
    ExecutionContext,
    ExecutionResult,
    ResourceLimits,
    SandboxAPI,
    SecureExecutor,
)
from xai.sandbox.wasm_executor import (
    WasmExecutor,
    WasmLimits,
    WasmResult,
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
    permissions: list[str]
    verified: bool = False
    install_time: float | None = None
    last_used: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MiniApp:
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

    Provides isolated execution environment with controlled access to wallet APIs.

    Now uses secure execution backends:
    - SecureExecutor for Python code (RestrictedPython)
    - WasmExecutor for WebAssembly modules
    - PermissionManager for capability-based security
    """

    def __init__(
        self,
        app: MiniApp,
        wallet_interface: Any,
        permission_manager: PermissionManager | None = None,
        storage_path: Path | None = None,
    ):
        self.app = app
        self.wallet_interface = wallet_interface

        # Legacy rate limiting (now also enforced by permission system)
        self.api_call_count = 0
        self.max_api_calls_per_minute = 60
        self.last_reset_time = time.time()
        self.storage_limit_bytes = 1024 * 1024  # 1MB per app
        self.storage_used = 0
        self.allowed_domains: set[str] = set()

        # New secure sandbox components
        self.permission_manager = permission_manager or PermissionManager(
            storage_path=storage_path / "permissions.json" if storage_path else None,
            audit_log=AuditLog(
                log_path=storage_path / "audit.log" if storage_path else None
            )
        )

        # Secure executors
        self.python_executor = SecureExecutor(
            limits=ResourceLimits(
                max_memory_mb=128,
                max_cpu_seconds=5,
                max_wall_time_seconds=10,
                max_output_bytes=100 * 1024,  # 100KB
            ),
            use_subprocess=False,  # Use RestrictedPython by default
        )

        self.wasm_executor = WasmExecutor(
            limits=WasmLimits(
                max_memory_pages=256,  # 16MB
                max_execution_fuel=1000000,
                max_wall_time_seconds=10,
            )
        )

        # Create sandbox API
        self.sandbox_api = SandboxAPI(
            app_id=app.app_id,
            permission_manager=self.permission_manager,
            wallet_interface=wallet_interface,
        )

    def execute(
        self,
        code: str,
        language: str = "python",
        entry_point: str = "main",
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult | WasmResult:
        """
        Execute app code in secure sandbox

        Args:
            code: App code to execute (Python source or WASM bytes)
            language: Code language ("python" or "wasm")
            entry_point: Entry point function name
            context: Execution context/arguments

        Returns:
            Execution result

        Raises:
            PermissionError: If sandbox execution is disabled
            NotImplementedError: If language is not supported
        """
        # Check rate limiting
        if not self._check_rate_limit():
            raise PermissionError("API rate limit exceeded")

        # Execute based on language
        if language == "python":
            return self._execute_python(code, entry_point, context or {})
        elif language == "wasm":
            return self._execute_wasm(code, entry_point, context or {})
        else:
            raise NotImplementedError(f"Language {language} not supported")

    def _execute_python(
        self,
        code: str,
        entry_point: str,
        arguments: dict[str, Any],
    ) -> ExecutionResult:
        """Execute Python code using SecureExecutor"""
        # Map old AppPermission to new Permission enum
        allowed_imports = set()
        if "storage" in self.app.permissions:
            allowed_imports.add("json")

        # Create execution context
        exec_context = ExecutionContext(
            app_id=self.app.app_id,
            code=code,
            entry_point=entry_point,
            arguments=arguments,
            allowed_imports=allowed_imports,
            allowed_network_domains=self.allowed_domains,
            api_functions={
                "get_balance": self.sandbox_api.get_balance,
                "get_transactions": self.sandbox_api.get_transactions,
                "create_transaction": self.sandbox_api.create_transaction,
            }
        )

        # Execute
        return self.python_executor.execute(exec_context)

    def _execute_wasm(
        self,
        wasm_bytes: bytes,
        entry_point: str,
        arguments: dict[str, Any],
    ) -> WasmResult:
        """Execute WebAssembly module"""
        # Convert wasm_bytes (might be passed as string in old code)
        if isinstance(wasm_bytes, str):
            wasm_bytes = wasm_bytes.encode('latin1')

        # Execute WASM
        return self.wasm_executor.execute(
            wasm_bytes=wasm_bytes,
            function_name=entry_point,
            arguments=list(arguments.values()),
        )

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

    def _create_app_api(self) -> dict[str, Callable]:
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

    def _get_balance(self, address: str | None = None) -> float:
        """Get balance (sandboxed)"""
        if not self._check_permission(AppPermission.READ_BALANCE):
            raise PermissionError("No permission to read balance")

        return self.wallet_interface.get_balance(address)

    def _get_transactions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get transactions (sandboxed)"""
        if not self._check_permission(AppPermission.READ_TRANSACTIONS):
            raise PermissionError("No permission to read transactions")

        # Limit to prevent abuse
        limit = min(limit, 100)

        return self.wallet_interface.get_transactions(limit)

    def _create_transaction(self, recipient: str, amount: float) -> dict[str, Any]:
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

    def _create_restricted_builtins(self) -> dict[str, Any]:
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

        self.apps: dict[str, MiniApp] = {}
        self.verified_developers: set[str] = set()
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

    def get_app(self, app_id: str) -> MiniApp | None:
        """Get app by ID"""
        return self.apps.get(app_id)

    def list_apps(self, verified_only: bool = False) -> list[MiniApp]:
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
        self.suspicious_activities: list[dict[str, Any]] = []

    def log_api_call(self, app_id: str, api_name: str, params: dict[str, Any]) -> None:
        """Log API call for monitoring"""
        # Detect suspicious patterns
        if self._is_suspicious(api_name, params):
            self.suspicious_activities.append({
                "app_id": app_id,
                "api": api_name,
                "params": params,
                "timestamp": time.time()
            })

    def _is_suspicious(self, api_name: str, params: dict[str, Any]) -> bool:
        """Detect suspicious activity"""
        # Check for large transaction attempts
        if api_name == "createTransaction":
            amount = params.get("amount", 0)
            if amount > 1000:  # Threshold
                return True

        # Check for rapid API calls
        # Check for unusual patterns

        return False

    def get_suspicious_activities(self, app_id: str | None = None) -> list[dict[str, Any]]:
        """Get suspicious activities"""
        if app_id:
            return [a for a in self.suspicious_activities if a["app_id"] == app_id]

        return self.suspicious_activities
