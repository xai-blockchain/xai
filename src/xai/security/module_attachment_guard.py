"""
Centralized module attachment guard.

Provides allowlist + path validation to ensure only trusted modules are
attached at runtime. Guards against path traversal, shadowed modules,
and missing hardening flags.
"""

from __future__ import annotations

import importlib
import importlib.util
import sysconfig
from pathlib import Path

class ModuleAttachmentError(RuntimeError):
    """Raised when a module fails attachment validation."""

class ModuleAttachmentGuard:
    """Validate that modules originate from trusted locations and are allowlisted."""

    def __init__(
        self,
        allowed_modules: Iterable[str],
        *,
        trusted_base: Path | None = None,
        trusted_stdlib: Path | None = None,
        require_attribute: str | None = None,
    ) -> None:
        self.allowed_modules: set[str] = {m.strip() for m in allowed_modules if m}
        self.require_attribute = require_attribute
        self.trusted_base = Path(trusted_base).resolve() if trusted_base else Path(__file__).resolve().parents[2]
        stdlib_path = trusted_stdlib or Path(sysconfig.get_paths()["stdlib"])
        self.trusted_stdlib = Path(stdlib_path).resolve()

    def verify_module(self, module_name: str) -> None:
        """Import and validate a module against allowlist and trusted paths."""
        if module_name not in self.allowed_modules:
            raise ModuleAttachmentError(f"Module {module_name!r} is not allowlisted for attachment")

        spec = importlib.util.find_spec(module_name)
        if spec is None:
            raise ModuleAttachmentError(f"Module {module_name!r} not found for attachment")

        module = importlib.import_module(module_name)
        origin = getattr(module, "__file__", None) or spec.origin

        if origin and origin not in {"built-in", "frozen"}:
            origin_path = Path(origin)
            if origin_path.is_symlink():
                raise ModuleAttachmentError(f"Module {module_name!r} resolved via symlink {origin_path}")

            path = origin_path.resolve()
            if not self._is_trusted_path(path):
                raise ModuleAttachmentError(
                    f"Module {module_name!r} resolved to untrusted path {path}"
                )
            if self._is_world_writable(path) or self._is_world_writable(path.parent):
                raise ModuleAttachmentError(
                    f"Module {module_name!r} located at world-writable path {path}"
                )

        if self.require_attribute:
            if not getattr(module, self.require_attribute, False):
                raise ModuleAttachmentError(
                    f"Module {module_name!r} missing required attribute {self.require_attribute!r}"
                )

    def require_all(self) -> None:
        """Validate all allowlisted modules up-front."""
        for module_name in sorted(self.allowed_modules):
            self.verify_module(module_name)

    def _is_trusted_path(self, path: Path) -> bool:
        if self.trusted_base and (path == self.trusted_base or self.trusted_base in path.parents):
            return True
        if self.trusted_stdlib and (path == self.trusted_stdlib or self.trusted_stdlib in path.parents):
            return True
        return False

    @staticmethod
    def _is_world_writable(path: Path) -> bool:
        try:
            mode = path.stat().st_mode
            return bool(mode & 0o002)
        except (OSError, ValueError):
            return False
