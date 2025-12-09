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

import secrets
import time
import json

import requests

from xai.core.htlc_p2wsh import build_utxo_contract, build_claim_witness


RPC_URL = "http://127.0.0.1:18443"
RPC_USER = "user"
RPC_PASS = "pass"
RPC_WALLET = "regtest"


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


def main() -> int:
    # Ensure wallet exists
    try:
        requests.post(
            f"{RPC_URL}/wallet/{RPC_WALLET}",
            auth=(RPC_USER, RPC_PASS),
            json={"jsonrpc": "1.0", "id": "load", "method": "loadwallet", "params": [RPC_WALLET]},
            timeout=5,
        )
    except Exception:
        pass
    # Create wallet if missing
    requests.post(
        RPC_URL,
        auth=(RPC_USER, RPC_PASS),
        json={"jsonrpc": "1.0", "id": "create", "method": "createwallet", "params": [RPC_WALLET]},
        timeout=5,
    )
    # Fund wallet if empty
    bal = rpc("getbalance")
    if bal < 1:
        fund_addr = rpc("getnewaddress")
        rpc("generatetoaddress", [101, fund_addr])
    # Generate recipient/sender keys
    sender_addr = rpc("getnewaddress")
    recipient_addr = rpc("getnewaddress")
    sender_info = rpc("getaddressinfo", [sender_addr])
    recipient_info = rpc("getaddressinfo", [recipient_addr])

    secret = secrets.token_bytes(32).hex()
    timelock = int(time.time()) + 600

    contract = build_utxo_contract(
        secret_hash_hex=secret,
        timelock=timelock,
        recipient_pubkey=recipient_info["pubkey"],
        sender_pubkey=sender_info["pubkey"],
    )
    print("P2WSH address:", contract["p2wsh_address"])

    # Fund HTLC
    txid = rpc("sendtoaddress", [contract["p2wsh_address"], 0.5])
    rpc("generatetoaddress", [1, sender_addr])  # mine 1 block to confirm
    print("Funded txid:", txid)

    # Build spending transaction
    utxos = rpc("listunspent", [1, 9999999, [contract["p2wsh_address"]]])
    if not utxos:
        raise RuntimeError("No UTXO found for HTLC")
    utxo = utxos[0]

    raw = rpc(
        "createrawtransaction",
        [
            [{"txid": utxo["txid"], "vout": utxo["vout"], "sequence": 0}],
            {recipient_addr: utxo["amount"] - 0.0001},
        ],
        0,
        True,
    )

    signed = rpc(
        "signrawtransactionwithwallet",
        [
            raw,
            [
                {
                    "txid": utxo["txid"],
                    "vout": utxo["vout"],
                    "redeemScript": contract["redeem_script_hex"],
                    "witnessScript": contract["redeem_script_hex"],
                    "scriptPubKey": utxo["scriptPubKey"],
                    "amount": utxo["amount"],
                }
            ],
        ],
    )
    final_tx = signed["hex"]

    txid_claim = rpc("sendrawtransaction", [final_tx])
    rpc("generatetoaddress", [1, sender_addr])
    print("Claimed txid:", txid_claim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
