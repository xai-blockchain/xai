# XAI SDK for Kotlin/Android

Official Kotlin SDK for the XAI blockchain. Designed for Android and JVM applications.

## Installation

### Gradle (Kotlin DSL)

```kotlin
dependencies {
    implementation("com.xai:xai-sdk:1.0.0")
}
```

### Gradle (Groovy)

```groovy
implementation 'com.xai:xai-sdk:1.0.0'
```

## Quick Start

```kotlin
import com.xai.sdk.XAIClient

// Create client
val client = XAIClient(
    baseUrl = "http://localhost:12001",
    apiKey = "your-api-key" // optional
)

// Use coroutines
suspend fun example() {
    // Get wallet balance
    val balance = client.wallet.getBalance("0x1234...")
    println("Balance: ${balance.balance}")

    // Get latest block
    val block = client.blocks.getLatestBlock()
    println("Block #${block.number}: ${block.hash}")

    // Get transaction
    val tx = client.transactions.getTransaction("0xabc...")
    println("Status: ${tx.status}")
}

// Always close when done
client.close()
```

## Client Configuration

```kotlin
// Default (localhost:12001)
val client = XAIClient()

// Custom URL
val client = XAIClient(baseUrl = "https://api.xai.io")

// With API key
val client = XAIClient(
    baseUrl = "https://api.xai.io",
    apiKey = "your-key"
)

// Full configuration
val client = XAIClient(XAIClientConfig(
    baseUrl = "https://api.xai.io",
    apiKey = "your-key",
    timeout = 60,
    maxRetries = 5,
    retryDelay = 1000,
    enableLogging = true
))

// Convenience constructors
val local = XAIClient.local()
val testnet = XAIClient.testnet()
val mainnet = XAIClient.mainnet("your-api-key")
```

## API Reference

### BlocksClient

```kotlin
// Get block by hash
val block = client.blocks.getBlock("0x...")

// Get block by number
val block = client.blocks.getBlockByNumber(1000)

// List blocks (paginated)
val blocks = client.blocks.getBlocks(page = 1, limit = 20)

// Get latest block
val latest = client.blocks.getLatestBlock()

// Get block transactions
val txs = client.blocks.getBlockTransactions("0x...")
```

### TransactionsClient

```kotlin
// Get transaction
val tx = client.transactions.getTransaction("0x...")

// Send signed transaction
val result = client.transactions.sendTransaction(SignedTransaction(
    from = "0x...",
    to = "0x...",
    amount = "1000",
    signature = "0x...",
    nonce = 5
))

// Get address transactions
val txs = client.transactions.getTransactions("0x...")

// Get status
val status = client.transactions.getStatus("0x...")

// Estimate fee
val fee = client.transactions.estimateFee(
    from = "0x...",
    to = "0x...",
    amount = "1000"
)

// Check confirmation
val confirmed = client.transactions.isConfirmed("0x...", requiredConfirmations = 6)

// Wait for confirmation
val confirmedTx = client.transactions.waitForConfirmation(
    txid = "0x...",
    confirmations = 3,
    timeoutSeconds = 120
)
```

### WalletClient

```kotlin
// Get balance
val balance = client.wallet.getBalance("0x...")

// Get UTXOs
val utxos = client.wallet.getUTXOs("0x...", minConfirmations = 6)

// Get address info
val address = client.wallet.getAddress("0x...")

// Create unsigned transaction
val unsignedTx = client.wallet.createTransaction(
    from = "0x...",
    to = "0x...",
    amount = "1000"
)

// Get nonce
val nonce = client.wallet.getNonce("0x...")

// Validate address
val valid = client.wallet.validateAddress("0x...")

// Get balances for multiple addresses
val balances = client.wallet.getMultiBalance(listOf("0x1...", "0x2..."))
```

### AIClient

```kotlin
// Submit AI task
val task = client.ai.submitTask(AITaskRequest(
    type = "text_generation",
    prompt = "Analyze this transaction...",
    providerId = "openai",
    model = "gpt-4",
    maxTokens = 2000
))

// Get task status
val taskStatus = client.ai.getTask(task.id)

// Wait for completion
val result = client.ai.waitForCompletion(task.id, timeoutSeconds = 120)

// List providers
val providers = client.ai.listProviders()

// Analyze wallet
val analysis = client.ai.analyzeWallet("0x...")

// Analyze blockchain
val blockchainAnalysis = client.ai.analyzeBlockchain(
    query = "What are the trends?",
    context = mapOf("timeframe" to "24h")
)
```

### StakingClient

```kotlin
// Get staking info
val info = client.staking.getStakingInfo("0x...")

// List validators
val validators = client.staking.listValidators()

// Get validator
val validator = client.staking.getValidator("0x...")

// Stake tokens
val result = client.staking.stake(
    from = "0x...",
    amount = "1000",
    validatorAddress = "0x...",
    signature = "0x..."
)

// Unstake
val unstakeResult = client.staking.unstake(
    from = "0x...",
    amount = "500",
    signature = "0x..."
)

// Claim rewards
val claimResult = client.staking.claimRewards(
    from = "0x...",
    signature = "0x..."
)

// Get APY
val apy = client.staking.getAPY()
```

### General Methods

```kotlin
// Health check
val health = client.healthCheck()

// Node info
val info = client.getNodeInfo()

// Sync status
val syncStatus = client.getSyncStatus()

// Check if synced
val synced = client.isSynced()

// Get stats
val stats = client.getStats()

// Mempool info
val mempool = client.getMempoolInfo()

// Gas price
val gasPrice = client.getGasPrice()

// Block height
val height = client.getBlockHeight()
```

## Error Handling

```kotlin
import com.xai.sdk.utils.*

try {
    val balance = client.wallet.getBalance("0x...")
} catch (e: ValidationException) {
    println("Invalid input: ${e.message}, field: ${e.field}")
} catch (e: AuthenticationException) {
    println("Auth failed: ${e.message}")
} catch (e: NotFoundException) {
    println("Not found: ${e.resource}")
} catch (e: RateLimitException) {
    println("Rate limited, retry after: ${e.retryAfter}ms")
} catch (e: NetworkException) {
    println("Network error: ${e.message}")
} catch (e: APIException) {
    println("API error ${e.statusCode}: ${e.message}")
} catch (e: XAIException) {
    println("SDK error: ${e.message}")
}
```

## Android Usage

```kotlin
class MainActivity : AppCompatActivity() {
    private lateinit var client: XAIClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        client = XAIClient.mainnet(BuildConfig.XAI_API_KEY)
    }

    override fun onDestroy() {
        super.onDestroy()
        client.close()
    }

    private fun loadBalance(address: String) {
        lifecycleScope.launch {
            try {
                val balance = withContext(Dispatchers.IO) {
                    client.wallet.getBalance(address)
                }
                updateUI(balance)
            } catch (e: XAIException) {
                showError(e.message)
            }
        }
    }
}
```

## License

MIT License
