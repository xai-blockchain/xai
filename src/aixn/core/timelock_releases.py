"""
XAI Time-Locked Software Releases

Stores software in genesis block with activation timestamps
Software automatically becomes available when timestamp passes
"""

import time
import base64
import hashlib
from typing import Dict, List, Optional


class TimeLockRelease:
    """Individual time-locked software release"""

    def __init__(
        self,
        component: str,
        code: str,
        activation_timestamp: int,
        version: str,
        description: str = "",
    ):
        self.component = component
        self.code = code  # Base64 encoded source code
        self.activation_timestamp = activation_timestamp
        self.version = version
        self.description = description
        self.code_hash = hashlib.sha256(code.encode()).hexdigest()

    def is_active(self) -> bool:
        """Check if release is active"""
        return time.time() >= self.activation_timestamp

    def get_code(self) -> Optional[str]:
        """Get code if active, None if locked"""
        if self.is_active():
            return base64.b64decode(self.code).decode("utf-8")
        return None

    def to_dict(self) -> Dict:
        """Convert to dictionary for genesis block"""
        return {
            "component": self.component,
            "code": self.code,  # Keep encoded in blockchain
            "activation_timestamp": self.activation_timestamp,
            "version": self.version,
            "description": self.description,
            "code_hash": self.code_hash,
        }

    def to_public_dict(self) -> Dict:
        """Public info (without code if not active)"""
        return {
            "component": self.component,
            "version": self.version,
            "description": self.description,
            "activation_timestamp": self.activation_timestamp,
            "is_active": self.is_active(),
            "code_hash": self.code_hash,
            "days_until_activation": (
                (self.activation_timestamp - time.time()) / 86400 if not self.is_active() else 0
            ),
        }


class SoftwareReleaseManager:
    """Manages time-locked software releases in blockchain"""

    def __init__(self, genesis_releases: List[Dict] = None):
        self.releases = []

        if genesis_releases:
            for release_data in genesis_releases:
                release = TimeLockRelease(
                    component=release_data["component"],
                    code=release_data["code"],
                    activation_timestamp=release_data["activation_timestamp"],
                    version=release_data["version"],
                    description=release_data.get("description", ""),
                )
                self.releases.append(release)

    def get_available_software(self) -> List[Dict]:
        """Get all currently active software releases"""
        active = [r for r in self.releases if r.is_active()]

        return [
            {
                "component": r.component,
                "version": r.version,
                "code": r.get_code(),  # Decoded source code
                "code_hash": r.code_hash,
            }
            for r in active
        ]

    def get_upcoming_releases(self) -> List[Dict]:
        """Get info about locked releases (no code)"""
        upcoming = [r for r in self.releases if not r.is_active()]
        return [r.to_public_dict() for r in upcoming]

    def get_all_releases_info(self) -> Dict:
        """Get comprehensive release information"""
        return {
            "available_now": self.get_available_software(),
            "upcoming": self.get_upcoming_releases(),
            "total_releases": len(self.releases),
        }


def create_genesis_software_releases() -> List[Dict]:
    """
    Create time-locked software releases for genesis block

    Returns list of releases to embed in genesis block
    """

    releases = []

    # Read GUI code
    import os

    gui_file = os.path.join(os.path.dirname(__file__), "simple_swap_gui.py")

    if os.path.exists(gui_file):
        with open(gui_file, "r") as f:
            gui_code = f.read()

        # Encode GUI code
        encoded_gui = base64.b64encode(gui_code.encode()).decode()

        # Release 1: Swap GUI (activate 3 months after genesis)
        release_1 = TimeLockRelease(
            component="simple_swap_gui",
            code=encoded_gui,
            activation_timestamp=1704067200 + (90 * 86400),  # Genesis + 90 days
            version="1.0.0",
            description="Simple swap GUI for atomic swaps",
        )
        releases.append(release_1.to_dict())

    # Release 2: Advanced trading tools (6 months)
    # (Placeholder - could add more later)
    release_2 = TimeLockRelease(
        component="advanced_trading",
        code=base64.b64encode(b"# Advanced trading tools TBD").decode(),
        activation_timestamp=1704067200 + (180 * 86400),  # Genesis + 180 days
        version="1.0.0",
        description="Advanced trading and analytics tools",
    )
    releases.append(release_2.to_dict())

    # Release 3: Mobile wallet code (9 months)
    release_3 = TimeLockRelease(
        component="mobile_wallet",
        code=base64.b64encode(b"# Mobile wallet code TBD").decode(),
        activation_timestamp=1704067200 + (270 * 86400),  # Genesis + 270 days
        version="1.0.0",
        description="Mobile wallet application",
    )
    releases.append(release_3.to_dict())

    return releases


def verify_release_integrity(release_data: Dict, expected_hash: str) -> bool:
    """
    Verify software release hasn't been tampered with

    Args:
        release_data: Release from blockchain
        expected_hash: Expected code hash

    Returns:
        bool: True if valid
    """
    actual_hash = hashlib.sha256(release_data["code"].encode()).hexdigest()
    return actual_hash == expected_hash


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("XAI Time-Locked Software Releases")
    print("=" * 70)

    # Create genesis releases
    genesis_releases = create_genesis_software_releases()

    print(f"\nGenesis Block Software Releases: {len(genesis_releases)}")
    print("-" * 70)

    for release in genesis_releases:
        from datetime import datetime

        activation_date = datetime.fromtimestamp(release["activation_timestamp"]).strftime(
            "%Y-%m-%d"
        )

        print(f"\nComponent: {release['component']}")
        print(f"  Version: {release['version']}")
        print(f"  Description: {release['description']}")
        print(f"  Activation: {activation_date}")
        print(f"  Code Hash: {release['code_hash'][:32]}...")
        print(f"  Code Size: {len(release['code'])} bytes (base64)")

    # Initialize manager
    print("\n\nInitializing Release Manager...")
    print("-" * 70)

    manager = SoftwareReleaseManager(genesis_releases)

    # Check current status
    status = manager.get_all_releases_info()

    print(f"\nCurrently Available: {len(status['available_now'])}")
    for release in status["available_now"]:
        print(f"  - {release['component']} v{release['version']}")

    print(f"\nUpcoming Releases: {len(status['upcoming'])}")
    for release in status["upcoming"]:
        print(f"  - {release['component']} v{release['version']}")
        print(f"    Activates in {release['days_until_activation']:.1f} days")

    # Test verification
    print("\n\nTesting Integrity Verification...")
    print("-" * 70)

    test_release = genesis_releases[0]
    is_valid = verify_release_integrity(test_release, test_release["code_hash"])
    print(f"Release integrity check: {'PASS' if is_valid else 'FAIL'}")

    print("\n" + "=" * 70)
    print("DEPLOYMENT PLAN")
    print("=" * 70)
    print(
        """
1. Embed these releases in genesis block
2. Release blockchain to public
3. Software automatically unlocks on schedule:
   - Month 3: Swap GUI available
   - Month 6: Advanced trading tools
   - Month 9: Mobile wallet

Nobody can say YOU released the software.
The blockchain protocol released it automatically.
You just created the protocol.
"""
    )
