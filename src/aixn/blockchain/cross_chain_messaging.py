from typing import Dict, Any, List, Tuple
import hashlib
import json
from src.aixn.blockchain.merkle import MerkleTree # Import MerkleTree

class CrossChainMessage:
    def __init__(self, origin_chain_id: str, destination_chain_id: str,
                 sender_address: str, recipient_address: str,
                 payload: Dict[str, Any], sequence_number: int,
                 merkle_proof: List[Tuple[str, str]] = None):
        if not origin_chain_id or not destination_chain_id:
            raise ValueError("Origin and destination chain IDs cannot be empty.")
        if not sender_address or not recipient_address:
            raise ValueError("Sender and recipient addresses cannot be empty.")
        if not payload:
            raise ValueError("Message payload cannot be empty.")
        if not isinstance(sequence_number, int) or sequence_number <= 0:
            raise ValueError("Sequence number must be a positive integer.")

        self.origin_chain_id = origin_chain_id
        self.destination_chain_id = destination_chain_id
        self.sender_address = sender_address
        self.recipient_address = recipient_address
        self.payload = payload
        self.sequence_number = sequence_number
        self.merkle_proof = merkle_proof # Proof of inclusion on origin chain

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin_chain_id": self.origin_chain_id,
            "destination_chain_id": self.destination_chain_id,
            "sender_address": self.sender_address,
            "recipient_address": self.recipient_address,
            "payload": self.payload,
            "sequence_number": self.sequence_number,
            # Merkle proof is not part of the message content for hashing, but attached for verification
        }

    def get_message_hash(self) -> str:
        """Generates a consistent hash of the message content for Merkle tree inclusion."""
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()

    def __repr__(self):
        return (
            f"CrossChainMessage(from='{self.origin_chain_id}', to='{self.destination_chain_id}', "
            f"seq={self.sequence_number}, payload={self.payload})"
        )

class CrossChainMessageVerifier:
    def __init__(self):
        pass

    def verify_message(self, message: CrossChainMessage, origin_chain_merkle_root: str) -> bool:
        """
        Verifies a cross-chain message using its attached Merkle proof against the
        known Merkle root of the origin chain.
        """
        if not message.merkle_proof:
            print(f"Error: Message {message.sequence_number} from {message.origin_chain_id} has no Merkle proof attached.")
            return False

        message_hash = message.get_message_hash()
        
        is_valid = MerkleTree.verify_merkle_proof(message.to_dict(), origin_chain_merkle_root, message.merkle_proof)

        if is_valid:
            print(f"Cross-chain message {message.sequence_number} from {message.origin_chain_id} VERIFIED.")
        else:
            print(f"Cross-chain message {message.sequence_number} from {message.origin_chain_id} FAILED VERIFICATION.")
        
        return is_valid

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # Simulate an origin chain's block with messages
    # In a real scenario, these would be actual transactions/events on the origin chain
    origin_chain_messages_data = [
        {"origin_chain_id": "ChainA", "destination_chain_id": "ChainB", "sender_address": "0xSender1", "recipient_address": "0xReceiver1", "payload": {"type": "transfer", "amount": 100}, "sequence_number": 1},
        {"origin_chain_id": "ChainA", "destination_chain_id": "ChainC", "sender_address": "0xSender2", "recipient_address": "0xReceiver2", "payload": {"type": "call_contract", "contract": "0xContractX", "method": "mint"}, "sequence_number": 2},
        {"origin_chain_id": "ChainA", "destination_chain_id": "ChainB", "sender_address": "0xSender3", "recipient_address": "0xReceiver3", "payload": {"type": "transfer", "amount": 50}, "sequence_number": 3},
    ]

    # Create Merkle tree from these messages on the origin chain
    # The MerkleTree expects raw data leaves, so we'll pass the dicts directly
    merkle_leaves = [msg for msg in origin_chain_messages_data]
    origin_merkle_tree = MerkleTree(merkle_leaves)
    origin_chain_root = origin_merkle_tree.get_root()
    print(f"Origin Chain Merkle Root: {origin_chain_root}")

    # Simulate a relayer picking up a message and generating a proof
    message_to_relay_data = origin_chain_messages_data[0] # Message 1
    message_to_relay = CrossChainMessage(
        origin_chain_id=message_to_relay_data["origin_chain_id"],
        destination_chain_id=message_to_relay_data["destination_chain_id"],
        sender_address=message_to_relay_data["sender_address"],
        recipient_address=message_to_relay_data["recipient_address"],
        payload=message_to_relay_data["payload"],
        sequence_number=message_to_relay_data["sequence_number"]
    )
    
    # Generate proof for the message (using the original dict for proof generation)
    proof_for_message = origin_merkle_tree.generate_merkle_proof(message_to_relay_data)
    message_to_relay.merkle_proof = proof_for_message

    print(f"\nMessage to relay: {message_to_relay}")
    print(f"Attached Merkle Proof: {message_to_relay.merkle_proof}")

    # Simulate the destination chain verifying the message
    verifier = CrossChainMessageVerifier()
    print("\n--- Verifying Message on Destination Chain ---")
    is_message_valid = verifier.verify_message(message_to_relay, origin_chain_root)
    print(f"Is relayed message valid? {is_message_valid}")

    # Test with a tampered message
    print("\n--- Testing with a tampered message ---")
    tampered_payload = {"type": "transfer", "amount": 99999} # Tampered amount
    tampered_message = CrossChainMessage(
        origin_chain_id="ChainA", destination_chain_id="ChainB",
        sender_address="0xSender1", recipient_address="0xReceiver1",
        payload=tampered_payload, sequence_number=1,
        merkle_proof=proof_for_message # Still using the original proof
    )
    is_tampered_valid = verifier.verify_message(tampered_message, origin_chain_root)
    print(f"Is tampered message valid? {is_tampered_valid}")

    # Test with an invalid proof (e.g., from a different message)
    print("\n--- Testing with an invalid proof ---")
    invalid_proof_message_data = origin_chain_messages_data[1] # Message 2
    invalid_proof = origin_merkle_tree.generate_merkle_proof(invalid_proof_message_data) # Proof for message 2
    
    message_with_invalid_proof = CrossChainMessage(
        origin_chain_id=message_to_relay_data["origin_chain_id"],
        destination_chain_id=message_to_relay_data["destination_chain_id"],
        sender_address=message_to_relay_data["sender_address"],
        recipient_address=message_to_relay_data["recipient_address"],
        payload=message_to_relay_data["payload"],
        sequence_number=message_to_relay_data["sequence_number"],
        merkle_proof=invalid_proof # Incorrect proof
    )
    is_invalid_proof_valid = verifier.verify_message(message_with_invalid_proof, origin_chain_root)
    print(f"Is message with invalid proof valid? {is_invalid_proof_valid}")
