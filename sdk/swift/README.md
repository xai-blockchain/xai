# XAI Swift SDK

Native iOS/macOS SDK for the XAI blockchain.

## Installation

### Swift Package Manager

Add to your `Package.swift`:

```swift
dependencies: [
    .package(url: "https://github.com/xai-blockchain/xai-swift-sdk", from: "1.0.0")
]
```

Or in Xcode: File > Add Package Dependencies > Enter repository URL.

## Quick Start

```swift
import XAI

// Initialize client
let client = XAIClient(baseURL: "http://localhost:12001", apiKey: "your-api-key")

// Get wallet balance
let balance = try await client.wallet.getBalance(address: "XAI1...")
print("Balance: \(balance.balance)")

// Get latest block
let block = try await client.blocks.getLatestBlock()
print("Block #\(block.number): \(block.hash)")

// Send transaction
let params = SendTransactionParams(from: "XAI1...", to: "XAI2...", amount: "1000")
let result = try await client.transactions.sendTransaction(params)
print("TX: \(result.hash)")
```

## Features

### Blocks
```swift
let block = try await client.blocks.getBlock(hash: "0x...")
let block = try await client.blocks.getBlock(number: 12345)
let blocks = try await client.blocks.getBlocks(page: 1, limit: 20)
let latest = try await client.blocks.getLatestBlock()
```

### Transactions
```swift
let tx = try await client.transactions.getTransaction(txid: "0x...")
let result = try await client.transactions.sendTransaction(params)
let history = try await client.transactions.getTransactions(address: "XAI1...")
let confirmed = try await client.transactions.waitForConfirmation(txid: "0x...", confirmations: 6)
```

### Wallet
```swift
let balance = try await client.wallet.getBalance(address: "XAI1...")
let utxos = try await client.wallet.getUTXOs(address: "XAI1...")
let unsignedTx = try await client.wallet.createTransaction(from: "XAI1...", to: "XAI2...", amount: "1000")
let wallet = try await client.wallet.createWallet()
```

### AI
```swift
let task = try await client.ai.submitTask(AITaskRequest(type: .analysis, prompt: "Analyze patterns"))
let result = try await client.ai.waitForCompletion(taskId: task.id)
let providers = try await client.ai.listProviders()
let analysis = try await client.ai.analyzeWallet(address: "XAI1...")
```

### Staking
```swift
let result = try await client.staking.stake(address: "XAI1...", validatorAddress: "VAL1...", amount: "1000")
let positions = try await client.staking.getPositions(address: "XAI1...")
let rewards = try await client.staking.getRewards(address: "XAI1...")
let validators = try await client.staking.listValidators(activeOnly: true)
```

## Error Handling

```swift
do {
    let balance = try await client.wallet.getBalance(address: "XAI1...")
} catch let error as XAIError {
    switch error {
    case .authenticationError(let message):
        print("Auth failed: \(message)")
    case .notFound(let message):
        print("Not found: \(message)")
    case .rateLimitError(let retryAfter):
        print("Rate limited. Retry after \(retryAfter ?? 0)s")
    case .timeout:
        print("Request timed out")
    default:
        print("Error: \(error.localizedDescription)")
    }
}
```

## Requirements

- iOS 15.0+ / macOS 12.0+ / tvOS 15.0+ / watchOS 8.0+
- Swift 5.9+
- Xcode 15.0+

## License

MIT License
