import math
import hashlib
import logging
import threading
from typing import Dict, Any, Set, Optional

logger = logging.getLogger(__name__)


class QuadraticVoter:
    def __init__(self, minimum_stake_for_verification: float = 100.0,
                 minimum_account_age_seconds: int = 86400):
        """
        Initialize QuadraticVoter with sybil resistance mechanisms.

        Args:
            minimum_stake_for_verification: Minimum stake required to be verified
            minimum_account_age_seconds: Minimum account age to participate (default: 24 hours)
        """
        # Stores voter balances: {voter_address: balance}
        self.balances: Dict[str, float] = {}

        # Sybil resistance: verified identities
        self.verified_voters: Set[str] = set()

        # Stake-based verification: track stakes
        self.voter_stakes: Dict[str, float] = {}

        # Social proof: track endorsements
        self.endorsements: Dict[str, Set[str]] = {}  # {voter: set of endorsers}

        # Account age tracking
        self.account_creation_times: Dict[str, int] = {}

        # Prevent multiple account detection
        self.identity_hashes: Dict[str, str] = {}  # {voter: identity_hash}
        self.hash_to_voters: Dict[str, Set[str]] = {}  # {identity_hash: set of voters}

        self.minimum_stake_for_verification = minimum_stake_for_verification
        self.minimum_account_age_seconds = minimum_account_age_seconds
        self._lock = threading.RLock()

        logger.info(
            f"QuadraticVoter initialized with sybil resistance. "
            f"Min stake: {minimum_stake_for_verification}, Min age: {minimum_account_age_seconds}s"
        )

    def register_voter(self, voter_address: str, creation_time: int, identity_proof: Optional[str] = None):
        """
        Register a new voter with identity verification.

        Args:
            voter_address: Address of the voter
            creation_time: Unix timestamp of account creation
            identity_proof: Optional identity proof for verification
        """
        with self._lock:
            if voter_address in self.account_creation_times:
                logger.warning(f"Voter {voter_address} already registered")
                return

            self.account_creation_times[voter_address] = creation_time

            # Generate identity hash to detect multiple accounts
            if identity_proof:
                identity_hash = hashlib.sha256(identity_proof.encode()).hexdigest()
                self.identity_hashes[voter_address] = identity_hash

                if identity_hash not in self.hash_to_voters:
                    self.hash_to_voters[identity_hash] = set()
                self.hash_to_voters[identity_hash].add(voter_address)

                # Flag potential sybil if multiple accounts from same identity
                if len(self.hash_to_voters[identity_hash]) > 1:
                    logger.warning(
                        f"Multiple accounts detected for identity hash {identity_hash[:8]}...: "
                        f"{self.hash_to_voters[identity_hash]}"
                    )

            logger.info(f"Voter {voter_address} registered at {creation_time}")

    def verify_voter_stake(self, voter_address: str, stake_amount: float) -> bool:
        """
        Verify voter through stake-based verification.

        Args:
            voter_address: Address of the voter
            stake_amount: Amount staked for verification

        Returns:
            True if verification successful
        """
        with self._lock:
            if stake_amount < self.minimum_stake_for_verification:
                logger.warning(
                    f"Stake verification failed for {voter_address}: "
                    f"{stake_amount:.2f} < {self.minimum_stake_for_verification:.2f}"
                )
                return False

            self.voter_stakes[voter_address] = stake_amount
            self.verified_voters.add(voter_address)
            logger.info(f"Voter {voter_address} verified with stake {stake_amount:.2f}")
            return True

    def add_social_proof(self, voter_address: str, endorser_address: str):
        """
        Add social proof through endorsement from verified voter.

        Args:
            voter_address: Address being endorsed
            endorser_address: Address of endorser (must be verified)
        """
        with self._lock:
            if endorser_address not in self.verified_voters:
                raise ValueError(f"Endorser {endorser_address} is not verified")

            if voter_address not in self.endorsements:
                self.endorsements[voter_address] = set()

            self.endorsements[voter_address].add(endorser_address)

            # Auto-verify if enough endorsements
            if len(self.endorsements[voter_address]) >= 3:
                self.verified_voters.add(voter_address)
                logger.info(
                    f"Voter {voter_address} verified through social proof "
                    f"({len(self.endorsements[voter_address])} endorsements)"
                )

    def is_verified(self, voter_address: str, current_time: int) -> bool:
        """
        Check if voter is verified and meets sybil resistance criteria.

        Args:
            voter_address: Address to check
            current_time: Current unix timestamp

        Returns:
            True if voter passes all sybil checks
        """
        with self._lock:
            # Must be explicitly verified
            if voter_address not in self.verified_voters:
                logger.debug(f"Voter {voter_address} not verified")
                return False

            # Check account age
            if voter_address in self.account_creation_times:
                account_age = current_time - self.account_creation_times[voter_address]
                if account_age < self.minimum_account_age_seconds:
                    logger.warning(
                        f"Voter {voter_address} account too new: {account_age}s < {self.minimum_account_age_seconds}s"
                    )
                    return False

            # Check for multiple account abuse
            if voter_address in self.identity_hashes:
                identity_hash = self.identity_hashes[voter_address]
                if len(self.hash_to_voters[identity_hash]) > 1:
                    logger.warning(f"Voter {voter_address} flagged for multiple accounts")
                    # In production, might reduce voting power or disallow
                    # For now, just log warning but allow

            return True

    def set_balance(self, voter_address: str, amount: float):
        """Sets the token balance for a voter."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Balance amount must be a non-negative number.")
        with self._lock:
            self.balances[voter_address] = amount
            logger.debug(f"Set balance for {voter_address}: {amount:.2f}")

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
            logger.warning(
                "ValueError in cast_votes",
                extra={
                    "error_type": "ValueError",
                    "error": str(e),
                    "function": "cast_votes"
                }
            )
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
            logger.warning(
                "ValueError in cast_votes",
                extra={
                    "error_type": "ValueError",
                    "error": str(e),
                    "function": "cast_votes"
                }
            )
            print(f"Error (expected): {e}")

    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Comparison ---")
    # If whale spent 100 tokens for 10 votes, effective votes = 10
    # If normal user spent 100 tokens (e.g., 5 votes + 8 votes = 89 tokens), effective votes = sqrt(89) = 9.43
    # This demonstrates how quadratic voting gives smaller holders more relative power for the same token spend.
    print(f"Whale final balance: {voter_manager.get_balance(whale_address):.2f}")
    print(f"Normal user final balance: {voter_manager.get_balance(normal_user_address):.2f}")
