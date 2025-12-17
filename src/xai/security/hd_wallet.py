"""
HD Wallet - Production BIP-32/BIP-44 Implementation (TASK 27)
Hierarchical Deterministic Wallet with proper derivation paths
Includes gap limit scanning (TASK 99)
"""

import hashlib
import hmac
import logging
from typing import List, Tuple, Optional, Dict, Any
import base58
from bip_utils import (
    Bip39SeedGenerator,
    Bip39MnemonicGenerator,
    Bip39WordsNum,
    Bip44,
    Bip44Coins,
    Bip44Changes,
    Bip32Slip10Secp256k1,
    Bip32KeyIndex,
)
from mnemonic import Mnemonic

from xai.security.slip44_registry import Slip44Registry

logger = logging.getLogger(__name__)


class HDWallet:
    """
    Production-grade Hierarchical Deterministic Wallet (TASK 27)

    Implements:
    - BIP-32: Hierarchical deterministic wallets
    - BIP-44: Multi-account hierarchy (m/44'/coin'/account'/change/index)
    - BIP-39: Mnemonic seed phrases
    - Gap limit scanning for wallet recovery (TASK 99)
    """

    # XAI coin type for BIP-44 derivation path. The Slip44Registry enforces
    # that the project uses the officially reserved identifier so the wallet
    # remains compatible with hardware vendors and multi-chain clients.
    _SLIP44_REGISTRY = Slip44Registry()
    XAI_COIN_TYPE = _SLIP44_REGISTRY.get_coin_type("XAI")

    # BIP-44 gap limit - stop scanning after N consecutive empty addresses
    GAP_LIMIT = 20

    def __init__(self, mnemonic: Optional[str] = None, passphrase: str = ""):
        """
        Initialize HD wallet from mnemonic or generate new one.

        Args:
            mnemonic: BIP-39 mnemonic phrase (if None, generates new one)
            passphrase: Optional passphrase for seed generation

        Raises:
            ValueError: If mnemonic is invalid
        """
        if mnemonic is None:
            # Generate new 24-word mnemonic (256 bits entropy)
            self.mnemonic = Bip39MnemonicGenerator().FromWordsNumber(Bip39WordsNum.WORDS_NUM_24)
        else:
            # Validate provided mnemonic
            mnemo_validator = Mnemonic("english")
            if not mnemo_validator.check(mnemonic):
                raise ValueError("Invalid BIP-39 mnemonic phrase")
            self.mnemonic = mnemonic

        # Generate seed from mnemonic
        self.seed = Bip39SeedGenerator(self.mnemonic).Generate(passphrase)

        # Initialize BIP-44 master key
        # Use Bitcoin derivation as XAI uses secp256k1 (same as Bitcoin)
        self.master_key = Bip32Slip10Secp256k1.FromSeed(self.seed)

        # Track derived accounts
        self.accounts: Dict[int, Dict[str, Any]] = {}
        self.address_cache: Dict[str, Dict] = {}
        self.selected_account: int = 0
        self.next_account_index: int = 0

    def get_mnemonic(self) -> str:
        """
        Get the wallet's mnemonic phrase.

        Returns:
            BIP-39 mnemonic phrase
        """
        return self.mnemonic

    def derive_account(self, account_index: int = 0) -> Dict[str, Any]:
        """
        Derive an account using BIP-44 path: m/44'/coin'/account' (TASK 27)

        Args:
            account_index: Account index (0-based)

        Returns:
            Account derivation info

        Raises:
            ValueError: If account_index is negative
        """
        if account_index < 0:
            raise ValueError("Account index must be non-negative")

        # Check cache
        if account_index in self.accounts:
            return self.accounts[account_index]

        # Derive account following BIP-44: m/44'/coin_type'/account'
        # All levels are hardened for account derivation
        purpose = self.master_key.ChildKey(Bip32KeyIndex.HardenIndex(44))
        coin_type = purpose.ChildKey(Bip32KeyIndex.HardenIndex(self.XAI_COIN_TYPE))
        account = coin_type.ChildKey(Bip32KeyIndex.HardenIndex(account_index))

        account_info = {
            "index": account_index,
            "path": f"m/44'/{self.XAI_COIN_TYPE}'/{account_index}'",
            "master_public_key": account.PublicKey().RawCompressed().ToHex(),
            "chain_code": account.ChainCode().ToHex(),
            "receiving_index": 0,
            "change_index": 0,
        }

        self.accounts[account_index] = account_info
        if account_index + 1 > self.next_account_index:
            self.next_account_index = account_index + 1
        return account_info

    def derive_address(
        self,
        account_index: int = 0,
        change: int = 0,
        address_index: int = 0,
        hardened: bool = False,
    ) -> Dict[str, str]:
        """
        Derive address using BIP-44 path (TASK 27).

        Full path: m/44'/coin'/account'/change/address_index

        Args:
            account_index: Account number (default: 0)
            change: 0 for external (receiving), 1 for internal (change)
            address_index: Address index within the chain
            hardened: Use hardened derivation for address (default: False)

        Returns:
            Dictionary with address, private key, public key, and path

        Raises:
            ValueError: If parameters are invalid
        """
        if account_index < 0 or address_index < 0:
            raise ValueError("Indexes must be non-negative")

        if change not in [0, 1]:
            raise ValueError("Change must be 0 (external) or 1 (internal)")

        # Build derivation path: m/44'/coin_type'/account'/change/address_index
        account_info = self.derive_account(account_index)

        purpose = self.master_key.ChildKey(Bip32KeyIndex.HardenIndex(44))
        coin_type = purpose.ChildKey(Bip32KeyIndex.HardenIndex(self.XAI_COIN_TYPE))
        account = coin_type.ChildKey(Bip32KeyIndex.HardenIndex(account_index))
        change_chain = account.ChildKey(change)

        # Derive address (hardened or non-hardened)
        if hardened:
            address_key = change_chain.ChildKey(Bip32KeyIndex.HardenIndex(address_index))
            hardened_marker = "'"
        else:
            address_key = change_chain.ChildKey(address_index)
            hardened_marker = ""

        # Extract keys
        private_key = address_key.PrivateKey().Raw().ToHex()
        raw_uncompressed = address_key.PublicKey().RawUncompressed().ToHex()
        if raw_uncompressed.startswith("04"):
            public_key = raw_uncompressed[2:]
        else:
            public_key = raw_uncompressed

        # Generate XAI address using the canonical wallet hashing scheme (SHA256 of
        # the uncompressed public key bytes without the 0x04 prefix).
        # Use network-appropriate prefix
        from xai.core.config import NETWORK
        prefix = "XAI" if NETWORK.lower() == "mainnet" else "TXAI"
        pub_key_bytes = bytes.fromhex(public_key)
        pub_hash = hashlib.sha256(pub_key_bytes).hexdigest()
        address = f"{prefix}{pub_hash[:40]}"

        derivation_path = f"m/44'/{self.XAI_COIN_TYPE}'/{account_index}'/{change}/{address_index}{hardened_marker}"

        result = {
            "address": address,
            "private_key": private_key,
            "public_key": public_key,
            "path": derivation_path,
            "account": account_index,
            "change": change,
            "index": address_index,
        }

        # Cache for gap scanning
        cache_key = f"{account_index}/{change}/{address_index}"
        self.address_cache[cache_key] = result

        if change == 0:
            account_info["receiving_index"] = max(account_info["receiving_index"], address_index + 1)
        else:
            account_info["change_index"] = max(account_info["change_index"], address_index + 1)

        return result

    def derive_receiving_address(self, account_index: int = 0, index: int = 0) -> Dict[str, str]:
        """
        Derive external (receiving) address.

        Args:
            account_index: Account number
            index: Address index (set to -1 to consume the next unused slot)

        Returns:
            Address info
        """
        account = self.derive_account(account_index)
        if index == -1:
            index = account["receiving_index"]
        return self.derive_address(account_index=account_index, change=0, address_index=index)

    def derive_change_address(self, account_index: int = 0, index: int = 0) -> Dict[str, str]:
        """
        Derive internal (change) address.

        Args:
            account_index: Account number
            index: Address index (set to -1 to consume the next unused slot)

        Returns:
            Address info
        """
        account = self.derive_account(account_index)
        if index == -1:
            index = account["change_index"]
        return self.derive_address(account_index=account_index, change=1, address_index=index)

    # ===== GAP LIMIT SCANNING (TASK 99) =====

    def scan_for_used_addresses(
        self,
        account_index: int = 0,
        change: int = 0,
        check_balance_func: Optional[callable] = None,
        max_scan: int = 1000,
    ) -> List[Dict]:
        """
        Scan for used addresses following BIP-44 gap limit (TASK 99).

        Scans until GAP_LIMIT (20) consecutive empty addresses are found.

        Args:
            account_index: Account to scan
            change: 0 for receiving, 1 for change addresses
            check_balance_func: Function to check if address has balance
                                Should return True if address has been used
            max_scan: Maximum addresses to scan (safety limit)

        Returns:
            List of all used addresses found

        Note:
            If check_balance_func is None, returns first GAP_LIMIT addresses
        """
        used_addresses = []
        consecutive_empty = 0
        current_index = 0

        while consecutive_empty < self.GAP_LIMIT and current_index < max_scan:
            # Derive address
            addr_info = self.derive_address(
                account_index=account_index,
                change=change,
                address_index=current_index
            )

            # Check if used
            if check_balance_func:
                is_used = check_balance_func(addr_info["address"])
            else:
                # No balance checker provided, just return empty result
                is_used = False

            if is_used:
                used_addresses.append(addr_info)
                consecutive_empty = 0  # Reset gap counter
            else:
                consecutive_empty += 1

            current_index += 1

        return used_addresses

    def recover_wallet_addresses(
        self,
        check_balance_func: callable,
        accounts_to_scan: int = 5,
    ) -> Dict[str, List[Dict]]:
        """
        Recover all wallet addresses by scanning with gap limit (TASK 99).

        Args:
            check_balance_func: Function to check address balance/usage
            accounts_to_scan: Number of accounts to scan (default: 5)

        Returns:
            Dictionary with used addresses by account and chain type
        """
        recovery_results = {
            "total_addresses_found": 0,
            "accounts": {}
        }

        for account_idx in range(accounts_to_scan):
            account_results = {
                "receiving_addresses": [],
                "change_addresses": [],
            }

            # Scan receiving addresses (change=0)
            receiving = self.scan_for_used_addresses(
                account_index=account_idx,
                change=0,
                check_balance_func=check_balance_func
            )
            account_results["receiving_addresses"] = receiving

            # Scan change addresses (change=1)
            change = self.scan_for_used_addresses(
                account_index=account_idx,
                change=1,
                check_balance_func=check_balance_func
            )
            account_results["change_addresses"] = change

            # Only include account if addresses were found
            total_for_account = len(receiving) + len(change)
            if total_for_account > 0:
                recovery_results["accounts"][account_idx] = account_results
                recovery_results["total_addresses_found"] += total_for_account

        return recovery_results

    def export_extended_public_key(self, account_index: int = 0) -> str:
        """
        Export standard BIP32 extended public key (xpub) for watch-only wallets.

        This serializes the account-level public node using mainnet version bytes
        0x0488B21E and Base58Check encoding.

        Args:
            account_index: Account index (0-based)

        Returns:
            xpub string
        """
        if account_index < 0:
            raise ValueError("Account index must be non-negative")

        # Derive nodes along m/44'/coin'/account'
        purpose = self.master_key.ChildKey(Bip32KeyIndex.HardenIndex(44))
        coin_type = purpose.ChildKey(Bip32KeyIndex.HardenIndex(self.XAI_COIN_TYPE))
        account = coin_type.ChildKey(Bip32KeyIndex.HardenIndex(account_index))

        # Compute parent fingerprint from coin_type node compressed pubkey
        parent_pub_hex = coin_type.PublicKey().RawCompressed().ToHex()
        parent_pub = bytes.fromhex(parent_pub_hex)
        parent_fingerprint = hashlib.new(
            "ripemd160", hashlib.sha256(parent_pub).digest()
        ).digest()[:4]

        # Child number is hardened account index
        child_number = (0x80000000 | account_index).to_bytes(4, "big")

        # Depth of account node: purpose (1), coin (2), account (3)
        depth = bytes([3])

        # Chain code and key data
        chain_code_hex = account.ChainCode().ToHex()
        chain_code = bytes.fromhex(chain_code_hex)
        pubkey_hex = account.PublicKey().RawCompressed().ToHex()
        pubkey = bytes.fromhex(pubkey_hex)

        if len(chain_code) != 32 or len(pubkey) != 33:
            raise ValueError("Invalid BIP32 node serialization components")

        # Version bytes for xpub
        version = bytes.fromhex("0488B21E")

        payload = (
            version + depth + parent_fingerprint + child_number + chain_code + pubkey
        )
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        return base58.b58encode(payload + checksum).decode("ascii")

    def derive_multiple_addresses(
        self,
        account_index: int = 0,
        change: int = 0,
        start_index: int = 0,
        count: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Derive multiple sequential addresses efficiently.

        Args:
            account_index: Account number
            change: 0 for receiving, 1 for change
            start_index: Starting address index
            count: Number of addresses to derive

        Returns:
            List of address info dictionaries
        """
        addresses = []
        for i in range(start_index, start_index + count):
            addr = self.derive_address(
                account_index=account_index,
                change=change,
                address_index=i
            )
            addresses.append(addr)

        return addresses

    def create_account(self, account_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Allocate the next unused account following BIP-44 rules.

        Args:
            account_name: Optional human-friendly label

        Returns:
            Account metadata dictionary
        """
        account_index = self.next_account_index
        self.next_account_index += 1

        account_info = self.derive_account(account_index)
        account_info["name"] = account_name or f"Account {account_index}"

        return account_info

    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        Return all derived accounts with balance indexes.
        """
        return [self.derive_account(idx) for idx in sorted(self.accounts)]

    def select_account(self, account_index: int) -> Dict[str, Any]:
        """
        Mark the active account for helper accessors.
        """
        account_info = self.derive_account(account_index)
        self.selected_account = account_index
        return account_info

    def get_selected_account(self) -> Dict[str, Any]:
        """
        Return metadata for the currently selected account.
        """
        return self.derive_account(self.selected_account)

    def derive_next_receiving(self, account_index: Optional[int] = None) -> Dict[str, str]:
        """
        Convenience helper for sequential receiving addresses.
        """
        idx = self.selected_account if account_index is None else account_index
        account = self.derive_account(idx)
        return self.derive_receiving_address(idx, index=account["receiving_index"])

    def derive_next_change(self, account_index: Optional[int] = None) -> Dict[str, str]:
        """
        Convenience helper for sequential change addresses.
        """
        idx = self.selected_account if account_index is None else account_index
        account = self.derive_account(idx)
        return self.derive_change_address(idx, index=account["change_index"])


# Example Usage (for development/testing only)
if __name__ == "__main__":
    # Configure basic logging for demo
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logger.info("=" * 70)
    logger.info("XAI HD WALLET - BIP-32/BIP-44 Implementation (TASK 27)")
    logger.info("=" * 70)

    # Create new HD wallet
    logger.info("1. Creating new HD wallet...")
    wallet = HDWallet()
    logger.info("Mnemonic: %s", wallet.get_mnemonic())

    # Derive account
    logger.info("2. Deriving account 0...")
    account = wallet.derive_account(0)
    logger.info("Path: %s", account['path'])
    logger.info("Master Public Key: %s...", account['master_public_key'][:32])

    # Derive receiving addresses
    logger.info(
        "3. Deriving receiving addresses (m/44'/%d'/0'/0/x)...",
        HDWallet.XAI_COIN_TYPE,
    )
    for i in range(3):
        addr = wallet.derive_receiving_address(account_index=0, index=i)
        logger.info("   [%d] %s - %s", i, addr['address'], addr['path'])

    # Derive change addresses
    logger.info(
        "4. Deriving change addresses (m/44'/%d'/0'/1/x)...",
        HDWallet.XAI_COIN_TYPE,
    )
    for i in range(2):
        addr = wallet.derive_change_address(account_index=0, index=i)
        logger.info("   [%d] %s - %s", i, addr['address'], addr['path'])

    # Demonstrate wallet recovery with gap scanning (TASK 99)
    logger.info("5. Demonstrating gap limit scanning (TASK 99)...")
    logger.info("Gap limit: %d addresses", HDWallet.GAP_LIMIT)

    # Mock balance checker for demonstration
    def mock_balance_checker(address):
        # Simulate some addresses having balance
        return address[-1] in ['0', '2', '5']  # Mock: some addresses are "used"

    logger.info("6. Scanning for used addresses...")
    used_addresses = wallet.scan_for_used_addresses(
        account_index=0,
        change=0,
        check_balance_func=mock_balance_checker,
        max_scan=50
    )
    logger.info("Found %d used addresses", len(used_addresses))

    logger.info("=" * 70)
    logger.info("HD Wallet implementation complete!")
    logger.info("=" * 70)
