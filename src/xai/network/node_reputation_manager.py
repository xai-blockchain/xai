from __future__ import annotations

import time
from typing import Any

class NodeReputationManager:
    def __init__(
        self,
        initial_reputation: float = 50.0,
        min_reputation: float = 0.0,
        max_reputation: float = 100.0,
        decay_rate: float = 0.01,
    ):
        if not (0 <= initial_reputation <= 100):
            raise ValueError("Initial reputation must be between 0 and 100.")
        if not (0 <= min_reputation < max_reputation <= 100):
            raise ValueError(
                "Min reputation must be less than max reputation and both between 0 and 100."
            )
        if not (0 <= decay_rate <= 1):
            raise ValueError("Decay rate must be between 0 and 1.")

        self.initial_reputation = initial_reputation
        self.min_reputation = min_reputation
        self.max_reputation = max_reputation
        self.decay_rate = decay_rate  # Percentage decay per time unit (e.g., per hour)

        # Stores reputation: {peer_id: {"score": float, "last_updated": float}}
        self.peer_reputations: dict[str, dict[str, float]] = {}
        print(
            f"NodeReputationManager initialized. Initial: {initial_reputation}, Min: {min_reputation}, Max: {max_reputation}, Decay: {decay_rate}."
        )

    def _get_reputation_entry(self, peer_id: str) -> dict[str, float]:
        """Initializes or retrieves reputation data for a peer."""
        if peer_id not in self.peer_reputations:
            self.peer_reputations[peer_id] = {
                "score": self.initial_reputation,
                "last_updated": time.time(),
            }
        return self.peer_reputations[peer_id]

    def _apply_decay(self, peer_id: str):
        """Applies reputation decay based on time elapsed."""
        entry = self._get_reputation_entry(peer_id)
        current_time = time.time()
        time_elapsed = current_time - entry["last_updated"]

        # For simplicity, decay linearly per second for now. In a real system,
        # this might be per hour, per day, or based on block intervals.
        decay_amount = self.decay_rate * time_elapsed * (entry["score"] - self.min_reputation)
        entry["score"] = max(self.min_reputation, entry["score"] - decay_amount)
        entry["last_updated"] = current_time

    def get_reputation(self, peer_id: str) -> float:
        """Returns the current reputation score for a peer, applying decay first."""
        self._apply_decay(peer_id)
        return self._get_reputation_entry(peer_id)["score"]

    def increase_reputation(self, peer_id: str, amount: float = 1.0):
        """Increases a peer's reputation score."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Reputation increase amount must be a non-negative number.")

        entry = self._get_reputation_entry(peer_id)
        self._apply_decay(peer_id)
        entry["score"] = min(self.max_reputation, entry["score"] + amount)
        print(f"Reputation for {peer_id} increased to {entry['score']:.2f}.")

    def decrease_reputation(self, peer_id: str, amount: float = 5.0):
        """Decreases a peer's reputation score."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Reputation decrease amount must be a non-negative number.")

        entry = self._get_reputation_entry(peer_id)
        self._apply_decay(peer_id)
        entry["score"] = max(self.min_reputation, entry["score"] - amount)
        print(f"Reputation for {peer_id} decreased to {entry['score']:.2f}.")

    def get_reputable_peers(
        self, all_peer_ids: list[str], min_score_threshold: float = 25.0
    ) -> list[str]:
        """
        Returns a list of peer IDs whose reputation is above the given threshold.
        """
        reputable_peers = []
        for peer_id in all_peer_ids:
            if self.get_reputation(peer_id) >= min_score_threshold:
                reputable_peers.append(peer_id)
        return reputable_peers

# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = NodeReputationManager(initial_reputation=50.0, decay_rate=0.05)

    peer_good = "peer_good_actor"
    peer_bad = "peer_bad_actor"
    peer_neutral = "peer_neutral_actor"

    print(f"Initial reputation for {peer_good}: {manager.get_reputation(peer_good):.2f}")
    print(f"Initial reputation for {peer_bad}: {manager.get_reputation(peer_bad):.2f}")

    print("\n--- Simulating Actions ---")
    manager.increase_reputation(peer_good, 10.0)
    manager.decrease_reputation(peer_bad, 20.0)
    manager.increase_reputation(peer_good, 5.0)

    print("\n--- Checking Reputations ---")
    print(f"Reputation for {peer_good}: {manager.get_reputation(peer_good):.2f}")
    print(f"Reputation for {peer_bad}: {manager.get_reputation(peer_bad):.2f}")
    print(f"Reputation for {peer_neutral}: {manager.get_reputation(peer_neutral):.2f}")

    print("\n--- Simulating Time Pass (2 seconds) ---")
    time.sleep(2.0)

    print("\n--- Checking Reputations After Decay ---")
    print(f"Reputation for {peer_good}: {manager.get_reputation(peer_good):.2f}")
    print(f"Reputation for {peer_bad}: {manager.get_reputation(peer_bad):.2f}")
    print(f"Reputation for {peer_neutral}: {manager.get_reputation(peer_neutral):.2f}")

    print("\n--- Getting Reputable Peers ---")
    all_peers = [peer_good, peer_bad, peer_neutral, "peer_new"]
    reputable = manager.get_reputable_peers(all_peers, min_score_threshold=40.0)
    print(f"Reputable peers (score >= 40): {reputable}")

    reputable_strict = manager.get_reputable_peers(all_peers, min_score_threshold=60.0)
    print(f"Reputable peers (score >= 60): {reputable_strict}")
