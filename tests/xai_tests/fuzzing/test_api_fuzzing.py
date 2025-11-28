"""
Fuzz testing for API schemas.
"""

from faker import Faker
import requests

FAKER = Faker()
BASE_URL = "http://localhost:18545"

def test_fuzz_contract_endpoints():
    """
    Fuzz the smart contract endpoints with random data.
    """
    endpoints = [
        "/contracts/deploy",
        "/contracts/call",
        "/contracts/governance/feature",
    ]
    for _ in range(100):
        endpoint = FAKER.random_element(elements=endpoints)
        payload = {
            "sender": FAKER.sha256(),
            "bytecode": FAKER.hexify(text="^" * 64),
            "gas_limit": FAKER.random_int(min=1, max=100000),
            "value": FAKER.random_number(digits=5),
            "fee": FAKER.random_number(digits=2),
            "public_key": FAKER.sha256(),
            "nonce": FAKER.random_int(),
            "signature": FAKER.sha256(),
            "contract_address": FAKER.sha256(),
            "payload": {"key": FAKER.word(), "value": FAKER.word()},
            "data": FAKER.hexify(text="^" * 64),
            "enabled": FAKER.boolean(),
            "reason": FAKER.sentence(),
        }
        try:
            requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=5)
        except requests.RequestException:
            pass  # Ignore network errors, as the node may not be running

