class APIError(Exception):
    pass


class MessageResponse:
    def __init__(self):
        self.content = [type("R", (object,), {"text": "stub response"})()]
        self.usage = type("U", (object,), {"input_tokens": 1, "output_tokens": 1})


class Anthropic:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.messages = self

    def create(self, **kwargs):
        return MessageResponse()
