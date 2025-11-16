class APIError(Exception):
    pass


class OpenAI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.chat = self
        self.completions = self.finish

    class finish:
        @staticmethod
        def create(**kwargs):
            return type(
                "R",
                (object,),
                {
                    "choices": [
                        type(
                            "C",
                            (object,),
                            {"message": type("M", (object,), {"content": "stub response"})()},
                        )
                    ],
                    "usage": type(
                        "U",
                        (object,),
                        {"total_tokens": 1, "prompt_tokens": 1, "completion_tokens": 0},
                    ),
                },
            )
