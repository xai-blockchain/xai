import math
from typing import Dict, Any


class QuadraticVoter:
    def __init__(self):
        # Stores voter balances: {voter_address: balance}
        self.balances: Dict[str, float] = {}
        print("QuadraticVoter initialized.")

    def set_balance(self, voter_address: str, amount: float):
        """Sets the token balance for a voter."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Balance amount must be a non-negative number.")
        self.balances[voter_address] = amount
        print(f"Set balance for {voter_address}: {amount:.2f}")

    def get_balance(self, voter_address: str) -> float:
        """Returns the token balance for a voter."""
        return self.balances.get(voter_address, 0.0)

    def calculate_vote_cost(self, num_votes: int) -> float:
        """
        Calculates the token cost for a given number of votes using the quadratic formula.
        Cost = votes^2
        """
        if not isinstance(num_votes, int) or num_votes < 0:
            raise ValueError("Number of votes must be a non-negative integer.")
        return float(num_votes**2)

    def calculate_effective_votes(self, tokens_spent: float) -> float:
        """
        Calculates the effective number of votes from tokens spent using the quadratic formula.
        Effective Votes = sqrt(tokens_spent)
        """
        if not isinstance(tokens_spent, (int, float)) or tokens_spent < 0:
            raise ValueError("Tokens spent must be a non-negative number.")
        return math.sqrt(tokens_spent)

    def cast_votes(self, voter_address: str, num_votes: int) -> float:
        """
        Simulates casting votes for a voter, deducting the quadratic cost from their balance.
        Returns the effective votes cast.
        """
        if not voter_address in self.balances:
            raise ValueError(f"Voter {voter_address} has no balance set.")

        cost = self.calculate_vote_cost(num_votes)
        current_balance = self.balances[voter_address]

        if current_balance < cost:
            raise ValueError(
                f"Voter {voter_address} has insufficient balance ({current_balance:.2f}) to cast {num_votes} votes (cost: {cost:.2f})."
            )

        self.balances[voter_address] -= cost
        effective_votes = self.calculate_effective_votes(cost)

        print(
            f"Voter {voter_address} cast {num_votes} votes (cost: {cost:.2f} tokens). Effective votes: {effective_votes:.2f}. Remaining balance: {self.balances[voter_address]:.2f}"
        )
        return effective_votes


# Example Usage (for testing purposes)
if __name__ == "__main__":
    voter_manager = QuadraticVoter()

    whale_address = "0xWhale"
    normal_user_address = "0xNormalUser"

    voter_manager.set_balance(whale_address, 10000.0)  # Whale has 10,000 tokens
    voter_manager.set_balance(normal_user_address, 100.0)  # Normal user has 100 tokens

    print("\n--- Whale Voting ---")
    try:
        # Whale casts 10 votes
        whale_effective_votes_1 = voter_manager.cast_votes(
            whale_address, 10
        )  # Cost: 10^2 = 100 tokens
        print(f"Whale effective votes (10 votes): {whale_effective_votes_1:.2f}")

        # Whale casts another 50 votes
        whale_effective_votes_2 = voter_manager.cast_votes(
            whale_address, 50
        )  # Cost: 50^2 = 2500 tokens
        print(f"Whale effective votes (50 votes): {whale_effective_votes_2:.2f}")

        # Whale tries to cast 100 votes (cost 10000)
        # Remaining balance: 10000 - 100 - 2500 = 7400
        # This should fail as 7400 < 10000
        try:
            voter_manager.cast_votes(whale_address, 100)
        except ValueError as e:
            print(f"Error (expected): {e}")

    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Normal User Voting ---")
    try:
        # Normal user casts 5 votes
        user_effective_votes_1 = voter_manager.cast_votes(
            normal_user_address, 5
        )  # Cost: 5^2 = 25 tokens
        print(f"Normal user effective votes (5 votes): {user_effective_votes_1:.2f}")

        # Normal user casts another 8 votes
        user_effective_votes_2 = voter_manager.cast_votes(
            normal_user_address, 8
        )  # Cost: 8^2 = 64 tokens
        print(f"Normal user effective votes (8 votes): {user_effective_votes_2:.2f}")

        # Normal user tries to cast 10 votes (cost 100)
        # Remaining balance: 100 - 25 - 64 = 11
        # This should fail as 11 < 100
        try:
            voter_manager.cast_votes(normal_user_address, 10)
        except ValueError as e:
            print(f"Error (expected): {e}")

    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Comparison ---")
    # If whale spent 100 tokens for 10 votes, effective votes = 10
    # If normal user spent 100 tokens (e.g., 5 votes + 8 votes = 89 tokens), effective votes = sqrt(89) = 9.43
    # This demonstrates how quadratic voting gives smaller holders more relative power for the same token spend.
    print(f"Whale final balance: {voter_manager.get_balance(whale_address):.2f}")
    print(f"Normal user final balance: {voter_manager.get_balance(normal_user_address):.2f}")
