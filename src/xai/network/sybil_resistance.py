from typing import Dict, Any


class SybilResistanceManager:
    def __init__(self, minimum_reputation_for_action: float = 50.0):
        if not isinstance(minimum_reputation_for_action, (int, float)) or not (
            0 <= minimum_reputation_for_action <= 100
        ):
            raise ValueError("Minimum reputation for action must be between 0 and 100.")

        self.minimum_reputation_for_action = minimum_reputation_for_action
        # Stores participant reputation scores: {address: score}
        self.reputation_scores: Dict[str, float] = {}
        # Conceptual registry for unique identities
        self.proof_of_personhood_registry: Dict[str, bool] = {}
        print(
            f"SybilResistanceManager initialized. Minimum reputation for action: {self.minimum_reputation_for_action:.2f}."
        )

    def register_personhood(self, participant_address: str):
        """Simulates registering a unique proof-of-personhood for an address."""
        if participant_address in self.proof_of_personhood_registry:
            raise ValueError(
                f"Participant {participant_address} already registered for personhood."
            )
        self.proof_of_personhood_registry[participant_address] = True
        self.reputation_scores[participant_address] = 0.0  # Start with base reputation
        print(f"Participant {participant_address} registered for proof-of-personhood.")

    def get_reputation(self, participant_address: str) -> float:
        """Returns the reputation score of a participant."""
        return self.reputation_scores.get(participant_address, 0.0)

    def update_reputation(self, participant_address: str, change: float):
        """
        Updates the reputation score of a participant.
        Positive change for good behavior, negative for bad.
        Reputation is capped between 0 and 100.
        """
        if participant_address not in self.reputation_scores:
            raise ValueError(f"Participant {participant_address} not found in reputation system.")

        current_reputation = self.reputation_scores[participant_address]
        new_reputation = max(0.0, min(100.0, current_reputation + change))
        self.reputation_scores[participant_address] = new_reputation
        print(
            f"Reputation for {participant_address} updated from {current_reputation:.2f} to {new_reputation:.2f}."
        )

    def check_participant_for_action(self, participant_address: str) -> bool:
        """
        Checks if a participant meets the minimum reputation requirement for a specific action.
        Also checks for proof-of-personhood.
        """
        if participant_address not in self.proof_of_personhood_registry:
            print(
                f"Participant {participant_address} not registered for proof-of-personhood. Action denied."
            )
            return False

        reputation = self.get_reputation(participant_address)
        if reputation >= self.minimum_reputation_for_action:
            print(
                f"Participant {participant_address} meets reputation requirement ({reputation:.2f} >= {self.minimum_reputation_for_action:.2f}). Action allowed."
            )
            return True
        else:
            print(
                f"Participant {participant_address} does not meet reputation requirement ({reputation:.2f} < {self.minimum_reputation_for_action:.2f}). Action denied."
            )
            return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    sybil_manager = SybilResistanceManager(minimum_reputation_for_action=60.0)

    user_a = "0xUserA"
    user_b = "0xUserB"
    sybil_user = "0xSybilUser"

    print("\n--- Registering Participants ---")
    sybil_manager.register_personhood(user_a)
    sybil_manager.register_personhood(user_b)
    # sybil_manager.register_personhood(sybil_user) # Sybil user might not pass personhood check

    print("\n--- Initial Checks ---")
    print(f"User A can perform action: {sybil_manager.check_participant_for_action(user_a)}")
    print(f"User B can perform action: {sybil_manager.check_participant_for_action(user_b)}")

    print("\n--- Updating Reputation ---")
    sybil_manager.update_reputation(user_a, 70.0)  # Good behavior
    sybil_manager.update_reputation(user_b, 30.0)  # Some good behavior

    print("\n--- Checks After Reputation Update ---")
    print(f"User A can perform action: {sybil_manager.check_participant_for_action(user_a)}")
    print(f"User B can perform action: {sybil_manager.check_participant_for_action(user_b)}")

    print("\n--- Simulating Bad Behavior for User B ---")
    sybil_manager.update_reputation(user_b, -40.0)  # Bad behavior
    print(f"User B can perform action: {sybil_manager.check_participant_for_action(user_b)}")

    print("\n--- Attempting action with unregistered user ---")
    print(
        f"Sybil user can perform action: {sybil_manager.check_participant_for_action(sybil_user)}"
    )
