import Foundation

/// Staking status.
public enum StakingStatus: String, Codable, Sendable {
    case active = "active"
    case unbonding = "unbonding"
    case inactive = "inactive"
}

/// Represents a staking position.
public struct StakingPosition: Codable, Sendable {
    /// Unique position ID
    public let id: String

    /// Staker address
    public let address: String

    /// Validator address
    public let validatorAddress: String

    /// Staked amount
    public let amount: String

    /// Staking status
    public let status: StakingStatus

    /// Start timestamp
    public let startedAt: Date

    /// Unbonding end time (if unbonding)
    public let unbondingEndsAt: Date?

    /// Accumulated rewards
    public let rewards: String

    /// Last reward claim timestamp
    public let lastClaimAt: Date?
}

/// Represents a validator.
public struct Validator: Codable, Sendable {
    /// Validator address
    public let address: String

    /// Validator name
    public let name: String

    /// Validator description
    public let description: String

    /// Commission rate (percentage)
    public let commissionRate: Double

    /// Total staked amount
    public let totalStaked: String

    /// Number of delegators
    public let delegators: Int

    /// Whether validator is active
    public let active: Bool

    /// Uptime percentage
    public let uptime: Double

    /// Voting power
    public let votingPower: String
}

/// Staking rewards information.
public struct StakingRewards: Codable, Sendable {
    /// Total rewards
    public let total: String

    /// Pending rewards (unclaimed)
    public let pending: String

    /// Claimed rewards
    public let claimed: String

    /// Estimated APY
    public let estimatedApy: Double
}

/// Stake transaction result.
public struct StakeResult: Codable, Sendable {
    /// Transaction hash
    public let txHash: String

    /// Position ID
    public let positionId: String

    /// Staked amount
    public let amount: String
}

/// Unstake transaction result.
public struct UnstakeResult: Codable, Sendable {
    /// Transaction hash
    public let txHash: String

    /// Position ID
    public let positionId: String

    /// Unstaked amount
    public let amount: String

    /// When unbonding ends
    public let unbondingEndsAt: Date
}

/// Client for staking operations.
public struct StakingClient: Sendable {
    private let httpClient: HTTPClient

    init(httpClient: HTTPClient) {
        self.httpClient = httpClient
    }

    /// Stake tokens with a validator.
    /// - Parameters:
    ///   - address: Staker address
    ///   - validatorAddress: Validator address
    ///   - amount: Amount to stake
    /// - Returns: Stake result
    /// - Throws: `XAIError` if the request fails
    public func stake(
        address: String,
        validatorAddress: String,
        amount: String
    ) async throws -> StakeResult {
        guard !address.isEmpty && !validatorAddress.isEmpty && !amount.isEmpty else {
            throw XAIError.validationError("address, validatorAddress, and amount are required")
        }

        struct StakeRequest: Encodable {
            let address: String
            let validatorAddress: String
            let amount: String
        }

        return try await httpClient.post(
            "/staking/stake",
            body: StakeRequest(address: address, validatorAddress: validatorAddress, amount: amount)
        )
    }

    /// Unstake tokens from a validator.
    /// - Parameters:
    ///   - address: Staker address
    ///   - positionId: Staking position ID
    ///   - amount: Amount to unstake (nil for full unstake)
    /// - Returns: Unstake result
    /// - Throws: `XAIError` if the request fails
    public func unstake(
        address: String,
        positionId: String,
        amount: String? = nil
    ) async throws -> UnstakeResult {
        guard !address.isEmpty && !positionId.isEmpty else {
            throw XAIError.validationError("address and positionId are required")
        }

        struct UnstakeRequest: Encodable {
            let address: String
            let positionId: String
            let amount: String?
        }

        return try await httpClient.post(
            "/staking/unstake",
            body: UnstakeRequest(address: address, positionId: positionId, amount: amount)
        )
    }

    /// Get staking positions for an address.
    /// - Parameter address: Staker address
    /// - Returns: List of staking positions
    /// - Throws: `XAIError` if the request fails
    public func getPositions(address: String) async throws -> [StakingPosition] {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }

        struct Response: Decodable {
            let positions: [StakingPosition]
        }

        let response: Response = try await httpClient.get("/staking/positions/\(address)")
        return response.positions
    }

    /// Get staking rewards for an address.
    /// - Parameter address: Staker address
    /// - Returns: Rewards information
    /// - Throws: `XAIError` if the request fails
    public func getRewards(address: String) async throws -> StakingRewards {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        return try await httpClient.get("/staking/rewards/\(address)")
    }

    /// Claim pending staking rewards.
    /// - Parameter address: Staker address
    /// - Returns: Transaction hash
    /// - Throws: `XAIError` if the request fails
    public func claimRewards(address: String) async throws -> String {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }

        struct ClaimRequest: Encodable {
            let address: String
        }

        struct Response: Decodable {
            let txHash: String
        }

        let response: Response = try await httpClient.post(
            "/staking/claim",
            body: ClaimRequest(address: address)
        )
        return response.txHash
    }

    /// List all validators.
    /// - Parameter activeOnly: Only return active validators
    /// - Returns: List of validators
    /// - Throws: `XAIError` if the request fails
    public func listValidators(activeOnly: Bool = false) async throws -> [Validator] {
        var queryItems: [URLQueryItem]? = nil
        if activeOnly {
            queryItems = [URLQueryItem(name: "active", value: "true")]
        }

        struct Response: Decodable {
            let validators: [Validator]
        }

        let response: Response = try await httpClient.get("/staking/validators", queryItems: queryItems)
        return response.validators
    }

    /// Get a specific validator.
    /// - Parameter address: Validator address
    /// - Returns: Validator details
    /// - Throws: `XAIError` if the request fails
    public func getValidator(address: String) async throws -> Validator {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        return try await httpClient.get("/staking/validators/\(address)")
    }

    /// Get estimated staking APY.
    /// - Returns: Current APY as a percentage
    /// - Throws: `XAIError` if the request fails
    public func getEstimatedApy() async throws -> Double {
        struct Response: Decodable {
            let apy: Double
        }
        let response: Response = try await httpClient.get("/staking/apy")
        return response.apy
    }
}
