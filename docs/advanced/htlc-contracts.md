# HTLC Contract Artifacts (BTC P2WSH + Ethereum)

This note captures reference artifacts for deploying XAI atomic swap HTLCs.

## Bitcoin / UTXO (P2WSH)

Redeem script template:
```
OP_IF
    OP_SHA256 <secret_hash> OP_EQUALVERIFY
    <recipient_pubkey> OP_CHECKSIG
OP_ELSE
    <timelock> OP_CHECKLOCKTIMEVERIFY OP_DROP
    <sender_pubkey> OP_CHECKSIG
OP_ENDIF
```
- Address type: P2WSH (v0). Script hash = `SHA256(redeemScript)`.
- Funding address: `bc1q...` derived from witness script hash.
- Claim path: provide `secret preimage`, recipient signature, and `OP_TRUE`.
- Refund path: after `timelock`, provide sender signature and `OP_FALSE`.

## Ethereum

Reference Solidity (0.8.x) contract:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AtomicSwapETH {
    bytes32 public immutable secretHash;
    address public immutable recipient;
    address public immutable sender;
    uint256 public immutable timelock;

    constructor(bytes32 _secretHash, address _recipient, uint256 _timelock) payable {
        secretHash = _secretHash;
        recipient = _recipient;
        sender = msg.sender;
        timelock = _timelock;
    }

    function claim(bytes32 secret) external {
        require(sha256(abi.encodePacked(secret)) == secretHash, "Invalid secret");
        require(msg.sender == recipient, "Not recipient");
        (bool ok, ) = recipient.call{value: address(this).balance}("");
        require(ok, "Transfer failed");
    }

    function refund() external {
        require(block.timestamp >= timelock, "Timelock not expired");
        require(msg.sender == sender, "Not sender");
        (bool ok, ) = sender.call{value: address(this).balance}("");
        require(ok, "Refund failed");
    }
}
```
- Gas estimate: ~150k for claim, ~50k for refund.
- For ERC-20, wrap with token address and `transferFrom/transfer` in place of value transfers.

## Next Steps
- Produce compiled artifacts (ABI/bytecode) and add deploy scripts for ETH + testnets.
- Add a P2WSH address derivation helper around the redeem script and a broadcast script for claim/refund.
- Wire deployment hooks into the swap orchestrator and add integration tests exercising funding/claim/refund on regtest/Hardhat.
