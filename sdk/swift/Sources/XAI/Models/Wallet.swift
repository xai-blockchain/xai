import Foundation

/// Wallet type enumeration.
public enum WalletType: String, Codable, Sendable {
    case standard = "standard"
    case embedded = "embedded"
    case hardware = "hardware"
}

/// Represents a blockchain wallet.
public struct Wallet: Codable, Equatable, Sendable {
    /// Wallet address
    public let address: String

    /// Public key
    public let publicKey: String

    /// Creation timestamp
    public let createdAt: Date

    /// Wallet type
    public let walletType: WalletType

    /// Private key (only returned on creation, handle securely)
    public let privateKey: String?

    /// Current nonce
    public let nonce: Int

    /// Additional metadata
    public let metadata: [String: AnyCodable]?

    public init(
        address: String,
        publicKey: String,
        createdAt: Date,
        walletType: WalletType = .standard,
        privateKey: String? = nil,
        nonce: Int = 0,
        metadata: [String: AnyCodable]? = nil
    ) {
        self.address = address
        self.publicKey = publicKey
        self.createdAt = createdAt
        self.walletType = walletType
        self.privateKey = privateKey
        self.nonce = nonce
        self.metadata = metadata
    }

    /// Check if wallet address is valid
    public var isValid: Bool {
        !address.isEmpty && !publicKey.isEmpty
    }
}

/// Represents wallet balance information.
public struct Balance: Codable, Equatable, Sendable {
    /// Wallet address
    public let address: String

    /// Total balance
    public let balance: String

    /// Locked balance (staking, pending transactions)
    public let lockedBalance: String

    /// Available balance for transactions
    public let availableBalance: String

    /// Current nonce
    public let nonce: Int

    /// Last update timestamp
    public let lastUpdated: Date?

    public init(
        address: String,
        balance: String,
        lockedBalance: String = "0",
        availableBalance: String? = nil,
        nonce: Int = 0,
        lastUpdated: Date? = nil
    ) {
        self.address = address
        self.balance = balance
        self.lockedBalance = lockedBalance
        self.availableBalance = availableBalance ?? balance
        self.nonce = nonce
        self.lastUpdated = lastUpdated
    }
}

/// Represents an unspent transaction output.
public struct UTXO: Codable, Equatable, Sendable {
    /// Transaction hash
    public let txHash: String

    /// Output index
    public let outputIndex: Int

    /// Amount in the UTXO
    public let amount: String

    /// Script public key
    public let scriptPubKey: String

    /// Whether the UTXO is confirmed
    public let confirmed: Bool

    /// Block height where UTXO was created
    public let blockHeight: Int?

    public init(
        txHash: String,
        outputIndex: Int,
        amount: String,
        scriptPubKey: String,
        confirmed: Bool = false,
        blockHeight: Int? = nil
    ) {
        self.txHash = txHash
        self.outputIndex = outputIndex
        self.amount = amount
        self.scriptPubKey = scriptPubKey
        self.confirmed = confirmed
        self.blockHeight = blockHeight
    }
}

/// Unsigned transaction that needs to be signed before submission.
public struct UnsignedTransaction: Codable, Sendable {
    /// Transaction hash (before signing)
    public let hash: String

    /// Sender address
    public let from: String

    /// Recipient address
    public let to: String

    /// Amount to send
    public let amount: String

    /// Transaction fee
    public let fee: String

    /// Transaction nonce
    public let nonce: Int

    /// Raw transaction data to sign
    public let rawData: String

    public init(
        hash: String,
        from: String,
        to: String,
        amount: String,
        fee: String,
        nonce: Int,
        rawData: String
    ) {
        self.hash = hash
        self.from = from
        self.to = to
        self.amount = amount
        self.fee = fee
        self.nonce = nonce
        self.rawData = rawData
    }
}

/// Parameters for creating a wallet.
public struct CreateWalletParams: Codable, Sendable {
    public var walletType: WalletType
    public var name: String?

    public init(walletType: WalletType = .standard, name: String? = nil) {
        self.walletType = walletType
        self.name = name
    }
}

/// UTXO list response.
public struct UTXOListResponse: Codable, Sendable {
    public let utxos: [UTXO]
    public let total: Int
}
