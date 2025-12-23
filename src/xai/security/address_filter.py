from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

class AddressFilter:
    def __init__(self, enable_whitelist: bool = False):
        self.whitelist: set[str] = set()
        self.blacklist: set[str] = set()
        self.enable_whitelist = enable_whitelist  # If True, only whitelisted addresses are allowed

    def add_to_whitelist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        self.whitelist.add(address)
        logger.info("Address added to whitelist", extra={"event": "address_filter.whitelist_add", "address": address})

    def remove_from_whitelist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        if address in self.whitelist:
            self.whitelist.remove(address)
            logger.info("Address removed from whitelist", extra={"event": "address_filter.whitelist_remove", "address": address})
        else:
            logger.info("Address not found in whitelist", extra={"event": "address_filter.whitelist_missing", "address": address})

    def add_to_blacklist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        self.blacklist.add(address)
        logger.warning("Address added to blacklist", extra={"event": "address_filter.blacklist_add", "address": address})

    def remove_from_blacklist(self, address: str):
        if not address:
            raise ValueError("Address cannot be empty.")
        if address in self.blacklist:
            self.blacklist.remove(address)
            logger.info("Address removed from blacklist", extra={"event": "address_filter.blacklist_remove", "address": address})
        else:
            logger.info("Address not found in blacklist", extra={"event": "address_filter.blacklist_missing", "address": address})

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
            logger.warning("Address blacklisted, access denied", extra={"event": "address_filter.denied_blacklist", "address": address})
            return False

        if self.enable_whitelist:
            if address in self.whitelist:
                logger.info("Address whitelisted, access granted", extra={"event": "address_filter.allowed_whitelist", "address": address})
                return True
            else:
                logger.warning("Address not whitelisted, access denied", extra={"event": "address_filter.denied_not_whitelisted", "address": address})
                return False
        else:
            # Whitelist is not enabled, so all non-blacklisted addresses are allowed
            logger.info("Address allowed (whitelist disabled)", extra={"event": "address_filter.allowed_default", "address": address})
            return True

if __name__ == "__main__":
    raise SystemExit("AddressFilter demo removed; use unit tests instead.")
