from typing import Dict, Any
from datetime import datetime, timedelta, timezone
from src.aixn.blockchain.slashing import SlashingManager, ValidatorStake # Re-using ValidatorStake for RelayerStake

class Relayer:
    def __init__(self, address: str, bonded_amount: int, status: str = "active"):
        if not isinstance(address, str) or not address:
            raise ValueError("Relayer address must be a non-empty string.")
        if not isinstance(bonded_amount, int) or bonded_amount <= 0:
            raise ValueError("Bonded amount must be a positive integer.")
        if status not in ["active", "unbonding", "slashed", "inactive"]:
            raise ValueError("Invalid relayer status.")

        self.address = address
        self.bonded_amount = bonded_amount
        self.status = status
        self.unbonding_start_timestamp: int = 0 # Timestamp when unbonding started

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "bonded_amount": self.bonded_amount,
            "status": self.status,
            "unbonding_start_timestamp": self.unbonding_start_timestamp
        }

    def __repr__(self):
        return (
            f"Relayer(address='{self.address[:8]}...', bonded={self.bonded_amount}, "
            f"status='{self.status}')"
        )

class RelayerStakingManager:
    DEFAULT_MIN_BOND = 10000
    DEFAULT_UNBONDING_PERIOD_SECONDS = 7 * 24 * 3600 # 7 days

    def __init__(self, slashing_manager: SlashingManager,
                 min_bond: int = DEFAULT_MIN_BOND,
                 unbonding_period_seconds: int = DEFAULT_UNBONDING_PERIOD_SECONDS):
        if not isinstance(min_bond, int) or min_bond <= 0:
            raise ValueError("Minimum bond must be a positive integer.")
        if not isinstance(unbonding_period_seconds, int) or unbonding_period_seconds <= 0:
            raise ValueError("Unbonding period must be a positive integer.")

        self.relay_pool: Dict[str, Relayer] = {}
        self.slashing_manager = slashing_manager
        self.min_bond = min_bond
        self.unbonding_period_seconds = unbonding_period_seconds

    def bond_stake(self, relayer_address: str, amount: int) -> Relayer:
        if amount < self.min_bond:
            raise ValueError(f"Bonded amount {amount} is less than minimum required bond {self.min_bond}.")
        
        if relayer_address in self.relay_pool:
            relayer = self.relay_pool[relayer_address]
            if relayer.status == "unbonding":
                raise ValueError(f"Relayer {relayer_address} is currently unbonding. Cannot bond more stake.")
            relayer.bonded_amount += amount
            relayer.status = "active"
            print(f"Relayer {relayer_address} added {amount} to bond. Total bonded: {relayer.bonded_amount}.")
        else:
            relayer = Relayer(relayer_address, amount, "active")
            self.relay_pool[relayer_address] = relayer
            # Also register with slashing manager
            self.slashing_manager.add_validator_stake(ValidatorStake(relayer_address, amount))
            print(f"New relayer {relayer_address} bonded {amount} and is now active.")
        return relayer

    def unbond_stake(self, relayer_address: str):
        relayer = self.relay_pool.get(relayer_address)
        if not relayer:
            raise ValueError(f"Relayer {relayer_address} not found in pool.")
        if relayer.status == "unbonding":
            print(f"Relayer {relayer_address} is already in unbonding period.")
            return
        if relayer.status == "slashed":
            raise ValueError(f"Relayer {relayer_address} is slashed and cannot unbond.")

        relayer.status = "unbonding"
        relayer.unbonding_start_timestamp = int(datetime.now(timezone.utc).timestamp())
        print(f"Relayer {relayer_address} started unbonding. Funds will be released after "
              f"{self.unbonding_period_seconds} seconds.")

    def finalize_unbonding(self, relayer_address: str, current_timestamp: int):
        relayer = self.relay_pool.get(relayer_address)
        if not relayer:
            raise ValueError(f"Relayer {relayer_address} not found in pool.")
        if relayer.status != "unbonding":
            raise ValueError(f"Relayer {relayer_address} is not in unbonding status.")

        if current_timestamp >= relayer.unbonding_start_timestamp + self.unbonding_period_seconds:
            # In a real system, funds would be transferred back to the relayer here.
            print(f"Relayer {relayer_address} unbonding finalized. {relayer.bonded_amount} released.")
            relayer.status = "inactive"
            # Remove from slashing manager as well
            self.slashing_manager.remove_validator_stake(relayer_address)
        else:
            remaining_time = (relayer.unbonding_start_timestamp + self.unbonding_period_seconds) - current_timestamp
            print(f"Relayer {relayer_address} unbonding not yet complete. Remaining: {remaining_time} seconds.")

    def slash_relayer(self, relayer_address: str, offense_type: str):
        relayer = self.relay_pool.get(relayer_address)
        if not relayer:
            raise ValueError(f"Relayer {relayer_address} not found in pool.")
        
        print(f"Slashing relayer {relayer_address} for {offense_type}...")
        self.slashing_manager.report_malicious_behavior(relayer_address, offense_type)
        
        # Update relayer's bonded amount based on slashing manager's deduction
        slashed_stake = self.slashing_manager.get_validator_stake(relayer_address)
        if slashed_stake:
            relayer.bonded_amount = slashed_stake.staked_amount
            if relayer.bonded_amount == 0:
                relayer.status = "slashed"
                print(f"Relayer {relayer_address} fully slashed and set to 'slashed' status.")
            else:
                print(f"Relayer {relayer_address} bonded amount reduced to {relayer.bonded_amount}.")
        else:
            print(f"Warning: Relayer {relayer_address} not found in slashing manager after slash attempt.")

    def get_relayer_status(self, relayer_address: str) -> str:
        relayer = self.relay_pool.get(relayer_address)
        return relayer.status if relayer else "not_found"

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Setup SlashingManager
    slashing_manager = SlashingManager()
    # Add a new offense type for relayer slashing
    SlashingManager.OFFENSE_PENALTIES["relayer_misbehavior"] = 0.30 # 30% slash

    staking_manager = RelayerStakingManager(slashing_manager, min_bond=1000, unbonding_period_seconds=5) # 5s unbonding for testing

    relayer1_addr = "0xRelayer1"
    relayer2_addr = "0xRelayer2"
    relayer3_addr = "0xRelayer3"

    print("--- Bonding Relayers ---")
    staking_manager.bond_stake(relayer1_addr, 5000)
    staking_manager.bond_stake(relayer2_addr, 1000)
    try:
        staking_manager.bond_stake(relayer3_addr, 500) # Should fail due to min_bond
    except ValueError as e:
        print(f"Error bonding relayer3 (expected): {e}")
    staking_manager.bond_stake(relayer3_addr, 2000)

    print("\n--- Current Relayer Pool ---")
    for addr, relayer in staking_manager.relay_pool.items():
        print(relayer)

    print("\n--- Slashing Relayer 1 ---")
    staking_manager.slash_relayer(relayer1_addr, "relayer_misbehavior")
    print(staking_manager.relay_pool[relayer1_addr])

    print("\n--- Unbonding Relayer 2 ---")
    staking_manager.unbond_stake(relayer2_addr)
    print(staking_manager.relay_pool[relayer2_addr])

    print("\n--- Attempting to finalize unbonding immediately (should not work) ---")
    staking_manager.finalize_unbonding(relayer2_addr, int(datetime.now(timezone.utc).timestamp()))

    print("\n--- Waiting for unbonding period ---")
    import time
    time.sleep(6) # Wait for 5 seconds + a bit

    print("\n--- Finalizing unbonding ---")
    staking_manager.finalize_unbonding(relayer2_addr, int(datetime.now(timezone.utc).timestamp()))
    print(staking_manager.relay_pool[relayer2_addr])
