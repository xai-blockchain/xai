"""
Simple API rotator stub that tracks usage limits.
"""

from typing import Dict


class AIAPIRotator:
    """Tracks donated API credits and rotations."""

    def __init__(self):
        self.available_requests = 10000
        self.rotations = 0

    def record_usage(self, count: int = 1):
        self.available_requests = max(0, self.available_requests - count)

    def rotate(self) -> Dict[str, object]:
        self.rotations += 1
        self.available_requests = max(0, self.available_requests - 1)
        return {"rotations": self.rotations, "available_requests": self.available_requests}

    def get_usage_stats(self) -> Dict[str, object]:
        return {"rotations": self.rotations, "available_requests": self.available_requests}
