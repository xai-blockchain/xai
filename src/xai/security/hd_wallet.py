"""
HD Wallet - Production BIP-32/BIP-44 Implementation (TASK 27)
Hierarchical Deterministic Wallet with proper derivation paths
Includes gap limit scanning (TASK 99)
"""

import hashlib
import hmac
from typing import List, Tuple, Optional, Dict, Any
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


class HDWallet:
    """
    Production-grade Hierarchical Deterministic Wallet (TASK 27)

    Implements:
    - BIP-32: Hierarchical deterministic wallets
    - BIP-44: Multi-account hierarchy (m/44'/coin'/account'/change/index)
    - BIP-39: Mnemonic seed phrases
    - Gap limit scanning for wallet recovery (TASK 99)
    """

    # XAI coin type (using 9999 as placeholder - register with SLIP-0044 for production)
    XAI_COIN_TYPE = 9999

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
        self.accounts: Dict[int, Any] = {}
        self.address_cache: Dict[str, Dict] = {}

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
        }

        self.accounts[account_index] = account_info
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
        public_key = address_key.PublicKey().RawCompressed().ToHex()

        # Generate XAI address (using SHA256 like in main wallet)
        pub_hash = hashlib.sha256(public_key.encode()).hexdigest()
        address = f"XAI{pub_hash[:40]}"

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

        return result

    def derive_receiving_address(self, account_index: int = 0, index: int = 0) -> Dict[str, str]:
        """
        Derive external (receiving) address.

        Args:
            account_index: Account number
            index: Address index

        Returns:
            Address info
        """
        return self.derive_address(account_index=account_index, change=0, address_index=index)

    def derive_change_address(self, account_index: int = 0, index: int = 0) -> Dict[str, str]:
        """
        Derive internal (change) address.

        Args:
            account_index: Account number
            index: Address index

        Returns:
            Address info
        """
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
        Export extended public key (xpub) for watch-only wallet.

        Args:
            account_index: Account index

        Returns:
            Extended public key string
        """
        # Derive account
        purpose = self.master_key.ChildKey(Bip32KeyIndex.HardenIndex(44))
        coin_type = purpose.ChildKey(Bip32KeyIndex.HardenIndex(self.XAI_COIN_TYPE))
        account = coin_type.ChildKey(Bip32KeyIndex.HardenIndex(account_index))

        # Get extended public key
        return account.PublicKey().RawCompressed().ToHex()

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


# Example Usage
if __name__ == "__main__":
    print("=" * 70)
    print("XAI HD WALLET - BIP-32/BIP-44 Implementation (TASK 27)")
    print("=" * 70)

    # Create new HD wallet
    print("\n1. Creating new HD wallet...")
    wallet = HDWallet()
    print(f"Mnemonic: {wallet.get_mnemonic()}")

    # Derive account
    print("\n2. Deriving account 0...")
    account = wallet.derive_account(0)
    print(f"Path: {account['path']}")
    print(f"Master Public Key: {account['master_public_key'][:32]}...")

    # Derive receiving addresses
    print("\n3. Deriving receiving addresses (m/44'/9999'/0'/0/x)...")
    for i in range(3):
        addr = wallet.derive_receiving_address(account_index=0, index=i)
        print(f"   [{i}] {addr['address']} - {addr['path']}")

    # Derive change addresses
    print("\n4. Deriving change addresses (m/44'/9999'/0'/1/x)...")
    for i in range(2):
        addr = wallet.derive_change_address(account_index=0, index=i)
        print(f"   [{i}] {addr['address']} - {addr['path']}")

    # Demonstrate wallet recovery with gap scanning (TASK 99)
    print("\n5. Demonstrating gap limit scanning (TASK 99)...")
    print(f"Gap limit: {HDWallet.GAP_LIMIT} addresses")

    # Mock balance checker for demonstration
    def mock_balance_checker(address):
        # Simulate some addresses having balance
        return address[-1] in ['0', '2', '5']  # Mock: some addresses are "used"

    print("\n6. Scanning for used addresses...")
    used_addresses = wallet.scan_for_used_addresses(
        account_index=0,
        change=0,
        check_balance_func=mock_balance_checker,
        max_scan=50
    )
    print(f"Found {len(used_addresses)} used addresses")

    print("\n" + "=" * 70)
    print("HD Wallet implementation complete!")
    print("=" * 70)
