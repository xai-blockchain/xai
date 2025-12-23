"""
Bitcoin regtest HTLC smoke test.

Prerequisites:
- bitcoind running in regtest mode with RPC enabled (user/pass).
- Wallets unlocked for funding and spending.

Flow:
1. Build P2WSH HTLC redeem script/address.
2. Fund HTLC output.
3. Mine 1 block for confirmation.
4. Spend via claim path using secret.
5. Mine to confirm claim.

Note: This uses RPC signing/creation for simplicity; production should use PSBT with hardware wallets.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from decimal import Decimal

import requests
from ecdsa import SECP256k1, SigningKey, util as ecdsa_util

from xai.core.htlc_p2wsh import build_utxo_contract

RPC_URL = "http://127.0.0.1:18443"
RPC_USER = "user"
RPC_PASS = "pass"
RPC_WALLET = "regtest_htlc"

def rpc(method: str, params=None):
    resp = requests.post(
        f"{RPC_URL}/wallet/{RPC_WALLET}",
        auth=(RPC_USER, RPC_PASS),
        json={"jsonrpc": "1.0", "id": "htlc", "method": method, "params": params or []},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data["result"]

def _encode_varint(value: int) -> bytes:
    if value < 0xFD:
        return value.to_bytes(1, "little")
    if value <= 0xFFFF:
        return b"\xFD" + value.to_bytes(2, "little")
    if value <= 0xFFFFFFFF:
        return b"\xFE" + value.to_bytes(4, "little")
    return b"\xFF" + value.to_bytes(8, "little")

def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    prefix = data[offset]
    if prefix < 0xFD:
        return prefix, offset + 1
    if prefix == 0xFD:
        return int.from_bytes(data[offset + 1 : offset + 3], "little"), offset + 3
    if prefix == 0xFE:
        return int.from_bytes(data[offset + 1 : offset + 5], "little"), offset + 5
    return int.from_bytes(data[offset + 1 : offset + 9], "little"), offset + 9

def _parse_transaction(raw_hex: str):
    """
    Minimal transaction parser that tolerates unsigned (no witness) and signed SegWit tx.
    Keeps all byte slices so outputs/inputs remain untouched.
    """
    tx = bytes.fromhex(raw_hex)
    cursor = 0
    version = tx[cursor : cursor + 4]
    cursor += 4
    marker = tx[cursor] if len(tx) > cursor else None
    flag = tx[cursor + 1] if len(tx) > cursor + 1 else None
    has_witness = marker == 0 and flag == 1
    marker_flag = tx[cursor : cursor + 2] if has_witness else None
    if has_witness:
        cursor += 2
    vin_count, cursor = _read_varint(tx, cursor)
    inputs = []
    for _ in range(vin_count):
        prev_txid = tx[cursor : cursor + 32]
        cursor += 32
        vout = tx[cursor : cursor + 4]
        cursor += 4
        script_len, cursor = _read_varint(tx, cursor)
        script_sig = tx[cursor : cursor + script_len]
        cursor += script_len
        sequence = tx[cursor : cursor + 4]
        cursor += 4
        inputs.append({"prev_txid": prev_txid, "vout": vout, "script_sig": script_sig, "sequence": sequence})
    vout_count, cursor = _read_varint(tx, cursor)
    outputs = []
    for _ in range(vout_count):
        amount = tx[cursor : cursor + 8]
        cursor += 8
        pk_len, cursor = _read_varint(tx, cursor)
        script_pubkey = tx[cursor : cursor + pk_len]
        cursor += pk_len
        outputs.append({"amount": amount, "script_pubkey": script_pubkey})
    witness_stacks: list[list[bytes]] = [[] for _ in range(vin_count)]
    if has_witness:
        for idx in range(vin_count):
            item_count, cursor = _read_varint(tx, cursor)
            stack = []
            for _ in range(item_count):
                item_len, cursor = _read_varint(tx, cursor)
                item = tx[cursor : cursor + item_len]
                cursor += item_len
                stack.append(item)
            witness_stacks[idx] = stack
    locktime = tx[cursor : cursor + 4]
    return version, marker_flag, inputs, outputs, witness_stacks, locktime

def _double_sha256(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def _bip143_sighash(
    version: bytes,
    inputs,
    outputs,
    locktime: bytes,
    input_index: int,
    script_code: bytes,
    amount_sats: int,
    sighash_type: int = 1,
) -> bytes:
    hash_prevouts = _double_sha256(b"".join([vin["prev_txid"] + vin["vout"] for vin in inputs]))
    hash_sequence = _double_sha256(b"".join([vin["sequence"] for vin in inputs]))
    hash_outputs = _double_sha256(
        b"".join(
            [
                vout["amount"]
                + _encode_varint(len(vout["script_pubkey"]))
                + vout["script_pubkey"]
                for vout in outputs
            ]
        )
    )
    script_prefixed = _encode_varint(len(script_code)) + script_code
    data = (
        version
        + hash_prevouts
        + hash_sequence
        + inputs[input_index]["prev_txid"]
        + inputs[input_index]["vout"]
        + script_prefixed
        + amount_sats.to_bytes(8, "little")
        + inputs[input_index]["sequence"]
        + hash_outputs
        + locktime
        + sighash_type.to_bytes(4, "little")
    )
    return _double_sha256(data)

def _serialize_transaction(version, marker_flag, inputs, outputs, witness_stacks, locktime) -> str:
    marker_flag = marker_flag or b"\x00\x01"
    parts = [version, marker_flag, _encode_varint(len(inputs))]
    for vin in inputs:
        parts.extend(
            [
                vin["prev_txid"],
                vin["vout"],
                _encode_varint(len(vin["script_sig"])),
                vin["script_sig"],
                vin["sequence"],
            ]
        )
    parts.append(_encode_varint(len(outputs)))
    for vout in outputs:
        parts.extend(
            [
                vout["amount"],
                _encode_varint(len(vout["script_pubkey"])),
                vout["script_pubkey"],
            ]
        )
    for stack in witness_stacks:
        parts.append(_encode_varint(len(stack)))
        for item in stack:
            parts.extend([_encode_varint(len(item)), item])
    parts.append(locktime)
    return b"".join(parts).hex()

def main() -> int:
    # Ensure wallet exists (descriptor wallet)
    requests.post(
        RPC_URL,
        auth=(RPC_USER, RPC_PASS),
        json={
            "jsonrpc": "1.0",
            "id": "create",
            "method": "createwallet",
            # disable_private_keys=False, blank=False, passphrase="", avoid_reuse=False, descriptors=True, load_on_startup=False, external_signer=False
            "params": [RPC_WALLET, False, False, "", False, True, False],
        },
        timeout=5,
    )
    # Fund wallet if empty
    bal = rpc("getbalance")
    if bal < 1:
        fund_addr = rpc("getnewaddress")
        rpc("generatetoaddress", [101, fund_addr])
    # Generate recipient key locally for deterministic signing; sender key comes from wallet (refund path).
    sender_addr = rpc("getnewaddress")
    sender_info = rpc("getaddressinfo", [sender_addr])
    recipient_priv = SigningKey.generate(curve=SECP256k1)
    recipient_pubkey_bytes = recipient_priv.get_verifying_key().to_string("compressed")
    recipient_pubkey_hex = recipient_pubkey_bytes.hex()

    secret_preimage = secrets.token_bytes(32)
    secret_hash_hex = hashlib.sha256(secret_preimage).hexdigest()
    timelock = int(time.time()) + 600

    contract = build_utxo_contract(
        secret_hash_hex=secret_hash_hex,
        timelock=timelock,
        recipient_pubkey=recipient_pubkey_hex,
        sender_pubkey=sender_info["pubkey"],
        hrp="bcrt",
    )
    print("P2WSH address:", contract["p2wsh_address"])

    # Fund HTLC
    txid = rpc("sendtoaddress", [contract["p2wsh_address"], 0.5])
    rpc("generatetoaddress", [1, sender_addr])  # mine 1 block to confirm
    print("Funded txid:", txid)

    # Decode tx to find vout
    decoded = rpc("getrawtransaction", [txid, True])
    vout = None
    amount = 0
    for out in decoded["vout"]:
        if out.get("scriptPubKey", {}).get("hex") == contract["script_pubkey"]:
            vout = out["n"]
            amount = out["value"]
            script_pub = out["scriptPubKey"]["hex"]
            break
    if vout is None:
        raise RuntimeError("HTLC output not found")

    raw = rpc(
        "createrawtransaction",
        [
            [{"txid": txid, "vout": vout, "sequence": 0}],
            {sender_addr: amount - 0.0001},
            0,
            True,
        ],
    )

    version, marker_flag, inputs, outputs, _witness_stacks, locktime = _parse_transaction(raw)
    redeem_script_bytes = bytes.fromhex(contract["redeem_script_hex"])
    amount_sats = int(Decimal(str(amount)) * 100_000_000)
    sighash = _bip143_sighash(
        version,
        inputs,
        outputs,
        locktime,
        0,
        redeem_script_bytes,
        amount_sats,
        sighash_type=1,
    )
    signer = recipient_priv
    signature = signer.sign_digest(sighash, sigencode=ecdsa_util.sigencode_der_canonize) + b"\x01"

    witness_stacks = [[] for _ in inputs]
    witness_stacks[0] = [signature, secret_preimage, b"\x01", redeem_script_bytes]
    final_tx = _serialize_transaction(version, marker_flag, inputs, outputs, witness_stacks, locktime)

    txid_claim = rpc("sendrawtransaction", [final_tx])
    rpc("generatetoaddress", [1, sender_addr])
    print("Claimed txid:", txid_claim)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
