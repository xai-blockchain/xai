"""
Contract Upgradability - Proxy Patterns.

Implements industry-standard proxy patterns for contract upgradability:
- Transparent Proxy (EIP-1967)
- UUPS Proxy (EIP-1822)
- Beacon Proxy (multiple contracts, single upgrade)
- Diamond Proxy (EIP-2535)

Security features:
- Admin-only upgrades
- Storage collision prevention (EIP-1967 slots)
- Implementation validation
- Upgrade authorization checks
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from ..vm.exceptions import VMExecutionError

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)

# EIP-1967 Storage Slots (keccak256 hash - 1 to avoid storage collisions)
# These are standardized slots used by all major proxy implementations
EIP1967_IMPLEMENTATION_SLOT = int.from_bytes(
    bytes.fromhex("360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"),
    "big"
)  # keccak256("eip1967.proxy.implementation") - 1

EIP1967_ADMIN_SLOT = int.from_bytes(
    bytes.fromhex("b53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"),
    "big"
)  # keccak256("eip1967.proxy.admin") - 1

EIP1967_BEACON_SLOT = int.from_bytes(
    bytes.fromhex("a3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"),
    "big"
)  # keccak256("eip1967.proxy.beacon") - 1

class ProxyType(Enum):
    """Types of proxy patterns."""
    TRANSPARENT = "transparent"
    UUPS = "uups"
    BEACON = "beacon"
    DIAMOND = "diamond"

@dataclass
class ImplementationInfo:
    """Information about a contract implementation."""
    address: str
    version: int
    deployed_at: float
    bytecode_hash: str
    initializer: str | None = None
    initialized: bool = False

@dataclass
class UpgradeHistory:
    """Record of an upgrade event."""
    from_implementation: str
    to_implementation: str
    timestamp: float
    upgrader: str
    version: int

@dataclass
class TransparentProxy:
    """
    Transparent Proxy Pattern (EIP-1967).

    Key characteristics:
    - Admin can only call upgrade functions
    - Non-admin calls are delegated to implementation
    - Clear separation between admin and user interactions
    - Used by OpenZeppelin TransparentUpgradeableProxy

    Security features:
    - Admin cannot accidentally trigger implementation functions
    - Implementation cannot clash with proxy functions
    - EIP-1967 storage slots prevent collisions
    """

    address: str = ""
    admin: str = ""
    implementation: str = ""

    # Storage for delegated state
    storage: dict[int, int] = field(default_factory=dict)

    # Version tracking
    version: int = 0
    upgrade_history: list[UpgradeHistory] = field(default_factory=list)

    # Initialization
    initialized: bool = False

    def __post_init__(self) -> None:
        """Initialize proxy."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"transparent_proxy:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Admin Functions ====================

    def upgrade_to(
        self,
        caller: str,
        new_implementation: str,
        data: bytes | None = None,
    ) -> bool:
        """
        Upgrade to a new implementation.

        Args:
            caller: Must be admin
            new_implementation: Address of new implementation
            data: Optional initialization data

        Returns:
            True if successful
        """
        self._require_admin(caller)

        if not new_implementation:
            raise VMExecutionError("Invalid implementation address")

        old_implementation = self.implementation
        self.implementation = new_implementation
        self.version += 1

        # Record upgrade
        self.upgrade_history.append(UpgradeHistory(
            from_implementation=old_implementation,
            to_implementation=new_implementation,
            timestamp=time.time(),
            upgrader=caller,
            version=self.version,
        ))

        logger.info(
            "Proxy upgraded",
            extra={
                "event": "proxy.upgraded",
                "proxy": self.address[:10],
                "old_impl": old_implementation[:10] if old_implementation else "none",
                "new_impl": new_implementation[:10],
                "version": self.version,
            }
        )

        # Call initializer if provided: record initializer digest and mark initialized
        if data:
            self.initialized = True
            self.storage[EIP1967_IMPLEMENTATION_SLOT] = int.from_bytes(
                hashlib.sha3_256(data).digest(), "big"
            )

        return True

    def upgrade_to_and_call(
        self,
        caller: str,
        new_implementation: str,
        data: bytes,
    ) -> bool:
        """
        Upgrade to new implementation and call initialization function.

        Args:
            caller: Must be admin
            new_implementation: Address of new implementation
            data: Initialization calldata

        Returns:
            True if successful
        """
        return self.upgrade_to(caller, new_implementation, data)

    def change_admin(self, caller: str, new_admin: str) -> bool:
        """
        Change the proxy admin.

        Args:
            caller: Must be current admin
            new_admin: Address of new admin

        Returns:
            True if successful
        """
        self._require_admin(caller)

        if not new_admin:
            raise VMExecutionError("New admin cannot be zero address")

        old_admin = self.admin
        self.admin = self._normalize(new_admin)

        logger.info(
            "Proxy admin changed",
            extra={
                "event": "proxy.admin_changed",
                "proxy": self.address[:10],
                "old_admin": old_admin[:10],
                "new_admin": new_admin[:10],
            }
        )

        return True

    # ==================== Delegation ====================

    def delegate_call(
        self,
        caller: str,
        calldata: bytes,
        implementations: dict[str, Any],
    ) -> Any:
        """
        Delegate call to implementation.

        For admin: Only proxy functions work
        For others: All calls delegated to implementation

        Args:
            caller: Message sender
            calldata: Call data
            implementations: Registry of implementation contracts

        Returns:
            Result of delegated call
        """
        # Admin can only call admin functions (handled separately)
        if self._normalize(caller) == self._normalize(self.admin):
            raise VMExecutionError(
                "Admin cannot call implementation functions. "
                "Use a different account or call via the implementation directly."
            )

        if not self.implementation:
            raise VMExecutionError("No implementation set")

        impl = implementations.get(self.implementation)
        if not impl:
            raise VMExecutionError(f"Implementation {self.implementation} not found")

        # In real EVM, this would be DELEGATECALL and the implementation executes
        # with proxy's storage context. Here we return a structured forwarding
        # directive that higher layers can act upon.
        return {
            "delegate_to": impl,
            "calldata": calldata,
            "proxy": self.address,
            "implementation": self.implementation,
        }

    # ==================== View Functions ====================

    def get_implementation(self) -> str:
        """Get current implementation address."""
        return self.implementation

    def get_admin(self) -> str:
        """Get current admin address."""
        return self.admin

    def get_version(self) -> int:
        """Get current version."""
        return self.version

    def get_upgrade_history(self) -> list[Dict]:
        """Get upgrade history."""
        return [
            {
                "from": h.from_implementation,
                "to": h.to_implementation,
                "timestamp": h.timestamp,
                "upgrader": h.upgrader,
                "version": h.version,
            }
            for h in self.upgrade_history
        ]

    # ==================== Helpers ====================

    def _normalize(self, address: str) -> str:
        return address.lower()

    def _require_admin(self, caller: str) -> None:
        if self._normalize(caller) != self._normalize(self.admin):
            raise VMExecutionError("Caller is not admin")

@dataclass
class UUPSProxy:
    """
    UUPS (Universal Upgradeable Proxy Standard) - EIP-1822.

    Key characteristics:
    - Upgrade logic in implementation, not proxy
    - Smaller proxy contract (cheaper deployment)
    - Implementation must include upgrade mechanism
    - Risk: If upgrade function is removed, proxy is stuck

    Security features:
    - Authorization check in implementation
    - Can add additional upgrade guards
    - EIP-1967 storage slots
    """

    address: str = ""
    implementation: str = ""

    # Storage for delegated state
    storage: dict[int, int] = field(default_factory=dict)

    # Version tracking
    version: int = 0
    upgrade_history: list[UpgradeHistory] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize proxy."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"uups_proxy:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    def upgrade_to(
        self,
        caller: str,
        new_implementation: str,
        authorize_upgrade: Callable[[str, str], bool],
    ) -> bool:
        """
        Upgrade to new implementation.

        Note: In UUPS, this function lives in the implementation.
        The proxy only holds minimal logic.

        Args:
            caller: Message sender
            new_implementation: New implementation address
            authorize_upgrade: Function to check authorization

        Returns:
            True if successful
        """
        # Authorization check (implemented in the implementation contract)
        if not authorize_upgrade(caller, new_implementation):
            raise VMExecutionError("Unauthorized upgrade")

        old_implementation = self.implementation
        self.implementation = new_implementation
        self.version += 1

        self.upgrade_history.append(UpgradeHistory(
            from_implementation=old_implementation,
            to_implementation=new_implementation,
            timestamp=time.time(),
            upgrader=caller,
            version=self.version,
        ))

        logger.info(
            "UUPS proxy upgraded",
            extra={
                "event": "uups.upgraded",
                "proxy": self.address[:10],
                "new_impl": new_implementation[:10],
                "version": self.version,
            }
        )

        return True

    def get_implementation(self) -> str:
        """Get current implementation."""
        return self.implementation

@dataclass
class UUPSImplementation:
    """
    Base class for UUPS-upgradeable implementations.

    Implementations must inherit from this to be UUPS-compatible.
    """

    owner: str = ""

    def authorize_upgrade(self, caller: str, new_implementation: str) -> bool:
        """
        Check if upgrade is authorized.

        Override this for custom authorization logic.

        Args:
            caller: Address requesting upgrade
            new_implementation: Proposed new implementation

        Returns:
            True if authorized
        """
        # Default: only owner can upgrade
        return caller.lower() == self.owner.lower()

    def _check_not_delegated(self) -> None:
        """
        Security check to ensure we're not being called via delegatecall
        for sensitive operations.
        """
        # In real implementation, would check address(this)
        pass

@dataclass
class UpgradeableBeacon:
    """
    Beacon Proxy Pattern.

    Key characteristics:
    - Multiple proxies can share a single beacon
    - Single upgrade updates all proxies at once
    - Useful for factory-deployed contracts
    - More gas efficient for many proxies

    Example use case:
    - ERC20 token factory where all tokens use same logic
    - NFT collections with shared implementation
    """

    address: str = ""
    owner: str = ""
    implementation: str = ""

    # Proxies using this beacon
    beacon_proxies: list[str] = field(default_factory=list)

    # Version tracking
    version: int = 0

    def __post_init__(self) -> None:
        """Initialize beacon."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"beacon:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    def upgrade_to(self, caller: str, new_implementation: str) -> bool:
        """
        Upgrade the beacon implementation.

        This upgrades ALL proxies pointing to this beacon.

        Args:
            caller: Must be owner
            new_implementation: New implementation address

        Returns:
            True if successful
        """
        self._require_owner(caller)

        if not new_implementation:
            raise VMExecutionError("Invalid implementation address")

        old_implementation = self.implementation
        self.implementation = new_implementation
        self.version += 1

        logger.info(
            "Beacon upgraded",
            extra={
                "event": "beacon.upgraded",
                "beacon": self.address[:10],
                "new_impl": new_implementation[:10],
                "proxy_count": len(self.beacon_proxies),
            }
        )

        return True

    def get_implementation(self) -> str:
        """Get current implementation."""
        return self.implementation

    def register_proxy(self, proxy_address: str) -> None:
        """Register a proxy using this beacon."""
        if proxy_address not in self.beacon_proxies:
            self.beacon_proxies.append(proxy_address)

    def _require_owner(self, caller: str) -> None:
        if caller.lower() != self.owner.lower():
            raise VMExecutionError("Caller is not owner")

@dataclass
class BeaconProxy:
    """
    Proxy that uses a beacon for implementation lookup.

    Instead of storing implementation directly, looks up from beacon.
    """

    address: str = ""
    beacon: str = ""

    # Storage for delegated state
    storage: dict[int, int] = field(default_factory=dict)

    # Initialization tracking
    initialized: bool = False

    def __post_init__(self) -> None:
        """Initialize beacon proxy."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"beacon_proxy:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    def get_implementation(self, beacons: dict[str, UpgradeableBeacon]) -> str:
        """
        Get implementation from beacon.

        Args:
            beacons: Registry of beacons

        Returns:
            Implementation address
        """
        beacon = beacons.get(self.beacon)
        if not beacon:
            raise VMExecutionError(f"Beacon {self.beacon} not found")
        return beacon.get_implementation()

# Diamond Proxy (EIP-2535) - Most flexible but complex

@dataclass
class FacetCut:
    """Describes changes to diamond facets."""
    facet_address: str
    action: str  # "add", "replace", "remove"
    function_selectors: list[bytes]  # 4-byte function selectors

@dataclass
class DiamondFacet:
    """A facet (module) of a diamond."""
    address: str
    function_selectors: list[bytes]

@dataclass
class DiamondProxy:
    """
    Diamond Proxy Pattern (EIP-2535).

    Key characteristics:
    - Multiple implementation contracts (facets)
    - Function-level granularity for upgrades
    - Unlimited contract size
    - Modular architecture

    Use cases:
    - Large contracts exceeding size limit
    - Modular upgradeable systems
    - Fine-grained access control

    Components:
    - Diamond: Main proxy contract
    - Facets: Implementation contracts
    - Loupe: Introspection functions
    """

    address: str = ""
    owner: str = ""

    # Function selector -> facet address mapping
    selector_to_facet: dict[bytes, str] = field(default_factory=dict)

    # Facet address -> selectors mapping (for loupe)
    facet_selectors: dict[str, list[bytes]] = field(default_factory=dict)

    # All facet addresses
    facet_addresses: list[str] = field(default_factory=list)

    # Storage
    storage: dict[int, int] = field(default_factory=dict)

    # Version tracking
    version: int = 0

    def __post_init__(self) -> None:
        """Initialize diamond."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"diamond:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== Diamond Cut ====================

    def diamond_cut(
        self,
        caller: str,
        facet_cuts: list[FacetCut],
        init_address: str | None = None,
        init_calldata: bytes | None = None,
    ) -> bool:
        """
        Add, replace, or remove facet functions.

        This is the main upgrade mechanism for diamonds.

        Args:
            caller: Must be owner
            facet_cuts: List of facet changes
            init_address: Optional initialization contract
            init_calldata: Optional initialization data

        Returns:
            True if successful
        """
        self._require_owner(caller)

        for cut in facet_cuts:
            if cut.action == "add":
                self._add_facet_selectors(cut.facet_address, cut.function_selectors)
            elif cut.action == "replace":
                self._replace_facet_selectors(cut.facet_address, cut.function_selectors)
            elif cut.action == "remove":
                self._remove_facet_selectors(cut.function_selectors)
            else:
                raise VMExecutionError(f"Invalid facet cut action: {cut.action}")

        self.version += 1

        logger.info(
            "Diamond cut executed",
            extra={
                "event": "diamond.cut",
                "diamond": self.address[:10],
                "cuts": len(facet_cuts),
                "version": self.version,
            }
        )

        # Execute initialization if provided
        if init_address and init_calldata:
            # Would delegatecall init_address with init_calldata
            pass

        return True

    def _add_facet_selectors(self, facet: str, selectors: list[bytes]) -> None:
        """Add new function selectors."""
        for selector in selectors:
            if selector in self.selector_to_facet:
                raise VMExecutionError(
                    f"Selector {selector.hex()} already exists"
                )
            self.selector_to_facet[selector] = facet

        # Update facet tracking
        if facet not in self.facet_addresses:
            self.facet_addresses.append(facet)
            self.facet_selectors[facet] = []

        self.facet_selectors[facet].extend(selectors)

    def _replace_facet_selectors(self, facet: str, selectors: list[bytes]) -> None:
        """Replace existing function selectors."""
        for selector in selectors:
            if selector not in self.selector_to_facet:
                raise VMExecutionError(
                    f"Selector {selector.hex()} does not exist"
                )

            old_facet = self.selector_to_facet[selector]
            if old_facet in self.facet_selectors:
                self.facet_selectors[old_facet] = [
                    s for s in self.facet_selectors[old_facet]
                    if s != selector
                ]

            self.selector_to_facet[selector] = facet

        # Update facet tracking
        if facet not in self.facet_addresses:
            self.facet_addresses.append(facet)
            self.facet_selectors[facet] = []

        self.facet_selectors[facet].extend(selectors)

        # Clean up empty facets
        self._cleanup_empty_facets()

    def _remove_facet_selectors(self, selectors: list[bytes]) -> None:
        """Remove function selectors."""
        for selector in selectors:
            if selector not in self.selector_to_facet:
                raise VMExecutionError(
                    f"Selector {selector.hex()} does not exist"
                )

            facet = self.selector_to_facet[selector]
            del self.selector_to_facet[selector]

            if facet in self.facet_selectors:
                self.facet_selectors[facet] = [
                    s for s in self.facet_selectors[facet]
                    if s != selector
                ]

        self._cleanup_empty_facets()

    def _cleanup_empty_facets(self) -> None:
        """Remove facets with no selectors."""
        empty_facets = [
            addr for addr, selectors in self.facet_selectors.items()
            if not selectors
        ]
        for facet in empty_facets:
            del self.facet_selectors[facet]
            self.facet_addresses.remove(facet)

    # ==================== Diamond Loupe (EIP-2535) ====================

    def facets(self) -> list[DiamondFacet]:
        """
        Get all facets and their selectors.

        Part of DiamondLoupe interface.
        """
        return [
            DiamondFacet(address=addr, function_selectors=selectors)
            for addr, selectors in self.facet_selectors.items()
        ]

    def facet_function_selectors(self, facet: str) -> list[bytes]:
        """
        Get all function selectors for a facet.

        Part of DiamondLoupe interface.
        """
        return self.facet_selectors.get(facet, [])

    def facet_addresses_list(self) -> list[str]:
        """
        Get all facet addresses.

        Part of DiamondLoupe interface.
        """
        return self.facet_addresses.copy()

    def facet_address(self, selector: bytes) -> str | None:
        """
        Get the facet that implements a function selector.

        Part of DiamondLoupe interface.
        """
        return self.selector_to_facet.get(selector)

    # ==================== Delegation ====================

    def delegate_call(
        self,
        calldata: bytes,
        facet_implementations: dict[str, Any],
    ) -> Any:
        """
        Route call to appropriate facet based on selector.

        Args:
            calldata: Call data (first 4 bytes are selector)
            facet_implementations: Registry of facet contracts

        Returns:
            Result of delegated call
        """
        if len(calldata) < 4:
            raise VMExecutionError("Invalid calldata")

        selector = bytes(calldata[:4])
        facet_address = self.selector_to_facet.get(selector)

        if not facet_address:
            raise VMExecutionError(
                f"Function with selector {selector.hex()} not found"
            )

        facet = facet_implementations.get(facet_address)
        if not facet:
            raise VMExecutionError(f"Facet {facet_address} not found")

        # In real EVM, would DELEGATECALL to facet
        return facet

    # ==================== Helpers ====================

    def _require_owner(self, caller: str) -> None:
        if caller.lower() != self.owner.lower():
            raise VMExecutionError("Caller is not owner")

@dataclass
class ProxyFactory:
    """
    Factory for deploying proxy contracts.

    Provides easy creation of different proxy types.
    """

    name: str = "XAI Proxy Factory"
    owner: str = ""

    # Deployed proxies
    proxies: dict[str, Any] = field(default_factory=dict)

    # Beacons
    beacons: dict[str, UpgradeableBeacon] = field(default_factory=dict)

    # Statistics
    total_proxies: int = 0

    def deploy_transparent_proxy(
        self,
        caller: str,
        implementation: str,
        admin: str,
    ) -> TransparentProxy:
        """
        Deploy a new transparent proxy.

        Args:
            caller: Deployer
            implementation: Implementation address
            admin: Proxy admin address

        Returns:
            Deployed proxy
        """
        proxy = TransparentProxy(
            admin=admin,
            implementation=implementation,
        )

        self.proxies[proxy.address] = proxy
        self.total_proxies += 1

        logger.info(
            "Transparent proxy deployed",
            extra={
                "event": "factory.proxy_deployed",
                "type": "transparent",
                "proxy": proxy.address[:10],
                "impl": implementation[:10],
            }
        )

        return proxy

    def deploy_uups_proxy(
        self,
        caller: str,
        implementation: str,
    ) -> UUPSProxy:
        """
        Deploy a new UUPS proxy.

        Args:
            caller: Deployer
            implementation: Implementation address

        Returns:
            Deployed proxy
        """
        proxy = UUPSProxy(implementation=implementation)

        self.proxies[proxy.address] = proxy
        self.total_proxies += 1

        logger.info(
            "UUPS proxy deployed",
            extra={
                "event": "factory.proxy_deployed",
                "type": "uups",
                "proxy": proxy.address[:10],
            }
        )

        return proxy

    def deploy_beacon(
        self,
        caller: str,
        implementation: str,
    ) -> UpgradeableBeacon:
        """
        Deploy a new upgradeable beacon.

        Args:
            caller: Deployer (becomes owner)
            implementation: Initial implementation

        Returns:
            Deployed beacon
        """
        beacon = UpgradeableBeacon(
            owner=caller,
            implementation=implementation,
        )

        self.beacons[beacon.address] = beacon

        logger.info(
            "Beacon deployed",
            extra={
                "event": "factory.beacon_deployed",
                "beacon": beacon.address[:10],
                "impl": implementation[:10],
            }
        )

        return beacon

    def deploy_beacon_proxy(
        self,
        caller: str,
        beacon_address: str,
    ) -> BeaconProxy:
        """
        Deploy a proxy using a beacon.

        Args:
            caller: Deployer
            beacon_address: Address of beacon to use

        Returns:
            Deployed beacon proxy
        """
        beacon = self.beacons.get(beacon_address)
        if not beacon:
            raise VMExecutionError(f"Beacon {beacon_address} not found")

        proxy = BeaconProxy(beacon=beacon_address)
        beacon.register_proxy(proxy.address)

        self.proxies[proxy.address] = proxy
        self.total_proxies += 1

        logger.info(
            "Beacon proxy deployed",
            extra={
                "event": "factory.proxy_deployed",
                "type": "beacon",
                "proxy": proxy.address[:10],
                "beacon": beacon_address[:10],
            }
        )

        return proxy

    def deploy_diamond(
        self,
        caller: str,
        initial_facets: list[FacetCut] | None = None,
    ) -> DiamondProxy:
        """
        Deploy a new diamond proxy.

        Args:
            caller: Deployer (becomes owner)
            initial_facets: Initial facet configuration

        Returns:
            Deployed diamond
        """
        diamond = DiamondProxy(owner=caller)

        if initial_facets:
            diamond.diamond_cut(caller, initial_facets)

        self.proxies[diamond.address] = diamond
        self.total_proxies += 1

        logger.info(
            "Diamond deployed",
            extra={
                "event": "factory.proxy_deployed",
                "type": "diamond",
                "diamond": diamond.address[:10],
            }
        )

        return diamond

    def get_proxy(self, address: str) -> Any | None:
        """Get a proxy by address."""
        return self.proxies.get(address)

    def get_beacon(self, address: str) -> UpgradeableBeacon | None:
        """Get a beacon by address."""
        return self.beacons.get(address)
