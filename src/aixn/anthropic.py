"""
Minimal anthropic stub used for offline tests and tooling.
"""


class APIError(Exception):
    pass


class Anthropic:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def completion(self, **kwargs):
        return {
            "completion": {"content": "stub"},
            "id": "stub",
            "model": kwargs.get("model", "claude-1"),
        }
