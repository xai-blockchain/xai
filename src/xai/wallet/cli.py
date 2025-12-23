#!/usr/bin/env python3
"""
Simple wallet CLI utilities.

Currently supports requesting testnet faucet funds via the public node API.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any

import requests

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf import pbkdf2

from xai.core.hardware_wallet import (
    HARDWARE_WALLET_ENABLED,
    HardwareWallet,
    get_default_hardware_wallet,
    get_hardware_wallet_manager,
)
from xai.core.wallet import Wallet
from xai.core.watch_only_wallet import (
    DuplicateWatchAddressError,
    WatchAddressNotFoundError,
    WatchOnlyWalletError,
    WatchOnlyWalletStore,
    XpubDerivationError,
)
from xai.security.two_factor_auth import TwoFactorAuthManager, TwoFactorSetup
from xai.wallet.mnemonic_qr_backup import (
    MnemonicQRBackupGenerator,
    QRCodeUnavailableError,
)
from xai.wallet.multisig_wallet import MultiSigWallet
from xai.wallet.two_factor_profile import TwoFactorProfile, TwoFactorProfileStore

# Configure module logger
logger = logging.getLogger(__name__)

DEFAULT_API_URL = os.getenv("XAI_API_URL", "http://localhost:12001")
DEFAULT_KEYSTORE_DIR = Path.home() / ".xai" / "keystores"
TWO_FACTOR_STORE = TwoFactorProfileStore()

# Encryption constants
PBKDF2_ITERATIONS = 600000  # NIST recommended minimum for 2023+
ARGON2_TIME_COST = 3  # ops limit
ARGON2_MEMORY_COST = 65536  # 64 MB
ARGON2_PARALLELISM = 4
SALT_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits for AES-GCM
KEY_SIZE = 32  # 256 bits for AES-256

def _get_hardware_wallet(args: argparse.Namespace) -> HardwareWallet:
    """Get hardware wallet based on CLI args."""
    if getattr(args, 'ledger', False):
        try:
            from xai.core.hardware_wallet_ledger import LedgerHardwareWallet
            wallet = LedgerHardwareWallet()
            wallet.connect()
            return wallet
        except ImportError:
            print("Ledger support requires: pip install ledgerblue", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Failed to connect to Ledger: {e}", file=sys.stderr)
            sys.exit(1)
    elif getattr(args, 'trezor', False):
        try:
            from xai.core.hardware_wallet_trezor import TrezorHardwareWallet
            wallet = TrezorHardwareWallet()
            wallet.connect()
            return wallet
        except ImportError:
            print("Trezor support requires: pip install trezor", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Failed to connect to Trezor: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Specify --ledger or --trezor", file=sys.stderr)
        sys.exit(1)

def _add_watch_add_arguments(parser: argparse.ArgumentParser) -> None:
    """Attach watch-only add options to a parser."""
    parser.add_argument("--address", help="Address to monitor (XAI/TXAI).")
    parser.add_argument("--xpub", help="Extended public key for deriving multiple watch-only addresses.")
    parser.add_argument(
        "--derive-count",
        type=int,
        default=5,
        help="Number of sequential addresses to derive when using --xpub (default: 5).",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Starting child index when deriving from --xpub (default: 0).",
    )
    parser.add_argument(
        "--change",
        type=int,
        choices=[0, 1],
        default=0,
        help="Change chain when deriving from --xpub (0=receiving, 1=change).",
    )
    parser.add_argument("--label", help="Optional label applied to each address.")
    parser.add_argument("--notes", help="Optional notes metadata stored with the entry.")
    parser.add_argument(
        "--tags",
        nargs="*",
        help="Optional tags (space-separated) stored with the entry.",
    )
    parser.add_argument(
        "--store",
        help="Override watch-only store path (default: ~/.xai/watch_only.json).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output instead of plaintext.")

def derive_key_from_password(password: str, salt: bytes, kdf: str = "pbkdf2") -> bytes:
    """
    Derive encryption key from password using PBKDF2-HMAC-SHA256 or argon2id.

    Args:
        password: User password
        salt: Random salt (32 bytes)
        kdf: Key derivation function ('pbkdf2' or 'argon2id')

    Returns:
        Derived key (32 bytes for AES-256)
    """
    if kdf == "argon2id":
        ph = PasswordHasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=KEY_SIZE,
            salt_len=SALT_SIZE,
        )
        # Argon2's hash function includes the salt, so we pass it in the password hash format
        # but we only need the key, so we use the raw hash
        return ph.hash(password.encode('utf-8'), salt=salt).split(b'$')[-1]
    
    # Default to PBKDF2
    kdf = pbkdf2.PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))

def encrypt_wallet_data(wallet_data: dict[str, Any], password: str, kdf: str = "pbkdf2") -> tuple[bytes, bytes, bytes, bytes]:
    """
    Encrypt wallet data using AES-256-GCM with PBKDF2 key derivation.

    Args:
        wallet_data: Wallet data dictionary
        password: Encryption password

    Returns:
        Tuple of (encrypted_data, salt, nonce, hmac_signature)
    """
    # Generate random salt and nonce
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)

    # Derive encryption key from password
    key = derive_key_from_password(password, salt)

    # Encrypt data using AES-256-GCM
    aesgcm = AESGCM(key)
    plaintext = json.dumps(wallet_data).encode('utf-8')
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # Generate HMAC-SHA256 for integrity verification
    hmac_key = hashlib.sha256(key + b"hmac").digest()
    signature = hmac.new(hmac_key, salt + nonce + ciphertext, hashlib.sha256).digest()

    return ciphertext, salt, nonce, signature

from dataclasses import dataclass


@dataclass
class DecryptionData:
    encrypted_data: bytes
    salt: bytes
    nonce: bytes
    signature: bytes
    password: str
    kdf: str = "pbkdf2"

def decrypt_wallet_data(data: DecryptionData) -> dict[str, Any]:
    """
    Decrypt wallet data and verify integrity.

    Args:
        data: DecryptionData object containing all necessary data.

    Returns:
        Decrypted wallet data dictionary

    Raises:
        ValueError: If decryption fails or integrity check fails
    """
    # Derive key from password
    key = derive_key_from_password(data.password, data.salt, data.kdf)

    # Verify HMAC signature for integrity
    hmac_key = hashlib.sha256(key + b"hmac").digest()
    expected_signature = hmac.new(hmac_key, data.salt + data.nonce + data.encrypted_data, hashlib.sha256).digest()

    if not hmac.compare_digest(data.signature, expected_signature):
        raise ValueError("Integrity check failed - file may be corrupted or tampered")

    # Decrypt data using AES-256-GCM
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(data.nonce, data.encrypted_data, None)
        return json.loads(plaintext.decode('utf-8'))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Decryption failed - invalid ciphertext or key: {str(e)}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Decryption succeeded but data is not valid JSON: {str(e)}") from e

def get_private_key_secure(
    keystore_path: str | None = None,
    allow_env: bool = False,
    prompt: str = "Enter private key"
) -> str:
    """
    Securely obtain private key without CLI argument exposure.

    This function implements multiple secure methods for obtaining private keys,
    ordered from most secure to least secure:
    1. Encrypted keystore file (recommended for production)
    2. Interactive secure input with getpass (no echo, no history)
    3. Environment variable (with security warning)

    Security considerations:
    - Never accepts private keys as CLI arguments (prevents shell history exposure)
    - Never echoes private keys to terminal
    - Clears sensitive data from memory (best effort in Python)
    - Validates key format before returning

    Args:
        keystore_path: Path to encrypted keystore file (most secure option)
        allow_env: Whether to check environment variable (default: False)
        prompt: Custom prompt for interactive input

    Returns:
        Private key as hex string (with or without '0x' prefix)

    Raises:
        ValueError: If no valid private key can be obtained
        FileNotFoundError: If keystore_path specified but not found
    """
    # Method 1: Load from encrypted keystore (most secure)
    if keystore_path:
        try:
            with open(keystore_path, "r", encoding="utf-8") as f:
                keystore_data = json.load(f)

            # Check if encrypted (version 2.0 format)
            if keystore_data.get("version") == "2.0" and "encrypted_data" in keystore_data:
                password = getpass.getpass("Enter keystore password: ")

                # Decode and decrypt
                encrypted_data = base64.b64decode(keystore_data["encrypted_data"])
                salt = base64.b64decode(keystore_data["salt"])
                nonce = base64.b64decode(keystore_data["nonce"])
                signature = base64.b64decode(keystore_data["hmac"])
                kdf = keystore_data.get("kdf", "pbkdf2")

                decryption_data = DecryptionData(
                    encrypted_data=encrypted_data,
                    salt=salt,
                    nonce=nonce,
                    signature=signature,
                    password=password,
                    kdf=kdf,
                )
                wallet_data = decrypt_wallet_data(decryption_data)

                # Clear password from memory (best effort)
                del password

                private_key = wallet_data.get("private_key", "")
                if not private_key:
                    raise ValueError("No private key found in keystore")

                return private_key.replace("0x", "")

            # Legacy unencrypted format
            else:
                logger.warning("Loading from unencrypted keystore (legacy format)")
                print("WARNING: Keystore is not encrypted!", file=sys.stderr)
                private_key = keystore_data.get("private_key", "")
                if not private_key:
                    raise ValueError("No private key found in keystore")
                return private_key.replace("0x", "")

        except FileNotFoundError:
            raise FileNotFoundError(f"Keystore file not found: {keystore_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid keystore file format: {e}") from e
        except OSError as e:
            raise ValueError(f"Failed to read keystore file: {e}") from e
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid keystore data structure: {e}") from e

    # Method 2: Check environment variable (with security warning)
    if allow_env:
        env_key = os.environ.get("XAI_PRIVATE_KEY")
        if env_key:
            logger.warning("Using private key from XAI_PRIVATE_KEY environment variable (not recommended)")
            print("=" * 70, file=sys.stderr)
            print("WARNING: Using private key from environment variable.", file=sys.stderr)
            print("This is NOT RECOMMENDED for production use!", file=sys.stderr)
            print("", file=sys.stderr)
            print("Security risks:", file=sys.stderr)
            print("  - Environment variables may be logged", file=sys.stderr)
            print("  - May be visible in process listings", file=sys.stderr)
            print("  - Can leak through crash dumps or debugging", file=sys.stderr)
            print("", file=sys.stderr)
            print("Recommended: Use --keystore with encrypted keystore file", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            return env_key.replace("0x", "")

    # Method 3: Interactive secure input (no echo, no history)
    print(f"{prompt} (input hidden):", file=sys.stderr)
    key_input = getpass.getpass("")

    if not key_input:
        raise ValueError("No private key provided")

    # Validate and normalize format
    key_hex = key_input.strip().replace("0x", "")

    # Basic validation: should be 64 hex characters
    if len(key_hex) != 64:
        raise ValueError(f"Invalid private key length: {len(key_hex)} (expected 64)")

    try:
        int(key_hex, 16)  # Validate hex format
    except ValueError:
        raise ValueError("Invalid private key format: must be hexadecimal")

    return key_hex

def create_keystore(
    address: str,
    private_key: str,
    public_key: str = "",
    output_path: str | None = None,
    kdf: str = "pbkdf2"
) -> str:
    """
    Create encrypted keystore file for secure private key storage.

    Args:
        address: Wallet address
        private_key: Private key to encrypt
        public_key: Public key (optional)
        output_path: Output file path (default: ~/.xai/keystores/ADDRESS.keystore)
        kdf: Key derivation function ('pbkdf2' or 'argon2id')

    Returns:
        Path to created keystore file

    Raises:
        ValueError: If password requirements not met
    """
    # Ensure keystore directory exists
    DEFAULT_KEYSTORE_DIR.mkdir(parents=True, exist_ok=True)

    if not output_path:
        output_path = str(DEFAULT_KEYSTORE_DIR / f"{address[:16]}.keystore")

    # Get password with strong requirements
    logger.debug("Creating new keystore for address: %s", address[:16])
    print("Create keystore password:", file=sys.stderr)
    print("Requirements: 12+ characters, uppercase, lowercase, digit, special char", file=sys.stderr)
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if password != password_confirm:
        raise ValueError("Passwords do not match!")

    # Enforce strong password policy
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters!")
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter!")
    if not any(char.islower() for char in password):
        raise ValueError("Password must contain at least one lowercase letter!")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one digit!")
    if not any(char in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for char in password):
        raise ValueError("Password must contain at least one special character!")

    # Prepare wallet data
    wallet_data = {
        "address": address,
        "private_key": private_key.replace("0x", ""),
        "public_key": public_key.replace("0x", ""),
        "created_at": time.time(),
        "version": "2.0"
    }

    # Encrypt with AES-256-GCM + HMAC
    encrypted_data, salt, nonce, signature = encrypt_wallet_data(wallet_data, password, kdf)

    # Create keystore structure
    keystore = {
        "version": "2.0",
        "algorithm": "AES-256-GCM",
        "kdf": kdf,
        "iterations": PBKDF2_ITERATIONS if kdf == "pbkdf2" else 0,
        "encrypted_data": base64.b64encode(encrypted_data).decode('ascii'),
        "salt": base64.b64encode(salt).decode('ascii'),
        "nonce": base64.b64encode(nonce).decode('ascii'),
        "hmac": base64.b64encode(signature).decode('ascii'),
        "address": address,  # Store address in plaintext for easy identification
    }

    # Write keystore file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(keystore, f, indent=2)

    # Set restrictive permissions (owner read/write only)
    os.chmod(output_path, 0o600)

    # Clear password from memory
    del password, password_confirm

    return output_path

def _format_response(data: dict[str, Any], as_json: bool) -> str:
    """Prepare CLI-friendly output."""
    if as_json:
        return json.dumps(data, indent=2, sort_keys=True)

    if data.get("success"):
        txid = data.get("txid", "pending")
        lines = [
            f"Success: {data.get('message', 'Faucet request accepted.')}",
            f"Amount: {data.get('amount', 'N/A')} XAI",
            f"Transaction ID: {txid}",
            data.get("note", ""),
        ]
        return "\n".join(filter(None, lines))

    return f"Error: {data.get('error', 'Unknown error')}"

def _request_faucet(args: argparse.Namespace) -> int:
    """Handle the request-faucet subcommand."""
    endpoint = f"{args.base_url.rstrip('/')}/faucet/claim"
    payload = {"address": args.address}

    logger.debug("Requesting faucet funds for address: %s", args.address)
    try:
        response = requests.post(endpoint, json=payload, timeout=args.timeout)
    except requests.RequestException as exc:
        logger.error("Faucet request failed: %s", exc)
        print(f"Network error contacting faucet: {exc}", file=sys.stderr)
        return 2

    try:
        data = response.json()
    except ValueError:
        logger.error("Invalid JSON response from faucet (status=%d)", response.status_code)
        print(
            f"Unexpected response ({response.status_code}): {response.text}",
            file=sys.stderr,
        )
        return 3

    success = response.ok and data.get("success") is True
    logger.info("Faucet request completed: success=%s", success)
    print(_format_response(data, args.json))
    return 0 if success else 1

def _generate_address(args: argparse.Namespace) -> int:
    """Handle the generate-address subcommand.

    Security: Private keys are NEVER printed to stdout by default.
    Use --save-keystore to create encrypted keystore or --show-private-key
    with explicit confirmation to display the key.
    """
    wallet = Wallet()
    logger.debug("Generated new wallet address: %s", wallet.address)

    # Deprecated --json flag warning
    if args.json:
        logger.warning("User requested deprecated --json output for wallet generation")
        print("=" * 70, file=sys.stderr)
        print("WARNING: --json flag is DEPRECATED and INSECURE", file=sys.stderr)
        print("It outputs private keys in plaintext which can expose them.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Use --save-keystore instead for secure key storage.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)

        # Still support it but require confirmation
        confirm = input("\nType 'SHOW JSON' to continue with insecure output: ")
        if confirm != "SHOW JSON":
            logger.info("User cancelled insecure JSON output")
            print("Cancelled. Use --save-keystore for secure storage.", file=sys.stderr)
            return 1

        logger.warning("User confirmed insecure JSON output - displaying private key")
        payload = {
            "success": True,
            "address": wallet.address,
            "public_key": wallet.public_key,
            "private_key": wallet.private_key,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    # If user wants to save to encrypted keystore (RECOMMENDED)
    if args.save_keystore:
        try:
            logger.info("Creating encrypted keystore for wallet: %s", wallet.address)
            keystore_path = create_keystore(
                address=wallet.address,
                private_key=wallet.private_key,
                public_key=wallet.public_key,
                output_path=args.keystore_output,
                kdf=args.kdf
            )
            logger.info("Keystore created successfully at: %s", keystore_path)
            print(f"Wallet generated successfully!")
            print(f"Address: {wallet.address}")
            print(f"Public Key: {wallet.public_key}")
            print(f"\nEncrypted keystore saved to: {keystore_path}")
            print("Keep your password secure - it cannot be recovered!")
            return 0
        except OSError as e:
            logger.error("Failed to write keystore file: %s", e, extra={"error_type": type(e).__name__})
            print(f"Error writing keystore file: {e}", file=sys.stderr)
            return 1
        except (ValueError, TypeError) as e:
            logger.error("Invalid data for keystore creation: %s", e, extra={"error_type": type(e).__name__})
            print(f"Error creating keystore: {e}", file=sys.stderr)
            return 1

    # If user explicitly wants to see private key (DANGEROUS)
    if args.show_private_key:
        logger.warning("User requested to display private key on screen")
        print("\n" + "=" * 70, file=sys.stderr)
        print("WARNING: You are about to display a private key!", file=sys.stderr)
        print("", file=sys.stderr)
        print("Security risks:", file=sys.stderr)
        print("  - Private key will be visible on screen", file=sys.stderr)
        print("  - May be recorded in terminal scrollback", file=sys.stderr)
        print("  - May be visible to others looking at your screen", file=sys.stderr)
        print("", file=sys.stderr)
        print("RECOMMENDED: Use --save-keystore for encrypted storage instead", file=sys.stderr)
        print("=" * 70, file=sys.stderr)

        confirm = input("\nType 'I UNDERSTAND THE RISKS' to continue: ")
        if confirm != "I UNDERSTAND THE RISKS":
            logger.info("User cancelled private key display")
            print("Cancelled. Use --save-keystore for secure storage.", file=sys.stderr)
            return 1

        # User confirmed - show everything
        logger.warning("User confirmed - displaying private key on screen")
        print(f"\nAddress:     {wallet.address}")
        print(f"Public Key:  {wallet.public_key}")
        print(f"Private Key: {wallet.private_key}")
        print("\nSave the private key securely. It cannot be recovered.")
        print("Clear your terminal after noting this information.")
        return 0

    # Default: Show address and public key only (SAFE)
    logger.info("Wallet generated successfully (address only mode): %s", wallet.address)
    print("Wallet generated successfully!")
    print(f"Address:     {wallet.address}")
    print(f"Public Key:  {wallet.public_key}")
    print("")
    print("IMPORTANT: Private key is NOT displayed for security.")
    print("To save securely, use: --save-keystore (recommended)")
    print("To display key (not recommended): --show-private-key")

    return 0

def _check_balance(args: argparse.Namespace) -> int:
    """Handle the check-balance subcommand."""
    endpoint = f"{args.base_url.rstrip('/')}/balance/{args.address}"

    logger.debug("Checking balance for address: %s", args.address)
    try:
        response = requests.get(endpoint, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            balance = data.get("balance", 0)
            pending_in = data.get("pending_incoming", 0)
            pending_out = data.get("pending_outgoing", 0)

            logger.info("Balance retrieved: %s XAI (pending_in=%s, pending_out=%s)", balance, pending_in, pending_out)
            print(f"Address: {args.address}")
            print(f"Balance: {balance} XAI")
            if pending_in > 0:
                print(f"Pending Incoming: {pending_in} XAI")
            if pending_out > 0:
                print(f"Pending Outgoing: {pending_out} XAI")

        return 0
    except requests.RequestException as exc:
        logger.error("Failed to check balance: %s", exc)
        print(f"Network error: {exc}", file=sys.stderr)
        return 2

def _send_transaction(args: argparse.Namespace) -> int:
    """Handle the send-transaction subcommand.

    Security: Private key is obtained securely via keystore or interactive input.
    NEVER passed as CLI argument.
    """
    two_fa_profile = getattr(args, '2fa_profile', None)
    if two_fa_profile:
        try:
            _require_two_factor(two_fa_profile, args.otp)
        except (ValueError, KeyError) as exc:
            logger.error("2FA verification failed: %s", exc, extra={"error_type": type(exc).__name__})
            print(f"2FA verification failed: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            logger.error("2FA profile I/O error: %s", exc, extra={"error_type": type(exc).__name__})
            print(f"2FA profile error: {exc}", file=sys.stderr)
            return 1

    try:
        # Securely obtain private key
        logger.debug("Obtaining private key for transaction")
        private_key = get_private_key_secure(
            keystore_path=args.keystore,
            allow_env=args.allow_env_key,
            prompt="Enter sender's private key"
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        logger.error("Failed to obtain private key: %s", e, extra={"error_type": type(e).__name__})
        print(f"Error obtaining private key: {e}", file=sys.stderr)
        return 1

    endpoint = f"{args.base_url.rstrip('/')}/transaction"

    payload = {
        "sender": args.sender,
        "recipient": args.recipient,
        "amount": args.amount,
        "private_key": private_key,
        "fee": args.fee,
    }

    logger.info("Sending transaction: %s -> %s (amount=%s, fee=%s)", args.sender, args.recipient, args.amount, args.fee)
    try:
        response = requests.post(endpoint, json=payload, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()

        # Clear private key from memory
        del private_key, payload

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            if data.get("success"):
                logger.info("Transaction sent successfully: txid=%s", data.get('txid', 'pending'))
                print(f"Transaction sent successfully!")
                print(f"TX ID: {data.get('txid', 'pending')}")
                print(f"Amount: {args.amount} XAI")
                print(f"Fee: {args.fee} XAI")
            else:
                logger.error("Transaction failed: %s", data.get('error', 'Unknown error'))
                print(f"Transaction failed: {data.get('error', 'Unknown error')}")
                return 1

        return 0
    except requests.RequestException as exc:
        logger.error("Transaction network error: %s", exc)
        print(f"Network error: {exc}", file=sys.stderr)
        return 2
    finally:
        # Ensure cleanup - only delete if variable exists in local scope
        if 'private_key' in locals():
            del private_key

def _wallet_history(args: argparse.Namespace) -> int:
    """Handle the wallet-history subcommand."""
    endpoint = f"{args.base_url.rstrip('/')}/history/{args.address}"
    params = {"limit": args.limit, "offset": args.offset}

    logger.debug("Fetching wallet history: address=%s, limit=%d, offset=%d", args.address, args.limit, args.offset)
    try:
        response = requests.get(endpoint, params=params, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            transactions = data.get("transactions", [])
            logger.info("Retrieved %d transactions for %s", len(transactions), args.address)
            print(f"Transaction History for {args.address}")
            print(f"Total: {len(transactions)} transactions")
            print("-" * 80)

            for i, tx in enumerate(transactions, 1):
                timestamp = tx.get("timestamp", "N/A")
                tx_type = "Sent" if tx.get("sender") == args.address else "Received"
                amount = tx.get("amount", 0)
                from_addr = tx.get("sender", "N/A")[:20]
                to_addr = tx.get("recipient", "N/A")[:20]

                print(f"{i}. {tx_type}: {amount} XAI")
                print(f"   From: {from_addr}... To: {to_addr}...")
                print(f"   Time: {timestamp}")
                print()

        return 0
    except requests.RequestException as exc:
        logger.error("Failed to fetch wallet history: %s", exc)
        print(f"Network error: {exc}", file=sys.stderr)
        return 2

def _export_wallet(args: argparse.Namespace) -> int:
    """Handle the export-wallet subcommand.

    Security: Private key obtained securely, never via CLI argument.
    """
    two_fa_profile = getattr(args, '2fa_profile', None)
    if two_fa_profile:
        try:
            _require_two_factor(two_fa_profile, args.otp)
        except (ValueError, KeyError) as exc:
            logger.error("2FA verification failed for export: %s", exc, extra={"error_type": type(exc).__name__})
            print(f"2FA verification failed: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            logger.error("2FA profile I/O error for export: %s", exc, extra={"error_type": type(exc).__name__})
            print(f"2FA profile error: {exc}", file=sys.stderr)
            return 1

    try:
        # Securely obtain private key
        logger.debug("Obtaining private key for wallet export")
        private_key = get_private_key_secure(
            keystore_path=args.keystore,
            allow_env=args.allow_env_key,
            prompt="Enter private key to export"
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        logger.error("Failed to obtain private key for export: %s", e, extra={"error_type": type(e).__name__})
        print(f"Error obtaining private key: {e}", file=sys.stderr)
        return 1

    wallet_data = {
        "address": args.address,
        "private_key": private_key,
        "public_key": args.public_key if args.public_key else "",
        "exported_at": time.time(),
        "version": "2.0"  # Encryption version
    }

    output_file = args.output or f"wallet_{args.address[:8]}.enc"

    try:
        if args.encrypt:
            # Get password from user
            logger.debug("Encrypting wallet export for address: %s", args.address)
            password = getpass.getpass("Enter encryption password: ")
            password_confirm = getpass.getpass("Confirm password: ")

            if password != password_confirm:
                logger.error("Password mismatch during wallet export")
                print("Passwords do not match!", file=sys.stderr)
                return 1

            if len(password) < 12:
                logger.error("Weak password rejected (too short)")
                print("Password must be at least 12 characters!", file=sys.stderr)
                return 1
            if not any(char.isupper() for char in password):
                logger.error("Weak password rejected (no uppercase)")
                print("Password must contain at least one uppercase letter!", file=sys.stderr)
                return 1
            if not any(char.islower() for char in password):
                logger.error("Weak password rejected (no lowercase)")
                print("Password must contain at least one lowercase letter!", file=sys.stderr)
                return 1
            if not any(char.isdigit() for char in password):
                logger.error("Weak password rejected (no digit)")
                print("Password must contain at least one digit!", file=sys.stderr)
                return 1
            if not any(char in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for char in password):
                logger.error("Weak password rejected (no special character)")
                print("Password must contain at least one special character!", file=sys.stderr)
                return 1

            # Encrypt wallet data with AES-256-GCM + HMAC
            encrypted_data, salt, nonce, signature = encrypt_wallet_data(wallet_data, password, args.kdf)

            # Create encrypted wallet file structure
            encrypted_wallet = {
                "version": "2.0",
                "algorithm": "AES-256-GCM",
                "kdf": args.kdf,
                "iterations": PBKDF2_ITERATIONS if args.kdf == "pbkdf2" else 0,
                "encrypted_data": base64.b64encode(encrypted_data).decode('ascii'),
                "salt": base64.b64encode(salt).decode('ascii'),
                "nonce": base64.b64encode(nonce).decode('ascii'),
                "hmac": base64.b64encode(signature).decode('ascii'),
                "address": args.address,  # Store address for easy identification
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_wallet, f, indent=2)

            # Clear sensitive data
            del password, password_confirm, private_key, wallet_data

            logger.info("Wallet exported (encrypted) to: %s", output_file)
            print(f"Wallet exported (encrypted with AES-256-GCM) to {output_file}")
            print(f"Encryption: AES-256-GCM with {args.kdf.upper()}")
            print("Keep your password secure - it cannot be recovered!")
        else:
            # Unencrypted export - require explicit confirmation
            logger.warning("User attempting unencrypted wallet export")
            print("\n" + "=" * 70, file=sys.stderr)
            print("WARNING: You are about to export UNENCRYPTED wallet!", file=sys.stderr)
            print("", file=sys.stderr)
            print("Security risks:", file=sys.stderr)
            print("  - Private key will be stored in plaintext", file=sys.stderr)
            print("  - Anyone with access to the file can steal your funds", file=sys.stderr)
            print("", file=sys.stderr)
            print("STRONGLY RECOMMENDED: Use --encrypt flag instead", file=sys.stderr)
            print("=" * 70, file=sys.stderr)

            confirm = input("\nType 'EXPORT UNENCRYPTED' to continue: ")
            if confirm != "EXPORT UNENCRYPTED":
                logger.info("User cancelled unencrypted export")
                print("Cancelled. Use --encrypt for secure export.", file=sys.stderr)
                del private_key, wallet_data
                return 1

            logger.warning("User confirmed unencrypted export - writing plaintext wallet")
            output_file = args.output or f"wallet_{args.address[:8]}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(wallet_data, f, indent=2)

            # Clear sensitive data
            del private_key, wallet_data

            logger.info("Wallet exported (unencrypted) to: %s", output_file)
            print(f"Wallet exported to {output_file}")
            print("WARNING: File is NOT encrypted. Keep it secure!")
            print("Recommendation: Use --encrypt flag for production wallets")

        # Set restrictive file permissions (owner read/write only)
        os.chmod(output_file, 0o600)

        return 0
    except OSError as e:
        logger.error("Wallet export I/O error: %s", e, extra={"error_type": type(e).__name__})
        print(f"Export I/O error: {e}", file=sys.stderr)
        # Clear sensitive data on error - only delete if variables exist in local scope
        if 'private_key' in locals():
            del private_key
        if 'wallet_data' in locals():
            del wallet_data
        return 1
    except (ValueError, TypeError) as e:
        logger.error("Wallet export data error: %s", e, extra={"error_type": type(e).__name__})
        print(f"Export data error: {e}", file=sys.stderr)
        # Clear sensitive data on error - only delete if variables exist in local scope
        if 'private_key' in locals():
            del private_key
        if 'wallet_data' in locals():
            del wallet_data
        return 1

def _import_wallet(args: argparse.Namespace) -> int:
    """Handle the import-wallet subcommand."""
    logger.debug("Importing wallet from file: %s", args.file)
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to parse as JSON first
        try:
            file_data = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Invalid wallet file format (not valid JSON)")
            print("Error: Invalid wallet file format", file=sys.stderr)
            return 1

        # Check if file is encrypted (version 2.0 format)
        if file_data.get("version") == "2.0" and "encrypted_data" in file_data:
            # Encrypted wallet - need password
            logger.debug("Encrypted wallet detected, requesting decryption password")
            password = getpass.getpass("Enter decryption password: ")

            try:
                # Decode base64 encrypted components
                encrypted_data = base64.b64decode(file_data["encrypted_data"])
                salt = base64.b64decode(file_data["salt"])
                nonce = base64.b64decode(file_data["nonce"])
                signature = base64.b64decode(file_data["hmac"])

                # Decrypt and verify integrity
                kdf = file_data.get("kdf", "pbkdf2")
                decryption_data = DecryptionData(
                    encrypted_data=encrypted_data,
                    salt=salt,
                    nonce=nonce,
                    signature=signature,
                    password=password,
                    kdf=kdf,
                )
                wallet_data = decrypt_wallet_data(decryption_data)

                logger.info("Wallet imported successfully (encrypted, address=%s)", wallet_data.get('address'))
                print("Wallet imported successfully (decrypted and verified)")
                print(f"Algorithm: {file_data.get('algorithm', 'AES-256-GCM')}")
                print(f"KDF: {kdf.upper()}")

            except ValueError as e:
                logger.error("Wallet decryption failed: %s", e)
                print(f"Decryption failed: {e}", file=sys.stderr)
                print("Possible reasons: wrong password, corrupted file, or tampered data", file=sys.stderr)
                return 1
        else:
            # Unencrypted wallet (legacy format)
            logger.warning("Importing unencrypted wallet (legacy format)")
            wallet_data = file_data
            print("Wallet imported (UNENCRYPTED)")
            print("WARNING: This wallet file was not encrypted!")

        # Display wallet information
        if args.json:
            print(json.dumps(wallet_data, indent=2))
        else:
            print(f"\nAddress: {wallet_data.get('address')}")
            print(f"Public Key: {wallet_data.get('public_key', 'N/A')[:40]}...")
            if not args.no_private_key:
                print(f"Private Key: {wallet_data.get('private_key', 'N/A')[:40]}...")
            if wallet_data.get('exported_at'):
                export_time = time.strftime('%Y-%m-%d %H:%M:%S',
                                           time.localtime(wallet_data['exported_at']))
                print(f"Exported: {export_time}")

        return 0
    except FileNotFoundError:
        logger.error("Wallet file not found: %s", args.file)
        print(f"Error: File '{args.file}' not found", file=sys.stderr)
        return 1
    except OSError as e:
        logger.error("Wallet import I/O error: %s", e, extra={"error_type": type(e).__name__})
        print(f"Import I/O error: {e}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
        logger.error("Wallet import data error: %s", e, extra={"error_type": type(e).__name__})
        print(f"Import data error: {e}", file=sys.stderr)
        return 1

def _read_mnemonic_from_args(args: argparse.Namespace) -> str:
    """Securely obtain mnemonic from CLI args or interactive prompt."""
    if args.mnemonic and args.mnemonic_file:
        raise ValueError("Provide either --mnemonic or --mnemonic-file, not both.")

    if args.mnemonic_file:
        with open(args.mnemonic_file, "r", encoding="utf-8") as handle:
            return handle.read().strip()

    if args.mnemonic:
        return args.mnemonic.strip()

    print(
        "Enter BIP-39 mnemonic (input hidden; words separated by spaces):",
        file=sys.stderr,
    )
    phrase = getpass.getpass("")
    if not phrase:
        raise ValueError("Mnemonic input is empty")
    if not args.skip_confirmation:
        confirm = getpass.getpass("Re-enter mnemonic to confirm: ")
        if phrase.strip() != confirm.strip():
            raise ValueError("Mnemonic phrases did not match")
    return phrase.strip()

def _mnemonic_qr_backup(args: argparse.Namespace) -> int:
    """Generate QR code backups for a mnemonic phrase."""
    logger.debug("Generating mnemonic QR backup")
    try:
        mnemonic_phrase = _read_mnemonic_from_args(args)
    except (ValueError, OSError) as exc:
        logger.error("Mnemonic input error: %s", exc, extra={"error_type": type(exc).__name__})
        print(f"Mnemonic input error: {exc}", file=sys.stderr)
        return 1

    bip39_passphrase = args.bip39_passphrase or ""

    try:
        generator = MnemonicQRBackupGenerator()
    except QRCodeUnavailableError as exc:  # pragma: no cover - dependency guard
        logger.error("QR code generator unavailable: %s", exc)
        print(str(exc), file=sys.stderr)
        return 1

    metadata: dict[str, Any] = {}
    if args.metadata_address:
        metadata["address"] = args.metadata_address
    if args.note:
        metadata["note"] = args.note

    try:
        bundle = generator.generate_bundle(
            mnemonic_phrase,
            passphrase=bip39_passphrase,
            include_passphrase=args.include_passphrase,
            metadata=metadata or None,
        )
        logger.info("QR backup bundle generated successfully")
    except (ValueError, TypeError) as exc:
        logger.error("Failed to build QR backup: %s", exc, extra={"error_type": type(exc).__name__})
        print(f"Failed to build QR backup: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        logger.error("QR backup I/O error: %s", exc, extra={"error_type": type(exc).__name__})
        print(f"QR backup I/O error: {exc}", file=sys.stderr)
        return 1
    finally:
        # Best-effort scrubbing of sensitive strings
        mnemonic_phrase = ""  # type: ignore

    if args.output:
        png_bytes = base64.b64decode(bundle.image_base64.encode("ascii"))
        with open(args.output, "wb") as handle:
            handle.write(png_bytes)
        os.chmod(args.output, 0o600)
        logger.info("QR backup image written to: %s", args.output)
        print(f"QR backup image written to: {args.output}")

    if args.payload_output:
        with open(args.payload_output, "w", encoding="utf-8") as handle:
            json.dump(bundle.payload, handle, indent=2, sort_keys=True)
        os.chmod(args.payload_output, 0o600)
        logger.info("QR payload saved to: %s", args.payload_output)
        print(f"Structured payload saved to: {args.payload_output}")

    if args.show_base64 or not args.output:
        print("\n--- BEGIN QR PNG (Base64) ---")
        print(bundle.image_base64)
        print("--- END QR PNG (Base64) ---\n")

    if args.ascii:
        print("ASCII QR Preview:\n")
        print(bundle.ascii_art)

    checksum = bundle.payload.get("checksum", "unknown")
    created_at = bundle.payload.get("created_at")
    word_count = bundle.payload.get("word_count")
    logger.info("Mnemonic QR backup generated successfully",
        word_count=word_count,
        checksum=checksum[:16],
        has_passphrase=bool(bip39_passphrase))
    print("Mnemonic QR backup generated successfully.")
    print(f"  Word count: {word_count}")
    if bip39_passphrase:
        print(
            f"  Passphrase hint: {bundle.payload.get('passphrase_hint', 'n/a')} "
            f"{'(passphrase embedded)' if args.include_passphrase else ''}"
        )
    print(f"  Payload checksum: {checksum[:16]}…")
    if created_at:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at))
        print(f"  Created at: {timestamp}")
    print("Store the PNG/ASCII output offline. Anyone scanning it gains full access to your funds!")
    return 0

def _watch_store_from_args(args: argparse.Namespace) -> WatchOnlyWalletStore:
    """Instantiate a watch-only store honoring CLI overrides."""
    store_path = getattr(args, "store", None)
    if store_path:
        return WatchOnlyWalletStore(Path(store_path))
    return WatchOnlyWalletStore()

def _watch_add(args: argparse.Namespace) -> int:
    """Add watch-only addresses manually or via xpub derivation."""
    store = _watch_store_from_args(args)
    tags = args.tags or []
    results: list[dict[str, Any]] = []
    try:
        if args.xpub:
            added = store.add_from_xpub(
                args.xpub,
                change=args.change,
                start_index=args.start_index,
                count=args.derive_count,
                label=args.label,
                notes=args.notes,
                tags=tags,
            )
            results = [entry.to_dict() for entry in added]
        else:
            if not args.address:
                print("ERROR: --address is required when --xpub is not provided.", file=sys.stderr)
                return 1
            entry = store.add_address(
                args.address,
                label=args.label,
                notes=args.notes,
                tags=tags,
            )
            results = [entry.to_dict()]
    except DuplicateWatchAddressError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (WatchOnlyWalletError, XpubDerivationError, ValueError) as exc:
        logger.error("Failed to add watch-only address: %s", exc, exc_info=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No new watch-only addresses were added (duplicates).")
        else:
            for entry in results:
                label = f" ({entry['label']})" if entry.get("label") else ""
                print(f"Added watch-only address {entry['address']}{label}")
    return 0

def _watch_list(args: argparse.Namespace) -> int:
    """List configured watch-only addresses."""
    store = _watch_store_from_args(args)
    entries = store.list_addresses(tags=args.tag)
    payload = [entry.to_dict() for entry in entries]
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        if not payload:
            print("No watch-only addresses configured.")
        else:
            for entry in payload:
                label = f" ({entry['label']})" if entry.get("label") else ""
                tags = f" [{', '.join(entry['tags'])}]" if entry.get("tags") else ""
                print(f"{entry['address']}{label}{tags} - source={entry.get('source', 'manual')}")
    return 0

def _watch_remove(args: argparse.Namespace) -> int:
    """Remove an address from the watch-only store."""
    store = _watch_store_from_args(args)
    try:
        entry = store.remove_address(args.address)
    except (WatchOnlyWalletError, WatchAddressNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(entry.to_dict(), indent=2))
    else:
        label = f" ({entry.label})" if entry.label else ""
        print(f"Removed watch-only address {entry.address}{label}")
    return 0

def _setup_two_factor(args: argparse.Namespace) -> int:
    """Provision a TOTP secret for the provided profile label."""
    label = args.label.strip()
    if not label:
        logger.error("2FA setup attempted with empty label")
        print("Label is required for 2FA setup.", file=sys.stderr)
        return 1

    if TWO_FACTOR_STORE.exists(label) and not args.force:
        logger.warning("2FA profile '%s' already exists (use --force to overwrite)", label)
        print(f"2FA profile '{label}' already exists. Use --force to overwrite.", file=sys.stderr)
        return 1

    logger.info("Setting up 2FA for profile: %s", label)
    manager = TwoFactorAuthManager()
    setup = manager.setup_2fa(label, user_email=args.user_email)
    hashed_codes = manager.hash_backup_codes(setup.backup_codes)

    profile = TwoFactorProfile(
        label=label,
        secret=setup.secret,
        backup_codes=hashed_codes,
        issuer=manager.issuer_name,
        metadata={"user_email": args.user_email} if args.user_email else {},
    )

    TWO_FACTOR_STORE.save(profile)
    logger.info("2FA profile '%s' created successfully", label)

    print("\n2FA Enabled Successfully")
    print(f"Profile Label: {label}")
    print(f"Secret (store securely): {setup.secret}")
    print(f"Provisioning URI: {setup.provisioning_uri}")
    print("\nBackup Codes (store offline, each usable once):")
    for idx, code in enumerate(setup.backup_codes, 1):
        print(f"  {idx:02d}: {code}")

    if args.qr_output:
        if qrcode is None:
            logger.warning("QR code generation requested but qrcode library not available")
            print("QR generation unavailable (missing qrcode dependency).", file=sys.stderr)
        else:
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=8, border=4)
            qr.add_data(setup.provisioning_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(args.qr_output)
            os.chmod(args.qr_output, 0o600)
            logger.info("2FA QR code saved to: %s", args.qr_output)
            print(f"\nQR code (PNG) saved to {args.qr_output}")

    return 0

def _two_factor_status(args: argparse.Namespace) -> int:
    """Show metadata about a 2FA profile."""
    label = args.label.strip()
    logger.debug("Checking status for 2FA profile: %s", label)
    try:
        profile = TWO_FACTOR_STORE.load(label)
    except FileNotFoundError:
        logger.error("2FA profile '%s' not found", label)
        print(f"2FA profile '{label}' not found.", file=sys.stderr)
        return 1

    created_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(profile.created_at))
    logger.debug("2FA profile info: label=%s, backup_codes=%d", label, len(profile.backup_codes))
    print(f"Profile: {label}")
    print(f"Issuer: {profile.issuer}")
    print(f"Created: {created_ts}")
    print(f"Remaining backup codes: {len(profile.backup_codes)}")
    if profile.metadata.get("user_email"):
        print(f"User email: {profile.metadata['user_email']}")
    return 0

def _two_factor_disable(args: argparse.Namespace) -> int:
    """Delete a 2FA profile."""
    label = args.label.strip()
    if not TWO_FACTOR_STORE.exists(label):
        logger.error("Cannot disable - 2FA profile '%s' not found", label)
        print(f"2FA profile '{label}' not found.", file=sys.stderr)
        return 1

    logger.warning("User attempting to disable 2FA profile: %s", label)
    confirm = input(f"Type 'DISABLE {label}' to remove this 2FA profile: ")
    if confirm != f"DISABLE {label}":
        logger.info("User cancelled 2FA disable operation")
        print("Operation cancelled.")
        return 1

    TWO_FACTOR_STORE.delete(label)
    logger.info("2FA profile '%s' removed", label)
    print(f"2FA profile '{label}' removed.")
    return 0

def _require_two_factor(profile_label: str, otp: str | None = None) -> None:
    """Prompt for and verify a 2FA code."""
    logger.debug("2FA verification required for profile: %s", profile_label)
    manager = TwoFactorAuthManager()
    code = otp or getpass.getpass("Enter 2FA code (or backup code): ").strip()
    if not code:
        logger.error("2FA code not provided")
        raise ValueError("2FA code required")

    success, message = TWO_FACTOR_STORE.verify_code(profile_label, code, manager=manager)
    if not success:
        logger.error("2FA verification failed for profile: %s", profile_label)
        raise ValueError("Invalid 2FA or backup code provided.")

    logger.info("2FA verification successful for profile: %s", profile_label)
    print(f"2FA verification successful ({message}).")

def _hw_address(args: argparse.Namespace) -> int:
    """Get address from hardware wallet."""
    try:
        hw = _get_hardware_wallet(args)
        address = hw.get_address()
        pubkey = hw.get_public_key()

        if args.json:
            print(json.dumps({"address": address, "public_key": pubkey}, indent=2))
        else:
            device = "Ledger" if getattr(args, 'ledger', False) else "Trezor"
            print(f"Device: {device}")
            print(f"Address: {address}")
            print(f"Public Key: {pubkey[:32]}...{pubkey[-8:]}")
        return 0
    except Exception as e:
        logger.error("Hardware wallet error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

def _hw_sign(args: argparse.Namespace) -> int:
    """Sign a message with hardware wallet."""
    try:
        hw = _get_hardware_wallet(args)

        # Read message from file or stdin
        if args.message_file:
            with open(args.message_file, 'rb') as f:
                message = f.read()
        elif args.message:
            message = args.message.encode('utf-8')
        else:
            print("Reading message from stdin (Ctrl+D to end):", file=sys.stderr)
            message = sys.stdin.buffer.read()

        # Show what we're signing
        msg_preview = message[:64].hex() if len(message) > 64 else message.hex()
        print(f"Signing {len(message)} bytes: {msg_preview}{'...' if len(message) > 64 else ''}", file=sys.stderr)
        print("Please confirm on your device...", file=sys.stderr)

        signature = hw.sign_transaction(message)
        sig_hex = signature.hex() if isinstance(signature, bytes) else signature

        if args.json:
            print(json.dumps({"signature": sig_hex, "message_hash": hashlib.sha256(message).hexdigest()}, indent=2))
        else:
            print(f"Signature: {sig_hex}")
        return 0
    except Exception as e:
        logger.error("Signing error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

def _hw_verify(args: argparse.Namespace) -> int:
    """Verify hardware wallet address matches on-device display."""
    try:
        hw = _get_hardware_wallet(args)
        address = hw.get_address()

        device = "Ledger" if getattr(args, 'ledger', False) else "Trezor"
        print(f"\n{'='*50}")
        print(f"ADDRESS VERIFICATION - {device}")
        print(f"{'='*50}")
        print(f"\nAddress from device: {address}")
        print(f"\nPlease verify this address matches your {device} screen.")
        print("If it does NOT match, your device may be compromised!")
        print(f"{'='*50}\n")

        if args.json:
            print(json.dumps({"address": address, "device": device.lower()}, indent=2))
        return 0
    except Exception as e:
        logger.error("Verification error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

def _hw_send(args: argparse.Namespace) -> int:
    """Send transaction using hardware wallet."""
    # Optional 2FA check
    if getattr(args, 'two_fa_profile', None):
        try:
            _require_two_factor(args.two_fa_profile, getattr(args, 'otp', None))
        except (ValueError, KeyError, OSError) as exc:
            print(f"2FA verification failed: {exc}", file=sys.stderr)
            return 1

    try:
        hw = _get_hardware_wallet(args)
        sender_address = hw.get_address()

        # Verify sender matches hardware wallet
        if args.sender and args.sender != sender_address:
            print(f"Warning: --sender {args.sender} differs from device address {sender_address}", file=sys.stderr)
            print("Using device address.", file=sys.stderr)

        device = "Ledger" if getattr(args, 'ledger', False) else "Trezor"
        print(f"\n{'='*50}")
        print(f"HARDWARE WALLET TRANSACTION - {device}")
        print(f"{'='*50}")
        print(f"From:   {sender_address}")
        print(f"To:     {args.recipient}")
        print(f"Amount: {args.amount} XAI")
        print(f"Fee:    {args.fee} XAI")
        print(f"{'='*50}")
        print(f"\nPlease review and confirm on your {device}...")

        # Build transaction for signing
        tx_payload = json.dumps({
            "sender": sender_address,
            "recipient": args.recipient,
            "amount": args.amount,
            "fee": args.fee,
            "timestamp": int(time.time()),
        }).encode('utf-8')

        signature = hw.sign_transaction(tx_payload)
        sig_hex = signature.hex() if isinstance(signature, bytes) else signature

        # Submit to node
        endpoint = f"{args.base_url.rstrip('/')}/transaction"
        payload = {
            "sender": sender_address,
            "recipient": args.recipient,
            "amount": args.amount,
            "fee": args.fee,
            "signature": sig_hex,
            "public_key": hw.get_public_key(),
        }

        response = requests.post(endpoint, json=payload, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            if data.get("success"):
                print(f"\nTransaction sent successfully!")
                print(f"TX ID: {data.get('txid', 'pending')}")
            else:
                print(f"\nTransaction failed: {data.get('error', 'Unknown error')}")
                return 1
        return 0
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 2
    except Exception as e:
        logger.error("Transaction error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

def _multisig_create(args: argparse.Namespace) -> int:
    """Create a new multisig wallet configuration."""
    try:
        from cryptography.hazmat.primitives import serialization

        from xai.core.crypto_utils import load_public_key_from_hex

        # Read public keys from file or args
        if args.keys_file:
            with open(args.keys_file, 'r') as f:
                public_keys_hex = [line.strip() for line in f if line.strip()]
        else:
            public_keys_hex = args.public_keys

        if not public_keys_hex or len(public_keys_hex) < 2:
            print("Error: At least 2 public keys required for multisig", file=sys.stderr)
            return 1

        if args.threshold > len(public_keys_hex):
            print(f"Error: Threshold ({args.threshold}) cannot exceed number of keys ({len(public_keys_hex)})", file=sys.stderr)
            return 1

        # Convert hex public keys to PEM format for multisig wallet
        public_keys_pem = []
        for hex_key in public_keys_hex:
            try:
                pub_key_obj = load_public_key_from_hex(hex_key)
                pem_bytes = pub_key_obj.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                public_keys_pem.append(pem_bytes.hex())
            except Exception as e:
                print(f"Error: Invalid public key format: {hex_key[:16]}... - {e}", file=sys.stderr)
                return 1

        # Create multisig wallet to validate
        wallet = MultiSigWallet(public_keys_pem, args.threshold)

        # Generate multisig configuration
        config = {
            "version": "1.0",
            "type": "multisig",
            "threshold": args.threshold,
            "total_signers": len(public_keys_pem),
            "public_keys": public_keys_pem,  # Store PEM format
            "created_at": int(time.time()),
        }

        # Save configuration
        output_path = args.output or f"multisig_{args.threshold}of{len(public_keys_pem)}.json"
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)

        if args.json:
            print(json.dumps(config, indent=2))
        else:
            print(f"Multisig wallet created: {args.threshold}-of-{len(public_keys_pem)}")
            print(f"Configuration saved to: {output_path}")
            print(f"Share this file with all signers.")

        return 0
    except Exception as e:
        logger.error("Multisig creation error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

def _multisig_sign(args: argparse.Namespace) -> int:
    """Add a signature to a multisig transaction."""
    try:
        # Load transaction file
        with open(args.tx_file, 'r') as f:
            tx_data = json.load(f)

        # Get private key securely
        private_key = get_private_key_secure(
            keystore_path=args.keystore,
            allow_env=False,
            prompt="Enter your private key for signing"
        )

        # Derive public key from private key and convert to PEM format
        from cryptography.hazmat.primitives import serialization

        from xai.core.crypto_utils import (
            derive_public_key_hex,
            load_public_key_from_hex,
            sign_message_hex,
        )

        public_key_hex = derive_public_key_hex(private_key)
        pub_key_obj = load_public_key_from_hex(public_key_hex)
        pem_bytes = pub_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key = pem_bytes.hex()

        # Sign the transaction payload
        payload = json.dumps(tx_data.get("payload", tx_data), sort_keys=True).encode('utf-8')
        signature = sign_message_hex(payload.hex(), private_key)

        # Add signature to transaction
        if "signatures" not in tx_data:
            tx_data["signatures"] = []

        # Check if already signed by this key
        for sig in tx_data["signatures"]:
            if sig.get("public_key") == public_key:
                print("Warning: This key has already signed this transaction", file=sys.stderr)
                return 1

        tx_data["signatures"].append({
            "public_key": public_key,
            "signature": signature,
            "signed_at": int(time.time()),
        })

        # Save updated transaction
        output_path = args.output or args.tx_file
        with open(output_path, 'w') as f:
            json.dump(tx_data, f, indent=2)

        sig_count = len(tx_data["signatures"])
        threshold = tx_data.get("threshold", "?")

        if args.json:
            print(json.dumps({"signatures": sig_count, "threshold": threshold, "output": output_path}))
        else:
            print(f"Signature added ({sig_count}/{threshold})")
            print(f"Updated transaction saved to: {output_path}")
            if sig_count >= int(threshold) if threshold != "?" else False:
                print("Transaction has enough signatures! Ready to submit.")

        return 0
    except Exception as e:
        logger.error("Multisig signing error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

def _multisig_submit(args: argparse.Namespace) -> int:
    """Submit a fully-signed multisig transaction."""
    try:
        # Load transaction file
        with open(args.tx_file, 'r') as f:
            tx_data = json.load(f)

        signatures = tx_data.get("signatures", [])
        threshold = tx_data.get("threshold", 0)

        if len(signatures) < threshold:
            print(f"Error: Not enough signatures ({len(signatures)}/{threshold})", file=sys.stderr)
            return 1

        # Prepare submission payload
        payload = tx_data.get("payload", {})
        submission = {
            **payload,
            "multisig": True,
            "signatures": [{"public_key": s["public_key"], "signature": s["signature"]} for s in signatures],
            "threshold": threshold,
        }

        # Submit to node
        endpoint = f"{args.base_url.rstrip('/')}/transaction/multisig"
        response = requests.post(endpoint, json=submission, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            if data.get("success"):
                print(f"Multisig transaction submitted successfully!")
                print(f"TX ID: {data.get('txid', 'pending')}")
            else:
                print(f"Submission failed: {data.get('error', 'Unknown error')}")
                return 1

        return 0
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 2
    except Exception as e:
        logger.error("Multisig submit error: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

def _multisig_status(args: argparse.Namespace) -> int:
    """Check status of a multisig transaction file."""
    try:
        with open(args.tx_file, 'r') as f:
            tx_data = json.load(f)

        signatures = tx_data.get("signatures", [])
        threshold = tx_data.get("threshold", 0)
        payload = tx_data.get("payload", {})

        if args.json:
            print(json.dumps({
                "threshold": threshold,
                "signatures_collected": len(signatures),
                "ready": len(signatures) >= threshold,
                "signers": [s.get("public_key", "")[:16] + "..." for s in signatures],
                "payload": payload,
            }, indent=2))
        else:
            print(f"{'='*50}")
            print(f"MULTISIG TRANSACTION STATUS")
            print(f"{'='*50}")
            print(f"Threshold:   {threshold} signatures required")
            print(f"Collected:   {len(signatures)} signatures")
            print(f"Status:      {'✓ READY TO SUBMIT' if len(signatures) >= threshold else f'⏳ Need {threshold - len(signatures)} more'}")
            print(f"{'='*50}")
            if payload:
                print(f"Sender:      {payload.get('sender', 'N/A')}")
                print(f"Recipient:   {payload.get('recipient', 'N/A')}")
                print(f"Amount:      {payload.get('amount', 'N/A')} XAI")
            print(f"{'='*50}")
            print(f"Signers:")
            for i, sig in enumerate(signatures, 1):
                pk = sig.get("public_key", "unknown")
                print(f"  {i}. {pk[:20]}...{pk[-8:]}")

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description="XAI wallet utilities")
    subparsers = parser.add_subparsers(dest="command")

    # Request faucet
    faucet = subparsers.add_parser(
        "request-faucet",
        help="Request testnet XAI via the faucet endpoint",
    )
    faucet.add_argument(
        "--address",
        required=True,
        help="Destination TXAI address",
    )
    faucet.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Node API base URL (default: {DEFAULT_API_URL})",
    )
    faucet.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds",
    )
    faucet.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON response",
    )
    faucet.set_defaults(func=_request_faucet)

    # Generate address
    generate = subparsers.add_parser(
        "generate-address",
        help="Generate a brand new wallet address",
        description=(
            "Generate a new wallet with secure key management.\n\n"
            "SECURITY BEST PRACTICES:\n"
            "  --save-keystore    Create encrypted keystore (RECOMMENDED)\n"
            "  --show-private-key Display private key (NOT RECOMMENDED)\n\n"
            "By default, only the address and public key are shown."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    generate.add_argument(
        "--save-keystore",
        action="store_true",
        help="Save to encrypted keystore file (RECOMMENDED)",
    )
    generate.add_argument(
        "--keystore-output",
        help="Output path for keystore (default: ~/.xai/keystores/ADDRESS.keystore)",
    )
    generate.add_argument(
        "--show-private-key",
        action="store_true",
        help="Display private key on screen (NOT RECOMMENDED - security risk)",
    )
    generate.add_argument(
        "--kdf",
        choices=["pbkdf2", "argon2id"],
        default="pbkdf2",
        help="Key derivation function for keystore (default: pbkdf2)",
    )
    generate.add_argument(
        "--json",
        action="store_true",
        help="Emit output as JSON (deprecated - insecure)",
    )
    generate.set_defaults(func=_generate_address)

    # Check balance
    balance = subparsers.add_parser(
        "balance",
        help="Check wallet balance with UTXO breakdown",
    )
    balance.add_argument(
        "--address",
        required=True,
        help="Wallet address to check",
    )
    balance.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Node API base URL (default: {DEFAULT_API_URL})",
    )
    balance.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds",
    )
    balance.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON response",
    )
    balance.set_defaults(func=_check_balance)

    # Send transaction
    send = subparsers.add_parser(
        "send",
        help="Send XAI to another address",
        description=(
            "Send XAI transaction with secure private key handling.\n\n"
            "SECURITY: Private key is NEVER passed as CLI argument.\n"
            "Use one of these secure methods:\n"
            "  --keystore PATH     Load from encrypted keystore (RECOMMENDED)\n"
            "  [interactive]       Secure password-style input (default)\n"
            "  --allow-env-key     Use XAI_PRIVATE_KEY env var (NOT RECOMMENDED)\n\n"
            "Example: xai-wallet send --sender ADDR --recipient ADDR --amount 10 --keystore ~/.xai/keystores/wallet.keystore"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    send.add_argument(
        "--sender",
        required=True,
        help="Sender address",
    )
    send.add_argument(
        "--recipient",
        required=True,
        help="Recipient address",
    )
    send.add_argument(
        "--amount",
        type=float,
        required=True,
        help="Amount to send",
    )
    send.add_argument(
        "--fee",
        type=float,
        default=0.001,
        help="Transaction fee (default: 0.001)",
    )
    send.add_argument(
        "--keystore",
        help="Path to encrypted keystore file (RECOMMENDED)",
    )
    send.add_argument(
        "--allow-env-key",
        action="store_true",
        help="Allow reading private key from XAI_PRIVATE_KEY env var (NOT RECOMMENDED)",
    )
    send.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Node API base URL (default: {DEFAULT_API_URL})",
    )
    send.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds",
    )
    send.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON response",
    )
    send.add_argument(
        "--2fa-profile",
        help="Require TOTP verification with the specified 2FA profile label",
    )
    send.add_argument(
        "--otp",
        help="Provide 2FA code via argument (use with caution). If omitted, prompts securely.",
    )
    send.set_defaults(func=_send_transaction)

    # Wallet history
    history = subparsers.add_parser(
        "history",
        help="View wallet transaction history",
    )
    history.add_argument(
        "--address",
        required=True,
        help="Wallet address",
    )
    history.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of transactions to show (default: 10)",
    )
    history.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset for pagination (default: 0)",
    )
    history.add_argument(
        "--base-url",
        default=DEFAULT_API_URL,
        help=f"Node API base URL (default: {DEFAULT_API_URL})",
    )
    history.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds",
    )
    history.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON response",
    )
    history.set_defaults(func=_wallet_history)

    # Export wallet
    export = subparsers.add_parser(
        "export",
        help="Export wallet to file",
        description=(
            "Export wallet with secure key handling.\n\n"
            "SECURITY: Private key is NEVER passed as CLI argument.\n"
            "Use one of these secure methods:\n"
            "  --keystore PATH     Load from existing keystore (RECOMMENDED)\n"
            "  [interactive]       Secure password-style input (default)\n\n"
            "Always use --encrypt to protect the exported file!"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    export.add_argument(
        "--address",
        required=True,
        help="Wallet address",
    )
    export.add_argument(
        "--public-key",
        default="",
        help="Public key (optional)",
    )
    export.add_argument(
        "--keystore",
        help="Path to source keystore file (secure method)",
    )
    export.add_argument(
        "--allow-env-key",
        action="store_true",
        help="Allow reading private key from XAI_PRIVATE_KEY env var (NOT RECOMMENDED)",
    )
    export.add_argument(
        "--output",
        help="Output file path (default: wallet_ADDRESS.enc)",
    )
    export.add_argument(
        "--encrypt",
        action="store_true",
        default=True,
        help="Encrypt the exported file (default: True, highly recommended)",
    )
    export.add_argument(
        "--no-encrypt",
        dest="encrypt",
        action="store_false",
        help="Export without encryption (DANGEROUS - requires confirmation)",
    )
    export.add_argument(
        "--kdf",
        choices=["pbkdf2", "argon2id"],
        default="pbkdf2",
        help="Key derivation function (default: pbkdf2)",
    )
    export.add_argument(
        "--2fa-profile",
        help="Require TOTP verification with the specified 2FA profile label",
    )
    export.add_argument(
        "--otp",
        help="Provide 2FA code via argument (use with caution). If omitted, prompts securely.",
    )
    export.set_defaults(func=_export_wallet)

    # Import wallet
    import_cmd = subparsers.add_parser(
        "import",
        help="Import wallet from file",
    )
    import_cmd.add_argument(
        "--file",
        required=True,
        help="Wallet file to import",
    )
    import_cmd.add_argument(
        "--no-private-key",
        action="store_true",
        help="Don't display private key",
    )
    import_cmd.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON output",
    )
    import_cmd.set_defaults(func=_import_wallet)

    # Mnemonic QR backup
    mnemonic_qr = subparsers.add_parser(
        "mnemonic-qr",
        help="Generate a QR code backup for a BIP-39 mnemonic",
        description=(
            "Create an offline QR code backup for a seed phrase. "
            "WARNING: The QR payload contains your entire mnemonic; treat it like the seed itself."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mnemonic_qr.add_argument(
        "--mnemonic",
        help="Mnemonic phrase (use quotes). Leaving empty prompts for secure input.",
    )
    mnemonic_qr.add_argument(
        "--mnemonic-file",
        help="Path to file containing mnemonic phrase (one line, words separated by spaces).",
    )
    mnemonic_qr.add_argument(
        "--bip39-passphrase",
        default="",
        help="Optional BIP-39 passphrase tied to the mnemonic.",
    )
    mnemonic_qr.add_argument(
        "--include-passphrase",
        action="store_true",
        help="Embed the plaintext passphrase in the QR payload (NOT recommended).",
    )
    mnemonic_qr.add_argument(
        "--metadata-address",
        help="Optional wallet address metadata stored in the QR payload.",
    )
    mnemonic_qr.add_argument(
        "--note",
        help="Optional note stored in the payload (e.g., device/location).",
    )
    mnemonic_qr.add_argument(
        "--output",
        help="Write PNG image to this path (default: print base64 representation).",
    )
    mnemonic_qr.add_argument(
        "--payload-output",
        help="Write structured payload JSON to this path (sensitive!).",
    )
    mnemonic_qr.add_argument(
        "--ascii",
        action="store_true",
        help="Render ASCII-art QR to stdout for immediate scanning.",
    )
    mnemonic_qr.add_argument(
        "--show-base64",
        action="store_true",
        help="Print base64 PNG data even if --output is specified.",
    )
    mnemonic_qr.add_argument(
        "--skip-confirmation",
        action="store_true",
        help="Skip mnemonic double-entry confirmation when prompted interactively.",
    )
    mnemonic_qr.set_defaults(func=_mnemonic_qr_backup)

    # 2FA subcommands
    twofa_setup = subparsers.add_parser(
        "2fa-setup",
        help="Enable TOTP-based 2FA for wallet commands",
    )
    twofa_setup.add_argument("--label", required=True, help="Profile label (e.g., wallet name)")
    twofa_setup.add_argument("--user-email", help="Optional email/account identifier for authenticator")
    twofa_setup.add_argument(
        "--qr-output",
        help="Optional path to save provisioning QR as PNG",
    )
    twofa_setup.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing profile if it already exists",
    )
    twofa_setup.set_defaults(func=_setup_two_factor)

    twofa_status = subparsers.add_parser(
        "2fa-status",
        help="Show metadata for a 2FA profile",
    )
    twofa_status.add_argument("--label", required=True, help="Profile label")
    twofa_status.set_defaults(func=_two_factor_status)

    twofa_disable = subparsers.add_parser(
        "2fa-disable",
        help="Delete a 2FA profile",
    )
    twofa_disable.add_argument("--label", required=True, help="Profile label to delete")
    twofa_disable.set_defaults(func=_two_factor_disable)

    # Watch-only wallet management
    watch = subparsers.add_parser(
        "watch",
        help="Manage watch-only wallet entries",
        description="Add, list, and remove watch-only addresses for monitoring without private keys.",
    )
    watch_sub = watch.add_subparsers(dest="watch_command")
    watch_sub.required = True

    watch_add = watch_sub.add_parser(
        "add",
        help="Add a watch-only address (manual or derived from xpub)",
    )
    _add_watch_add_arguments(watch_add)
    watch_add.set_defaults(func=_watch_add)

    watch_list = watch_sub.add_parser("list", help="List watch-only addresses")
    watch_list.add_argument(
        "--tag",
        action="append",
        help="Filter by tag (repeatable, case-insensitive).",
    )
    watch_list.add_argument(
        "--store",
        help="Override watch-only store path (default: ~/.xai/watch_only.json).",
    )
    watch_list.add_argument("--json", action="store_true", help="Emit JSON output.")
    watch_list.set_defaults(func=_watch_list)

    watch_remove = watch_sub.add_parser("remove", help="Remove watch-only address")
    watch_remove.add_argument("--address", required=True, help="Address to remove from the store.")
    watch_remove.add_argument(
        "--store",
        help="Override watch-only store path (default: ~/.xai/watch_only.json).",
    )
    watch_remove.add_argument("--json", action="store_true", help="Emit JSON output.")
    watch_remove.set_defaults(func=_watch_remove)

    # Legacy alias for docs/scripts
    watch_alias = subparsers.add_parser(
        "watch-address",
        help="Alias for 'watch add' to maintain backward compatibility with existing guides.",
    )
    _add_watch_add_arguments(watch_alias)
    watch_alias.set_defaults(func=_watch_add)

    # Hardware wallet commands
    hw_address = subparsers.add_parser(
        "hw-address",
        help="Get address from connected hardware wallet",
    )
    hw_address.add_argument("--ledger", action="store_true", help="Use Ledger device")
    hw_address.add_argument("--trezor", action="store_true", help="Use Trezor device")
    hw_address.add_argument("--json", action="store_true", help="Output as JSON")
    hw_address.set_defaults(func=_hw_address)

    hw_sign = subparsers.add_parser(
        "hw-sign",
        help="Sign a message with hardware wallet",
    )
    hw_sign.add_argument("--ledger", action="store_true", help="Use Ledger device")
    hw_sign.add_argument("--trezor", action="store_true", help="Use Trezor device")
    hw_sign.add_argument("--message", help="Message to sign (text)")
    hw_sign.add_argument("--message-file", help="File containing message to sign")
    hw_sign.add_argument("--json", action="store_true", help="Output as JSON")
    hw_sign.set_defaults(func=_hw_sign)

    hw_verify = subparsers.add_parser(
        "hw-verify",
        help="Verify hardware wallet address (display on device)",
    )
    hw_verify.add_argument("--ledger", action="store_true", help="Use Ledger device")
    hw_verify.add_argument("--trezor", action="store_true", help="Use Trezor device")
    hw_verify.add_argument("--json", action="store_true", help="Output as JSON")
    hw_verify.set_defaults(func=_hw_verify)

    hw_send = subparsers.add_parser(
        "hw-send",
        help="Send XAI using hardware wallet for signing",
        description=(
            "Send XAI transaction signed by your hardware wallet.\n\n"
            "SECURITY: Private key NEVER leaves your device.\n"
            "The transaction is displayed on your device screen for verification.\n\n"
            "Example: xai-wallet hw-send --ledger --recipient ADDR --amount 10"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    hw_send.add_argument("--ledger", action="store_true", help="Use Ledger device")
    hw_send.add_argument("--trezor", action="store_true", help="Use Trezor device")
    hw_send.add_argument("--sender", help="Sender address (optional, derived from device)")
    hw_send.add_argument("--recipient", required=True, help="Recipient address")
    hw_send.add_argument("--amount", type=float, required=True, help="Amount to send")
    hw_send.add_argument("--fee", type=float, default=0.001, help="Transaction fee (default: 0.001)")
    hw_send.add_argument("--base-url", default=DEFAULT_API_URL, help=f"Node API URL (default: {DEFAULT_API_URL})")
    hw_send.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout")
    hw_send.add_argument("--json", action="store_true", help="Output as JSON")
    hw_send.add_argument("--2fa-profile", help="Require TOTP verification")
    hw_send.add_argument("--otp", help="2FA code (prompts if omitted)")
    hw_send.set_defaults(func=_hw_send)

    # Multisig commands
    ms_create = subparsers.add_parser(
        "multisig-create",
        help="Create a new multisig wallet configuration",
        description=(
            "Create an M-of-N multisig wallet configuration.\n\n"
            "Example: xai-wallet multisig-create --threshold 2 --public-keys KEY1 KEY2 KEY3"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ms_create.add_argument("--threshold", "-m", type=int, required=True, help="Required signatures (M in M-of-N)")
    ms_create.add_argument("--public-keys", "-k", nargs="+", help="Public keys (hex format)")
    ms_create.add_argument("--keys-file", help="File containing public keys (one per line)")
    ms_create.add_argument("--output", "-o", help="Output file for multisig config")
    ms_create.add_argument("--json", action="store_true", help="Output as JSON")
    ms_create.set_defaults(func=_multisig_create)

    ms_sign = subparsers.add_parser(
        "multisig-sign",
        help="Add your signature to a multisig transaction",
        description=(
            "Sign a multisig transaction with your private key.\n\n"
            "Example: xai-wallet multisig-sign --tx-file tx.json --keystore wallet.keystore"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ms_sign.add_argument("--tx-file", required=True, help="Transaction file to sign")
    ms_sign.add_argument("--keystore", help="Path to your encrypted keystore")
    ms_sign.add_argument("--output", "-o", help="Output file (default: overwrite input)")
    ms_sign.add_argument("--json", action="store_true", help="Output as JSON")
    ms_sign.set_defaults(func=_multisig_sign)

    ms_submit = subparsers.add_parser(
        "multisig-submit",
        help="Submit a fully-signed multisig transaction",
    )
    ms_submit.add_argument("--tx-file", required=True, help="Signed transaction file")
    ms_submit.add_argument("--base-url", default=DEFAULT_API_URL, help=f"Node API URL (default: {DEFAULT_API_URL})")
    ms_submit.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout")
    ms_submit.add_argument("--json", action="store_true", help="Output as JSON")
    ms_submit.set_defaults(func=_multisig_submit)

    ms_status = subparsers.add_parser(
        "multisig-status",
        help="Check status of a multisig transaction",
    )
    ms_status.add_argument("--tx-file", required=True, help="Transaction file to check")
    ms_status.add_argument("--json", action="store_true", help="Output as JSON")
    ms_status.set_defaults(func=_multisig_status)

    return parser

def main(argv: Any = None) -> int:
    """Program entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
