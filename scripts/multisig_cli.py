import argparse
import json
import os
from src.aixn.wallet.multisig_wallet import MultiSigWallet

# Directory to store wallet data (private keys, public keys, multisig configs)
WALLET_DATA_DIR = "multisig_data"
if not os.path.exists(WALLET_DATA_DIR):
    os.makedirs(WALLET_DATA_DIR)


def save_key_pair(private_key_hex, public_key_hex, name):
    with open(os.path.join(WALLET_DATA_DIR, f"{name}_priv.txt"), "w") as f:
        f.write(private_key_hex)
    with open(os.path.join(WALLET_DATA_DIR, f"{name}_pub.txt"), "w") as f:
        f.write(public_key_hex)
    print(f"Key pair for {name} saved to {WALLET_DATA_DIR}/")


def load_key_pair(name):
    try:
        with open(os.path.join(WALLET_DATA_DIR, f"{name}_priv.txt"), "r") as f:
            private_key_hex = f.read().strip()
        with open(os.path.join(WALLET_DATA_DIR, f"{name}_pub.txt"), "r") as f:
            public_key_hex = f.read().strip()
        return private_key_hex, public_key_hex
    except FileNotFoundError:
        print(f"Key pair for {name} not found in {WALLET_DATA_DIR}/")
        return None, None


def save_multisig_config(multisig_wallet):
    config = {
        "required_signatures": multisig_wallet.required_signatures,
        "public_keys": [pk.to_string("compressed").hex() for pk in multisig_wallet.public_keys],
        "multisig_address": multisig_wallet.multisig_address,
    }
    with open(
        os.path.join(WALLET_DATA_DIR, f"multisig_{multisig_wallet.multisig_address}.json"), "w"
    ) as f:
        json.dump(config, f, indent=4)
    print(
        f"Multisig wallet config saved to {WALLET_DATA_DIR}/multisig_{multisig_wallet.multisig_address}.json"
    )


def load_multisig_config(address):
    try:
        with open(os.path.join(WALLET_DATA_DIR, f"multisig_{address}.json"), "r") as f:
            config = json.load(f)
        return MultiSigWallet(config["required_signatures"], config["public_keys"])
    except FileNotFoundError:
        print(f"Multisig wallet config for address {address} not found.")
        return None


def save_transaction(transaction, filename):
    with open(os.path.join(WALLET_DATA_DIR, filename), "w") as f:
        json.dump(transaction, f, indent=4)
    print(f"Transaction saved to {WALLET_DATA_DIR}/{filename}")


def load_transaction(filename):
    try:
        with open(os.path.join(WALLET_DATA_DIR, filename), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Transaction file {filename} not found in {WALLET_DATA_DIR}/")
        return None


def main():
    parser = argparse.ArgumentParser(description="Multi-signature Wallet CLI for AIXN Blockchain.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate Key Pair
    generate_parser = subparsers.add_parser(
        "generate-key", help="Generate a new private/public key pair."
    )
    generate_parser.add_argument(
        "--name", required=True, help="A name to identify this key pair (e.g., owner1)."
    )

    # Create Multisig Wallet
    create_multisig_parser = subparsers.add_parser(
        "create-multisig", help="Create a new multi-signature wallet."
    )
    create_multisig_parser.add_argument(
        "--required", type=int, required=True, help="Number of signatures required (m)."
    )
    create_multisig_parser.add_argument(
        "--public-keys",
        nargs="+",
        required=True,
        help="List of public keys (hex strings) of the owners (n).",
    )

    # Create Transaction
    create_tx_parser = subparsers.add_parser(
        "create-tx", help="Create a new transaction for a multisig wallet."
    )
    create_tx_parser.add_argument(
        "--multisig-address", required=True, help="Address of the multisig wallet."
    )
    create_tx_parser.add_argument("--recipient", required=True, help="Recipient address.")
    create_tx_parser.add_argument("--amount", type=float, required=True, help="Amount to send.")
    create_tx_parser.add_argument("--payload", help="Optional transaction payload.")
    create_tx_parser.add_argument(
        "--output-file",
        default="unsigned_tx.json",
        help="Filename to save the unsigned transaction.",
    )

    # Sign Transaction
    sign_tx_parser = subparsers.add_parser(
        "sign-tx", help="Sign an existing transaction with a private key."
    )
    sign_tx_parser.add_argument(
        "--private-key-name", required=True, help="Name of the private key to use for signing."
    )
    sign_tx_parser.add_argument(
        "--transaction-file", required=True, help="Path to the unsigned transaction JSON file."
    )
    sign_tx_parser.add_argument(
        "--output-file",
        help="Optional: Filename to save the signed transaction (defaults to overwriting input).",
    )

    # Verify Transaction
    verify_tx_parser = subparsers.add_parser(
        "verify-tx", help="Verify if a transaction has enough valid signatures."
    )
    verify_tx_parser.add_argument(
        "--multisig-address", required=True, help="Address of the multisig wallet."
    )
    verify_tx_parser.add_argument(
        "--transaction-file", required=True, help="Path to the signed transaction JSON file."
    )

    args = parser.parse_args()

    if args.command == "generate-key":
        priv_key, pub_key = MultiSigWallet.generate_key_pair()
        save_key_pair(priv_key, pub_key, args.name)
        print(f"Generated Public Key for {args.name}: {pub_key}")

    elif args.command == "create-multisig":
        try:
            multisig_wallet = MultiSigWallet(args.required, args.public_keys)
            save_multisig_config(multisig_wallet)
            print(f"Multisig Wallet created with address: {multisig_wallet.get_address()}")
        except ValueError as e:
            print(f"Error creating multisig wallet: {e}")

    elif args.command == "create-tx":
        multisig_wallet = load_multisig_config(args.multisig_address)
        if multisig_wallet:
            tx = multisig_wallet.create_transaction(args.recipient, args.amount, args.payload)
            save_transaction(tx, args.output_file)

    elif args.command == "sign-tx":
        priv_key_hex, pub_key_hex = load_key_pair(args.private_key_name)
        if not priv_key_hex:
            return

        transaction = load_transaction(args.transaction_file)
        if not transaction:
            return

        # Check if this public key has already signed
        for sig, pk in transaction["signatures"]:
            if pk == pub_key_hex:
                print(
                    f"Warning: Key '{args.private_key_name}' has already signed this transaction."
                )
                # return # Allow re-signing for now, but a real system might prevent this

        signature = MultiSigWallet.sign_transaction(priv_key_hex, transaction)
        transaction["signatures"].append((signature, pub_key_hex))

        output_file = args.output_file if args.output_file else args.transaction_file
        save_transaction(transaction, output_file)
        print(
            f"Transaction signed by {args.private_key_name}. Current signatures: {len(transaction['signatures'])}"
        )

    elif args.command == "verify-tx":
        multisig_wallet = load_multisig_config(args.multisig_address)
        if not multisig_wallet:
            return

        transaction = load_transaction(args.transaction_file)
        if not transaction:
            return

        if multisig_wallet.is_transaction_authorized(transaction):
            print("Transaction is AUTHORIZED by enough owners!")
        else:
            print("Transaction is NOT AUTHORIZED by enough owners.")
            print(f"Required signatures: {multisig_wallet.required_signatures}")
            print(f"Current valid signatures: {len(transaction['signatures'])}")
            # Optional: detailed breakdown of valid/invalid signatures
            # For a real system, you'd want to know *which* signatures are valid/invalid


if __name__ == "__main__":
    main()
