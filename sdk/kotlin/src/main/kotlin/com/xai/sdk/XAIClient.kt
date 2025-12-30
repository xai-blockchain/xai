package com.xai.sdk

import com.xai.sdk.api.AIClient
import com.xai.sdk.api.BlocksClient
import com.xai.sdk.api.StakingClient
import com.xai.sdk.api.TransactionsClient
import com.xai.sdk.api.WalletClient
import com.xai.sdk.models.BlockchainStats
import com.xai.sdk.models.HealthCheckResponse
import com.xai.sdk.models.MempoolInfo
import com.xai.sdk.models.NetworkInfo
import com.xai.sdk.models.SyncStatus
import com.xai.sdk.utils.HttpClient
import com.xai.sdk.utils.HttpClientConfig
import kotlinx.serialization.Serializable
import java.io.Closeable

/**
 * XAI SDK Client Configuration
 *
 * @property baseUrl Base URL for the XAI blockchain API
 * @property apiKey Optional API key for authentication
 * @property timeout Request timeout in seconds
 * @property maxRetries Maximum retry attempts for failed requests
 * @property retryDelay Delay between retries in milliseconds
 * @property enableLogging Enable HTTP request/response logging
 */
data class XAIClientConfig(
    val baseUrl: String = "http://localhost:12001",
    val apiKey: String? = null,
    val timeout: Long = 30,
    val maxRetries: Int = 3,
    val retryDelay: Long = 500,
    val enableLogging: Boolean = false
)

/**
 * Main client for XAI blockchain operations
 *
 * Provides unified interface to wallet, transaction, blockchain,
 * staking, and AI operations.
 *
 * Example:
 * ```kotlin
 * // Create client with default configuration
 * val client = XAIClient()
 *
 * // Create client with custom configuration
 * val client = XAIClient(
 *     baseUrl = "https://api.xai-blockchain.io",
 *     apiKey = "your-api-key"
 * )
 *
 * // Or using config object
 * val client = XAIClient(XAIClientConfig(
 *     baseUrl = "https://api.xai-blockchain.io",
 *     apiKey = "your-api-key",
 *     timeout = 60
 * ))
 *
 * // Use the client
 * val balance = client.wallet.getBalance("0x1234...")
 * val block = client.blocks.getLatestBlock()
 * val tx = client.transactions.getTransaction("0x5678...")
 *
 * // Always close when done
 * client.close()
 * ```
 */
class XAIClient : Closeable {

    private val httpClient: HttpClient

    /**
     * Client for block operations
     *
     * Query blocks, get block details, and list transactions in blocks.
     */
    val blocks: BlocksClient

    /**
     * Client for transaction operations
     *
     * Query transactions, send transactions, and track confirmations.
     */
    val transactions: TransactionsClient

    /**
     * Client for wallet operations
     *
     * Query balances, UTXOs, and create unsigned transactions.
     */
    val wallet: WalletClient

    /**
     * Client for AI operations
     *
     * Submit AI tasks, query providers, and get AI-powered insights.
     */
    val ai: AIClient

    /**
     * Client for staking operations
     *
     * Stake tokens, delegate to validators, and claim rewards.
     */
    val staking: StakingClient

    /**
     * Create XAI Client with default configuration
     */
    constructor() : this(XAIClientConfig())

    /**
     * Create XAI Client with base URL and optional API key
     *
     * @param baseUrl Base URL for the API (default: http://localhost:12001)
     * @param apiKey Optional API key for authentication
     */
    constructor(
        baseUrl: String,
        apiKey: String? = null
    ) : this(XAIClientConfig(baseUrl = baseUrl, apiKey = apiKey))

    /**
     * Create XAI Client with configuration object
     *
     * @param config Client configuration
     */
    constructor(config: XAIClientConfig) {
        httpClient = HttpClient(
            HttpClientConfig(
                baseUrl = config.baseUrl,
                apiKey = config.apiKey,
                timeout = config.timeout,
                maxRetries = config.maxRetries,
                retryDelay = config.retryDelay,
                enableLogging = config.enableLogging
            )
        )

        blocks = BlocksClient(httpClient)
        transactions = TransactionsClient(httpClient)
        wallet = WalletClient(httpClient)
        ai = AIClient(httpClient)
        staking = StakingClient(httpClient)
    }

    /**
     * Check API health status
     *
     * @return Health check response
     *
     * Example:
     * ```kotlin
     * val health = client.healthCheck()
     * if (health.status == "healthy") {
     *     println("API is healthy")
     * }
     * ```
     */
    suspend fun healthCheck(): HealthCheckResponse {
        return httpClient.get("/health")
    }

    /**
     * Get blockchain node information
     *
     * @return Node information including version and endpoints
     *
     * Example:
     * ```kotlin
     * val info = client.getNodeInfo()
     * println("Node version: ${info.version}")
     * println("Chain ID: ${info.chainId}")
     * ```
     */
    suspend fun getNodeInfo(): NetworkInfo {
        @Serializable
        data class NodeInfoResponse(
            val status: String,
            val node: String,
            val version: String,
            val chain_id: String? = null,
            val peer_count: Int = 0,
            val endpoints: List<String> = emptyList()
        )

        val response: NodeInfoResponse = httpClient.get("/")

        return NetworkInfo(
            status = response.status,
            node = response.node,
            version = response.version,
            chainId = response.chain_id,
            peerCount = response.peer_count,
            endpoints = response.endpoints
        )
    }

    /**
     * Get blockchain synchronization status
     *
     * @return Sync status including progress percentage
     *
     * Example:
     * ```kotlin
     * val syncStatus = client.getSyncStatus()
     * if (syncStatus.syncing) {
     *     println("Syncing: ${syncStatus.syncProgress}%")
     * } else {
     *     println("Fully synchronized")
     * }
     * ```
     */
    suspend fun getSyncStatus(): SyncStatus {
        @Serializable
        data class SyncResponse(
            val syncing: Boolean,
            val current_block: Long? = null,
            val highest_block: Long? = null,
            val starting_block: Long? = null
        )

        val response: SyncResponse = httpClient.get("/sync")

        return SyncStatus(
            syncing = response.syncing,
            currentBlock = response.current_block,
            highestBlock = response.highest_block,
            startingBlock = response.starting_block
        )
    }

    /**
     * Get blockchain statistics
     *
     * @return Blockchain statistics including block count and hashrate
     *
     * Example:
     * ```kotlin
     * val stats = client.getStats()
     * println("Total blocks: ${stats.totalBlocks}")
     * println("Network hashrate: ${stats.hashrate}")
     * ```
     */
    suspend fun getStats(): BlockchainStats {
        return httpClient.get("/stats")
    }

    /**
     * Get mempool information
     *
     * @return Mempool statistics
     *
     * Example:
     * ```kotlin
     * val mempool = client.getMempoolInfo()
     * println("Pending transactions: ${mempool.size}")
     * println("Min fee: ${mempool.minFee}")
     * ```
     */
    suspend fun getMempoolInfo(): MempoolInfo {
        return httpClient.get("/mempool")
    }

    /**
     * Check if the node is synchronized
     *
     * @return True if node is fully synchronized
     *
     * Example:
     * ```kotlin
     * if (client.isSynced()) {
     *     // Safe to perform operations
     * }
     * ```
     */
    suspend fun isSynced(): Boolean {
        val status = getSyncStatus()
        return !status.syncing
    }

    /**
     * Get current gas price
     *
     * @return Current gas price as string
     *
     * Example:
     * ```kotlin
     * val gasPrice = client.getGasPrice()
     * println("Current gas price: $gasPrice")
     * ```
     */
    suspend fun getGasPrice(): String {
        @Serializable
        data class GasPriceResponse(val gas_price: String)

        val response: GasPriceResponse = httpClient.get("/gas-price")
        return response.gas_price
    }

    /**
     * Get current block height
     *
     * @return Current block number
     *
     * Example:
     * ```kotlin
     * val height = client.getBlockHeight()
     * println("Current block: $height")
     * ```
     */
    suspend fun getBlockHeight(): Long {
        @Serializable
        data class HeightResponse(val height: Long)

        val response: HeightResponse = httpClient.get("/height")
        return response.height
    }

    /**
     * Close the client and release resources
     *
     * Should be called when the client is no longer needed.
     *
     * Example:
     * ```kotlin
     * val client = XAIClient()
     * try {
     *     // Use client
     * } finally {
     *     client.close()
     * }
     *
     * // Or use with use() block
     * XAIClient().use { client ->
     *     // Use client
     * }
     * ```
     */
    override fun close() {
        httpClient.close()
    }

    companion object {
        /**
         * SDK version
         */
        const val VERSION = "1.0.0"

        /**
         * Create a client for local development
         *
         * @return Client configured for localhost:12001
         */
        fun local(): XAIClient = XAIClient(
            baseUrl = "http://localhost:12001"
        )

        /**
         * Create a client for testnet
         *
         * @param apiKey Optional API key
         * @return Client configured for testnet
         */
        fun testnet(apiKey: String? = null): XAIClient = XAIClient(
            baseUrl = "https://testnet-api.xai-blockchain.io",
            apiKey = apiKey
        )

        /**
         * Create a client for mainnet
         *
         * @param apiKey API key for authentication
         * @return Client configured for mainnet
         */
        fun mainnet(apiKey: String): XAIClient = XAIClient(
            baseUrl = "https://api.xai-blockchain.io",
            apiKey = apiKey
        )
    }
}
