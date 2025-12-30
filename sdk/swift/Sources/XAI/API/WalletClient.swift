import Foundation

/// Client for wallet operations.
public struct WalletClient: Sendable {
    private let httpClient: HTTPClient

    init(httpClient: HTTPClient) {
        self.httpClient = httpClient
    }

    /// Get wallet balance.
    /// - Parameter address: Wallet address
    /// - Returns: Balance information
    /// - Throws: `XAIError` if the request fails
    public func getBalance(address: String) async throws -> Balance {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        return try await httpClient.get("/wallet/\(address)/balance")
    }

    /// Get unspent transaction outputs (UTXOs) for an address.
    /// - Parameter address: Wallet address
    /// - Returns: List of UTXOs
    /// - Throws: `XAIError` if the request fails
    public func getUTXOs(address: String) async throws -> [UTXO] {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        let response: UTXOListResponse = try await httpClient.get("/wallet/\(address)/utxos")
        return response.utxos
    }

    /// Create an unsigned transaction.
    /// - Parameters:
    ///   - from: Sender address
    ///   - to: Recipient address
    ///   - amount: Amount to send
    /// - Returns: Unsigned transaction ready for signing
    /// - Throws: `XAIError` if the request fails
    public func createTransaction(from: String, to: String, amount: String) async throws -> UnsignedTransaction {
        guard !from.isEmpty && !to.isEmpty && !amount.isEmpty else {
            throw XAIError.validationError("from, to, and amount are required")
        }

        struct CreateTxRequest: Encodable {
            let from: String
            let to: String
            let amount: String
        }

        return try await httpClient.post(
            "/wallet/create-transaction",
            body: CreateTxRequest(from: from, to: to, amount: amount)
        )
    }

    /// Get wallet information.
    /// - Parameter address: Wallet address
    /// - Returns: Wallet details
    /// - Throws: `XAIError` if the request fails
    public func getWallet(address: String) async throws -> Wallet {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        return try await httpClient.get("/wallet/\(address)")
    }

    /// Create a new wallet.
    /// - Parameter params: Wallet creation parameters
    /// - Returns: Created wallet (includes private key - store securely!)
    /// - Throws: `XAIError` if the request fails
    public func createWallet(params: CreateWalletParams = CreateWalletParams()) async throws -> Wallet {
        try await httpClient.post("/wallet/create", body: params)
    }

    /// Get transaction history for a wallet.
    /// - Parameters:
    ///   - address: Wallet address
    ///   - page: Page number (1-indexed)
    ///   - limit: Number of transactions per page (max 100)
    /// - Returns: Transaction history with pagination info
    /// - Throws: `XAIError` if the request fails
    public func getTransactions(address: String, page: Int = 1, limit: Int = 50) async throws -> TransactionListResponse {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        let offset = (page - 1) * limit
        let queryItems = [
            URLQueryItem(name: "limit", value: String(min(limit, 100))),
            URLQueryItem(name: "offset", value: String(offset))
        ]
        return try await httpClient.get("/wallet/\(address)/transactions", queryItems: queryItems)
    }

    /// Get wallet nonce (transaction count).
    /// - Parameter address: Wallet address
    /// - Returns: Current nonce
    /// - Throws: `XAIError` if the request fails
    public func getNonce(address: String) async throws -> Int {
        let balance = try await getBalance(address: address)
        return balance.nonce
    }

    /// Validate a wallet address format.
    /// - Parameter address: Address to validate
    /// - Returns: True if address format is valid
    public func validateAddress(_ address: String) -> Bool {
        // Basic validation - XAI addresses should start with "XAI" and be 42 chars
        // or follow standard hex format (0x prefix + 40 hex chars)
        if address.hasPrefix("XAI") && address.count == 42 {
            return true
        }
        if address.hasPrefix("0x") && address.count == 42 {
            let hexPart = address.dropFirst(2)
            return hexPart.allSatisfy { $0.isHexDigit }
        }
        return false
    }
}
