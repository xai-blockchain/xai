import Foundation

/// Blockchain node information.
public struct NodeInfo: Codable, Sendable {
    /// Node status
    public let status: String

    /// Node identifier
    public let node: String

    /// Node version
    public let version: String

    /// Whether AI features are enabled
    public let algorithmicFeatures: Bool?

    /// Available API endpoints
    public let endpoints: [String]?

    public init(
        status: String,
        node: String,
        version: String,
        algorithmicFeatures: Bool? = nil,
        endpoints: [String]? = nil
    ) {
        self.status = status
        self.node = node
        self.version = version
        self.algorithmicFeatures = algorithmicFeatures
        self.endpoints = endpoints
    }
}

/// Health check response.
public struct HealthCheckResponse: Codable, Sendable {
    /// Overall health status
    public let status: String

    /// Timestamp of the check
    public let timestamp: Int

    /// Blockchain health details
    public let blockchain: [String: AnyCodable]?

    /// Service health details
    public let services: [String: AnyCodable]?

    /// Network health details
    public let network: [String: AnyCodable]?

    /// Transaction backlog info
    public let backlog: [String: AnyCodable]?

    /// Error message if unhealthy
    public let error: String?

    /// Whether the node is healthy
    public var isHealthy: Bool {
        status.lowercased() == "healthy" || status.lowercased() == "ok"
    }
}

/// Blockchain synchronization status.
public struct SyncStatus: Codable, Sendable {
    /// Whether the node is currently syncing
    public let syncing: Bool

    /// Current block number
    public let currentBlock: Int?

    /// Highest known block number
    public let highestBlock: Int?

    /// Starting block when sync began
    public let startingBlock: Int?

    /// Sync progress percentage (0-100)
    public let syncProgress: Double?

    /// Whether the node is fully synced
    public var isSynced: Bool {
        !syncing
    }
}

/// Mempool information.
public struct MempoolInfo: Codable, Sendable {
    /// Number of pending transactions
    public let size: Int

    /// Total size in bytes
    public let bytes: Int

    /// Minimum fee rate for inclusion
    public let minFeeRate: String

    /// Maximum fee rate in mempool
    public let maxFeeRate: String

    /// Average fee rate
    public let avgFeeRate: String
}

/// Network information.
public struct NetworkInfo: Codable, Sendable {
    /// Network name
    public let name: String

    /// Chain ID
    public let chainId: String

    /// Current block height
    public let blockHeight: Int

    /// Number of connected peers
    public let peerCount: Int

    /// Network difficulty
    public let difficulty: String

    /// Network hashrate
    public let hashrate: String

    /// Average block time in seconds
    public let avgBlockTime: Double

    public init(
        name: String,
        chainId: String,
        blockHeight: Int,
        peerCount: Int,
        difficulty: String,
        hashrate: String,
        avgBlockTime: Double
    ) {
        self.name = name
        self.chainId = chainId
        self.blockHeight = blockHeight
        self.peerCount = peerCount
        self.difficulty = difficulty
        self.hashrate = hashrate
        self.avgBlockTime = avgBlockTime
    }
}

/// Blockchain statistics.
public struct BlockchainStats: Codable, Sendable {
    /// Total number of blocks
    public let totalBlocks: Int

    /// Total number of transactions
    public let totalTransactions: Int

    /// Total number of accounts
    public let totalAccounts: Int

    /// Current difficulty
    public let difficulty: String

    /// Current hashrate
    public let hashrate: String

    /// Average block time
    public let averageBlockTime: Double

    /// Total token supply
    public let totalSupply: String

    /// Network name
    public let network: String?

    /// Stats timestamp
    public let timestamp: Date?
}
