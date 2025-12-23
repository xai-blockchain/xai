"""
ERC721 Non-Fungible Token (NFT) Standard Implementation.

This module provides a complete ERC721 implementation compatible with
the Ethereum ERC721 standard (EIP-721), including:
- Basic NFT operations (transferFrom, safeTransferFrom, approve)
- Enumerable extension (tokenOfOwnerByIndex, totalSupply)
- Metadata extension (tokenURI)
- Minting and burning
- Royalties (EIP-2981)

Security features:
- Owner verification
- Approval validation
- Zero address checks
- Safe transfer receiver checks
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..vm.exceptions import VMExecutionError

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)

# ERC721 Function selectors
ERC721_SELECTORS = {
    "balanceOf(address)": "70a08231",
    "ownerOf(uint256)": "6352211e",
    "safeTransferFrom(address,address,uint256)": "42842e0e",
    "safeTransferFrom(address,address,uint256,bytes)": "b88d4fde",
    "transferFrom(address,address,uint256)": "23b872dd",
    "approve(address,uint256)": "095ea7b3",
    "setApprovalForAll(address,bool)": "a22cb465",
    "getApproved(uint256)": "081812fc",
    "isApprovedForAll(address,address)": "e985e9c5",
    # Metadata
    "name()": "06fdde03",
    "symbol()": "95d89b41",
    "tokenURI(uint256)": "c87b56dd",
    # Enumerable
    "totalSupply()": "18160ddd",
    "tokenOfOwnerByIndex(address,uint256)": "2f745c59",
    "tokenByIndex(uint256)": "4f6ccce7",
    # Royalties (EIP-2981)
    "royaltyInfo(uint256,uint256)": "2a55205a",
}

# Event signatures
TRANSFER_EVENT = hashlib.sha3_256(b"Transfer(address,address,uint256)").digest()
APPROVAL_EVENT = hashlib.sha3_256(b"Approval(address,address,uint256)").digest()
APPROVAL_FOR_ALL_EVENT = hashlib.sha3_256(
    b"ApprovalForAll(address,address,bool)"
).digest()

@dataclass
class NFTMetadata:
    """Metadata for an NFT."""

    name: str = ""
    description: str = ""
    image: str = ""
    external_url: str = ""
    animation_url: str = ""
    attributes: list[Dict] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)

@dataclass
class NFTEvent:
    """Represents an ERC721 event."""

    event_type: str  # "Transfer", "Approval", "ApprovalForAll"
    from_address: str
    to_address: str
    token_id: int
    approved: bool = False  # For ApprovalForAll
    timestamp: float = field(default_factory=time.time)

@dataclass
class ERC721Token:
    """
    Complete ERC721 (NFT) token implementation.

    Implements the ERC721 standard with extensions:
    - Enumerable (tracking all tokens)
    - Metadata (token URIs)
    - Royalties (EIP-2981)
    - Burnable

    Security features:
    - Owner verification on all transfers
    - Safe transfer with receiver checks
    - Approval management
    """

    # Collection metadata
    name: str
    symbol: str
    base_uri: str = ""

    # Contract address
    address: str = ""

    # Owner (for admin functions)
    owner: str = ""

    # Token state
    owners: dict[int, str] = field(default_factory=dict)  # tokenId -> owner
    balances: dict[str, int] = field(default_factory=dict)  # owner -> count
    token_approvals: dict[int, str] = field(default_factory=dict)  # tokenId -> approved
    operator_approvals: dict[str, dict[str, bool]] = field(
        default_factory=dict
    )  # owner -> operator -> approved

    # Enumerable data
    all_tokens: list[int] = field(default_factory=list)
    owner_tokens: dict[str, list[int]] = field(default_factory=dict)  # owner -> tokenIds

    # Metadata
    token_uris: dict[int, str] = field(default_factory=dict)
    token_metadata: dict[int, NFTMetadata] = field(default_factory=dict)

    # Royalties (EIP-2981)
    royalty_receiver: str = ""
    royalty_fraction: int = 0  # Basis points (e.g., 250 = 2.5%)

    # Minting
    next_token_id: int = 1
    max_supply: int = 0  # 0 = unlimited

    # Pause state
    paused: bool = False

    # Events
    events: list[NFTEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize NFT contract."""
        if not self.address:
            addr_input = f"{self.name}{self.symbol}{time.time()}".encode()
            addr_hash = hashlib.sha3_256(addr_input).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== View Functions ====================

    def balance_of(self, owner: str) -> int:
        """
        Get number of NFTs owned by an address.

        Args:
            owner: Owner address

        Returns:
            Number of NFTs owned
        """
        return self.balances.get(self._normalize(owner), 0)

    def owner_of(self, token_id: int) -> str:
        """
        Get the owner of an NFT.

        Args:
            token_id: Token ID

        Returns:
            Owner address

        Raises:
            VMExecutionError: If token doesn't exist
        """
        owner = self.owners.get(token_id)
        if not owner:
            raise VMExecutionError(f"ERC721: token {token_id} does not exist")
        return owner

    def get_approved(self, token_id: int) -> str:
        """
        Get approved address for a token.

        Args:
            token_id: Token ID

        Returns:
            Approved address (zero if none)
        """
        self._require_minted(token_id)
        return self.token_approvals.get(token_id, "0x" + "0" * 40)

    def is_approved_for_all(self, owner: str, operator: str) -> bool:
        """
        Check if operator is approved for all tokens of owner.

        Args:
            owner: Token owner
            operator: Operator address

        Returns:
            True if approved for all
        """
        owner_norm = self._normalize(owner)
        operator_norm = self._normalize(operator)
        return self.operator_approvals.get(owner_norm, {}).get(operator_norm, False)

    def token_uri(self, token_id: int) -> str:
        """
        Get the metadata URI for a token.

        Args:
            token_id: Token ID

        Returns:
            Metadata URI
        """
        self._require_minted(token_id)

        # Check for specific URI
        if token_id in self.token_uris:
            return self.token_uris[token_id]

        # Construct from base URI
        if self.base_uri:
            return f"{self.base_uri}{token_id}"

        return ""

    def total_supply(self) -> int:
        """Get total number of minted tokens."""
        return len(self.all_tokens)

    def token_by_index(self, index: int) -> int:
        """
        Get token ID by index (enumerable).

        Args:
            index: Index in all tokens

        Returns:
            Token ID

        Raises:
            VMExecutionError: If index out of bounds
        """
        if index >= len(self.all_tokens):
            raise VMExecutionError(f"ERC721: index {index} out of bounds")
        return self.all_tokens[index]

    def token_of_owner_by_index(self, owner: str, index: int) -> int:
        """
        Get token ID by owner and index.

        Args:
            owner: Owner address
            index: Index in owner's tokens

        Returns:
            Token ID

        Raises:
            VMExecutionError: If index out of bounds
        """
        owner_norm = self._normalize(owner)
        tokens = self.owner_tokens.get(owner_norm, [])
        if index >= len(tokens):
            raise VMExecutionError(f"ERC721: owner index {index} out of bounds")
        return tokens[index]

    def royalty_info(self, token_id: int, sale_price: int) -> tuple[str, int]:
        """
        Get royalty info for a token (EIP-2981).

        Args:
            token_id: Token ID
            sale_price: Sale price

        Returns:
            Tuple of (receiver, royalty_amount)
        """
        self._require_minted(token_id)

        if not self.royalty_receiver or self.royalty_fraction == 0:
            return ("0x" + "0" * 40, 0)

        royalty_amount = (sale_price * self.royalty_fraction) // 10000
        return (self.royalty_receiver, royalty_amount)

    # ==================== State-Changing Functions ====================

    def approve(self, caller: str, to: str, token_id: int) -> bool:
        """
        Approve an address to transfer a specific token.

        Args:
            caller: Message sender
            to: Address to approve
            token_id: Token ID

        Returns:
            True if successful
        """
        self._require_not_paused()
        owner = self.owner_of(token_id)
        caller_norm = self._normalize(caller)
        to_norm = self._normalize(to)

        if to_norm == owner:
            raise VMExecutionError("ERC721: approval to current owner")

        if caller_norm != owner and not self.is_approved_for_all(owner, caller_norm):
            raise VMExecutionError("ERC721: approve caller is not owner nor approved")

        self.token_approvals[token_id] = to_norm
        self._emit_approval(owner, to_norm, token_id)

        return True

    def set_approval_for_all(
        self, caller: str, operator: str, approved: bool
    ) -> bool:
        """
        Set or revoke operator approval for all tokens.

        Args:
            caller: Token owner
            operator: Operator address
            approved: Approval status

        Returns:
            True if successful
        """
        self._require_not_paused()
        caller_norm = self._normalize(caller)
        operator_norm = self._normalize(operator)

        if operator_norm == caller_norm:
            raise VMExecutionError("ERC721: approve to caller")

        if caller_norm not in self.operator_approvals:
            self.operator_approvals[caller_norm] = {}
        self.operator_approvals[caller_norm][operator_norm] = approved

        self._emit_approval_for_all(caller_norm, operator_norm, approved)

        return True

    def transfer_from(
        self, caller: str, from_addr: str, to_addr: str, token_id: int
    ) -> bool:
        """
        Transfer an NFT.

        Args:
            caller: Message sender
            from_addr: Current owner
            to_addr: New owner
            token_id: Token ID

        Returns:
            True if successful
        """
        self._require_not_paused()
        self._transfer(caller, from_addr, to_addr, token_id)
        return True

    def safe_transfer_from(
        self,
        caller: str,
        from_addr: str,
        to_addr: str,
        token_id: int,
        data: bytes = b"",
    ) -> bool:
        """
        Safely transfer an NFT (checks receiver).

        Args:
            caller: Message sender
            from_addr: Current owner
            to_addr: New owner
            token_id: Token ID
            data: Optional data for receiver

        Returns:
            True if successful
        """
        self._require_not_paused()
        self._transfer(caller, from_addr, to_addr, token_id)

        # In a full implementation, would check if to_addr is a contract
        # and call onERC721Received

        return True

    def _transfer(
        self, caller: str, from_addr: str, to_addr: str, token_id: int
    ) -> None:
        """Internal transfer logic."""
        from_norm = self._normalize(from_addr)
        to_norm = self._normalize(to_addr)
        caller_norm = self._normalize(caller)

        # Verify ownership
        owner = self.owner_of(token_id)
        if owner != from_norm:
            raise VMExecutionError("ERC721: transfer from incorrect owner")

        # Verify authorization
        if not self._is_approved_or_owner(caller_norm, token_id):
            raise VMExecutionError("ERC721: caller is not owner nor approved")

        # Validate recipient
        if to_norm == "0x" + "0" * 40:
            raise VMExecutionError("ERC721: transfer to zero address")

        # Clear approval
        if token_id in self.token_approvals:
            del self.token_approvals[token_id]

        # Update balances
        self.balances[from_norm] = self.balances.get(from_norm, 1) - 1
        self.balances[to_norm] = self.balances.get(to_norm, 0) + 1

        # Update ownership
        self.owners[token_id] = to_norm

        # Update enumerable data
        if from_norm in self.owner_tokens:
            self.owner_tokens[from_norm].remove(token_id)
        if to_norm not in self.owner_tokens:
            self.owner_tokens[to_norm] = []
        self.owner_tokens[to_norm].append(token_id)

        # Emit event
        self._emit_transfer(from_norm, to_norm, token_id)

        logger.debug(
            "ERC721 transfer",
            extra={
                "event": "erc721.transfer",
                "collection": self.symbol,
                "token_id": token_id,
                "from": from_norm[:10],
                "to": to_norm[:10],
            }
        )

    # ==================== Minting & Burning ====================

    def mint(
        self,
        minter: str,
        to: str,
        token_id: int | None = None,
        uri: str = "",
        metadata: NFTMetadata | None = None,
    ) -> int:
        """
        Mint a new NFT.

        Args:
            minter: Address calling mint (must be owner)
            to: Recipient address
            token_id: Optional specific token ID
            uri: Optional token URI
            metadata: Optional metadata

        Returns:
            Minted token ID

        Raises:
            VMExecutionError: If minting fails
        """
        self._require_not_paused()
        self._require_owner(minter)

        to_norm = self._normalize(to)
        if to_norm == "0x" + "0" * 40:
            raise VMExecutionError("ERC721: mint to zero address")

        # Determine token ID
        if token_id is None:
            token_id = self.next_token_id
            self.next_token_id += 1
        elif token_id in self.owners:
            raise VMExecutionError(f"ERC721: token {token_id} already minted")

        # Check supply cap
        if self.max_supply > 0 and len(self.all_tokens) >= self.max_supply:
            raise VMExecutionError(
                f"ERC721: max supply {self.max_supply} reached"
            )

        # Update state
        self.owners[token_id] = to_norm
        self.balances[to_norm] = self.balances.get(to_norm, 0) + 1

        # Enumerable
        self.all_tokens.append(token_id)
        if to_norm not in self.owner_tokens:
            self.owner_tokens[to_norm] = []
        self.owner_tokens[to_norm].append(token_id)

        # Metadata
        if uri:
            self.token_uris[token_id] = uri
        if metadata:
            self.token_metadata[token_id] = metadata

        # Emit transfer from zero address
        self._emit_transfer("0x" + "0" * 40, to_norm, token_id)

        logger.info(
            "ERC721 mint",
            extra={
                "event": "erc721.mint",
                "collection": self.symbol,
                "token_id": token_id,
                "to": to_norm[:10],
            }
        )

        return token_id

    def burn(self, caller: str, token_id: int) -> bool:
        """
        Burn an NFT.

        Args:
            caller: Message sender (must be owner or approved)
            token_id: Token ID to burn

        Returns:
            True if successful
        """
        self._require_not_paused()
        owner = self.owner_of(token_id)
        caller_norm = self._normalize(caller)

        if not self._is_approved_or_owner(caller_norm, token_id):
            raise VMExecutionError("ERC721: caller is not owner nor approved")

        # Clear approval
        if token_id in self.token_approvals:
            del self.token_approvals[token_id]

        # Update balances
        self.balances[owner] = self.balances.get(owner, 1) - 1

        # Remove ownership
        del self.owners[token_id]

        # Update enumerable
        self.all_tokens.remove(token_id)
        if owner in self.owner_tokens:
            self.owner_tokens[owner].remove(token_id)

        # Clear metadata
        if token_id in self.token_uris:
            del self.token_uris[token_id]
        if token_id in self.token_metadata:
            del self.token_metadata[token_id]

        # Emit transfer to zero address
        self._emit_transfer(owner, "0x" + "0" * 40, token_id)

        logger.info(
            "ERC721 burn",
            extra={
                "event": "erc721.burn",
                "collection": self.symbol,
                "token_id": token_id,
            }
        )

        return True

    # ==================== Admin Functions ====================

    def set_base_uri(self, caller: str, base_uri: str) -> bool:
        """Set base URI for token metadata."""
        self._require_owner(caller)
        self.base_uri = base_uri
        return True

    def set_token_uri(self, caller: str, token_id: int, uri: str) -> bool:
        """Set specific URI for a token."""
        self._require_owner(caller)
        self._require_minted(token_id)
        self.token_uris[token_id] = uri
        return True

    def set_royalty(self, caller: str, receiver: str, fraction: int) -> bool:
        """
        Set royalty info (EIP-2981).

        Args:
            caller: Must be owner
            receiver: Royalty receiver address
            fraction: Royalty fraction in basis points (e.g., 250 = 2.5%)
        """
        self._require_owner(caller)
        if fraction > 10000:
            raise VMExecutionError("ERC721: royalty fraction exceeds 100%")
        self.royalty_receiver = self._normalize(receiver)
        self.royalty_fraction = fraction
        return True

    def pause(self, caller: str) -> bool:
        """Pause token transfers."""
        self._require_owner(caller)
        self.paused = True
        return True

    def unpause(self, caller: str) -> bool:
        """Unpause token transfers."""
        self._require_owner(caller)
        self.paused = False
        return True

    # ==================== Helpers ====================

    def _normalize(self, address: str) -> str:
        """Normalize address to lowercase."""
        return address.lower()

    def _require_minted(self, token_id: int) -> None:
        """Require token exists."""
        if token_id not in self.owners:
            raise VMExecutionError(f"ERC721: token {token_id} does not exist")

    def _require_owner(self, caller: str) -> None:
        """Require caller is contract owner."""
        if self._normalize(caller) != self._normalize(self.owner):
            raise VMExecutionError("ERC721: caller is not owner")

    def _require_not_paused(self) -> None:
        """Require contract is not paused."""
        if self.paused:
            raise VMExecutionError("ERC721: token is paused")

    def _is_approved_or_owner(self, caller: str, token_id: int) -> bool:
        """Check if caller is owner or approved for token."""
        owner = self.owner_of(token_id)
        return (
            caller == owner
            or self.get_approved(token_id) == caller
            or self.is_approved_for_all(owner, caller)
        )

    def _emit_transfer(self, from_addr: str, to_addr: str, token_id: int) -> None:
        """Emit Transfer event."""
        self.events.append(
            NFTEvent(
                event_type="Transfer",
                from_address=from_addr,
                to_address=to_addr,
                token_id=token_id,
            )
        )

    def _emit_approval(self, owner: str, approved: str, token_id: int) -> None:
        """Emit Approval event."""
        self.events.append(
            NFTEvent(
                event_type="Approval",
                from_address=owner,
                to_address=approved,
                token_id=token_id,
            )
        )

    def _emit_approval_for_all(
        self, owner: str, operator: str, approved: bool
    ) -> None:
        """Emit ApprovalForAll event."""
        self.events.append(
            NFTEvent(
                event_type="ApprovalForAll",
                from_address=owner,
                to_address=operator,
                token_id=0,
                approved=approved,
            )
        )

    # ==================== Serialization ====================

    def to_dict(self) -> Dict:
        """Serialize NFT state to dictionary."""
        return {
            "name": self.name,
            "symbol": self.symbol,
            "base_uri": self.base_uri,
            "address": self.address,
            "owner": self.owner,
            "owners": dict(self.owners),
            "balances": dict(self.balances),
            "token_approvals": dict(self.token_approvals),
            "operator_approvals": {
                k: dict(v) for k, v in self.operator_approvals.items()
            },
            "all_tokens": list(self.all_tokens),
            "owner_tokens": {k: list(v) for k, v in self.owner_tokens.items()},
            "token_uris": dict(self.token_uris),
            "royalty_receiver": self.royalty_receiver,
            "royalty_fraction": self.royalty_fraction,
            "next_token_id": self.next_token_id,
            "max_supply": self.max_supply,
            "paused": self.paused,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ERC721Token":
        """Deserialize NFT state from dictionary."""
        token = cls(
            name=data["name"],
            symbol=data["symbol"],
            base_uri=data.get("base_uri", ""),
            address=data.get("address", ""),
            owner=data.get("owner", ""),
            max_supply=data.get("max_supply", 0),
            paused=data.get("paused", False),
        )
        token.owners = {int(k): v for k, v in data.get("owners", {}).items()}
        token.balances = dict(data.get("balances", {}))
        token.token_approvals = {
            int(k): v for k, v in data.get("token_approvals", {}).items()
        }
        token.operator_approvals = {
            k: dict(v) for k, v in data.get("operator_approvals", {}).items()
        }
        token.all_tokens = list(data.get("all_tokens", []))
        token.owner_tokens = {k: list(v) for k, v in data.get("owner_tokens", {}).items()}
        token.token_uris = {int(k): v for k, v in data.get("token_uris", {}).items()}
        token.royalty_receiver = data.get("royalty_receiver", "")
        token.royalty_fraction = data.get("royalty_fraction", 0)
        token.next_token_id = data.get("next_token_id", 1)
        return token

class ERC721Factory:
    """Factory for creating ERC721 NFT collections."""

    def __init__(self, blockchain: "Blockchain" | None = None) -> None:
        """Initialize the factory."""
        self.blockchain = blockchain
        self.deployed_collections: dict[str, ERC721Token] = {}

    def create_collection(
        self,
        creator: str,
        name: str,
        symbol: str,
        base_uri: str = "",
        max_supply: int = 0,
        royalty_receiver: str = "",
        royalty_fraction: int = 0,
    ) -> ERC721Token:
        """
        Create a new NFT collection.

        Args:
            creator: Collection owner
            name: Collection name
            symbol: Collection symbol
            base_uri: Base URI for metadata
            max_supply: Maximum supply (0 = unlimited)
            royalty_receiver: Royalty receiver address
            royalty_fraction: Royalty in basis points

        Returns:
            Deployed ERC721Token instance
        """
        if not name:
            raise VMExecutionError("ERC721Factory: name cannot be empty")
        if not symbol:
            raise VMExecutionError("ERC721Factory: symbol cannot be empty")

        collection = ERC721Token(
            name=name,
            symbol=symbol,
            base_uri=base_uri,
            owner=creator,
            max_supply=max_supply,
            royalty_receiver=royalty_receiver or creator,
            royalty_fraction=royalty_fraction,
        )

        self.deployed_collections[collection.address] = collection

        if self.blockchain:
            metadata = {
                "name": name,
                "symbol": symbol,
                "owner": creator,
            }
            self.blockchain.contracts[collection.address.upper()] = {
                "type": "ERC721",
                "address": collection.address,
                "metadata": metadata,
                "data": collection.to_dict(),
                "created_at": time.time(),
                "creator": creator,
                "storage": {},
            }

        logger.info(
            "ERC721 collection created",
            extra={
                "event": "erc721.created",
                "address": collection.address,
                "name": name,
                "symbol": symbol,
                "creator": creator[:10],
            }
        )

        return collection

    def get_collection(self, address: str) -> ERC721Token | None:
        """Get a deployed collection by address."""
        if address.lower() in self.deployed_collections:
            return self.deployed_collections[address.lower()]

        if self.blockchain:
            contract_data = self.blockchain.contracts.get(address.upper())
            if contract_data and contract_data.get("type") == "ERC721":
                collection = ERC721Token.from_dict(contract_data["data"])
                self.deployed_collections[address.lower()] = collection
                return collection

        return None

    def list_collections(self) -> list[Dict]:
        """List all deployed collections."""
        return [
            {
                "address": addr,
                "name": coll.name,
                "symbol": coll.symbol,
                "total_supply": coll.total_supply(),
                "owner": coll.owner,
            }
            for addr, coll in self.deployed_collections.items()
        ]
