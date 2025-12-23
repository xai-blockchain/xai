"""
Minimal Python SDK for XAI Node API.

Provides convenience wrappers for fee estimation and transaction submission.
"""

from __future__ import annotations

import json
from typing import Any

import requests

class XAISDK:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def estimate_fee(self, priority: str = "normal") -> dict[str, Any]:
        url = f"{self.base_url}/algo/fee-estimate"
        resp = requests.get(url, params={"priority": priority}, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def send_transaction(self, signed_tx: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/send"
        payload = json.dumps(signed_tx)
        resp = requests.post(url, data=payload, headers=self._headers(), timeout=self.timeout)
        # Allow 400/403 to return structured error
        if resp.status_code >= 400:
            try:
                return resp.json()
            except Exception:
                resp.raise_for_status()
        return resp.json()

