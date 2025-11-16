from typing import Dict, Any, List
import time


class DustPreventionManager:
    def __init__(self, asset_symbol: str, dust_threshold_amount: float):
        if not asset_symbol:
            raise ValueError("Asset symbol cannot be empty.")
        if not isinstance(dust_threshold_amount, (int, float)) or dust_threshold_amount <= 0:
            raise ValueError("Dust threshold amount must be a positive number.")

        self.asset_symbol = asset_symbol
        self.dust_threshold_amount = dust_threshold_amount
        self.wallet_balances: Dict[str, float] = {}  # {address: balance}
        self.dust_transactions_log: List[Dict[str, Any]] = []

    def is_dust_amount(self, amount: float) -> bool:
        """Checks if a given amount is below the dust threshold."""
        return amount < self.dust_threshold_amount

    def process_incoming_transaction(
        self, to_address: str, amount: float, from_address: str = "0xSender"
    ):
        """
        Simulates processing an incoming transaction and identifies if it's a dust attack.
        """
        if not to_address:
            raise ValueError("Recipient address cannot be empty.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Amount must be a positive number.")

        if self.is_dust_amount(amount):
            print(
                f"!!! DUST ATTACK DETECTED !!! Incoming transaction of {amount:.8f} {self.asset_symbol} to {to_address} from {from_address} is below dust threshold."
            )
            self.dust_transactions_log.append(
                {
                    "to_address": to_address,
                    "amount": amount,
                    "from_address": from_address,
                    "timestamp": int(time.time()),
                    "status": "dust_ignored",
                }
            )
            # In a real system, this might not be added to the main balance or require user confirmation.
            # For this simulation, we'll still add it to the balance but log it as dust.
            self.wallet_balances[to_address] = self.wallet_balances.get(to_address, 0.0) + amount
            return False  # Indicate it was dust
        else:
            self.wallet_balances[to_address] = self.wallet_balances.get(to_address, 0.0) + amount
            print(
                f"Processed incoming transaction: {amount:.8f} {self.asset_symbol} to {to_address}. New balance: {self.wallet_balances[to_address]:.8f}"
            )
            return True  # Indicate it was not dust

    def consolidate_dust(self, main_address: str, addresses_to_consolidate: List[str]):
        """
        Simulates consolidating dust amounts from multiple addresses into a main address.
        """
        if not main_address:
            raise ValueError("Main address cannot be empty.")
        if not addresses_to_consolidate:
            print("No addresses to consolidate dust from.")
            return

        total_consolidated_amount = 0.0
        for address in addresses_to_consolidate:
            if address == main_address:
                continue  # Don't consolidate from main address to itself

            balance = self.wallet_balances.get(address, 0.0)
            if self.is_dust_amount(balance) and balance > 0:
                total_consolidated_amount += balance
                self.wallet_balances[address] = 0.0  # Clear balance from dust address
                print(f"Consolidated {balance:.8f} {self.asset_symbol} from {address}.")
            elif balance > 0:
                print(
                    f"Address {address} has {balance:.8f} {self.asset_symbol}, which is above dust threshold. Not consolidating."
                )

        if total_consolidated_amount > 0:
            self.wallet_balances[main_address] = (
                self.wallet_balances.get(main_address, 0.0) + total_consolidated_amount
            )
            print(
                f"Total {total_consolidated_amount:.8f} {self.asset_symbol} consolidated to {main_address}. New balance: {self.wallet_balances[main_address]:.8f}"
            )
        else:
            print("No dust amounts found for consolidation.")


# Example Usage (for testing purposes)
if __name__ == "__main__":
    dust_manager = DustPreventionManager(
        asset_symbol="BTC", dust_threshold_amount=0.00001
    )  # 1000 satoshis

    user_wallet = "0xUserMainWallet"
    dust_wallet_1 = "0xDustWallet1"
    dust_wallet_2 = "0xDustWallet2"
    attacker_address = "0xAttacker"

    print("--- Initial State ---")
    dust_manager.wallet_balances[user_wallet] = 0.1  # Initial balance
    print(f"User main wallet balance: {dust_manager.wallet_balances[user_wallet]:.8f}")

    print("\n--- Simulating Dust Attacks ---")
    dust_manager.process_incoming_transaction(user_wallet, 0.000005, attacker_address)  # Dust
    dust_manager.process_incoming_transaction(dust_wallet_1, 0.000001, attacker_address)  # Dust
    dust_manager.process_incoming_transaction(dust_wallet_2, 0.000008, attacker_address)  # Dust

    print("\n--- Simulating Normal Transaction ---")
    dust_manager.process_incoming_transaction(user_wallet, 0.01, "0xFriend")  # Not dust

    print("\n--- Balances after transactions ---")
    print(f"User main wallet balance: {dust_manager.wallet_balances.get(user_wallet, 0.0):.8f}")
    print(f"Dust wallet 1 balance: {dust_manager.wallet_balances.get(dust_wallet_1, 0.0):.8f}")
    print(f"Dust wallet 2 balance: {dust_manager.wallet_balances.get(dust_wallet_2, 0.0):.8f}")
    print(f"Dust transactions log: {dust_manager.dust_transactions_log}")

    print("\n--- Consolidating Dust ---")
    dust_manager.consolidate_dust(user_wallet, [dust_wallet_1, dust_wallet_2, user_wallet])

    print("\n--- Balances after consolidation ---")
    print(f"User main wallet balance: {dust_manager.wallet_balances.get(user_wallet, 0.0):.8f}")
    print(f"Dust wallet 1 balance: {dust_manager.wallet_balances.get(dust_wallet_1, 0.0):.8f}")
    print(f"Dust wallet 2 balance: {dust_manager.wallet_balances.get(dust_wallet_2, 0.0):.8f}")
