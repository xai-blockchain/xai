"""Lightweight Flask sock stub for tests."""


class Sock:
    """Minimal replacement for flask_sock so tests can run."""

    def __init__(self, app):
        self.app = app

    def route(self, path):
        def decorator(handler):
            return handler

        return decorator
