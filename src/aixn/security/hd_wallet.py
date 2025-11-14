import hashlib
import hmac
from typing import List, Tuple, Optional, Dict, Any

# For conceptual demonstration, not for production use.
# In a real application, you would use a robust cryptographic library
# that implements BIP32/BIP44 standards (e.g., bip32, hdwallet libraries).

class HDWallet:
    def __init__(self, seed: Optional[bytes] = None):
        if seed is None:
            # For demonstration, generate a simple seed.
            # In production, this would be a cryptographically secure random seed (e.g., 128-bit or 256-bit entropy).
            self.seed = b"this is a very insecure seed for demonstration purposes only"
        else:
            self.seed = seed
        
        self.master_private_key, self.master_chain_code = self._derive_master_key(self.seed)
        self.accounts: List[Dict[str, Any]] = [] # Stores derived accounts

    def _derive_master_key(self, seed: bytes) -> Tuple[bytes, bytes]:
        """
        Derives the master private key and chain code from the seed.
        Simplified for demonstration. In BIP32, this uses HMAC-SHA512.
        """
        # Using HMAC-SHA512 as per BIP32, but with a simplified "key" for demonstration
        I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
        master_private_key = I[:32]
        master_chain_code = I[32:]
        return master_private_key, master_chain_code

    def _derive_child_key(self, parent_private_key: bytes, parent_chain_code: bytes, index: int) -> Tuple[bytes, bytes]:
        """
        Derives a child private key and chain code from a parent.
        Simplified for demonstration. In BIP32, this involves specific serialization
        and HMAC-SHA512.
        """
        # For hardened derivation (index >= 0x80000000), the parent private key is used.
        # For non-hardened, the parent public key is used.
        # We'll simplify and always use parent private key for this conceptual model.
        
        # Data to hash: parent_private_key + index (serialized)
        data = parent_private_key + index.to_bytes(4, 'big') # 4 bytes for index
        
        I = hmac.new(parent_chain_code, data, hashlib.sha512).digest()
        child_private_key = I[:32]
        child_chain_code = I[32:]
        
        # In a real BIP32 implementation, you'd add the left 32 bytes of I to the parent private key
        # modulo the secp256k1 curve order. This is a conceptual simplification.
        
        return child_private_key, child_chain_code

    def _generate_address_from_private_key(self, private_key: bytes) -> str:
        """
        Generates a conceptual address from a private key.
        In a real system, this involves elliptic curve cryptography (secp256k1),
        SHA256, RIPEMD160, and Base58Check encoding.
        """
        # For demonstration, a simple hash of the private key
        return hashlib.sha256(private_key).hexdigest()[:40] # Truncated for brevity

    def create_account(self, account_index: int) -> Dict[str, Any]:
        """
        Creates a new account (conceptual BIP44 path: m/purpose'/coin_type'/account').
        We'll simplify to m/account_index'.
        """
        if account_index < 0:
            raise ValueError("Account index must be non-negative.")
        
        # Derive account private key and chain code
        # For BIP44, account derivation is hardened (index + 0x80000000)
        hardened_index = account_index + 0x80000000
        account_private_key, account_chain_code = self._derive_child_key(
            self.master_private_key, self.master_chain_code, hardened_index
        )
        
        # For simplicity, we'll just store the account private key and generate a single address
        # In BIP44, you'd then derive external and internal chain keys (m/account'/0/address_index and m/account'/1/address_index)
        account_address = self._generate_address_from_private_key(account_private_key)
        
        account_info = {
            "index": account_index,
            "private_key": account_private_key.hex(), # Store as hex for display
            "chain_code": account_chain_code.hex(),
            "address": account_address,
            "derived_addresses": [account_address] # For simplicity, one address per account
        }
        self.accounts.append(account_info)
        print(f"Created account {account_index} with address: {account_address}")
        return account_info

    def get_account(self, account_index: int) -> Optional[Dict[str, Any]]:
        """Retrieves an account by its index."""
        for account in self.accounts:
            if account["index"] == account_index:
                return account
        return None

    def get_all_addresses(self) -> List[str]:
        """Returns a list of all derived addresses."""
        all_addresses = []
        for account in self.accounts:
            all_addresses.extend(account["derived_addresses"])
        return all_addresses

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Using a fixed seed for reproducible examples
    fixed_seed = b"my_secret_hd_wallet_seed_12345"
    wallet = HDWallet(seed=fixed_seed)

    print(f"Master Private Key (conceptual): {wallet.master_private_key.hex()}")
    print(f"Master Chain Code (conceptual): {wallet.master_chain_code.hex()}")

    print("\n--- Creating Accounts ---")
    account0 = wallet.create_account(0)
    account1 = wallet.create_account(1)
    account2 = wallet.create_account(2)

    print("\n--- Retrieving Account Info ---")
    retrieved_account1 = wallet.get_account(1)
    if retrieved_account1:
        print(f"Account 1 Address: {retrieved_account1['address']}")
    
    print("\n--- All Derived Addresses ---")
    print(wallet.get_all_addresses())

    # Demonstrate that different seeds produce different keys
    print("\n--- Different Seed, Different Keys ---")
    another_seed = b"another_secret_hd_wallet_seed_67890"
    another_wallet = HDWallet(seed=another_seed)
    another_wallet.create_account(0)
    print(f"Another Wallet Account 0 Address: {another_wallet.get_account(0)['address']}")
