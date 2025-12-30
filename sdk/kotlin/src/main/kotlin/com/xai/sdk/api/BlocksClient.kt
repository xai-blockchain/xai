package com.xai.sdk.api

import com.xai.sdk.models.Block
import com.xai.sdk.models.PaginatedResponse
import com.xai.sdk.models.Transaction
import com.xai.sdk.utils.HttpClient
import com.xai.sdk.utils.ValidationException
import com.xai.sdk.utils.XAIException
import kotlinx.serialization.Serializable

/**
 * Client for blockchain block operations
 *
 * Provides methods for querying blocks and their transactions.
 *
 * Example:
 * ```kotlin
 * val client = XAIClient(baseUrl = "http://localhost:12001")
 * val latestBlock = client.blocks.getLatestBlock()
 * val block = client.blocks.getBlock(latestBlock.hash)
 * val blocks = client.blocks.getBlocks(page = 1, limit = 20)
 * ```
 */
class BlocksClient internal constructor(private val httpClient: HttpClient) {

    @Serializable
    private data class BlockResponse(
        val number: Long,
        val hash: String,
        val parent_hash: String,
        val timestamp: Long,
        val miner: String,
        val difficulty: String,
        val gas_limit: String = "0",
        val gas_used: String = "0",
        val transaction_count: Int = 0,
        val transactions: List<String> = emptyList()
    )

    @Serializable
    private data class BlocksListResponse(
        val blocks: List<BlockResponse>,
        val total: Int,
        val limit: Int,
        val offset: Int
    )

    /**
     * Get a block by its hash
     *
     * @param hash Block hash
     * @return Block details
     * @throws ValidationException if hash is blank
     * @throws XAIException if request fails
     *
     * Example:
     * ```kotlin
     * val block = client.blocks.getBlock("0x1234...")
     * println("Block ${block.number}: ${block.transactionCount} txs")
     * ```
     */
    suspend fun getBlock(hash: String): Block {
        if (hash.isBlank()) {
            throw ValidationException("Block hash is required", "hash")
        }

        val response: BlockResponse = httpClient.get("/blocks/$hash")
        return response.toBlock()
    }

    /**
     * Get a block by its number
     *
     * @param number Block number
     * @return Block details
     * @throws ValidationException if number is negative
     * @throws XAIException if request fails
     *
     * Example:
     * ```kotlin
     * val block = client.blocks.getBlockByNumber(1000)
     * println("Block hash: ${block.hash}")
     * ```
     */
    suspend fun getBlockByNumber(number: Long): Block {
        if (number < 0) {
            throw ValidationException("Block number must be non-negative", "number")
        }

        val response: BlockResponse = httpClient.get("/blocks/number/$number")
        return response.toBlock()
    }

    /**
     * Get a paginated list of blocks
     *
     * @param page Page number (1-indexed)
     * @param limit Number of blocks per page (max 100)
     * @return Paginated list of blocks
     * @throws ValidationException if page or limit are invalid
     * @throws XAIException if request fails
     *
     * Example:
     * ```kotlin
     * val blocks = client.blocks.getBlocks(page = 1, limit = 20)
     * blocks.forEach { block ->
     *     println("Block ${block.number}: ${block.hash}")
     * }
     * ```
     */
    suspend fun getBlocks(page: Int = 1, limit: Int = 20): List<Block> {
        if (page < 1) {
            throw ValidationException("Page must be at least 1", "page")
        }
        if (limit < 1 || limit > 100) {
            throw ValidationException("Limit must be between 1 and 100", "limit")
        }

        val offset = (page - 1) * limit
        val response: BlocksListResponse = httpClient.get(
            "/blocks",
            mapOf("limit" to limit, "offset" to offset)
        )

        return response.blocks.map { it.toBlock() }
    }

    /**
     * Get a paginated list of blocks with pagination info
     *
     * @param page Page number (1-indexed)
     * @param limit Number of blocks per page (max 100)
     * @return Paginated response with blocks and metadata
     * @throws ValidationException if page or limit are invalid
     * @throws XAIException if request fails
     */
    suspend fun getBlocksPaginated(page: Int = 1, limit: Int = 20): PaginatedResponse<Block> {
        if (page < 1) {
            throw ValidationException("Page must be at least 1", "page")
        }
        if (limit < 1 || limit > 100) {
            throw ValidationException("Limit must be between 1 and 100", "limit")
        }

        val offset = (page - 1) * limit
        val response: BlocksListResponse = httpClient.get(
            "/blocks",
            mapOf("limit" to limit, "offset" to offset)
        )

        return PaginatedResponse(
            data = response.blocks.map { it.toBlock() },
            total = response.total,
            limit = response.limit,
            offset = response.offset
        )
    }

    /**
     * Get the latest block
     *
     * @return Latest block details
     * @throws XAIException if request fails
     *
     * Example:
     * ```kotlin
     * val latest = client.blocks.getLatestBlock()
     * println("Latest block: ${latest.number}")
     * ```
     */
    suspend fun getLatestBlock(): Block {
        val response: BlockResponse = httpClient.get("/blocks/latest")
        return response.toBlock()
    }

    /**
     * Get transactions in a block by block hash
     *
     * @param hash Block hash
     * @return List of transactions in the block
     * @throws ValidationException if hash is blank
     * @throws XAIException if request fails
     *
     * Example:
     * ```kotlin
     * val txs = client.blocks.getBlockTransactions("0x1234...")
     * txs.forEach { tx ->
     *     println("${tx.from} -> ${tx.to}: ${tx.amount}")
     * }
     * ```
     */
    suspend fun getBlockTransactions(hash: String): List<Transaction> {
        if (hash.isBlank()) {
            throw ValidationException("Block hash is required", "hash")
        }

        @Serializable
        data class TransactionsResponse(val transactions: List<Transaction>)

        val response: TransactionsResponse = httpClient.get("/blocks/$hash/transactions")
        return response.transactions
    }

    /**
     * Get transactions in a block by block number
     *
     * @param number Block number
     * @return List of transactions in the block
     * @throws ValidationException if number is negative
     * @throws XAIException if request fails
     */
    suspend fun getBlockTransactionsByNumber(number: Long): List<Transaction> {
        if (number < 0) {
            throw ValidationException("Block number must be non-negative", "number")
        }

        @Serializable
        data class TransactionsResponse(val transactions: List<Transaction>)

        val response: TransactionsResponse = httpClient.get("/blocks/number/$number/transactions")
        return response.transactions
    }

    private fun BlockResponse.toBlock() = Block(
        number = number,
        hash = hash,
        parentHash = parent_hash,
        timestamp = timestamp,
        miner = miner,
        difficulty = difficulty,
        gasLimit = gas_limit,
        gasUsed = gas_used,
        transactionCount = transaction_count,
        transactionHashes = transactions
    )
}
