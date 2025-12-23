import logging
import math
import os

logger = logging.getLogger(__name__)


class CSPRNG:
    def __init__(self):
        logger.info("CSPRNG initialized", extra={"event": "csprng.init"})

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
            random_int = int.from_bytes(random_bytes, "big")

            # Apply the mask to get a number within the bit length
            random_int &= mask

            # Check if the number falls within the desired range
            if random_int < range_size:
                return min_val + random_int


# Example usage is intentionally omitted in production modules.
