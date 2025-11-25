"""
Minimal anthropic stub used for offline tests and tooling.
"""

from typing import Any, Dict


class APIError(Exception):
    """Exception raised for API-related errors."""

    pass


class Anthropic:
    """Stub implementation of Anthropic API client for testing."""

    def __init__(self, api_key: str) -> None:
        """
        Initialize the Anthropic client stub.

        Args:
            api_key: API authentication key
        """
        self.api_key = api_key

    def completion(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Stub method for API completion requests.

        Args:
            **kwargs: Arbitrary keyword arguments for completion request

        Returns:
            Dictionary containing stub completion response
        """
        return {
            "completion": {"content": "stub"},
            "id": "stub",
            "model": kwargs.get("model", "claude-1"),
        }
