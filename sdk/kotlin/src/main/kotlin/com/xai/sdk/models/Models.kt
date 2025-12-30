package com.xai.sdk.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Transaction status enumeration
 */
@Serializable
enum class TransactionStatus {
    @SerialName("pending") PENDING,
    @SerialName("confirmed") CONFIRMED,
    @SerialName("failed") FAILED
}

/**
 * Wallet type enumeration
 */
@Serializable
enum class WalletType {
    @SerialName("standard") STANDARD,
    @SerialName("embedded") EMBEDDED,
    @SerialName("hardware") HARDWARE
}

/**
 * Proposal status enumeration
 */
@Serializable
enum class ProposalStatus {
    @SerialName("pending") PENDING,
    @SerialName("active") ACTIVE,
    @SerialName("passed") PASSED,
    @SerialName("failed") FAILED
}

/**
 * AI task status enumeration
 */
@Serializable
enum class AITaskStatus {
    @SerialName("pending") PENDING,
    @SerialName("processing") PROCESSING,
    @SerialName("completed") COMPLETED,
    @SerialName("failed") FAILED
}

/**
 * Represents a blockchain block
 */
@Serializable
data class Block(
    val number: Long,
    val hash: String,
    @SerialName("parent_hash") val parentHash: String,
    val timestamp: Long,
    val miner: String,
    val difficulty: String,
    @SerialName("gas_limit") val gasLimit: String = "0",
    @SerialName("gas_used") val gasUsed: String = "0",
    @SerialName("transaction_count") val transactionCount: Int = 0,
    @SerialName("transactions") val transactionHashes: List<String> = emptyList()
)

/**
 * Represents a blockchain transaction
 */
@Serializable
data class Transaction(
    val hash: String,
    val from: String,
    val to: String,
    val amount: String,
    val timestamp: String,
    val status: TransactionStatus = TransactionStatus.PENDING,
    val fee: String = "0",
    @SerialName("gas_limit") val gasLimit: String = "21000",
    @SerialName("gas_used") val gasUsed: String = "0",
    @SerialName("gas_price") val gasPrice: String = "0",
    val nonce: Int = 0,
    val data: String? = null,
    @SerialName("block_number") val blockNumber: Long? = null,
    @SerialName("block_hash") val blockHash: String? = null,
    val confirmations: Int = 0
)

/**
 * Represents a wallet address
 */
@Serializable
data class Address(
    val address: String,
    @SerialName("public_key") val publicKey: String,
    @SerialName("created_at") val createdAt: String,
    @SerialName("wallet_type") val walletType: WalletType = WalletType.STANDARD,
    val nonce: Int = 0
)

/**
 * Represents wallet balance information
 */
@Serializable
data class Balance(
    val address: String,
    val balance: String,
    @SerialName("locked_balance") val lockedBalance: String = "0",
    @SerialName("available_balance") val availableBalance: String = "0",
    val nonce: Int = 0,
    @SerialName("last_updated") val lastUpdated: String? = null
)

/**
 * Represents a UTXO (Unspent Transaction Output)
 */
@Serializable
data class UTXO(
    @SerialName("tx_hash") val txHash: String,
    @SerialName("output_index") val outputIndex: Int,
    val amount: String,
    val address: String,
    @SerialName("block_height") val blockHeight: Long,
    val confirmations: Int = 0,
    @SerialName("script_pubkey") val scriptPubKey: String? = null
)

/**
 * Represents an AI task
 */
@Serializable
data class AITask(
    val id: String,
    val type: String,
    val status: AITaskStatus = AITaskStatus.PENDING,
    @SerialName("created_at") val createdAt: String,
    @SerialName("completed_at") val completedAt: String? = null,
    val result: Map<String, String>? = null,
    val error: String? = null,
    val progress: Int = 0
)

/**
 * Represents an AI provider
 */
@Serializable
data class AIProvider(
    val id: String,
    val name: String,
    val description: String,
    val capabilities: List<String> = emptyList(),
    val models: List<String> = emptyList(),
    @SerialName("price_per_token") val pricePerToken: String = "0",
    val available: Boolean = true
)

/**
 * Request to submit an AI task
 */
@Serializable
data class AITaskRequest(
    val type: String,
    val prompt: String,
    @SerialName("provider_id") val providerId: String? = null,
    val model: String? = null,
    val parameters: Map<String, String> = emptyMap(),
    @SerialName("max_tokens") val maxTokens: Int? = null,
    val priority: String = "normal"
)

/**
 * Represents network information
 */
@Serializable
data class NetworkInfo(
    val status: String,
    val node: String,
    val version: String,
    @SerialName("chain_id") val chainId: String? = null,
    @SerialName("peer_count") val peerCount: Int = 0,
    @SerialName("sync_status") val syncStatus: SyncStatus? = null,
    val endpoints: List<String> = emptyList()
)

/**
 * Represents sync status
 */
@Serializable
data class SyncStatus(
    val syncing: Boolean,
    @SerialName("current_block") val currentBlock: Long? = null,
    @SerialName("highest_block") val highestBlock: Long? = null,
    @SerialName("starting_block") val startingBlock: Long? = null
) {
    val syncProgress: Double?
        get() = if (currentBlock != null && highestBlock != null && highestBlock > 0) {
            (currentBlock.toDouble() / highestBlock.toDouble()) * 100
        } else null
}

/**
 * Represents mempool information
 */
@Serializable
data class MempoolInfo(
    val size: Int,
    val bytes: Long,
    @SerialName("min_fee") val minFee: String,
    @SerialName("max_fee") val maxFee: String,
    @SerialName("total_fee") val totalFee: String
)

/**
 * Represents blockchain statistics
 */
@Serializable
data class BlockchainStats(
    @SerialName("total_blocks") val totalBlocks: Long,
    @SerialName("total_transactions") val totalTransactions: Long,
    @SerialName("total_accounts") val totalAccounts: Long,
    val difficulty: String,
    val hashrate: String,
    @SerialName("average_block_time") val averageBlockTime: Double = 0.0,
    @SerialName("total_supply") val totalSupply: String,
    val network: String = "mainnet"
)

/**
 * Represents a signed transaction ready to broadcast
 */
@Serializable
data class SignedTransaction(
    val from: String,
    val to: String,
    val amount: String,
    val signature: String,
    val nonce: Int,
    @SerialName("gas_limit") val gasLimit: String = "21000",
    @SerialName("gas_price") val gasPrice: String = "0",
    val data: String? = null
)

/**
 * Result of transaction submission
 */
@Serializable
data class TxResult(
    val hash: String,
    val status: String,
    val message: String? = null,
    @SerialName("block_number") val blockNumber: Long? = null
)

/**
 * Represents an unsigned transaction
 */
@Serializable
data class UnsignedTx(
    val from: String,
    val to: String,
    val amount: String,
    val nonce: Int,
    @SerialName("gas_limit") val gasLimit: String = "21000",
    @SerialName("gas_price") val gasPrice: String = "0",
    val data: String? = null,
    @SerialName("estimated_fee") val estimatedFee: String = "0"
)

/**
 * Health check response
 */
@Serializable
data class HealthCheckResponse(
    val status: String,
    val timestamp: Long,
    val services: Map<String, String> = emptyMap()
)

/**
 * Paginated response wrapper
 */
@Serializable
data class PaginatedResponse<T>(
    val data: List<T>,
    val total: Int,
    val limit: Int,
    val offset: Int
)

/**
 * Fee estimation response
 */
@Serializable
data class FeeEstimation(
    @SerialName("estimated_fee") val estimatedFee: String,
    @SerialName("gas_limit") val gasLimit: String,
    @SerialName("gas_price") val gasPrice: String,
    @SerialName("base_fee") val baseFee: String? = null,
    @SerialName("priority_fee") val priorityFee: String? = null
)

/**
 * Staking info response
 */
@Serializable
data class StakingInfo(
    val address: String,
    @SerialName("staked_amount") val stakedAmount: String,
    val rewards: String,
    @SerialName("validator_address") val validatorAddress: String? = null,
    @SerialName("stake_date") val stakeDate: String? = null,
    @SerialName("unlock_date") val unlockDate: String? = null,
    @SerialName("apy_rate") val apyRate: String = "0"
)

/**
 * Validator info response
 */
@Serializable
data class Validator(
    val address: String,
    val name: String? = null,
    @SerialName("total_stake") val totalStake: String,
    @SerialName("delegator_count") val delegatorCount: Int = 0,
    val commission: String = "0",
    val status: String = "active",
    val uptime: Double = 100.0
)
