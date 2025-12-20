---
sidebar_position: 3
---

# Python SDK

The XAI Python SDK provides a complete interface for interacting with the XAI blockchain.

## Installation

```bash
pip install xai-blockchain
```

## Quick Start

```python
from xai.sdk import XAIClient

# Connect to a node
client = XAIClient("http://localhost:12001")

# Get blockchain info
info = client.get_blockchain_info()
print(f"Height: {info['height']}")

# Check balance
balance = client.get_balance("TXAI_ADDRESS")
print(f"Balance: {balance} XAI")

# Send transaction
tx = client.send_transaction(
    sender="TXAI_FROM",
    recipient="TXAI_TO",
    amount=10.0,
    private_key="YOUR_PRIVATE_KEY"
)
print(f"Transaction: {tx['txid']}")
```

## API Reference

### Client

```python
class XAIClient:
    def __init__(self, node_url: str):
        """Initialize client with node URL"""
    
    def get_blockchain_info(self) -> dict:
        """Get blockchain information"""
    
    def get_balance(self, address: str) -> float:
        """Get address balance"""
    
    def send_transaction(self, sender: str, recipient: str, 
                        amount: float, private_key: str) -> dict:
        """Send a transaction"""
    
    def get_block(self, height: int) -> dict:
        """Get block by height"""
    
    def get_transaction(self, txid: str) -> dict:
        """Get transaction by ID"""
```

### Wallet

```python
from xai.sdk import Wallet

# Create new wallet
wallet = Wallet.generate()
print(f"Address: {wallet.address}")

# Load existing wallet
wallet = Wallet.from_private_key("YOUR_PRIVATE_KEY")

# Sign transaction
signature = wallet.sign(transaction_hash)
```

### Smart Contracts

```python
from xai.sdk import Contract

# Deploy contract
contract = Contract.deploy(
    bytecode="0x...",
    constructor_args=[],
    sender=wallet
)

# Call contract method
result = contract.call("transfer", ["TXAI_RECIPIENT", 100])
```

## Resources

- [Developer Overview](overview)
- [AI Trading](ai-trading)
- [REST API](../api/rest-api)
