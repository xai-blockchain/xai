import time
from typing import Dict, Any, Optional

class VestingManager:
    def __init__(self):
        # Stores vesting schedules: {schedule_id: {"recipient": str, "total_amount": float, "start_time": int, "end_time": int, "cliff_duration": int, "claimed_amount": float}}
        self.vesting_schedules: Dict[str, Dict[str, Any]] = {}
        self._schedule_id_counter = 0
        print("VestingManager initialized.")

    def create_vesting_schedule(self, recipient_address: str, total_amount: float, start_time: int, end_time: int, cliff_duration: int) -> str:
        """
        Creates a new vesting schedule.
        - total_amount: Total tokens to be vested.
        - start_time: Unix timestamp when vesting begins.
        - end_time: Unix timestamp when vesting fully completes.
        - cliff_duration: Duration in seconds before any tokens start vesting.
        """
        if not recipient_address:
            raise ValueError("Recipient address cannot be empty.")
        if not isinstance(total_amount, (int, float)) or total_amount <= 0:
            raise ValueError("Total amount must be a positive number.")
        if not isinstance(start_time, int) or not isinstance(end_time, int) or not isinstance(cliff_duration, int):
            raise ValueError("Time parameters must be integers (Unix timestamps/durations).")
        if start_time >= end_time:
            raise ValueError("Start time must be before end time.")
        if cliff_duration < 0:
            raise ValueError("Cliff duration cannot be negative.")

        self._schedule_id_counter += 1
        schedule_id = f"vesting_{self._schedule_id_counter}"

        self.vesting_schedules[schedule_id] = {
            "recipient": recipient_address,
            "total_amount": total_amount,
            "start_time": start_time,
            "end_time": end_time,
            "cliff_duration": cliff_duration,
            "claimed_amount": 0.0
        }
        print(f"Vesting schedule {schedule_id} created for {recipient_address} for {total_amount:.2f} tokens.")
        return schedule_id

    def get_vested_amount(self, schedule_id: str, current_time: Optional[int] = None) -> float:
        """
        Calculates the amount of tokens that have vested for a given schedule up to current_time.
        """
        schedule = self.vesting_schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Vesting schedule {schedule_id} not found.")
        
        if current_time is None:
            current_time = int(time.time())

        total_amount = schedule["total_amount"]
        start_time = schedule["start_time"]
        end_time = schedule["end_time"]
        cliff_duration = schedule["cliff_duration"]
        claimed_amount = schedule["claimed_amount"]

        # Before cliff, no tokens vest
        if current_time < (start_time + cliff_duration):
            return 0.0
        
        # After end_time, all tokens have vested
        if current_time >= end_time:
            return total_amount - claimed_amount
        
        # Calculate vested amount proportionally between start_time and end_time (after cliff)
        vesting_start_after_cliff = start_time + cliff_duration
        if current_time < vesting_start_after_cliff: # Should be caught by first if, but for safety
            return 0.0

        vesting_duration = end_time - vesting_start_after_cliff
        time_elapsed_since_cliff = current_time - vesting_start_after_cliff

        if vesting_duration <= 0: # Should not happen with start_time < end_time
            return total_amount - claimed_amount

        vested_proportion = time_elapsed_since_cliff / vesting_duration
        vested_amount = total_amount * min(vested_proportion, 1.0) # Cap at 100%
        
        return max(0.0, vested_amount - claimed_amount) # Only return unclaimed vested amount

    def claim_vested_tokens(self, schedule_id: str, current_time: Optional[int] = None) -> float:
        """
        Simulates claiming available vested tokens for a given schedule.
        """
        schedule = self.vesting_schedules.get(schedule_id)
        if not schedule:
            raise ValueError(f"Vesting schedule {schedule_id} not found.")
        
        if current_time is None:
            current_time = int(time.time())

        available_to_claim = self.get_vested_amount(schedule_id, current_time)
        
        if available_to_claim <= 0:
            print(f"No tokens available to claim for schedule {schedule_id} at current time.")
            return 0.0
        
        schedule["claimed_amount"] += available_to_claim
        print(f"Claimed {available_to_claim:.2f} tokens for schedule {schedule_id}. Total claimed: {schedule['claimed_amount']:.2f}")
        return available_to_claim

# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = VestingManager()

    team_member = "0xTeamMember1"
    investor = "0xEarlyInvestor"

    # Define a vesting schedule: 1000 tokens, 10 seconds cliff, 30 seconds total vesting
    start_t = int(time.time())
    end_t = start_t + 30
    cliff_d = 10

    schedule_id_team = manager.create_vesting_schedule(team_member, 1000.0, start_t, end_t, cliff_d)
    schedule_id_investor = manager.create_vesting_schedule(investor, 5000.0, start_t, start_t + 60, 20)

    print("\n--- Simulating Time and Claiming ---")

    # Time 0: Before cliff
    print(f"\nTime: {time.ctime(start_t)}")
    print(f"Team member vested: {manager.get_vested_amount(schedule_id_team, start_t):.2f}")
    manager.claim_vested_tokens(schedule_id_team, start_t)

    # Time 1: After cliff, some vested
    time.sleep(cliff_d + 2) # 12 seconds after start, 2 seconds after cliff
    current_t1 = int(time.time())
    print(f"\nTime: {time.ctime(current_t1)}")
    print(f"Team member vested: {manager.get_vested_amount(schedule_id_team, current_t1):.2f}")
    manager.claim_vested_tokens(schedule_id_team, current_t1)
    print(f"Team member vested (after claim): {manager.get_vested_amount(schedule_id_team, current_t1):.2f}")

    # Time 2: Halfway through vesting
    time.sleep(10) # 22 seconds after start
    current_t2 = int(time.time())
    print(f"\nTime: {time.ctime(current_t2)}")
    print(f"Team member vested: {manager.get_vested_amount(schedule_id_team, current_t2):.2f}")
    manager.claim_vested_tokens(schedule_id_team, current_t2)

    # Time 3: After full vesting
    time.sleep(15) # 37 seconds after start, past end_time
    current_t3 = int(time.time())
    print(f"\nTime: {time.ctime(current_t3)}")
    print(f"Team member vested: {manager.get_vested_amount(schedule_id_team, current_t3):.2f}")
    manager.claim_vested_tokens(schedule_id_team, current_t3)
    print(f"Team member vested (after full claim): {manager.get_vested_amount(schedule_id_team, current_t3):.2f}")

    # Check investor schedule
    print(f"\nInvestor vested (at current time {time.ctime(current_t3)}): {manager.get_vested_amount(schedule_id_investor, current_t3):.2f}")
    manager.claim_vested_tokens(schedule_id_investor, current_t3)
