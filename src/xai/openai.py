"""
Minimal openai stub for offline builds.
"""


class OpenAIError(Exception):
    pass


class OpenAI:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def ChatCompletion(self, **kwargs):
        return type("Res", (), {"choices": [{"message": {"content": "stub"}}], "usage": {}})
