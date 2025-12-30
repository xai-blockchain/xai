import Foundation

/// Client for blockchain block operations.
public struct BlocksClient: Sendable {
    private let httpClient: HTTPClient

    init(httpClient: HTTPClient) {
        self.httpClient = httpClient
    }

    /// Get a block by its hash.
    /// - Parameter hash: Block hash
    /// - Returns: Block details
    /// - Throws: `XAIError` if the request fails
    public func getBlock(hash: String) async throws -> Block {
        try await httpClient.get("/blocks/hash/\(hash)")
    }

    /// Get a block by its number.
    /// - Parameter number: Block number/height
    /// - Returns: Block details
    /// - Throws: `XAIError` if the request fails
    public func getBlock(number: Int) async throws -> Block {
        guard number >= 0 else {
            throw XAIError.validationError("Block number must be non-negative")
        }
        return try await httpClient.get("/blocks/\(number)")
    }

    /// Get a list of recent blocks.
    /// - Parameters:
    ///   - page: Page number (1-indexed)
    ///   - limit: Number of blocks per page (max 100)
    /// - Returns: List of blocks with pagination info
    /// - Throws: `XAIError` if the request fails
    public func getBlocks(page: Int = 1, limit: Int = 20) async throws -> BlockListResponse {
        let offset = (page - 1) * limit
        let queryItems = [
            URLQueryItem(name: "limit", value: String(min(limit, 100))),
            URLQueryItem(name: "offset", value: String(offset))
        ]
        return try await httpClient.get("/blocks", queryItems: queryItems)
    }

    /// Get the latest block.
    /// - Returns: The most recent block
    /// - Throws: `XAIError` if the request fails
    public func getLatestBlock() async throws -> Block {
        try await httpClient.get("/blocks/latest")
    }

    /// Get transactions in a specific block.
    /// - Parameter blockNumber: Block number
    /// - Returns: List of transaction hashes
    /// - Throws: `XAIError` if the request fails
    public func getBlockTransactions(blockNumber: Int) async throws -> [String] {
        struct Response: Decodable {
            let transactions: [String]
        }
        let response: Response = try await httpClient.get("/blocks/\(blockNumber)/transactions")
        return response.transactions
    }

    /// Get block by hash with full transaction details.
    /// - Parameter hash: Block hash
    /// - Returns: Block with transactions
    /// - Throws: `XAIError` if the request fails
    public func getBlockWithTransactions(hash: String) async throws -> (block: Block, transactions: [Transaction]) {
        struct Response: Decodable {
            let block: Block
            let transactions: [Transaction]
        }
        let response: Response = try await httpClient.get("/blocks/hash/\(hash)/full")
        return (response.block, response.transactions)
    }
}
