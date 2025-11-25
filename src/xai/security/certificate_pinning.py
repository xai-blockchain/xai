import hashlib
from typing import Dict, List, Optional

# This is a highly simplified conceptual model of Certificate Pinning.
# It does NOT perform actual TLS/SSL handshake interception or real certificate validation.
# Its purpose is to illustrate the concept of associating hosts with expected cryptographic identities.
# DO NOT use this for any production or security-sensitive applications.


class CertificatePinner:
    def __init__(self):
        # Stores pinned public key hashes (SPKI hashes) for hosts: {hostname: [spki_hash1, spki_hash2, ...]})
        self.pinned_public_key_hashes: Dict[str, List[str]] = {}
        print("CertificatePinner initialized.")

    def pin_certificate(self, hostname: str, spki_hash: str):
        """
        Adds a public key hash (SPKI hash) to the list of pinned certificates for a given hostname.
        In a real scenario, spki_hash would be derived from the server's public key.
        """
        if not hostname or not spki_hash:
            raise ValueError("Hostname and SPKI hash cannot be empty.")

        self.pinned_public_key_hashes.setdefault(hostname, []).append(spki_hash)
        print(f"Pinned SPKI hash '{spki_hash}' for host '{hostname}'.")

    def verify_connection(self, hostname: str, presented_spki_hash: str) -> bool:
        """
        Simulates verifying a network connection by checking the presented SPKI hash
        against the pinned hashes for the given hostname.
        """
        if not hostname or not presented_spki_hash:
            raise ValueError("Hostname and presented SPKI hash cannot be empty.")

        if hostname not in self.pinned_public_key_hashes:
            print(
                f"Warning: No pins found for host '{hostname}'. Connection allowed (no pinning enforced)."
            )
            return True  # No pins, so no pinning violation

        expected_hashes = self.pinned_public_key_hashes[hostname]
        if presented_spki_hash in expected_hashes:
            print(f"Connection to '{hostname}' verified. Presented hash matches a pinned hash.")
            return True
        else:
            print(
                f"!!! SECURITY ALERT !!! Connection to '{hostname}' failed. Presented SPKI hash '{presented_spki_hash}' does not match any pinned hash."
            )
            return False


# Example Usage (for testing purposes)
if __name__ == "__main__":
    pinner = CertificatePinner()

    # Simulate a real SPKI hash (e.g., from a server's public key)
    # In a real scenario, you'd get this from the actual certificate.
    # For demonstration, we'll use a dummy hash.
    google_spki_hash = "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="  # Dummy hash
    xai_api_spki_hash = "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="  # Dummy hash

    # Pin certificates for specific hosts
    pinner.pin_certificate("api.example.com", google_spki_hash)
    pinner.pin_certificate("xai.network", xai_api_spki_hash)
    pinner.pin_certificate(
        "xai.network", "sha256/CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC="
    )  # Add another valid pin

    print("\n--- Simulating Connections ---")

    # Valid connection to api.example.com
    print("\nAttempting connection to api.example.com with correct pin:")
    is_valid_google = pinner.verify_connection("api.example.com", google_spki_hash)
    print(f"Connection to api.example.com valid: {is_valid_google}")

    # Invalid connection to api.example.com (wrong hash)
    print("\nAttempting connection to api.example.com with incorrect pin:")
    is_invalid_google = pinner.verify_connection(
        "api.example.com", "sha256/DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD="
    )
    print(f"Connection to api.example.com valid: {is_invalid_google}")

    # Valid connection to xai.network (matches one of multiple pins)
    print("\nAttempting connection to xai.network with one of the correct pins:")
    is_valid_xai = pinner.verify_connection("xai.network", xai_api_spki_hash)
    print(f"Connection to xai.network valid: {is_valid_xai}")

    # Connection to an unpinned host
    print("\nAttempting connection to unpinned.host.com:")
    is_unpinned = pinner.verify_connection(
        "unpinned.host.com", "sha256/EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE="
    )
    print(f"Connection to unpinned.host.com valid: {is_unpinned}")
