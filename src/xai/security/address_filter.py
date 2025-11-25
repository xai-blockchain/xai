from typing import Set, List


class AddressFilter:
    def __init__(self, enable_whitelist: bool = False):
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()
        self.enable_whitelist = enable_whitelist  # If True, only whitelisted addresses are allowed

    def add_to_whitelist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        self.whitelist.add(address)
        print(f"Address {address} added to whitelist.")

    def remove_from_whitelist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        if address in self.whitelist:
            self.whitelist.remove(address)
            print(f"Address {address} removed from whitelist.")
        else:
            print(f"Address {address} not found in whitelist.")

    def add_to_blacklist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        self.blacklist.add(address)
        print(f"Address {address} added to blacklist.")

    def remove_from_blacklist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        if address in self.blacklist:
            self.blacklist.remove(address)
            print(f"Address {address} removed from blacklist.")
        else:
            print(f"Address {address} not found in blacklist.")

    def is_whitelisted(self, address: str) -> bool:
        return address in self.whitelist

    def is_blacklisted(self, address: str) -> bool:
        return address in self.blacklist

    def check_address(self, address: str) -> bool:
        """
        Checks an address against the blacklist and whitelist.
        Returns True if the address is allowed, False otherwise.
        Blacklist takes precedence over whitelist.
        If whitelist is enabled, only whitelisted addresses are allowed (unless blacklisted).
        If whitelist is disabled, all addresses are allowed unless blacklisted.
        """
        if not address:
            return False  # Empty address is never allowed

        if address in self.blacklist:
            print(f"Address {address} is BLACKLISTED. Access DENIED.")
            return False

        if self.enable_whitelist:
            if address in self.whitelist:
                print(f"Address {address} is WHITELISTED. Access GRANTED.")
                return True
            else:
                print(f"Address {address} is NOT WHITELISTED. Access DENIED (whitelist enabled).")
                return False
        else:
            # Whitelist is not enabled, so all non-blacklisted addresses are allowed
            print(f"Address {address} is not blacklisted. Access GRANTED (whitelist disabled).")
            return True


# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Scenario 1: Blacklist only
    print("--- Scenario 1: Blacklist Only ---")
    filter_blacklist_only = AddressFilter(enable_whitelist=False)
    filter_blacklist_only.add_to_blacklist("0xBadActor1")
    filter_blacklist_only.add_to_blacklist("0xScammerAddress")

    print(f"Check 0xGoodUser: {filter_blacklist_only.check_address('0xGoodUser')}")
    print(f"Check 0xBadActor1: {filter_blacklist_only.check_address('0xBadActor1')}")
    print(f"Check 0xAnotherGoodUser: {filter_blacklist_only.check_address('0xAnotherGoodUser')}")

    # Scenario 2: Whitelist enabled
    print("\n--- Scenario 2: Whitelist Enabled ---")
    filter_whitelist_enabled = AddressFilter(enable_whitelist=True)
    filter_whitelist_enabled.add_to_whitelist("0xAdmin1")
    filter_whitelist_enabled.add_to_whitelist("0xRelayerA")
    filter_whitelist_enabled.add_to_blacklist("0xCompromisedAdmin")  # Blacklist takes precedence

    print(f"Check 0xAdmin1: {filter_whitelist_enabled.check_address('0xAdmin1')}")
    print(f"Check 0xRelayerA: {filter_whitelist_enabled.check_address('0xRelayerA')}")
    print(
        f"Check 0xUnauthorizedUser: {filter_whitelist_enabled.check_address('0xUnauthorizedUser')}"
    )
    print(
        f"Check 0xCompromisedAdmin: {filter_whitelist_enabled.check_address('0xCompromisedAdmin')}"
    )

    # Scenario 3: Dynamic changes
    print("\n--- Scenario 3: Dynamic Changes ---")
    filter_dynamic = AddressFilter(enable_whitelist=False)
    filter_dynamic.add_to_blacklist("0xTempBlocked")
    print(f"Check 0xTempBlocked: {filter_dynamic.check_address('0xTempBlocked')}")
    filter_dynamic.remove_from_blacklist("0xTempBlocked")
    print(f"Check 0xTempBlocked after removal: {filter_dynamic.check_address('0xTempBlocked')}")

    filter_dynamic.enable_whitelist = True
    filter_dynamic.add_to_whitelist("0xNewAdmin")
    print(f"Check 0xNewAdmin (whitelist enabled): {filter_dynamic.check_address('0xNewAdmin')}")
    print(
        f"Check 0xRegularUser (whitelist enabled): {filter_dynamic.check_address('0xRegularUser')}"
    )
