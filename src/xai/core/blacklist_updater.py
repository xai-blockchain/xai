"""
XAI Blacklist Auto-Updater

Year 1: PROMPTED (optional) - nodes reminded to update blacklists
After 1 Year: Community vote decides if mandatory and frequency
"""

from abc import ABC, abstractmethod
import os
import time
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Set
import xml.etree.ElementTree as ET

import logging
logger = logging.getLogger(__name__)


import requests


BLACKLIST_USE_MOCK = os.getenv("XAI_BLACKLIST_USE_MOCK", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
}
BLACKLIST_HTTP_TIMEOUT = int(os.getenv("XAI_BLACKLIST_HTTP_TIMEOUT", "30"))
COMMUNITY_VOTE_THRESHOLD = int(os.getenv("XAI_COMMUNITY_VOTE_THRESHOLD", "7"))


class BlacklistSource(ABC):
    """Base class for blacklist sources"""

    def __init__(self, name: str, url: str, update_frequency_hours: int):
        self.name = name
        self.url = url
        self.update_frequency = update_frequency_hours
        self.last_update = 0
        self.cached_addresses = set()

    def needs_update(self) -> bool:
        """Check if update is needed"""
        elapsed = time.time() - self.last_update
        return elapsed > (self.update_frequency * 3600)

    @abstractmethod
    def fetch_addresses(self) -> Set[str]:
        """Fetch and return addresses exposed by this source."""

    def update(self) -> Dict:
        """Update blacklist from source"""
        if not self.needs_update():
            return {
                "source": self.name,
                "status": "cached",
                "count": len(self.cached_addresses),
                "last_update": self.last_update,
            }

        try:
            addresses = self.fetch_addresses()
            self.cached_addresses = addresses
            self.last_update = time.time()

            return {
                "source": self.name,
                "status": "updated",
                "count": len(addresses),
                "last_update": self.last_update,
            }
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.warning(
                "Exception in update",
                extra={
                    "error_type": "Exception",
                    "error": str(e),
                    "function": "update"
                }
            )
            return {
                "source": self.name,
                "status": "failed",
                "error": str(e),
                "last_update": self.last_update,
            }


class OFACBlacklist(BlacklistSource):
    """OFAC Sanctions List"""

    def __init__(self):
        super().__init__(
            name="OFAC",
            url="https://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xml",
            update_frequency_hours=24,
        )

    def fetch_addresses(self) -> Set[str]:
        """
        Fetch OFAC SDN (Specially Designated Nationals) list

        NOTE: This makes external HTTP request when run by nodes
        Mocks are returned by default and real data is fetched when
        XAI_BLACKLIST_USE_MOCK=0 (or False) in the environment.
        """

        if BLACKLIST_USE_MOCK:
            return {"OFAC_MOCK_ADDRESS_1", "OFAC_MOCK_ADDRESS_2", "OFAC_MOCK_ADDRESS_3"}

        response = requests.get(self.url, timeout=BLACKLIST_HTTP_TIMEOUT)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        addresses = set()

        for entry in root.findall(".//sdnEntry"):
            for id_entry in entry.findall(".//ID"):
                id_type = id_entry.find("idType")
                id_number = id_entry.find("idNumber")

                if (
                    id_type is not None
                    and id_type.text
                    and "Digital Currency" in id_type.text
                    and id_number is not None
                    and id_number.text
                ):
                    addresses.add(id_number.text.strip())

        return addresses


class CommunityBlacklist(BlacklistSource):
    """Community-governed blacklist (multi-sig voting)"""

    def __init__(self):
        super().__init__(
            name="Community",
            update_frequency_hours=6,
        )

    def fetch_addresses(self) -> Set[str]:
        """
        Fetch community-voted blacklist

        NOTE: Real HTTP requests are optional and controlled by environment.
        """

        if BLACKLIST_USE_MOCK:
            return {"COMMUNITY_MOCK_1", "COMMUNITY_MOCK_2"}

        response = requests.get(self.url, timeout=BLACKLIST_HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        addresses = set()

        for entry in data.get("blacklisted_addresses", []):
            if entry.get("votes", 0) >= COMMUNITY_VOTE_THRESHOLD:
                address = entry.get("address")
                if address:
                    addresses.add(address.strip())

        return addresses


class RansomwareTrackerBlacklist(BlacklistSource):
    """Known ransomware addresses"""

    def __init__(self):
        super().__init__(
            name="RansomwareTracker",
            url="https://ransomwaretracker.abuse.ch/downloads/RW_CRYPTO.txt",
            update_frequency_hours=24,
        )

    def fetch_addresses(self) -> Set[str]:
        """
        Fetch known ransomware payment addresses

        NOTE: Controlled by XAI_BLACKLIST_USE_MOCK for development.
        """

        if BLACKLIST_USE_MOCK:
            return {"RANSOMWARE_MOCK_1", "RANSOMWARE_MOCK_2"}

        response = requests.get(self.url, timeout=BLACKLIST_HTTP_TIMEOUT)
        response.raise_for_status()
        lines = response.text.splitlines()

        addresses = set()

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(",")
            if len(parts) >= 2:
                address = parts[1].strip()
                if address:
                    addresses.add(address)

        return addresses


class BlacklistManager:
    """
    Manages all blacklist sources
    Year 1: Optional, nodes prompted to update
    After 1 year: Community votes on mandate
    """

    def __init__(self):
        self.sources = [OFACBlacklist(), CommunityBlacklist(), RansomwareTrackerBlacklist()]

        # Governance settings
        self.genesis_time = 1704067200.0  # Nov 6, 2024
        self.governance_vote_time = self.genesis_time + (365 * 86400)  # 1 year later

        self.consolidated_blacklist = set()
        self.last_full_update = 0
        self.update_history = []

    def update_all_sources(self) -> Dict:
        """Update from all sources"""

        results = {
            "timestamp": time.time(),
            "sources": [],
            "total_addresses": 0,
            "new_addresses": 0,
        }

        old_count = len(self.consolidated_blacklist)

        for source in self.sources:
            result = source.update()
            results["sources"].append(result)

            if result["status"] == "updated":
                self.consolidated_blacklist.update(source.cached_addresses)

        # Also add cached addresses from sources that didn't update
        for source in self.sources:
            self.consolidated_blacklist.update(source.cached_addresses)

        results["total_addresses"] = len(self.consolidated_blacklist)
        results["new_addresses"] = len(self.consolidated_blacklist) - old_count

        self.last_full_update = time.time()
        self.update_history.append(results)

        # Keep only last 100 updates in history
        if len(self.update_history) > 100:
            self.update_history = self.update_history[-100:]

        return results

    def get_blacklist(self) -> Set[str]:
        """Get current consolidated blacklist"""
        return self.consolidated_blacklist.copy()

    def is_blacklisted(self, address: str) -> bool:
        """Check if address is blacklisted"""
        return address in self.consolidated_blacklist

    def get_blacklist_hash(self) -> str:
        """
        Get hash of current blacklist
        Used for consensus - nodes must have matching hash
        """
        sorted_addresses = sorted(list(self.consolidated_blacklist))
        data = "|".join(sorted_addresses)
        return hashlib.sha256(data.encode()).hexdigest()

    def get_update_status(self) -> Dict:
        """Get update status for all sources"""

        status = {
            "last_full_update": self.last_full_update,
            "hours_since_update": (time.time() - self.last_full_update) / 3600,
            "total_addresses": len(self.consolidated_blacklist),
            "blacklist_hash": self.get_blacklist_hash(),
            "sources": [],
        }

        for source in self.sources:
            status["sources"].append(
                {
                    "name": source.name,
                    "last_update": source.last_update,
                    "hours_since_update": (time.time() - source.last_update) / 3600,
                    "needs_update": source.needs_update(),
                    "address_count": len(source.cached_addresses),
                }
            )

        return status

    def is_update_current(self, max_hours: int = 48) -> bool:
        """
        Check if blacklist is current enough for consensus
        Nodes with stale blacklists get rejected
        """
        hours_since = (time.time() - self.last_full_update) / 3600
        return hours_since <= max_hours

    def export_blacklist(self, filepath: str):
        """Export blacklist to file"""
        data = {
            "updated": time.time(),
            "updated_readable": datetime.fromtimestamp(time.time()).isoformat(),
            "total_addresses": len(self.consolidated_blacklist),
            "blacklist_hash": self.get_blacklist_hash(),
            "addresses": sorted(list(self.consolidated_blacklist)),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def import_blacklist(self, filepath: str):
        """Import blacklist from file (for quick startup)"""
        with open(filepath, "r") as f:
            data = json.load(f)

        self.consolidated_blacklist = set(data["addresses"])
        self.last_full_update = data["updated"]


class ConsensusBlacklistValidator:
    """
    Validates nodes have current blacklist
    Rejects blocks from nodes with stale blacklists
    """

    def __init__(self, max_stale_hours: int = 48):
        self.max_stale_hours = max_stale_hours

    def validate_node_blacklist(
        self, node_blacklist_hash: str, node_last_update: float, current_blacklist_hash: str
    ) -> Dict:
        """
        Validate node's blacklist is current

        Returns validation result
        """

        hours_since = (time.time() - node_last_update) / 3600

        # Check if too stale
        if hours_since > self.max_stale_hours:
            return {
                "valid": False,
                "reason": "BLACKLIST_TOO_STALE",
                "hours_since_update": round(hours_since, 2),
                "max_allowed": self.max_stale_hours,
            }

        # Check if hash matches (same blacklist)
        if node_blacklist_hash != current_blacklist_hash:
            return {
                "valid": False,
                "reason": "BLACKLIST_MISMATCH",
                "node_hash": node_blacklist_hash[:16],
                "expected_hash": current_blacklist_hash[:16],
            }

        return {"valid": True, "hours_since_update": round(hours_since, 2)}


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI BLACKLIST AUTO-UPDATER")
    print("=" * 70)

    print("\nNOTE: Using mock data - no external API calls made")
    print("Nodes will fetch real data when running live\n")

    # Initialize manager
    manager = BlacklistManager()

    # Update all sources (uses mock data)
    print("Updating blacklist sources...")
    results = manager.update_all_sources()

    print(f"\nUpdate Results:")
    print(f"  Timestamp: {datetime.fromtimestamp(results['timestamp']).isoformat()}")
    print(f"  Total addresses: {results['total_addresses']}")
    print(f"  New addresses: {results['new_addresses']}")

    print(f"\nSource Status:")
    for source in results["sources"]:
        print(f"  {source['source']}: {source['status']} - {source.get('count', 0)} addresses")

    # Get status
    status = manager.get_update_status()
    print(f"\nCurrent Status:")
    print(f"  Blacklist Hash: {status['blacklist_hash'][:32]}...")
    print(f"  Hours since update: {status['hours_since_update']:.2f}")
    print(f"  Is current: {manager.is_update_current()}")

    # Test address check
    test_address = "OFAC_MOCK_ADDRESS_1"
    print(f"\nTest Address Check:")
    print(f"  Address: {test_address}")
    print(f"  Is blacklisted: {manager.is_blacklisted(test_address)}")

    # Test consensus validation
    validator = ConsensusBlacklistValidator()

    valid_result = validator.validate_node_blacklist(
        node_blacklist_hash=status["blacklist_hash"],
        node_last_update=time.time(),
        current_blacklist_hash=status["blacklist_hash"],
    )

    print(f"\nConsensus Validation (Current):")
    print(f"  Valid: {valid_result['valid']}")

    stale_result = validator.validate_node_blacklist(
        node_blacklist_hash=status["blacklist_hash"],
        node_last_update=time.time() - (50 * 3600),  # 50 hours old
        current_blacklist_hash=status["blacklist_hash"],
    )

    print(f"\nConsensus Validation (Stale):")
    print(f"  Valid: {stale_result['valid']}")
    print(f"  Reason: {stale_result.get('reason')}")

    print("\n" + "=" * 70)
