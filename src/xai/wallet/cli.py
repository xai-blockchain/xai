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
from typing import Any, Dict, Tuple

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf import pbkdf2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from xai.core.wallet import Wallet

DEFAULT_API_URL = os.getenv("XAI_API_URL", "http://localhost:18545")

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
    """Handle the generate-address subcommand."""
    wallet = Wallet()
    payload = {
        "success": True,
        "address": wallet.address,
        "public_key": wallet.public_key,
        "private_key": wallet.private_key,
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "\n".join(
                [
                    f"Address:     {wallet.address}",
                    f"Public Key:  {wallet.public_key}",
                    f"Private Key: {wallet.private_key}",
                    "\nSave the private key securely. It cannot be recovered.",
                ]
            )
        )

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
    """Handle the send-transaction subcommand."""
    endpoint = f"{args.base_url.rstrip('/')}/transaction"

    payload = {
        "sender": args.sender,
        "recipient": args.recipient,
        "amount": args.amount,
        "private_key": args.private_key,
        "fee": args.fee,
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=args.timeout)
        response.raise_for_status()
        data = response.json()

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
    """Handle the export-wallet subcommand."""
    wallet_data = {
        "address": args.address,
        "private_key": args.private_key,
        "public_key": args.public_key if hasattr(args, "public_key") else "",
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
                "hmac": base64.b64encode(signature).decode('ascii')
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(encrypted_wallet, f, indent=2)

            print(f"Wallet exported (encrypted with AES-256-GCM) to {output_file}")
            print(f"Encryption: AES-256-GCM with {args.kdf.upper()}")
            print("Keep your password secure - it cannot be recovered!")
        else:
            # Unencrypted export (warn user)
            output_file = args.output or f"wallet_{args.address[:8]}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(wallet_data, f, indent=2)

            print(f"Wallet exported to {output_file}")
            print("WARNING: File is NOT encrypted. Keep it secure!")
            print("Recommendation: Use --encrypt flag for production wallets")

        # Set restrictive file permissions (owner read/write only)
        os.chmod(output_file, 0o600)

        return 0
    except Exception as e:
        print(f"Export error: {e}", file=sys.stderr)
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
    )
    generate.add_argument(
        "--json",
        action="store_true",
        help="Emit the generated keys as JSON",
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
        "--private-key",
        required=True,
        help="Sender's private key",
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
    )
    export.add_argument(
        "--address",
        required=True,
        help="Wallet address",
    )
    export.add_argument(
        "--private-key",
        required=True,
        help="Private key",
    )
    export.add_argument(
        "--output",
        help="Output file path (default: wallet_ADDRESS.json)",
    )
    export.add_argument(
        "--encrypt",
        action="store_true",
        help="Encrypt the exported file",
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
