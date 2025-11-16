from abc import ABC, abstractmethod
import pyotp  # Will need to add to requirements.txt
import base64
import os


class TwoFactorAuthInterface(ABC):
    """
    Abstract Base Class for Two-Factor Authentication (2FA) providers.
    """

    @abstractmethod
    def generate_secret(self) -> str:
        """
        Generates a new 2FA secret.
        """
        pass

    @abstractmethod
    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verifies a 2FA code against a given secret.
        """
        pass

    @abstractmethod
    def get_provisioning_uri(self, secret: str, account_name: str, issuer_name: str) -> str:
        """
        Generates a provisioning URI for setting up the 2FA in an authenticator app.
        """
        pass


class TOTPAuthenticator(TwoFactorAuthInterface):
    """
    A Time-based One-Time Password (TOTP) authenticator implementation.
    Uses pyotp library.
    """

    def generate_secret(self) -> str:
        # Generate a base32 secret for TOTP
        return base64.b32encode(os.urandom(10)).decode("utf-8")

    def verify_code(self, secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    def get_provisioning_uri(self, secret: str, account_name: str, issuer_name: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=account_name, issuer_name=issuer_name)


# Example Usage (for testing purposes)
if __name__ == "__main__":
    authenticator = TOTPAuthenticator()

    # 1. Generate a secret for a user
    user_secret = authenticator.generate_secret()
    print(f"User's 2FA Secret: {user_secret}")

    # 2. Get provisioning URI (e.g., to scan with Google Authenticator)
    provisioning_uri = authenticator.get_provisioning_uri(
        user_secret, "admin@aixn.io", "AIXN Blockchain"
    )
    print(f"Provisioning URI: {provisioning_uri}")
    print("Scan this URI with your authenticator app (e.g., Google Authenticator).")

    # 3. Simulate verification
    print("\nEnter the 6-digit code from your authenticator app:")
    entered_code = input("2FA Code: ").strip()

    if authenticator.verify_code(user_secret, entered_code):
        print("2FA code is valid. Authentication successful!")
    else:
        print("2FA code is invalid. Authentication failed.")
