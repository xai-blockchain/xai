import Foundation

/// Represents a blockchain block.
public struct Block: Codable, Equatable, Sendable {
    /// Block number/height
    public let number: Int

    /// Block hash
    public let hash: String

    /// Parent block hash
    public let parentHash: String

    /// Block timestamp (Unix timestamp)
    public let timestamp: Int

    /// Miner address
    public let miner: String

    /// Block difficulty
    public let difficulty: String

    /// Gas limit for the block
    public let gasLimit: String

    /// Gas used in the block
    public let gasUsed: String

    /// Number of transactions in the block
    public let transactions: Int

    /// Transaction hashes in this block
    public let transactionHashes: [String]?

    /// Additional metadata
    public let metadata: [String: AnyCodable]?

    public init(
        number: Int,
        hash: String,
        parentHash: String,
        timestamp: Int,
        miner: String,
        difficulty: String,
        gasLimit: String = "0",
        gasUsed: String = "0",
        transactions: Int = 0,
        transactionHashes: [String]? = nil,
        metadata: [String: AnyCodable]? = nil
    ) {
        self.number = number
        self.hash = hash
        self.parentHash = parentHash
        self.timestamp = timestamp
        self.miner = miner
        self.difficulty = difficulty
        self.gasLimit = gasLimit
        self.gasUsed = gasUsed
        self.transactions = transactions
        self.transactionHashes = transactionHashes
        self.metadata = metadata
    }

    /// Block creation date
    public var date: Date {
        Date(timeIntervalSince1970: TimeInterval(timestamp))
    }
}

/// Response for listing blocks
public struct BlockListResponse: Codable, Sendable {
    public let blocks: [Block]
    public let total: Int
    public let limit: Int
    public let offset: Int
}
