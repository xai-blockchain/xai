from typing import Dict, Any
from src.aixn.blockchain.token_supply_manager import TokenSupplyManager

class AntiWhaleManager:
    def __init__(self, token_supply_manager: TokenSupplyManager, 
                 max_governance_voting_power_percentage: float = 10.0, # Max 10% of total supply for voting
                 max_transaction_size_percentage_of_total_supply: float = 1.0): # Max 1% of total supply per transaction
        
        if not isinstance(token_supply_manager, TokenSupplyManager):
            raise ValueError("token_supply_manager must be an instance of TokenSupplyManager.")
        if not isinstance(max_governance_voting_power_percentage, (int, float)) or not (0 < max_governance_voting_power_percentage <= 100):
            raise ValueError("Max governance voting power percentage must be between 0 and 100.")
        if not isinstance(max_transaction_size_percentage_of_total_supply, (int, float)) or not (0 < max_transaction_size_percentage_of_total_supply <= 100):
            raise ValueError("Max transaction size percentage must be between 0 and 100.")

        self.token_supply_manager = token_supply_manager
        self.max_governance_voting_power_percentage = max_governance_voting_power_percentage
        self.max_transaction_size_percentage_of_total_supply = max_transaction_size_percentage_of_total_supply
        print(f"AntiWhaleManager initialized. Max voting power: {self.max_governance_voting_power_percentage}%, Max transaction size: {self.max_transaction_size_percentage_of_total_supply}% of total supply.")

    def check_governance_vote(self, voter_address: str, proposed_vote_power: float) -> float:
        """
        Checks and limits the effective voting power of an address.
        Returns the effective voting power after applying the cap.
        """
        total_supply = self.token_supply_manager.get_current_supply()
        if total_supply == 0:
            return 0.0 # No supply, no voting power

        max_allowed_vote_power = total_supply * (self.max_governance_voting_power_percentage / 100.0)
        
        effective_vote_power = min(proposed_vote_power, max_allowed_vote_power)
        
        if effective_vote_power < proposed_vote_power:
            print(f"Warning: Voter {voter_address} proposed {proposed_vote_power:.2f} voting power, "
                  f"but capped to {effective_vote_power:.2f} due to anti-whale mechanism.")
        
        return effective_vote_power

    def check_transaction_size(self, sender_address: str, transaction_amount: float) -> bool:
        """
        Checks if a transaction amount exceeds the maximum allowed percentage of total supply.
        Returns True if the transaction is allowed, False otherwise.
        """
        total_supply = self.token_supply_manager.get_current_supply()
        if total_supply == 0:
            print(f"Transaction from {sender_address} for {transaction_amount:.2f} blocked: Total supply is zero.")
            return False

        max_allowed_transaction_amount = total_supply * (self.max_transaction_size_percentage_of_total_supply / 100.0)
        
        if transaction_amount > max_allowed_transaction_amount:
            print(f"!!! ANTI-WHALE ALERT !!! Transaction from {sender_address} for {transaction_amount:.2f} "
                  f"exceeds maximum allowed transaction size of {max_allowed_transaction_amount:.2f} ({self.max_transaction_size_percentage_of_total_supply}% of total supply). Transaction blocked.")
            return False
        
        print(f"Transaction from {sender_address} for {transaction_amount:.2f} allowed.")
        return True

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Setup a dummy TokenSupplyManager
    supply_manager = TokenSupplyManager(max_supply=1000000.0)
    supply_manager.mint_tokens(800000.0) # Set current supply to 800,000

    anti_whale_manager = AntiWhaleManager(supply_manager, 
                                          max_governance_voting_power_percentage=5.0, # 5% cap
                                          max_transaction_size_percentage_of_total_supply=0.5) # 0.5% cap

    whale_voter = "0xWhaleVoter"
    small_voter = "0xSmallVoter"
    normal_user = "0xNormalUser"

    print("\n--- Checking Governance Votes ---")
    # Whale tries to vote with 10% of total supply (80,000 tokens)
    effective_vote_whale = anti_whale_manager.check_governance_vote(whale_voter, 80000.0)
    print(f"Whale effective vote power: {effective_vote_whale:.2f}") # Should be capped at 5% of 800k = 40k

    # Small voter votes with 1% of total supply (8,000 tokens)
    effective_vote_small = anti_whale_manager.check_governance_vote(small_voter, 8000.0)
    print(f"Small voter effective vote power: {effective_vote_small:.2f}") # Should not be capped

    print("\n--- Checking Transaction Sizes ---")
    # Normal transaction
    is_tx_allowed_normal = anti_whale_manager.check_transaction_size(normal_user, 3000.0) # 3000 is less than 0.5% of 800k (4000)
    print(f"Normal transaction allowed: {is_tx_allowed_normal}")

    # Large transaction (exceeds 0.5% of 800k = 4000)
    is_tx_allowed_large = anti_whale_manager.check_transaction_size(whale_voter, 5000.0)
    print(f"Large transaction allowed: {is_tx_allowed_large}")

    # Transaction exactly at the limit
    is_tx_allowed_limit = anti_whale_manager.check_transaction_size(normal_user, 4000.0)
    print(f"Limit transaction allowed: {is_tx_allowed_limit}")
