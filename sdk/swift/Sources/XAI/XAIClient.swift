import Foundation

/// Configuration options for the XAI client.
public struct XAIClientConfig: Sendable {
    /// Base URL for API requests
    public let baseURL: URL

    /// API key for authentication
    public let apiKey: String?

    /// Request timeout in seconds
    public let timeout: TimeInterval

    /// Maximum number of retries for failed requests
    public let maxRetries: Int

    /// Creates a new configuration.
    /// - Parameters:
    ///   - baseURL: Base URL for API requests (default: http://localhost:12001)
    ///   - apiKey: Optional API key for authentication
    ///   - timeout: Request timeout in seconds (default: 30)
    ///   - maxRetries: Maximum retries for failed requests (default: 3)
    public init(
        baseURL: String = "http://localhost:12001",
        apiKey: String? = nil,
        timeout: TimeInterval = 30,
        maxRetries: Int = 3
    ) {
        self.baseURL = URL(string: baseURL)!
        self.apiKey = apiKey
        self.timeout = timeout
        self.maxRetries = maxRetries
    }
}

/// Main client for XAI blockchain operations.
///
/// Provides unified interface to wallet, transaction, blockchain,
/// staking, and AI operations.
///
/// ## Example
/// ```swift
/// let client = XAIClient(baseURL: "http://localhost:12001", apiKey: "your-api-key")
///
/// // Get balance
/// let balance = try await client.wallet.getBalance(address: "XAI...")
/// print("Balance: \(balance.balance)")
///
/// // Get latest block
/// let block = try await client.blocks.getLatestBlock()
/// print("Latest block: \(block.number)")
///
/// // Submit AI task
/// let task = try await client.ai.submitTask(AITaskRequest(
///     type: .analysis,
///     prompt: "Analyze transaction patterns"
/// ))
/// ```
public final class XAIClient: Sendable {
    private let httpClient: HTTPClient

    /// Client for block operations
    public let blocks: BlocksClient

    /// Client for transaction operations
    public let transactions: TransactionsClient

    /// Client for wallet operations
    public let wallet: WalletClient

    /// Client for AI operations
    public let ai: AIClient

    /// Client for staking operations
    public let staking: StakingClient

    /// Creates a new XAI client with URL and API key.
    /// - Parameters:
    ///   - baseURL: Base URL for API requests
    ///   - apiKey: Optional API key for authentication
    public convenience init(baseURL: String = "http://localhost:12001", apiKey: String? = nil) {
        self.init(config: XAIClientConfig(baseURL: baseURL, apiKey: apiKey))
    }

    /// Creates a new XAI client with configuration.
    /// - Parameter config: Client configuration
    public init(config: XAIClientConfig) {
        self.httpClient = HTTPClient(
            baseURL: config.baseURL,
            apiKey: config.apiKey,
            timeout: config.timeout,
            maxRetries: config.maxRetries
        )

        self.blocks = BlocksClient(httpClient: httpClient)
        self.transactions = TransactionsClient(httpClient: httpClient)
        self.wallet = WalletClient(httpClient: httpClient)
        self.ai = AIClient(httpClient: httpClient)
        self.staking = StakingClient(httpClient: httpClient)
    }

    /// Performs a health check on the API.
    /// - Returns: Health check response
    /// - Throws: `XAIError` if the request fails
    public func healthCheck() async throws -> HealthCheckResponse {
        try await httpClient.get("/health")
    }

    /// Gets blockchain node information.
    /// - Returns: Node information
    /// - Throws: `XAIError` if the request fails
    public func getInfo() async throws -> NodeInfo {
        try await httpClient.get("/")
    }

    /// Gets blockchain synchronization status.
    /// - Returns: Sync status
    /// - Throws: `XAIError` if the request fails
    public func getSyncStatus() async throws -> SyncStatus {
        try await httpClient.get("/sync")
    }

    /// Gets blockchain statistics.
    /// - Returns: Blockchain stats
    /// - Throws: `XAIError` if the request fails
    public func getStats() async throws -> BlockchainStats {
        try await httpClient.get("/stats")
    }

    /// Gets mempool information.
    /// - Returns: Mempool info
    /// - Throws: `XAIError` if the request fails
    public func getMempoolInfo() async throws -> MempoolInfo {
        try await httpClient.get("/mempool")
    }

    /// Gets network information.
    /// - Returns: Network info
    /// - Throws: `XAIError` if the request fails
    public func getNetworkInfo() async throws -> NetworkInfo {
        try await httpClient.get("/network")
    }

    /// Checks if the blockchain is fully synced.
    /// - Returns: True if synced
    /// - Throws: `XAIError` if the request fails
    public func isSynced() async throws -> Bool {
        let status = try await getSyncStatus()
        return status.isSynced
    }
}

// MARK: - Convenience Extensions

extension XAIClient {
    /// Quick access to balance for an address.
    /// - Parameter address: Wallet address
    /// - Returns: Balance information
    public func balance(for address: String) async throws -> Balance {
        try await wallet.getBalance(address: address)
    }

    /// Quick access to latest block.
    /// - Returns: Latest block
    public func latestBlock() async throws -> Block {
        try await blocks.getLatestBlock()
    }

    /// Quick access to transaction.
    /// - Parameter txid: Transaction hash
    /// - Returns: Transaction details
    public func transaction(_ txid: String) async throws -> Transaction {
        try await transactions.getTransaction(txid: txid)
    }
}
