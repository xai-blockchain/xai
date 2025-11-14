from typing import List, Dict, Any

class MEVRedistributor:
    def __init__(self, redistribution_percentage: float = 50.0):
        if not isinstance(redistribution_percentage, (int, float)) or not (0 <= redistribution_percentage <= 100):
            raise ValueError("Redistribution percentage must be between 0 and 100.")
        
        self.redistribution_percentage = redistribution_percentage
        self.total_mev_captured = 0.0
        self.total_mev_redistributed = 0.0
        print(f"MEVRedistributor initialized. Redistribution percentage: {self.redistribution_percentage}%")

    def capture_mev(self, amount: float):
        """Simulates capturing MEV from a block."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("MEV amount must be a non-negative number.")
        self.total_mev_captured += amount
        print(f"Captured {amount:.2f} MEV. Total captured: {self.total_mev_captured:.2f}")

    def redistribute_mev(self, users: Dict[str, float]) -> Dict[str, float]:
        """
        Redistributes a portion of the captured MEV to users based on their proportional share.
        'users' is a dictionary of {user_address: proportional_share_factor}.
        Returns a dictionary of {user_address: redistributed_amount}.
        """
        if not users:
            print("No users to redistribute MEV to.")
            return {}

        mev_to_redistribute = self.total_mev_captured * (self.redistribution_percentage / 100.0)
        
        if mev_to_redistribute <= 0:
            print("No MEV available for redistribution.")
            return {}

        total_share_factors = sum(users.values())
        if total_share_factors == 0:
            print("Total share factors are zero, cannot redistribute.")
            return {}

        redistributed_amounts: Dict[str, float] = {}
        for user_address, share_factor in users.items():
            if share_factor > 0:
                amount_for_user = (share_factor / total_share_factors) * mev_to_redistribute
                redistributed_amounts[user_address] = amount_for_user
                self.total_mev_redistributed += amount_for_user
                print(f"Redistributed {amount_for_user:.2f} MEV to {user_address}.")
        
        self.total_mev_captured -= mev_to_redistribute # Deduct redistributed amount from captured
        print(f"Total MEV redistributed: {self.total_mev_redistributed:.2f}. Remaining captured MEV: {self.total_mev_captured:.2f}")
        return redistributed_amounts

# Example Usage (for testing purposes)
if __name__ == "__main__":
    mev_manager = MEVRedistributor(redistribution_percentage=75.0) # Redistribute 75% of MEV

    print("\n--- Capturing MEV ---")
    mev_manager.capture_mev(100.0)
    mev_manager.capture_mev(50.0)

    print("\n--- Redistributing MEV ---")
    # Simulate users with different staking amounts (share factors)
    stakers = {
        "0xStaker1": 1000.0,
        "0xStaker2": 500.0,
        "0xStaker3": 2000.0
    }
    redistributed = mev_manager.redistribute_mev(stakers)
    print(f"Redistributed amounts: {redistributed}")

    print("\n--- Capturing More MEV and Redistributing ---")
    mev_manager.capture_mev(200.0)
    liquidity_providers = {
        "0xLP1": 5000.0,
        "0xLP2": 10000.0
    }
    redistributed_lp = mev_manager.redistribute_mev(liquidity_providers)
    print(f"Redistributed amounts to LPs: {redistributed_lp}")

    print(f"\nFinal Total MEV Captured: {mev_manager.total_mev_captured:.2f}")
    print(f"Final Total MEV Redistributed: {mev_manager.total_mev_redistributed:.2f}")
