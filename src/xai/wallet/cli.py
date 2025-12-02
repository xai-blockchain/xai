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
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf import pbkdf2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from xai.core.wallet import Wallet

DEFAULT_API_URL = os.getenv("XAI_API_URL", "http://localhost:18545")
DEFAULT_KEYSTORE_DIR = Path.home() / ".xai" / "keystores"

# Encryption constants
PBKDF2_ITERATIONS = 600000  # NIST recommended minimum for 2023+
ARGON2_TIME_COST = 3  # ops limit
ARGON2_MEMORY_COST = 65536  # 64 MB
ARGON2_PARALLELISM = 4
SALT_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits for AES-GCM
KEY_SIZE = 32  # 256 bits for AES-256


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
    kdf = pbkdf2.PBKDF2(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


def encrypt_wallet_data(wallet_data: Dict[str, Any], password: str, kdf: str = "pbkdf2") -> Tuple[bytes, bytes, bytes, bytes]:
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

def decrypt_wallet_data(data: DecryptionData) -> Dict[str, Any]:
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
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")


def get_private_key_secure(
    keystore_path: Optional[str] = None,
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
                print("WARNING: Keystore is not encrypted!", file=sys.stderr)
                private_key = keystore_data.get("private_key", "")
                if not private_key:
                    raise ValueError("No private key found in keystore")
                return private_key.replace("0x", "")

        except FileNotFoundError:
            raise FileNotFoundError(f"Keystore file not found: {keystore_path}")
        except json.JSONDecodeError:
            raise ValueError("Invalid keystore file format")
        except Exception as e:
            raise ValueError(f"Failed to load keystore: {e}")

    # Method 2: Check environment variable (with security warning)
    if allow_env:
        env_key = os.environ.get("XAI_PRIVATE_KEY")
        if env_key:
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
    output_path: Optional[str] = None,
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



def _format_response(data: Dict[str, Any], as_json: bool) -> str:
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

    try:
        response = requests.post(endpoint, json=payload, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"Network error contacting faucet: {exc}", file=sys.stderr)
        return 2

    try:
        data = response.json()
    except ValueError:
        print(
            f"Unexpected response ({response.status_code}): {response.text}",
            file=sys.stderr,
        )
        return 3

    success = response.ok and data.get("success") is True
    print(_format_response(data, args.json))
    return 0 if success else 1


def _generate_address(args: argparse.Namespace) -> int:
    """Handle the generate-address subcommand.

    Security: Private keys are NEVER printed to stdout by default.
    Use --save-keystore to create encrypted keystore or --show-private-key
    with explicit confirmation to display the key.
    """
    wallet = Wallet()

    # Deprecated --json flag warning
    if args.json:
        print("=" * 70, file=sys.stderr)
        print("WARNING: --json flag is DEPRECATED and INSECURE", file=sys.stderr)
        print("It outputs private keys in plaintext which can expose them.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Use --save-keystore instead for secure key storage.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)

        # Still support it but require confirmation
        confirm = input("\nType 'SHOW JSON' to continue with insecure output: ")
        if confirm != "SHOW JSON":
            print("Cancelled. Use --save-keystore for secure storage.", file=sys.stderr)
            return 1

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
            keystore_path = create_keystore(
                address=wallet.address,
                private_key=wallet.private_key,
                public_key=wallet.public_key,
                output_path=args.keystore_output,
                kdf=args.kdf
            )
            print(f"Wallet generated successfully!")
            print(f"Address: {wallet.address}")
            print(f"Public Key: {wallet.public_key}")
            print(f"\nEncrypted keystore saved to: {keystore_path}")
            print("Keep your password secure - it cannot be recovered!")
            return 0
        except Exception as e:
            print(f"Error creating keystore: {e}", file=sys.stderr)
            return 1

    # If user explicitly wants to see private key (DANGEROUS)
    if args.show_private_key:
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
            print("Cancelled. Use --save-keystore for secure storage.", file=sys.stderr)
            return 1

        # User confirmed - show everything
        print(f"\nAddress:     {wallet.address}")
        print(f"Public Key:  {wallet.public_key}")
        print(f"Private Key: {wallet.private_key}")
        print("\nSave the private key securely. It cannot be recovered.")
        print("Clear your terminal after noting this information.")
        return 0

    # Default: Show address and public key only (SAFE)
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

            print(f"Address: {args.address}")
            print(f"Balance: {balance} XAI")
            if pending_in > 0:
                print(f"Pending Incoming: {pending_in} XAI")
            if pending_out > 0:
                print(f"Pending Outgoing: {pending_out} XAI")

        return 0
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 2


def _send_transaction(args: argparse.Namespace) -> int:
    """Handle the send-transaction subcommand.

    Security: Private key is obtained securely via keystore or interactive input.
    NEVER passed as CLI argument.
    """
    try:
        # Securely obtain private key
        private_key = get_private_key_secure(
            keystore_path=args.keystore,
            allow_env=args.allow_env_key,
            prompt="Enter sender's private key"
        )
    except Exception as e:
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
                print(f"Transaction sent successfully!")
                print(f"TX ID: {data.get('txid', 'pending')}")
                print(f"Amount: {args.amount} XAI")
                print(f"Fee: {args.fee} XAI")
            else:
                print(f"Transaction failed: {data.get('error', 'Unknown error')}")
                return 1

        return 0
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 2
    finally:
        # Ensure cleanup
        try:
            del private_key
        except NameError:
            pass


def _wallet_history(args: argparse.Namespace) -> int:
    """Handle the wallet-history subcommand."""
    endpoint = f"{args.base_url.rstrip('/')}/history/{args.address}"
    params = {"limit": args.limit, "offset": args.offset}

    try:
        response = requests.get(endpoint, params=params, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            transactions = data.get("transactions", [])
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
        print(f"Network error: {exc}", file=sys.stderr)
        return 2


def _export_wallet(args: argparse.Namespace) -> int:
    """Handle the export-wallet subcommand.

    Security: Private key obtained securely, never via CLI argument.
    """
    try:
        # Securely obtain private key
        private_key = get_private_key_secure(
            keystore_path=args.keystore,
            allow_env=args.allow_env_key,
            prompt="Enter private key to export"
        )
    except Exception as e:
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
            password = getpass.getpass("Enter encryption password: ")
            password_confirm = getpass.getpass("Confirm password: ")

            if password != password_confirm:
                print("Passwords do not match!", file=sys.stderr)
                return 1

            if len(password) < 12:
                print("Password must be at least 12 characters!", file=sys.stderr)
                return 1
            if not any(char.isupper() for char in password):
                print("Password must contain at least one uppercase letter!", file=sys.stderr)
                return 1
            if not any(char.islower() for char in password):
                print("Password must contain at least one lowercase letter!", file=sys.stderr)
                return 1
            if not any(char.isdigit() for char in password):
                print("Password must contain at least one digit!", file=sys.stderr)
                return 1
            if not any(char in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for char in password):
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

            print(f"Wallet exported (encrypted with AES-256-GCM) to {output_file}")
            print(f"Encryption: AES-256-GCM with {args.kdf.upper()}")
            print("Keep your password secure - it cannot be recovered!")
        else:
            # Unencrypted export - require explicit confirmation
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
                print("Cancelled. Use --encrypt for secure export.", file=sys.stderr)
                del private_key, wallet_data
                return 1

            output_file = args.output or f"wallet_{args.address[:8]}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(wallet_data, f, indent=2)

            # Clear sensitive data
            del private_key, wallet_data

            print(f"Wallet exported to {output_file}")
            print("WARNING: File is NOT encrypted. Keep it secure!")
            print("Recommendation: Use --encrypt flag for production wallets")

        # Set restrictive file permissions (owner read/write only)
        os.chmod(output_file, 0o600)

        return 0
    except Exception as e:
        print(f"Export error: {e}", file=sys.stderr)
        # Clear sensitive data on error
        try:
            del private_key, wallet_data
        except NameError:
            pass
        return 1


def _import_wallet(args: argparse.Namespace) -> int:
    """Handle the import-wallet subcommand."""
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to parse as JSON first
        try:
            file_data = json.loads(content)
        except json.JSONDecodeError:
            print("Error: Invalid wallet file format", file=sys.stderr)
            return 1

        # Check if file is encrypted (version 2.0 format)
        if file_data.get("version") == "2.0" and "encrypted_data" in file_data:
            # Encrypted wallet - need password
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

                print("Wallet imported successfully (decrypted and verified)")
                print(f"Algorithm: {file_data.get('algorithm', 'AES-256-GCM')}")
                print(f"KDF: {kdf.upper()}")

            except ValueError as e:
                print(f"Decryption failed: {e}", file=sys.stderr)
                print("Possible reasons: wrong password, corrupted file, or tampered data", file=sys.stderr)
                return 1
        else:
            # Unencrypted wallet (legacy format)
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
        print(f"Error: File '{args.file}' not found", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Import error: {e}", file=sys.stderr)
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
