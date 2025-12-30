import Foundation

/// Transaction status enumeration.
public enum TransactionStatus: String, Codable, Sendable {
    case pending = "pending"
    case confirmed = "confirmed"
    case failed = "failed"
}

/// Represents a blockchain transaction.
public struct Transaction: Codable, Equatable, Sendable {
    /// Transaction hash
    public let hash: String

    /// Sender address
    public let from: String

    /// Recipient address
    public let to: String

    /// Transaction amount
    public let amount: String

    /// Transaction timestamp
    public let timestamp: Date

    /// Transaction status
    public let status: TransactionStatus

    /// Transaction fee
    public let fee: String

    /// Gas limit
    public let gasLimit: String

    /// Gas used
    public let gasUsed: String

    /// Gas price
    public let gasPrice: String

    /// Transaction nonce
    public let nonce: Int

    /// Transaction data (for smart contracts)
    public let data: String?

    /// Block number where transaction was included
    public let blockNumber: Int?

    /// Block hash where transaction was included
    public let blockHash: String?

    /// Number of confirmations
    public let confirmations: Int

    /// Additional metadata
    public let metadata: [String: AnyCodable]?

    public init(
        hash: String,
        from: String,
        to: String,
        amount: String,
        timestamp: Date,
        status: TransactionStatus = .pending,
        fee: String = "0",
        gasLimit: String = "21000",
        gasUsed: String = "0",
        gasPrice: String = "0",
        nonce: Int = 0,
        data: String? = nil,
        blockNumber: Int? = nil,
        blockHash: String? = nil,
        confirmations: Int = 0,
        metadata: [String: AnyCodable]? = nil
    ) {
        self.hash = hash
        self.from = from
        self.to = to
        self.amount = amount
        self.timestamp = timestamp
        self.status = status
        self.fee = fee
        self.gasLimit = gasLimit
        self.gasUsed = gasUsed
        self.gasPrice = gasPrice
        self.nonce = nonce
        self.data = data
        self.blockNumber = blockNumber
        self.blockHash = blockHash
        self.confirmations = confirmations
        self.metadata = metadata
    }

    /// Check if transaction is confirmed
    public var isConfirmed: Bool {
        status == .confirmed
    }

    /// Check if transaction is pending
    public var isPending: Bool {
        status == .pending
    }

    /// Check if transaction failed
    public var isFailed: Bool {
        status == .failed
    }
}

/// Parameters for sending a transaction.
public struct SendTransactionParams: Codable, Sendable {
    public let from: String
    public let to: String
    public let amount: String
    public var data: String?
    public var gasLimit: String?
    public var gasPrice: String?
    public var nonce: Int?
    public var signature: String?

    public init(
        from: String,
        to: String,
        amount: String,
        data: String? = nil,
        gasLimit: String? = nil,
        gasPrice: String? = nil,
        nonce: Int? = nil,
        signature: String? = nil
    ) {
        self.from = from
        self.to = to
        self.amount = amount
        self.data = data
        self.gasLimit = gasLimit
        self.gasPrice = gasPrice
        self.nonce = nonce
        self.signature = signature
    }
}

/// Signed transaction ready for submission.
public struct SignedTransaction: Codable, Sendable {
    public let rawTransaction: String
    public let hash: String
    public let from: String
    public let to: String
    public let amount: String
    public let signature: String

    public init(
        rawTransaction: String,
        hash: String,
        from: String,
        to: String,
        amount: String,
        signature: String
    ) {
        self.rawTransaction = rawTransaction
        self.hash = hash
        self.from = from
        self.to = to
        self.amount = amount
        self.signature = signature
    }
}

/// Transaction result after submission.
public struct TransactionResult: Codable, Sendable {
    public let hash: String
    public let status: TransactionStatus
    public let blockNumber: Int?
    public let gasUsed: String?

    public init(
        hash: String,
        status: TransactionStatus,
        blockNumber: Int? = nil,
        gasUsed: String? = nil
    ) {
        self.hash = hash
        self.status = status
        self.blockNumber = blockNumber
        self.gasUsed = gasUsed
    }
}

/// Fee estimation response.
public struct FeeEstimation: Codable, Sendable {
    public let estimatedFee: String
    public let gasLimit: String
    public let gasPrice: String
    public let baseFee: String?
    public let priorityFee: String?
}

/// Transaction list response.
public struct TransactionListResponse: Codable, Sendable {
    public let transactions: [Transaction]
    public let total: Int
    public let limit: Int
    public let offset: Int
}
