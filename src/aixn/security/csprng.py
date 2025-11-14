import os
import math
from typing import Optional

class CSPRNG:
    def __init__(self):
        print("CSPRNG initialized. Relying on OS-provided cryptographic randomness (os.urandom).")

    def generate_bytes(self, num_bytes: int) -> bytes:
        """
        Generates a specified number of cryptographically secure random bytes.
        Uses os.urandom, which is suitable for cryptographic purposes.
        """
        if not isinstance(num_bytes, int) or num_bytes <= 0:
            raise ValueError("Number of bytes must be a positive integer.")
        
        return os.urandom(num_bytes)

    def generate_int(self, min_val: int, max_val: int) -> int:
        """
        Generates a cryptographically secure random integer within the inclusive range [min_val, max_val].
        """
        if not isinstance(min_val, int) or not isinstance(max_val, int):
            raise ValueError("min_val and max_val must be integers.")
        if min_val > max_val:
            raise ValueError("min_val cannot be greater than max_val.")
        if min_val == max_val:
            return min_val

        # Calculate the range size
        range_size = max_val - min_val + 1
        
        # Determine the number of bits needed to represent the range
        num_bits = range_size.bit_length()
        
        # Determine the number of bytes needed
        num_bytes = math.ceil(num_bits / 8)
        
        # Create a mask to get only the relevant bits
        mask = (1 << num_bits) - 1

        while True:
            # Generate random bytes
            random_bytes = self.generate_bytes(num_bytes)
            
            # Convert bytes to an integer
            random_int = int.from_bytes(random_bytes, 'big')
            
            # Apply the mask to get a number within the bit length
            random_int &= mask
            
            # Check if the number falls within the desired range
            if random_int < range_size:
                return min_val + random_int

# Example Usage (for testing purposes)
if __name__ == "__main__":
    csprng = CSPRNG()

    print("\n--- Generating Random Bytes ---")
    random_bytes_16 = csprng.generate_bytes(16)
    print(f"16 random bytes (hex): {random_bytes_16.hex()}")

    random_bytes_32 = csprng.generate_bytes(32)
    print(f"32 random bytes (hex): {random_bytes_32.hex()}")

    print("\n--- Generating Random Integers ---")
    random_int_small = csprng.generate_int(1, 10)
    print(f"Random integer between 1 and 10: {random_int_small}")

    random_int_large = csprng.generate_int(1000, 1000000)
    print(f"Random integer between 1000 and 1,000,000: {random_int_large}")

    random_int_private_key_range = csprng.generate_int(1, 2**256 - 1) # Common range for private keys
    print(f"Random integer in private key range (first 100 chars): {str(random_int_private_key_range)[:100]}...")

    # Test edge case: min_val == max_val
    random_int_single = csprng.generate_int(50, 50)
    print(f"Random integer between 50 and 50: {random_int_single}")

    # Test with invalid input
    try:
        csprng.generate_bytes(0)
    except ValueError as e:
        print(f"\nError (expected): {e}")

    try:
        csprng.generate_int(10, 1)
    except ValueError as e:
        print(f"Error (expected): {e}")
