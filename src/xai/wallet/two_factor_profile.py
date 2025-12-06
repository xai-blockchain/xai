"""
Persistent storage helpers for wallet two-factor authentication profiles.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from xai.security.two_factor_auth import TwoFactorAuthManager


@dataclass
class TwoFactorProfile:
    label: str
    secret: str
    backup_codes: List[str]
    issuer: str
    created_at: float = field(default_factory=lambda: time.time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "secret": self.secret,
            "backup_codes": self.backup_codes,
            "issuer": self.issuer,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TwoFactorProfile":
        return TwoFactorProfile(
            label=data["label"],
            secret=data["secret"],
            backup_codes=list(data.get("backup_codes", [])),
            issuer=data.get("issuer", "XAI Blockchain"),
            created_at=data.get("created_at", time.time()),
            metadata=data.get("metadata", {}),
        )


class TwoFactorProfileStore:
    """Filesystem-based persistence for 2FA profiles."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (Path.home() / ".xai" / "2fa_profiles")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, label: str) -> Path:
        sanitized = label.replace("/", "_")
        return self.base_dir / f"{sanitized}.json"

    def exists(self, label: str) -> bool:
        return self._profile_path(label).exists()

    def save(self, profile: TwoFactorProfile) -> None:
        path = self._profile_path(profile.label)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(profile.to_dict(), handle, indent=2)
        os.chmod(path, 0o600)

    def load(self, label: str) -> TwoFactorProfile:
        path = self._profile_path(label)
        if not path.exists():
            raise FileNotFoundError(f"2FA profile '{label}' not found")
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return TwoFactorProfile.from_dict(data)

    def delete(self, label: str) -> None:
        path = self._profile_path(label)
        if path.exists():
            path.unlink()

    def verify_code(
        self,
        label: str,
        code: str,
        manager: Optional[TwoFactorAuthManager] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify a TOTP or backup code against the stored profile.

        Returns:
            Tuple of (success, message). On success, message describes method used.
        """
        profile = self.load(label)
        manager = manager or TwoFactorAuthManager()

        if manager.verify_totp(profile.secret, code):
            return True, "TOTP verified"

        valid, updated = manager.verify_backup_code(code, profile.backup_codes)
        if valid and updated is not None:
            profile.backup_codes = updated
            self.save(profile)
            return True, "Backup code consumed"

        return False, None
