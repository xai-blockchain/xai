import pytest

from xai.blockchain.cross_chain_messaging import CrossChainMessage, CrossChainMessageVerifier
from xai.blockchain.merkle import MerkleTree
from xai.blockchain.fraud_proofs import FraudProofManager
from xai.blockchain.slashing import SlashingManager, ValidatorStake


class ManualClock:
    def __init__(self, start: int):
        self.current = start

    def now(self) -> int:
        return self.current

    def advance(self, seconds: int):
        self.current += seconds


def build_messages():
    base_payloads = [
        {
            "origin_chain_id": "ChainA",
            "destination_chain_id": "ChainB",
            "sender_address": "0xSender1",
            "recipient_address": "0xRecipient1",
            "payload": {"type": "transfer", "amount": 25},
            "sequence_number": 1,
        },
        {
            "origin_chain_id": "ChainA",
            "destination_chain_id": "ChainC",
            "sender_address": "0xSender2",
            "recipient_address": "0xRecipient2",
            "payload": {"type": "contract_call", "method": "mint"},
            "sequence_number": 2,
        },
    ]
    return base_payloads


def test_cross_chain_message_verifier_happy_path():
    messages = build_messages()
    tree = MerkleTree(messages)
    root = tree.get_root()

    message = CrossChainMessage(**messages[0])
    message.merkle_proof = tree.generate_merkle_proof(messages[0])

    verifier = CrossChainMessageVerifier()
    assert verifier.verify_message(message, root) is True


def test_cross_chain_message_verifier_failure_cases():
    messages = build_messages()
    tree = MerkleTree(messages)
    root = tree.get_root()

    verifier = CrossChainMessageVerifier()

    message = CrossChainMessage(**messages[0])
    message.merkle_proof = tree.generate_merkle_proof(messages[0])
    message.payload["amount"] = 999
    assert verifier.verify_message(message, root) is False

    missing_proof_msg = CrossChainMessage(**messages[0])
    missing_proof_msg.merkle_proof = None
    assert verifier.verify_message(missing_proof_msg, root) is False


@pytest.fixture()
def fraud_manager():
    clock = ManualClock(start=1_700_000_000)
    slashing_manager = SlashingManager()
    slashing_manager.add_validator_stake(ValidatorStake("0xTarget", 10000))
    manager = FraudProofManager(slashing_manager, time_provider=clock.now)
    return manager, clock


def test_fraud_proof_verification_and_slashing(fraud_manager):
    manager, clock = fraud_manager
    proof_id = manager.submit_fraud_proof(
        challenger_address="0xChallenger",
        challenged_validator_address="0xTarget",
        proof_data={"type": "invalid_state_transition"},
        block_number=50,
        challenge_period_duration_seconds=60,
    )

    assert manager.verify_fraud_proof(proof_id) is True
    stake = manager.slashing_manager.get_validator_stake("0xTarget")
    assert stake.staked_amount < 10000


def test_fraud_proof_expiration(fraud_manager):
    manager, clock = fraud_manager
    proof_id = manager.submit_fraud_proof(
        challenger_address="0xChallenger",
        challenged_validator_address="0xTarget",
        proof_data={"type": "invalid_state_transition"},
        block_number=75,
        challenge_period_duration_seconds=10,
    )

    clock.advance(20)
    assert manager.verify_fraud_proof(proof_id) is False
    proof = manager.get_proof(proof_id)
    assert proof.status == "expired"


def test_fraud_proof_invalid_data_rejected(fraud_manager):
    manager, _ = fraud_manager
    proof_id = manager.submit_fraud_proof(
        challenger_address="0xChallenger",
        challenged_validator_address="0xTarget",
        proof_data={"type": "minor_issue"},
        block_number=90,
        challenge_period_duration_seconds=30,
    )

    assert manager.verify_fraud_proof(proof_id) is False
    proof = manager.get_proof(proof_id)
    assert proof.status == "rejected"


def test_fraud_proof_missing_entry(fraud_manager):
    manager, _ = fraud_manager
    assert manager.verify_fraud_proof("unknown_proof_id") is False
