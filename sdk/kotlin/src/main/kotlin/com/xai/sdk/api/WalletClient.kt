package com.xai.sdk.api

import com.xai.sdk.models.Address
import com.xai.sdk.models.Balance
import com.xai.sdk.models.UnsignedTx
import com.xai.sdk.models.UTXO
import com.xai.sdk.models.WalletType
import com.xai.sdk.utils.HttpClient
import com.xai.sdk.utils.ValidationException
import com.xai.sdk.utils.WalletException
import kotlinx.serialization.Serializable

/**
 * Client for wallet operations
 *
 * Provides methods for querying wallet balances, UTXOs, and creating transactions.
 *
 * Example:
 * ```kotlin
 * val client = XAIClient(baseUrl = "http://localhost:12001")
 * val balance = client.wallet.getBalance("0x1234...")
 * val utxos = client.wallet.getUTXOs("0x1234...")
 * ```
 */
class WalletClient internal constructor(private val httpClient: HttpClient) {

    @Serializable
    private data class BalanceResponse(
        val address: String,
        val balance: String,
        val locked_balance: String = "0",
        val available_balance: String = "0",
        val nonce: Int = 0,
        val last_updated: String? = null
    )

    @Serializable
    private data class UTXOsResponse(
        val utxos: List<UTXOItem>,
        val total: Int = 0
    )

    @Serializable
    private data class UTXOItem(
        val tx_hash: String,
        val output_index: Int,
        val amount: String,
        val address: String,
        val block_height: Long,
        val confirmations: Int = 0,
        val script_pubkey: String? = null
    )

    @Serializable
    private data class AddressResponse(
        val address: String,
        val public_key: String,
        val created_at: String,
        val wallet_type: WalletType = WalletType.STANDARD,
        val nonce: Int = 0
    )

    @Serializable
    private data class CreateTxRequest(
        val from: String,
        val to: String,
        val amount: String,
        val data: String? = null
    )

    @Serializable
    private data class UnsignedTxResponse(
        val from: String,
        val to: String,
        val amount: String,
        val nonce: Int,
        val gas_limit: String = "21000",
        val gas_price: String = "0",
        val data: String? = null,
        val estimated_fee: String = "0"
    )

    /**
     * Get wallet balance
     *
     * @param address Wallet address
     * @return Balance information including available and locked amounts
     * @throws ValidationException if address is blank
     * @throws WalletException if wallet not found
     *
     * Example:
     * ```kotlin
     * val balance = client.wallet.getBalance("0x1234...")
     * println("Available: ${balance.availableBalance}")
     * println("Locked: ${balance.lockedBalance}")
     * ```
     */
    suspend fun getBalance(address: String): Balance {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        val response: BalanceResponse = httpClient.get("/wallet/$address/balance")

        return Balance(
            address = response.address,
            balance = response.balance,
            lockedBalance = response.locked_balance,
            availableBalance = response.available_balance,
            nonce = response.nonce,
            lastUpdated = response.last_updated
        )
    }

    /**
     * Get wallet UTXOs (Unspent Transaction Outputs)
     *
     * @param address Wallet address
     * @param minConfirmations Minimum confirmations required (default: 1)
     * @return List of UTXOs
     * @throws ValidationException if address is blank
     *
     * Example:
     * ```kotlin
     * val utxos = client.wallet.getUTXOs("0x1234...", minConfirmations = 6)
     * val totalAvailable = utxos.sumOf { BigDecimal(it.amount) }
     * println("Total available: $totalAvailable")
     * ```
     */
    suspend fun getUTXOs(
        address: String,
        minConfirmations: Int = 1
    ): List<UTXO> {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        val response: UTXOsResponse = httpClient.get(
            "/wallet/$address/utxos",
            mapOf("min_confirmations" to minConfirmations)
        )

        return response.utxos.map { utxo ->
            UTXO(
                txHash = utxo.tx_hash,
                outputIndex = utxo.output_index,
                amount = utxo.amount,
                address = utxo.address,
                blockHeight = utxo.block_height,
                confirmations = utxo.confirmations,
                scriptPubKey = utxo.script_pubkey
            )
        }
    }

    /**
     * Get wallet information
     *
     * @param address Wallet address
     * @return Address information
     * @throws ValidationException if address is blank
     * @throws WalletException if wallet not found
     *
     * Example:
     * ```kotlin
     * val info = client.wallet.getAddress("0x1234...")
     * println("Public Key: ${info.publicKey}")
     * println("Created: ${info.createdAt}")
     * ```
     */
    suspend fun getAddress(address: String): Address {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        val response: AddressResponse = httpClient.get("/wallet/$address")

        return Address(
            address = response.address,
            publicKey = response.public_key,
            createdAt = response.created_at,
            walletType = response.wallet_type,
            nonce = response.nonce
        )
    }

    /**
     * Create an unsigned transaction
     *
     * Creates a transaction ready for signing. The transaction includes
     * the current nonce and estimated fees.
     *
     * @param from Sender address
     * @param to Recipient address
     * @param amount Amount to send
     * @param data Optional transaction data
     * @return Unsigned transaction ready for signing
     * @throws ValidationException if parameters are invalid
     *
     * Example:
     * ```kotlin
     * val unsignedTx = client.wallet.createTransaction(
     *     from = "0x1234...",
     *     to = "0x5678...",
     *     amount = "1000"
     * )
     * println("Nonce: ${unsignedTx.nonce}")
     * println("Estimated Fee: ${unsignedTx.estimatedFee}")
     * // Sign the transaction with your private key
     * ```
     */
    suspend fun createTransaction(
        from: String,
        to: String,
        amount: String,
        data: String? = null
    ): UnsignedTx {
        if (from.isBlank()) {
            throw ValidationException("From address is required", "from")
        }
        if (to.isBlank()) {
            throw ValidationException("To address is required", "to")
        }
        if (amount.isBlank()) {
            throw ValidationException("Amount is required", "amount")
        }

        val request = CreateTxRequest(from, to, amount, data)
        val response: UnsignedTxResponse = httpClient.post("/wallet/transaction/create", request)

        return UnsignedTx(
            from = response.from,
            to = response.to,
            amount = response.amount,
            nonce = response.nonce,
            gasLimit = response.gas_limit,
            gasPrice = response.gas_price,
            data = response.data,
            estimatedFee = response.estimated_fee
        )
    }

    /**
     * Get the current nonce for an address
     *
     * The nonce is used to ensure transaction ordering and prevent replay attacks.
     *
     * @param address Wallet address
     * @return Current nonce value
     * @throws ValidationException if address is blank
     *
     * Example:
     * ```kotlin
     * val nonce = client.wallet.getNonce("0x1234...")
     * println("Next transaction should use nonce: $nonce")
     * ```
     */
    suspend fun getNonce(address: String): Int {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        @Serializable
        data class NonceResponse(val nonce: Int)

        val response: NonceResponse = httpClient.get("/wallet/$address/nonce")
        return response.nonce
    }

    /**
     * Validate an address format
     *
     * @param address Address to validate
     * @return True if address format is valid
     *
     * Example:
     * ```kotlin
     * if (client.wallet.validateAddress("0x1234...")) {
     *     println("Address is valid")
     * }
     * ```
     */
    suspend fun validateAddress(address: String): Boolean {
        if (address.isBlank()) {
            return false
        }

        @Serializable
        data class ValidateResponse(val valid: Boolean, val message: String? = null)

        return try {
            val response: ValidateResponse = httpClient.post(
                "/wallet/validate",
                mapOf("address" to address)
            )
            response.valid
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Get transaction history for a wallet
     *
     * @param address Wallet address
     * @param limit Maximum transactions to return (default: 50, max: 100)
     * @param offset Pagination offset
     * @return List of transaction hashes
     *
     * Example:
     * ```kotlin
     * val history = client.wallet.getTransactionHistory("0x1234...", limit = 20)
     * history.forEach { txHash ->
     *     println("Transaction: $txHash")
     * }
     * ```
     */
    suspend fun getTransactionHistory(
        address: String,
        limit: Int = 50,
        offset: Int = 0
    ): List<String> {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        val actualLimit = limit.coerceIn(1, 100)

        @Serializable
        data class HistoryResponse(
            val transactions: List<String>,
            val total: Int
        )

        val response: HistoryResponse = httpClient.get(
            "/wallet/$address/history",
            mapOf("limit" to actualLimit, "offset" to offset)
        )

        return response.transactions
    }

    /**
     * Get total balance across multiple addresses
     *
     * @param addresses List of wallet addresses
     * @return Map of address to balance
     * @throws ValidationException if addresses list is empty
     *
     * Example:
     * ```kotlin
     * val addresses = listOf("0x1234...", "0x5678...")
     * val balances = client.wallet.getMultiBalance(addresses)
     * balances.forEach { (addr, bal) ->
     *     println("$addr: ${bal.balance}")
     * }
     * ```
     */
    suspend fun getMultiBalance(addresses: List<String>): Map<String, Balance> {
        if (addresses.isEmpty()) {
            throw ValidationException("At least one address is required", "addresses")
        }

        @Serializable
        data class MultiBalanceRequest(val addresses: List<String>)

        @Serializable
        data class MultiBalanceResponse(val balances: Map<String, BalanceResponse>)

        val response: MultiBalanceResponse = httpClient.post(
            "/wallet/balances",
            MultiBalanceRequest(addresses)
        )

        return response.balances.mapValues { (_, v) ->
            Balance(
                address = v.address,
                balance = v.balance,
                lockedBalance = v.locked_balance,
                availableBalance = v.available_balance,
                nonce = v.nonce,
                lastUpdated = v.last_updated
            )
        }
    }
}
