package com.xai.sdk.api

import com.xai.sdk.models.PaginatedResponse
import com.xai.sdk.models.StakingInfo
import com.xai.sdk.models.TxResult
import com.xai.sdk.models.Validator
import com.xai.sdk.utils.HttpClient
import com.xai.sdk.utils.ValidationException
import kotlinx.serialization.Serializable

/**
 * Client for staking operations
 *
 * Provides methods for staking, delegation, and validator management.
 *
 * Example:
 * ```kotlin
 * val client = XAIClient(baseUrl = "http://localhost:12001")
 * val info = client.staking.getStakingInfo("0x1234...")
 * val validators = client.staking.listValidators()
 * ```
 */
class StakingClient internal constructor(private val httpClient: HttpClient) {

    @Serializable
    private data class StakingInfoResponse(
        val address: String,
        val staked_amount: String,
        val rewards: String,
        val validator_address: String? = null,
        val stake_date: String? = null,
        val unlock_date: String? = null,
        val apy_rate: String = "0"
    )

    @Serializable
    private data class ValidatorResponse(
        val address: String,
        val name: String? = null,
        val total_stake: String,
        val delegator_count: Int = 0,
        val commission: String = "0",
        val status: String = "active",
        val uptime: Double = 100.0
    )

    @Serializable
    private data class ValidatorsListResponse(
        val validators: List<ValidatorResponse>,
        val total: Int,
        val limit: Int,
        val offset: Int
    )

    @Serializable
    private data class StakeRequest(
        val from: String,
        val amount: String,
        val validator_address: String? = null,
        val signature: String
    )

    @Serializable
    private data class UnstakeRequest(
        val from: String,
        val amount: String,
        val signature: String
    )

    @Serializable
    private data class ClaimRewardsRequest(
        val from: String,
        val signature: String
    )

    /**
     * Get staking information for an address
     *
     * @param address Wallet address
     * @return Staking info including staked amount and rewards
     * @throws ValidationException if address is blank
     *
     * Example:
     * ```kotlin
     * val info = client.staking.getStakingInfo("0x1234...")
     * println("Staked: ${info.stakedAmount}")
     * println("Rewards: ${info.rewards}")
     * println("APY: ${info.apyRate}%")
     * ```
     */
    suspend fun getStakingInfo(address: String): StakingInfo {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        val response: StakingInfoResponse = httpClient.get("/staking/$address")

        return StakingInfo(
            address = response.address,
            stakedAmount = response.staked_amount,
            rewards = response.rewards,
            validatorAddress = response.validator_address,
            stakeDate = response.stake_date,
            unlockDate = response.unlock_date,
            apyRate = response.apy_rate
        )
    }

    /**
     * List all active validators
     *
     * @param page Page number (1-indexed)
     * @param limit Number of validators per page
     * @return List of validators
     *
     * Example:
     * ```kotlin
     * val validators = client.staking.listValidators()
     * validators.forEach { v ->
     *     println("${v.name}: ${v.totalStake} (${v.uptime}% uptime)")
     * }
     * ```
     */
    suspend fun listValidators(
        page: Int = 1,
        limit: Int = 50
    ): List<Validator> {
        val actualLimit = limit.coerceIn(1, 100)
        val offset = (page - 1) * actualLimit

        val response: ValidatorsListResponse = httpClient.get(
            "/staking/validators",
            mapOf("limit" to actualLimit, "offset" to offset)
        )

        return response.validators.map { it.toValidator() }
    }

    /**
     * List validators with pagination info
     *
     * @param page Page number (1-indexed)
     * @param limit Number of validators per page
     * @return Paginated response with validators
     */
    suspend fun listValidatorsPaginated(
        page: Int = 1,
        limit: Int = 50
    ): PaginatedResponse<Validator> {
        val actualLimit = limit.coerceIn(1, 100)
        val offset = (page - 1) * actualLimit

        val response: ValidatorsListResponse = httpClient.get(
            "/staking/validators",
            mapOf("limit" to actualLimit, "offset" to offset)
        )

        return PaginatedResponse(
            data = response.validators.map { it.toValidator() },
            total = response.total,
            limit = response.limit,
            offset = response.offset
        )
    }

    /**
     * Get validator details by address
     *
     * @param address Validator address
     * @return Validator details
     * @throws ValidationException if address is blank
     *
     * Example:
     * ```kotlin
     * val validator = client.staking.getValidator("0x1234...")
     * println("Commission: ${validator.commission}%")
     * println("Delegators: ${validator.delegatorCount}")
     * ```
     */
    suspend fun getValidator(address: String): Validator {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        val response: ValidatorResponse = httpClient.get("/staking/validators/$address")
        return response.toValidator()
    }

    /**
     * Stake tokens
     *
     * @param from Staker address
     * @param amount Amount to stake
     * @param validatorAddress Optional validator to delegate to
     * @param signature Transaction signature
     * @return Transaction result
     * @throws ValidationException if parameters are invalid
     *
     * Example:
     * ```kotlin
     * val result = client.staking.stake(
     *     from = "0x1234...",
     *     amount = "1000",
     *     validatorAddress = "0x5678...",
     *     signature = "0xsig..."
     * )
     * println("Stake tx: ${result.hash}")
     * ```
     */
    suspend fun stake(
        from: String,
        amount: String,
        validatorAddress: String? = null,
        signature: String
    ): TxResult {
        if (from.isBlank()) {
            throw ValidationException("From address is required", "from")
        }
        if (amount.isBlank()) {
            throw ValidationException("Amount is required", "amount")
        }
        if (signature.isBlank()) {
            throw ValidationException("Signature is required", "signature")
        }

        return httpClient.post(
            "/staking/stake",
            StakeRequest(from, amount, validatorAddress, signature)
        )
    }

    /**
     * Unstake tokens
     *
     * @param from Staker address
     * @param amount Amount to unstake
     * @param signature Transaction signature
     * @return Transaction result
     * @throws ValidationException if parameters are invalid
     *
     * Example:
     * ```kotlin
     * val result = client.staking.unstake(
     *     from = "0x1234...",
     *     amount = "500",
     *     signature = "0xsig..."
     * )
     * println("Unstake tx: ${result.hash}")
     * ```
     */
    suspend fun unstake(
        from: String,
        amount: String,
        signature: String
    ): TxResult {
        if (from.isBlank()) {
            throw ValidationException("From address is required", "from")
        }
        if (amount.isBlank()) {
            throw ValidationException("Amount is required", "amount")
        }
        if (signature.isBlank()) {
            throw ValidationException("Signature is required", "signature")
        }

        return httpClient.post(
            "/staking/unstake",
            UnstakeRequest(from, amount, signature)
        )
    }

    /**
     * Claim staking rewards
     *
     * @param from Staker address
     * @param signature Transaction signature
     * @return Transaction result
     * @throws ValidationException if parameters are invalid
     *
     * Example:
     * ```kotlin
     * val info = client.staking.getStakingInfo("0x1234...")
     * if (info.rewards.toBigDecimal() > BigDecimal.ZERO) {
     *     val result = client.staking.claimRewards(
     *         from = "0x1234...",
     *         signature = "0xsig..."
     *     )
     *     println("Claimed rewards: ${result.hash}")
     * }
     * ```
     */
    suspend fun claimRewards(
        from: String,
        signature: String
    ): TxResult {
        if (from.isBlank()) {
            throw ValidationException("From address is required", "from")
        }
        if (signature.isBlank()) {
            throw ValidationException("Signature is required", "signature")
        }

        return httpClient.post(
            "/staking/claim-rewards",
            ClaimRewardsRequest(from, signature)
        )
    }

    /**
     * Get current staking APY rate
     *
     * @return Current APY rate as a string percentage
     *
     * Example:
     * ```kotlin
     * val apy = client.staking.getAPY()
     * println("Current staking APY: $apy%")
     * ```
     */
    suspend fun getAPY(): String {
        @Serializable
        data class APYResponse(val apy: String)

        val response: APYResponse = httpClient.get("/staking/apy")
        return response.apy
    }

    /**
     * Get total staked amount in the network
     *
     * @return Total staked amount
     *
     * Example:
     * ```kotlin
     * val totalStaked = client.staking.getTotalStaked()
     * println("Total network stake: $totalStaked")
     * ```
     */
    suspend fun getTotalStaked(): String {
        @Serializable
        data class TotalStakedResponse(val total_staked: String)

        val response: TotalStakedResponse = httpClient.get("/staking/total")
        return response.total_staked
    }

    private fun ValidatorResponse.toValidator() = Validator(
        address = address,
        name = name,
        totalStake = total_stake,
        delegatorCount = delegator_count,
        commission = commission,
        status = status,
        uptime = uptime
    )
}
