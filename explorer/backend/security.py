"""API authentication utilities for the explorer backend."""

from __future__ import annotations

import hmac
import logging
import os
from typing import Any, Callable

from fastapi import Depends, Header, HTTPException, Query, WebSocket, status

logger = logging.getLogger(__name__)

class APIKeyAuthError(RuntimeError):
    """Raised when API key validation fails."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(message)

class APIAuthConfig:
    """Configuration wrapper for API authentication settings."""

    def __init__(
        self,
        *,
        require_api_key: bool = False,
        key_file: str | None = None,
        env_var: str = "EXPLORER_API_KEY",
        initial_keys: Sequence[str] | None = None,
    ) -> None:
        self.require_api_key = require_api_key
        self.key_file = key_file
        self.env_var = env_var
        self._initial_keys = {k.strip() for k in (initial_keys or []) if k}
        self._keys = set(self._initial_keys)
        self._load_keys()

    def _load_keys(self) -> None:
        """Pull keys from environment and optional file into memory."""
        self._keys = set(self._initial_keys)
        env_key = os.getenv(self.env_var)
        if env_key:
            self._keys.add(env_key.strip())

        path = os.path.expanduser(self.key_file) if self.key_file else None
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            self._keys.add(line)
            except OSError as exc:
                logger.error("Failed to load explorer API keys from %s: %s", path, exc)

    def reload(self) -> None:
        """Reload key material from configured sources."""
        self._load_keys()

    def add_keys(self, keys: Iterable[str]) -> None:
        """Add in-memory keys (useful for tests)."""
        for key in keys:
            if key:
                self._keys.add(key.strip())

    def validate(self, api_key: str | None) -> bool:
        """Constant-time validation of presented API keys."""
        if not self.require_api_key:
            return True
        if not api_key:
            return False
        presented = api_key.strip()
        for stored in self._keys:
            if hmac.compare_digest(presented, stored):
                return True
        return False

def build_api_key_dependency(config: APIAuthConfig) -> Callable:
    """Return a FastAPI dependency that enforces API key authentication."""

    async def _dependency(
        header_key: str | None = Header(default=None, alias="X-API-Key"),
        query_key: str | None = Query(default=None, alias="api_key"),
    ) -> None:
        api_key = header_key or query_key
        if not config.validate(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )

    return _dependency

async def enforce_websocket_api_key(websocket: WebSocket, config: APIAuthConfig) -> None:
    """Validate API key for websocket connections before accepting."""
    presented_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if not config.validate(presented_key):
        await websocket.close(code=1008)
        raise APIKeyAuthError("Invalid or missing API key for websocket channel")

def optional_dependencies(config: APIAuthConfig) -> list[Any]:
    """Helper returning a dependency list for FastAPI route registration."""
    if not config.require_api_key:
        return []
    return [Depends(build_api_key_dependency(config))]
