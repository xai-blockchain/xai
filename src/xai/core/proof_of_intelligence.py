import hashlib
import random
import time


class ProofOfIntelligence:
    def __init__(self, difficulty=4):
        self.difficulty = difficulty

    def generate_ai_task(self, difficulty):
        """
        Generates a mock AI task. In a real implementation, this would be a complex problem.
        """
        return {
            "task_id": random.randint(1000, 9999),
            "difficulty": difficulty,
            "description": "Solve a complex AI problem.",
        }

    def simulate_ai_computation(self, task, miner_address):
        """
        Simulates the process of solving the AI task.
        """
        print(f"Miner {miner_address} is attempting to solve AI task {task['task_id']}...")
        start_time = time.time()

        # In a real scenario, this would involve intensive AI computation.
        # Here, we simulate it with a proof-of-work-like challenge.
        nonce = 0
        while True:
            hasher = hashlib.sha256()
            hasher.update(str(task["task_id"]).encode())
            hasher.update(str(miner_address).encode())
            hasher.update(str(nonce).encode())
            hex_hash = hasher.hexdigest()
            if hex_hash.startswith("0" * self.difficulty):
                end_time = time.time()
                print(
                    f"Miner {miner_address} found a valid proof in {end_time - start_time:.2f} seconds."
                )
                return {
                    "task_id": task["task_id"],
                    "nonce": nonce,
                    "hash": hex_hash,
                    "miner": miner_address,
                }
            nonce += 1

    def validate_proof(self, proof, task):
        """
        Validates the proof provided by a miner.
        """
        hasher = hashlib.sha256()
        hasher.update(str(task["task_id"]).encode())
        hasher.update(str(proof["miner"]).encode())
        hasher.update(str(proof["nonce"]).encode())
        hex_hash = hasher.hexdigest()

        return hex_hash == proof["hash"] and hex_hash.startswith("0" * self.difficulty)
