import argparse
import json
import os
from datetime import datetime, timezone

from src.aixn.wallet.multisig_wallet import MultiSigWallet
from scripts.multisig_cli import load_key_pair, save_key_pair
from scripts.node_profile import write_node_config, ADMIN_PUBLIC_KEY_HEX, EMERGENCY_ADMIN_PUBLIC_KEY_HEX

def main():
    parser = argparse.ArgumentParser(description="Rotate Validator Key for AIXN Node.")
    parser.add_argument("--node-data-dir", required=True, help="Path to the node's data directory (e.g., ./data/node01).")
    parser.add_argument("--admin-key-name", default="admin_owner", help="Name of the admin key pair to use for signing the config update.")
    parser.add_argument("--use-emergency-key", action="store_true", help="Use an emergency admin key for signing.")
    parser.add_argument("--enactment-delay-hours", type=int, default=0, help="Time-lock delay for config changes in hours (0 for immediate).")
    parser.add_argument("--new-key-name", required=True, help="Name to save the new validator key pair (e.g., validator_key_new).")
    
    args = parser.parse_args()

    # 1. Generate a new validator key pair
    new_priv_key, new_pub_key = MultiSigWallet.generate_key_pair()
    save_key_pair(new_priv_key, new_pub_key, args.new_key_name)
    print(f"New validator key pair generated and saved as '{args.new_key_name}'.")
    print(f"New Public Key: {new_pub_key}")

    # 2. Load current node config to update the validator key
    node_data_dir_path = Path(args.node_data_dir).expanduser()
    config_path = node_data_dir_path / "node_config.json"
    if not config_path.exists():
        print(f"Error: Node config file not found at {config_path}. Please run node_wizard.py first.")
        return

    with open(config_path, "r", encoding="utf-8") as fp:
        current_node_config = json.load(fp)

    # Update the miner (validator) address in the payload
    # Assuming 'miner' field in node_config.json represents the validator's public key
    updated_node_payload = current_node_config.copy()
    updated_node_payload["miner"] = new_pub_key # Assuming miner address is the validator's public key

    # 3. Prepare for administrative action (update node config)
    signer_priv_key, signer_pub_key = load_key_pair(args.admin_key_name)
    if not signer_priv_key or not signer_pub_key:
        print(f"Admin key pair '{args.admin_key_name}' not found. Please generate it using 'python scripts/multisig_cli.py generate-key --name {args.admin_key_name}' first.")
        return

    if args.use_emergency_key:
        if signer_pub_key != EMERGENCY_ADMIN_PUBLIC_KEY_HEX:
            print(f"Error: Public key for '{args.admin_key_name}' does not match the designated EMERGENCY_ADMIN_PUBLIC_KEY_HEX.")
            return
    else:
        if signer_pub_key != ADMIN_PUBLIC_KEY_HEX:
            print(f"Error: Public key for '{args.admin_key_name}' does not match the designated ADMIN_PUBLIC_KEY_HEX.")
            return

    # Sign the updated node_payload
    payload_for_signing = {"payload_data": updated_node_payload}
    admin_signature = MultiSigWallet.sign_transaction(signer_priv_key, payload_for_signing)

    # Calculate enactment timestamp if delay is specified
    enactment_timestamp = None
    if args.enactment_delay_hours > 0:
        delay_seconds = args.enactment_delay_hours * 3600
        enactment_timestamp = int(datetime.now(timezone.utc).timestamp()) + delay_seconds
        print(f"Config change will be time-locked and enacted at: {datetime.fromtimestamp(enactment_timestamp, timezone.utc)} UTC")

    # 4. Call write_node_config to update the validator key
    try:
        write_node_config(node_data_dir_path, updated_node_payload, admin_signature, signer_pub_key, enactment_timestamp)
        print(f"Validator key rotation initiated for node at {args.node_data_dir}.")
        print(f"Node config updated with new validator public key: {new_pub_key}")
    except PermissionError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
