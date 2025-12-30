import Foundation

/// Client for transaction operations.
public struct TransactionsClient: Sendable {
    private let httpClient: HTTPClient

    init(httpClient: HTTPClient) {
        self.httpClient = httpClient
    }

    /// Get a transaction by its hash.
    /// - Parameter txid: Transaction hash
    /// - Returns: Transaction details
    /// - Throws: `XAIError` if the request fails
    public func getTransaction(txid: String) async throws -> Transaction {
        guard !txid.isEmpty else {
            throw XAIError.validationError("Transaction ID is required")
        }
        return try await httpClient.get("/transaction/\(txid)")
    }

    /// Send a signed transaction to the network.
    /// - Parameter signedTransaction: The signed transaction
    /// - Returns: Transaction result with hash and status
    /// - Throws: `XAIError` if the request fails
    public func sendTransaction(_ signedTransaction: SignedTransaction) async throws -> TransactionResult {
        try await httpClient.post("/transaction/send", body: signedTransaction)
    }

    /// Send a transaction using parameters.
    /// - Parameter params: Transaction parameters
    /// - Returns: Transaction result
    /// - Throws: `XAIError` if the request fails
    public func sendTransaction(_ params: SendTransactionParams) async throws -> TransactionResult {
        guard !params.from.isEmpty && !params.to.isEmpty && !params.amount.isEmpty else {
            throw XAIError.validationError("from, to, and amount are required")
        }
        return try await httpClient.post("/transaction/send", body: params)
    }

    /// Get transactions for a specific address.
    /// - Parameters:
    ///   - address: Wallet address
    ///   - page: Page number (1-indexed)
    ///   - limit: Number of transactions per page (max 100)
    /// - Returns: List of transactions with pagination info
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

    /// Get pending transactions for an address.
    /// - Parameter address: Wallet address
    /// - Returns: List of pending transactions
    /// - Throws: `XAIError` if the request fails
    public func getPendingTransactions(address: String) async throws -> [Transaction] {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        let queryItems = [URLQueryItem(name: "status", value: "pending")]
        let response: TransactionListResponse = try await httpClient.get(
            "/wallet/\(address)/transactions",
            queryItems: queryItems
        )
        return response.transactions
    }

    /// Get transaction status.
    /// - Parameter txid: Transaction hash
    /// - Returns: Transaction status information
    /// - Throws: `XAIError` if the request fails
    public func getTransactionStatus(txid: String) async throws -> TransactionStatus {
        struct Response: Decodable {
            let status: TransactionStatus
        }
        let response: Response = try await httpClient.get("/transaction/\(txid)/status")
        return response.status
    }

    /// Estimate the fee for a transaction.
    /// - Parameter params: Transaction parameters
    /// - Returns: Fee estimation details
    /// - Throws: `XAIError` if the request fails
    public func estimateFee(_ params: SendTransactionParams) async throws -> FeeEstimation {
        try await httpClient.post("/transaction/estimate-fee", body: params)
    }

    /// Check if a transaction has the required number of confirmations.
    /// - Parameters:
    ///   - txid: Transaction hash
    ///   - confirmations: Required number of confirmations
    /// - Returns: True if transaction has enough confirmations
    /// - Throws: `XAIError` if the request fails
    public func isConfirmed(txid: String, confirmations: Int = 1) async throws -> Bool {
        let transaction = try await getTransaction(txid: txid)
        return transaction.confirmations >= confirmations
    }

    /// Wait for a transaction to be confirmed.
    /// - Parameters:
    ///   - txid: Transaction hash
    ///   - confirmations: Required number of confirmations
    ///   - timeout: Maximum time to wait in seconds
    ///   - pollInterval: Time between status checks in seconds
    /// - Returns: Confirmed transaction
    /// - Throws: `XAIError` if confirmation times out or fails
    public func waitForConfirmation(
        txid: String,
        confirmations: Int = 1,
        timeout: TimeInterval = 600,
        pollInterval: TimeInterval = 5
    ) async throws -> Transaction {
        let startTime = Date()

        while Date().timeIntervalSince(startTime) < timeout {
            let transaction = try await getTransaction(txid: txid)

            if transaction.confirmations >= confirmations {
                return transaction
            }

            if transaction.status == .failed {
                throw XAIError.transactionError("Transaction failed")
            }

            try await Task.sleep(nanoseconds: UInt64(pollInterval * 1_000_000_000))
        }

        throw XAIError.timeout
    }
}
