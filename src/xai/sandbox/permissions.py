"""
Capability-Based Permission System for Mini-Apps

Implements a fine-grained permission model with:
- Permission levels (none, read, write, execute)
- User approval tracking
- Audit logging of all operations
- Time-limited grants
- Revocation support
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for mini-app capabilities"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


class Permission(Enum):
    """Available permissions for mini-apps"""
    # Blockchain permissions
    READ_BALANCE = "read_balance"
    READ_TRANSACTIONS = "read_transactions"
    READ_BLOCKCHAIN = "read_blockchain"
    SIGN_TRANSACTIONS = "sign_transactions"
    SEND_TRANSACTIONS = "send_transactions"

    # Network permissions
    NETWORK_HTTP = "network_http"
    NETWORK_HTTPS = "network_https"
    NETWORK_WEBSOCKET = "network_websocket"
    NETWORK_ALL = "network_all"

    # Storage permissions
    STORAGE_READ = "storage_read"
    STORAGE_WRITE = "storage_write"
    STORAGE_DELETE = "storage_delete"

    # System permissions
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    PROCESS_SPAWN = "process_spawn"

    # UI permissions
    CAMERA = "camera"
    MICROPHONE = "microphone"
    GEOLOCATION = "geolocation"
    NOTIFICATIONS = "notifications"
    CONTACTS = "contacts"

    # Dangerous permissions (require explicit user approval)
    KEYRING_ACCESS = "keyring_access"
    PRIVATE_KEY_EXPORT = "private_key_export"


class PermissionDeniedError(Exception):
    """Raised when a permission is denied"""
    def __init__(self, permission: Permission, app_id: str, reason: str = ""):
        self.permission = permission
        self.app_id = app_id
        self.reason = reason
        super().__init__(
            f"Permission {permission.value} denied for app {app_id}"
            + (f": {reason}" if reason else "")
        )


@dataclass
class PermissionGrant:
    """A granted permission with metadata"""
    permission: Permission
    level: PermissionLevel
    granted_at: float
    expires_at: Optional[float] = None
    user_approved: bool = False
    approval_timestamp: Optional[float] = None
    restrictions: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if grant is still valid"""
        if not self.user_approved:
            return False

        if self.expires_at is not None:
            return time.time() < self.expires_at

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        data = asdict(self)
        data["permission"] = self.permission.value
        data["level"] = self.level.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PermissionGrant:
        """Deserialize from dictionary"""
        data = data.copy()
        data["permission"] = Permission(data["permission"])
        data["level"] = PermissionLevel(data["level"])
        return cls(**data)


@dataclass
class AuditLogEntry:
    """Audit log entry for permission usage"""
    timestamp: float
    app_id: str
    permission: Permission
    action: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    user_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        data = asdict(self)
        data["permission"] = self.permission.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditLogEntry:
        """Deserialize from dictionary"""
        data = data.copy()
        data["permission"] = Permission(data["permission"])
        return cls(**data)


class AuditLog:
    """
    Audit logging for all sandbox operations

    Provides immutable audit trail of all permission usage
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path
        self.entries: List[AuditLogEntry] = []
        self.max_memory_entries = 10000

        if log_path:
            self._load_from_disk()

    def log(
        self,
        app_id: str,
        permission: Permission,
        action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        user_address: Optional[str] = None,
    ) -> None:
        """Log a permission usage event"""
        entry = AuditLogEntry(
            timestamp=time.time(),
            app_id=app_id,
            permission=permission,
            action=action,
            success=success,
            details=details or {},
            user_address=user_address,
        )

        self.entries.append(entry)

        # Log to Python logger
        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"Sandbox audit: app={app_id} permission={permission.value} "
            f"action={action} success={success}",
            extra={
                "event": "sandbox.permission_usage",
                "app_id": app_id,
                "permission": permission.value,
                "action": action,
                "success": success,
                "user_address": user_address,
            }
        )

        # Keep memory bounded
        if len(self.entries) > self.max_memory_entries:
            self._flush_to_disk()

        # Persist to disk if configured
        if self.log_path:
            self._append_to_disk(entry)

    def get_entries(
        self,
        app_id: Optional[str] = None,
        permission: Optional[Permission] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 1000,
    ) -> List[AuditLogEntry]:
        """Query audit log entries with filters"""
        filtered = self.entries

        if app_id:
            filtered = [e for e in filtered if e.app_id == app_id]

        if permission:
            filtered = [e for e in filtered if e.permission == permission]

        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]

        # Sort by timestamp descending (newest first)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        return filtered[:limit]

    def get_suspicious_activity(self, app_id: str, threshold: int = 10) -> List[AuditLogEntry]:
        """
        Get potentially suspicious activity

        Detects:
        - High frequency of permission denials
        - Unusual permission combinations
        - After-hours activity
        """
        recent_time = time.time() - 3600  # Last hour
        entries = self.get_entries(app_id=app_id, start_time=recent_time)

        # Count denials
        denials = [e for e in entries if not e.success]

        if len(denials) >= threshold:
            return denials

        return []

    def _flush_to_disk(self) -> None:
        """Flush old entries to disk and clear from memory"""
        if not self.log_path:
            # Just truncate if no disk storage
            self.entries = self.entries[-1000:]
            return

        # Keep recent entries in memory
        self.entries = self.entries[-1000:]

    def _append_to_disk(self, entry: AuditLogEntry) -> None:
        """Append single entry to disk log"""
        if not self.log_path:
            return

        try:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _load_from_disk(self) -> None:
        """Load recent entries from disk"""
        if not self.log_path or not self.log_path.exists():
            return

        try:
            with open(self.log_path, 'r') as f:
                # Load last N lines
                lines = f.readlines()
                for line in lines[-self.max_memory_entries:]:
                    try:
                        data = json.loads(line)
                        self.entries.append(AuditLogEntry.from_dict(data))
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")


class PermissionManager:
    """
    Manages permissions for mini-apps

    Features:
    - Per-app permission grants
    - User approval tracking
    - Time-limited permissions
    - Audit logging
    - Revocation
    """

    # Permissions that always require user approval
    DANGEROUS_PERMISSIONS = {
        Permission.SIGN_TRANSACTIONS,
        Permission.SEND_TRANSACTIONS,
        Permission.KEYRING_ACCESS,
        Permission.PRIVATE_KEY_EXPORT,
        Permission.FILESYSTEM_WRITE,
        Permission.PROCESS_SPAWN,
    }

    # Permissions that can be auto-granted for verified apps
    SAFE_PERMISSIONS = {
        Permission.READ_BALANCE,
        Permission.READ_TRANSACTIONS,
        Permission.READ_BLOCKCHAIN,
        Permission.STORAGE_READ,
        Permission.STORAGE_WRITE,
        Permission.NOTIFICATIONS,
    }

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        audit_log: Optional[AuditLog] = None,
    ):
        self.storage_path = storage_path
        self.audit_log = audit_log or AuditLog()

        # app_id -> {permission -> grant}
        self.grants: Dict[str, Dict[Permission, PermissionGrant]] = {}

        # Verified app IDs (can auto-grant safe permissions)
        self.verified_apps: Set[str] = set()

        if storage_path:
            self._load_from_disk()

    def request_permission(
        self,
        app_id: str,
        permission: Permission,
        level: PermissionLevel = PermissionLevel.READ,
        duration_seconds: Optional[int] = None,
        auto_approve: bool = False,
    ) -> bool:
        """
        Request a permission for an app

        Args:
            app_id: Application identifier
            permission: Permission being requested
            level: Permission level (read/write/execute)
            duration_seconds: Grant duration (None = permanent)
            auto_approve: Auto-approve if app is verified

        Returns:
            True if granted, False otherwise
        """
        # Check if already granted and valid
        if self.has_permission(app_id, permission, level):
            return True

        # Check if can auto-approve
        can_auto_approve = (
            auto_approve
            and app_id in self.verified_apps
            and permission in self.SAFE_PERMISSIONS
        )

        # Create grant
        expires_at = None
        if duration_seconds:
            expires_at = time.time() + duration_seconds

        grant = PermissionGrant(
            permission=permission,
            level=level,
            granted_at=time.time(),
            expires_at=expires_at,
            user_approved=can_auto_approve,
            approval_timestamp=time.time() if can_auto_approve else None,
        )

        # Store grant
        if app_id not in self.grants:
            self.grants[app_id] = {}

        self.grants[app_id][permission] = grant

        # Log the request
        self.audit_log.log(
            app_id=app_id,
            permission=permission,
            action="request",
            success=can_auto_approve,
            details={
                "level": level.value,
                "auto_approved": can_auto_approve,
                "duration_seconds": duration_seconds,
            }
        )

        # Save to disk
        if self.storage_path:
            self._save_to_disk()

        return can_auto_approve

    def approve_permission(
        self,
        app_id: str,
        permission: Permission,
        user_address: str,
    ) -> None:
        """
        User approves a pending permission request

        Args:
            app_id: Application identifier
            permission: Permission to approve
            user_address: Address of approving user
        """
        if app_id not in self.grants or permission not in self.grants[app_id]:
            raise ValueError(f"No pending request for {permission.value}")

        grant = self.grants[app_id][permission]
        grant.user_approved = True
        grant.approval_timestamp = time.time()

        # Log approval
        self.audit_log.log(
            app_id=app_id,
            permission=permission,
            action="approve",
            success=True,
            user_address=user_address,
        )

        # Save to disk
        if self.storage_path:
            self._save_to_disk()

    def revoke_permission(
        self,
        app_id: str,
        permission: Permission,
        user_address: Optional[str] = None,
    ) -> None:
        """Revoke a granted permission"""
        if app_id in self.grants and permission in self.grants[app_id]:
            del self.grants[app_id][permission]

            # Log revocation
            self.audit_log.log(
                app_id=app_id,
                permission=permission,
                action="revoke",
                success=True,
                user_address=user_address,
            )

            # Save to disk
            if self.storage_path:
                self._save_to_disk()

    def revoke_all_permissions(self, app_id: str) -> None:
        """Revoke all permissions for an app"""
        if app_id in self.grants:
            permissions = list(self.grants[app_id].keys())
            del self.grants[app_id]

            # Log bulk revocation
            for permission in permissions:
                self.audit_log.log(
                    app_id=app_id,
                    permission=permission,
                    action="revoke_all",
                    success=True,
                )

            # Save to disk
            if self.storage_path:
                self._save_to_disk()

    def has_permission(
        self,
        app_id: str,
        permission: Permission,
        level: PermissionLevel = PermissionLevel.READ,
    ) -> bool:
        """Check if app has a specific permission"""
        if app_id not in self.grants:
            return False

        grant = self.grants[app_id].get(permission)
        if not grant:
            return False

        # Check if valid
        if not grant.is_valid():
            return False

        # Check level
        if level == PermissionLevel.EXECUTE and grant.level != PermissionLevel.EXECUTE:
            return False

        if level == PermissionLevel.WRITE and grant.level == PermissionLevel.READ:
            return False

        return True

    def check_permission(
        self,
        app_id: str,
        permission: Permission,
        level: PermissionLevel = PermissionLevel.READ,
        action: str = "access",
    ) -> None:
        """
        Check permission and raise if denied

        Args:
            app_id: Application identifier
            permission: Permission to check
            level: Permission level required
            action: Action being performed (for audit log)

        Raises:
            PermissionDeniedError: If permission is denied
        """
        if not self.has_permission(app_id, permission, level):
            # Log denial
            self.audit_log.log(
                app_id=app_id,
                permission=permission,
                action=action,
                success=False,
                details={"level": level.value, "reason": "permission_denied"}
            )

            raise PermissionDeniedError(
                permission=permission,
                app_id=app_id,
                reason=f"Permission not granted or invalid",
            )

        # Log successful access
        self.audit_log.log(
            app_id=app_id,
            permission=permission,
            action=action,
            success=True,
            details={"level": level.value}
        )

    def get_app_permissions(self, app_id: str) -> Dict[Permission, PermissionGrant]:
        """Get all permissions for an app"""
        if app_id not in self.grants:
            return {}

        # Return only valid grants
        return {
            perm: grant
            for perm, grant in self.grants[app_id].items()
            if grant.is_valid()
        }

    def verify_app(self, app_id: str) -> None:
        """Mark app as verified (allows auto-grant of safe permissions)"""
        self.verified_apps.add(app_id)

        if self.storage_path:
            self._save_to_disk()

    def unverify_app(self, app_id: str) -> None:
        """Remove verification status"""
        self.verified_apps.discard(app_id)

        if self.storage_path:
            self._save_to_disk()

    def _save_to_disk(self) -> None:
        """Save permissions to disk"""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "grants": {
                app_id: {
                    perm.value: grant.to_dict()
                    for perm, grant in grants.items()
                }
                for app_id, grants in self.grants.items()
            },
            "verified_apps": list(self.verified_apps),
        }

        try:
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save permissions: {e}")

    def _load_from_disk(self) -> None:
        """Load permissions from disk"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Load grants
            for app_id, grants_data in data.get("grants", {}).items():
                self.grants[app_id] = {}
                for perm_value, grant_data in grants_data.items():
                    try:
                        permission = Permission(perm_value)
                        grant = PermissionGrant.from_dict(grant_data)
                        self.grants[app_id][permission] = grant
                    except Exception as e:
                        logger.warning(f"Failed to load grant: {e}")

            # Load verified apps
            self.verified_apps = set(data.get("verified_apps", []))

        except Exception as e:
            logger.error(f"Failed to load permissions: {e}")
