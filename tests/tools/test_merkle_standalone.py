#!/usr/bin/env python3
"""
Standalone test for Merkle Proof functionality.
Tests the core algorithm without requiring full blockchain dependencies.
"""

import hashlib
from typing import List, Tuple


def calculate_merkle_root(tx_hashes: List[str]) -> str:
    """Calculate merkle root from transaction hashes"""
    if not tx_hashes:
        return hashlib.sha256(b"").hexdigest()

    hashes = tx_hashes.copy()

    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])

        new_hashes = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            new_hash = hashlib.sha256(combined.encode()).hexdigest()
            new_hashes.append(new_hash)

        hashes = new_hashes

    return hashes[0]


def generate_merkle_proof(tx_hashes: List[str], txid: str) -> List[Tuple[str, bool]]:
    """Generate a merkle proof for a transaction"""
    if not tx_hashes:
        raise ValueError("No transactions")

    try:
        tx_index = tx_hashes.index(txid)
    except ValueError:
        raise ValueError(f"Transaction {txid} not found")

    proof: List[Tuple[str, bool]] = []
    current_index = tx_index
    current_level = tx_hashes.copy()

    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        if current_index % 2 == 0:
            sibling_index = current_index + 1
            is_right = True
        else:
            sibling_index = current_index - 1
            is_right = False

        sibling_hash = current_level[sibling_index]
        proof.append((sibling_hash, is_right))

        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            parent_hash = hashlib.sha256(combined.encode()).hexdigest()
            next_level.append(parent_hash)

        current_level = next_level
        current_index = current_index // 2

    return proof


def verify_merkle_proof(txid: str, merkle_proof: List[Tuple[str, bool]], merkle_root: str) -> bool:
    """Verify a transaction is in a block using a merkle proof"""
    if not merkle_proof and txid == merkle_root:
        return True

    if not merkle_proof:
        return False

    current_hash = txid

    for sibling_hash, is_right in merkle_proof:
        if is_right:
            combined = current_hash + sibling_hash
        else:
            combined = sibling_hash + current_hash

        current_hash = hashlib.sha256(combined.encode()).hexdigest()

    return current_hash == merkle_root


def test_merkle_proof():
    """Test merkle proof functionality"""
    print("=" * 70)
    print("MERKLE PROOF VERIFICATION - STANDALONE TEST")
    print("=" * 70)

    # Test 1: Single transaction
    print("\n[TEST 1] Single transaction...")
    tx_hashes = ["abc123"]
    merkle_root = calculate_merkle_root(tx_hashes)
    proof = generate_merkle_proof(tx_hashes, "abc123")

    assert proof == []
    assert verify_merkle_proof("abc123", proof, merkle_root)
    print("✓ Single transaction: PASS")

    # Test 2: Two transactions
    print("\n[TEST 2] Two transactions...")
    tx_hashes = ["tx1hash", "tx2hash"]
    merkle_root = calculate_merkle_root(tx_hashes)

    proof1 = generate_merkle_proof(tx_hashes, "tx1hash")
    assert len(proof1) == 1
    assert proof1[0][0] == "tx2hash"
    assert proof1[0][1] == True  # Right sibling
    assert verify_merkle_proof("tx1hash", proof1, merkle_root)

    proof2 = generate_merkle_proof(tx_hashes, "tx2hash")
    assert len(proof2) == 1
    assert proof2[0][0] == "tx1hash"
    assert proof2[0][1] == False  # Left sibling
    assert verify_merkle_proof("tx2hash", proof2, merkle_root)
    print("✓ Two transactions: PASS")

    # Test 3: Four transactions (perfect tree)
    print("\n[TEST 3] Four transactions...")
    tx_hashes = [f"tx{i}hash" for i in range(4)]
    merkle_root = calculate_merkle_root(tx_hashes)

    for i, txid in enumerate(tx_hashes):
        proof = generate_merkle_proof(tx_hashes, txid)
        assert len(proof) == 2  # Tree depth is 2
        assert verify_merkle_proof(txid, proof, merkle_root)

    print("✓ Four transactions: PASS")

    # Test 4: Odd number of transactions
    print("\n[TEST 4] Five transactions (odd number)...")
    tx_hashes = [f"tx{i}hash" for i in range(5)]
    merkle_root = calculate_merkle_root(tx_hashes)

    for txid in tx_hashes:
        proof = generate_merkle_proof(tx_hashes, txid)
        assert verify_merkle_proof(txid, proof, merkle_root)

    print("✓ Five transactions: PASS")

    # Test 5: Large number of transactions
    print("\n[TEST 5] 100 transactions...")
    tx_hashes = [f"tx{i:03d}hash" for i in range(100)]
    merkle_root = calculate_merkle_root(tx_hashes)

    # Test a few
    for i in [0, 25, 50, 75, 99]:
        txid = tx_hashes[i]
        proof = generate_merkle_proof(tx_hashes, txid)
        assert len(proof) <= 7  # log2(100) ≈ 6.6
        assert verify_merkle_proof(txid, proof, merkle_root)

    print(f"✓ 100 transactions: PASS (proof size: {len(proof)} elements)")

    # Test 6: Tampered proof detection
    print("\n[TEST 6] Tampered proof detection...")
    tx_hashes = [f"tx{i}hash" for i in range(10)]
    merkle_root = calculate_merkle_root(tx_hashes)

    proof = generate_merkle_proof(tx_hashes, tx_hashes[5])
    tampered_proof = [(proof[0][0] + "XXX", proof[0][1])] + proof[1:]

    assert not verify_merkle_proof(tx_hashes[5], tampered_proof, merkle_root)
    print("✓ Tampered proof rejected: PASS")

    # Test 7: Wrong merkle root
    print("\n[TEST 7] Wrong merkle root detection...")
    proof = generate_merkle_proof(tx_hashes, tx_hashes[0])
    wrong_root = "0" * 64

    assert not verify_merkle_proof(tx_hashes[0], proof, wrong_root)
    print("✓ Wrong merkle root rejected: PASS")

    # Test 8: Proof size is logarithmic
    print("\n[TEST 8] Proof size is logarithmic...")
    import math

    for num_txs in [1, 2, 4, 8, 16, 32, 64, 128]:
        tx_hashes = [f"tx{i:03d}" for i in range(num_txs)]
        merkle_root = calculate_merkle_root(tx_hashes)
        proof = generate_merkle_proof(tx_hashes, tx_hashes[0])

        expected_max = math.ceil(math.log2(num_txs)) if num_txs > 1 else 0
        actual = len(proof)

        print(f"  {num_txs:3d} txs: proof size = {actual}, max expected = {expected_max}")
        assert actual <= expected_max

    print("✓ Logarithmic proof size: PASS")

    # Test 9: Light client simulation
    print("\n[TEST 9] Light client simulation...")
    # Full node has 1000 transactions
    tx_hashes = [f"tx{i:04d}" for i in range(1000)]
    merkle_root = calculate_merkle_root(tx_hashes)

    # Light client wants to verify tx #500
    target_tx = tx_hashes[500]

    # Full node generates proof
    proof = generate_merkle_proof(tx_hashes, target_tx)

    # Light client only needs: target_tx, proof (10 hashes), and merkle_root
    # They do NOT need all 1000 transactions!
    light_client_verified = verify_merkle_proof(target_tx, proof, merkle_root)

    assert light_client_verified
    print(f"✓ Light client verified with {len(proof)} hashes instead of 1000 transactions: PASS")

    print("\n" + "=" * 70)
    print("✅ ALL MERKLE PROOF TESTS PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    import sys
    try:
        test_merkle_proof()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
