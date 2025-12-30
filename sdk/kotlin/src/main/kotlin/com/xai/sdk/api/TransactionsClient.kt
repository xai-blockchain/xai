package com.xai.sdk.api

import com.xai.sdk.models.FeeEstimation
import com.xai.sdk.models.PaginatedResponse
import com.xai.sdk.models.SignedTransaction
import com.xai.sdk.models.Transaction
import com.xai.sdk.models.TransactionStatus
import com.xai.sdk.models.TxResult
import com.xai.sdk.utils.HttpClient
import com.xai.sdk.utils.TimeoutException
import com.xai.sdk.utils.TransactionException
import com.xai.sdk.utils.ValidationException
import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable

/**
 * Client for transaction operations
 *
 * Provides methods for querying and submitting transactions.
 *
 * Example:
 * ```kotlin
 * val client = XAIClient(baseUrl = "http://localhost:12001")
 * val tx = client.transactions.getTransaction("0x1234...")
 * val result = client.transactions.sendTransaction(signedTx)
 * ```
 */
class TransactionsClient internal constructor(private val httpClient: HttpClient) {

    @Serializable
    private data class TransactionResponse(
        val hash: String,
        val from: String,
        val to: String,
        val amount: String,
        val timestamp: String,
        val status: TransactionStatus = TransactionStatus.PENDING,
        val fee: String = "0",
        val gas_limit: String = "21000",
        val gas_used: String = "0",
        val gas_price: String = "0",
        val nonce: Int = 0,
        val data: String? = null,
        val block_number: Long? = null,
        val block_hash: String? = null,
        val confirmations: Int = 0
    )

    @Serializable
    private data class TransactionsListResponse(
        val transactions: List<TransactionResponse>,
        val total: Int,
        val limit: Int,
        val offset: Int
    )

    @Serializable
    private data class TxStatusResponse(
        val status: TransactionStatus,
        val confirmations: Int = 0,
        val block_number: Long? = null
    )

    /**
     * Get a transaction by its hash
     *
     * @param txid Transaction hash
     * @return Transaction details
     * @throws ValidationException if txid is blank
     * @throws TransactionException if transaction not found
     *
     * Example:
     * ```kotlin
     * val tx = client.transactions.getTransaction("0x1234...")
     * println("Status: ${tx.status}, Confirmations: ${tx.confirmations}")
     * ```
     */
    suspend fun getTransaction(txid: String): Transaction {
        if (txid.isBlank()) {
            throw ValidationException("Transaction ID is required", "txid")
        }

        val response: TransactionResponse = httpClient.get("/transaction/$txid")
        return response.toTransaction()
    }

    /**
     * Send a signed transaction
     *
     * @param tx Signed transaction to broadcast
     * @return Transaction result with hash
     * @throws ValidationException if transaction is invalid
     * @throws TransactionException if broadcast fails
     *
     * Example:
     * ```kotlin
     * val signedTx = SignedTransaction(
     *     from = "0x...",
     *     to = "0x...",
     *     amount = "1000",
     *     signature = "0x...",
     *     nonce = 5
     * )
     * val result = client.transactions.sendTransaction(signedTx)
     * println("Transaction submitted: ${result.hash}")
     * ```
     */
    suspend fun sendTransaction(tx: SignedTransaction): TxResult {
        validateSignedTransaction(tx)

        @Serializable
        data class SendRequest(
            val from: String,
            val to: String,
            val amount: String,
            val signature: String,
            val nonce: Int,
            val gas_limit: String,
            val gas_price: String,
            val data: String?
        )

        val request = SendRequest(
            from = tx.from,
            to = tx.to,
            amount = tx.amount,
            signature = tx.signature,
            nonce = tx.nonce,
            gas_limit = tx.gasLimit,
            gas_price = tx.gasPrice,
            data = tx.data
        )

        return httpClient.post("/transaction/send", request)
    }

    /**
     * Get transactions for a specific address
     *
     * @param address Wallet address
     * @param page Page number (1-indexed)
     * @param limit Number of transactions per page (max 100)
     * @return List of transactions
     * @throws ValidationException if address is blank
     *
     * Example:
     * ```kotlin
     * val txs = client.transactions.getTransactions("0x1234...")
     * txs.forEach { tx ->
     *     println("${tx.from} -> ${tx.to}: ${tx.amount}")
     * }
     * ```
     */
    suspend fun getTransactions(
        address: String,
        page: Int = 1,
        limit: Int = 50
    ): List<Transaction> {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }
        if (page < 1) {
            throw ValidationException("Page must be at least 1", "page")
        }

        val actualLimit = limit.coerceIn(1, 100)
        val offset = (page - 1) * actualLimit

        val response: TransactionsListResponse = httpClient.get(
            "/wallet/$address/transactions",
            mapOf("limit" to actualLimit, "offset" to offset)
        )

        return response.transactions.map { it.toTransaction() }
    }

    /**
     * Get transactions for a specific address with pagination info
     *
     * @param address Wallet address
     * @param page Page number (1-indexed)
     * @param limit Number of transactions per page (max 100)
     * @return Paginated response with transactions
     */
    suspend fun getTransactionsPaginated(
        address: String,
        page: Int = 1,
        limit: Int = 50
    ): PaginatedResponse<Transaction> {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        val actualLimit = limit.coerceIn(1, 100)
        val offset = (page - 1) * actualLimit

        val response: TransactionsListResponse = httpClient.get(
            "/wallet/$address/transactions",
            mapOf("limit" to actualLimit, "offset" to offset)
        )

        return PaginatedResponse(
            data = response.transactions.map { it.toTransaction() },
            total = response.total,
            limit = response.limit,
            offset = response.offset
        )
    }

    /**
     * Get transaction status
     *
     * @param txid Transaction hash
     * @return Current transaction status
     * @throws ValidationException if txid is blank
     *
     * Example:
     * ```kotlin
     * val status = client.transactions.getStatus("0x1234...")
     * if (status == TransactionStatus.CONFIRMED) {
     *     println("Transaction confirmed!")
     * }
     * ```
     */
    suspend fun getStatus(txid: String): TransactionStatus {
        if (txid.isBlank()) {
            throw ValidationException("Transaction ID is required", "txid")
        }

        val response: TxStatusResponse = httpClient.get("/transaction/$txid/status")
        return response.status
    }

    /**
     * Estimate transaction fee
     *
     * @param from Sender address
     * @param to Recipient address
     * @param amount Amount to send
     * @param data Optional transaction data
     * @return Fee estimation details
     *
     * Example:
     * ```kotlin
     * val fee = client.transactions.estimateFee(
     *     from = "0x...",
     *     to = "0x...",
     *     amount = "1000"
     * )
     * println("Estimated fee: ${fee.estimatedFee}")
     * ```
     */
    suspend fun estimateFee(
        from: String,
        to: String,
        amount: String,
        data: String? = null
    ): FeeEstimation {
        if (from.isBlank() || to.isBlank()) {
            throw ValidationException("From and to addresses are required")
        }

        @Serializable
        data class EstimateRequest(
            val from: String,
            val to: String,
            val amount: String,
            val data: String?
        )

        return httpClient.post(
            "/transaction/estimate-fee",
            EstimateRequest(from, to, amount, data)
        )
    }

    /**
     * Check if a transaction is confirmed
     *
     * @param txid Transaction hash
     * @param requiredConfirmations Number of required confirmations (default: 1)
     * @return True if transaction has enough confirmations
     *
     * Example:
     * ```kotlin
     * if (client.transactions.isConfirmed("0x1234...", requiredConfirmations = 6)) {
     *     println("Transaction is fully confirmed!")
     * }
     * ```
     */
    suspend fun isConfirmed(txid: String, requiredConfirmations: Int = 1): Boolean {
        if (txid.isBlank()) {
            throw ValidationException("Transaction ID is required", "txid")
        }

        val response: TxStatusResponse = httpClient.get("/transaction/$txid/status")
        return response.confirmations >= requiredConfirmations
    }

    /**
     * Wait for transaction confirmation
     *
     * @param txid Transaction hash
     * @param confirmations Required number of confirmations
     * @param timeoutSeconds Maximum time to wait in seconds
     * @param pollIntervalSeconds Polling interval in seconds
     * @return Confirmed transaction
     * @throws TimeoutException if confirmation times out
     * @throws TransactionException if transaction fails
     *
     * Example:
     * ```kotlin
     * try {
     *     val confirmedTx = client.transactions.waitForConfirmation(
     *         txid = "0x1234...",
     *         confirmations = 3,
     *         timeoutSeconds = 120
     *     )
     *     println("Transaction confirmed in block ${confirmedTx.blockNumber}")
     * } catch (e: TimeoutException) {
     *     println("Transaction not confirmed within timeout")
     * }
     * ```
     */
    suspend fun waitForConfirmation(
        txid: String,
        confirmations: Int = 1,
        timeoutSeconds: Int = 300,
        pollIntervalSeconds: Int = 5
    ): Transaction {
        if (txid.isBlank()) {
            throw ValidationException("Transaction ID is required", "txid")
        }
        if (confirmations < 1) {
            throw ValidationException("Confirmations must be at least 1", "confirmations")
        }

        val startTime = System.currentTimeMillis()
        val timeoutMillis = timeoutSeconds * 1000L
        val pollIntervalMillis = pollIntervalSeconds * 1000L

        while (true) {
            val elapsed = System.currentTimeMillis() - startTime
            if (elapsed > timeoutMillis) {
                throw TimeoutException(
                    "Transaction confirmation timeout after $timeoutSeconds seconds"
                )
            }

            try {
                val tx = getTransaction(txid)

                when (tx.status) {
                    TransactionStatus.FAILED -> {
                        throw TransactionException(
                            "Transaction failed",
                            txid
                        )
                    }
                    TransactionStatus.CONFIRMED -> {
                        if (tx.confirmations >= confirmations) {
                            return tx
                        }
                    }
                    TransactionStatus.PENDING -> {
                        // Continue waiting
                    }
                }
            } catch (e: TransactionException) {
                throw e
            } catch (e: Exception) {
                // Transaction might not be found yet, continue waiting
            }

            delay(pollIntervalMillis)
        }
    }

    /**
     * Get pending transactions from mempool
     *
     * @param limit Maximum number of transactions to return
     * @return List of pending transactions
     */
    suspend fun getPendingTransactions(limit: Int = 100): List<Transaction> {
        val actualLimit = limit.coerceIn(1, 1000)

        val response: TransactionsListResponse = httpClient.get(
            "/mempool/transactions",
            mapOf("limit" to actualLimit)
        )

        return response.transactions.map { it.toTransaction() }
    }

    private fun validateSignedTransaction(tx: SignedTransaction) {
        if (tx.from.isBlank()) {
            throw ValidationException("From address is required", "from")
        }
        if (tx.to.isBlank()) {
            throw ValidationException("To address is required", "to")
        }
        if (tx.amount.isBlank()) {
            throw ValidationException("Amount is required", "amount")
        }
        if (tx.signature.isBlank()) {
            throw ValidationException("Signature is required", "signature")
        }
        if (tx.nonce < 0) {
            throw ValidationException("Nonce must be non-negative", "nonce")
        }
    }

    private fun TransactionResponse.toTransaction() = Transaction(
        hash = hash,
        from = from,
        to = to,
        amount = amount,
        timestamp = timestamp,
        status = status,
        fee = fee,
        gasLimit = gas_limit,
        gasUsed = gas_used,
        gasPrice = gas_price,
        nonce = nonce,
        data = data,
        blockNumber = block_number,
        blockHash = block_hash,
        confirmations = confirmations
    )
}
