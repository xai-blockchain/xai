import Foundation

/// Client for AI operations on the XAI blockchain.
public struct AIClient: Sendable {
    private let httpClient: HTTPClient

    init(httpClient: HTTPClient) {
        self.httpClient = httpClient
    }

    /// Submit an AI task to the network.
    /// - Parameter request: Task request parameters
    /// - Returns: Created AI task
    /// - Throws: `XAIError` if the request fails
    public func submitTask(_ request: AITaskRequest) async throws -> AITask {
        try await httpClient.post("/ai/tasks", body: request)
    }

    /// Get an AI task by its ID.
    /// - Parameter taskId: Task identifier
    /// - Returns: Task details
    /// - Throws: `XAIError` if the request fails
    public func getTask(taskId: String) async throws -> AITask {
        guard !taskId.isEmpty else {
            throw XAIError.validationError("Task ID is required")
        }
        return try await httpClient.get("/ai/tasks/\(taskId)")
    }

    /// List available AI providers.
    /// - Returns: List of AI providers
    /// - Throws: `XAIError` if the request fails
    public func listProviders() async throws -> [AIProvider] {
        let response: AIProviderListResponse = try await httpClient.get("/ai/providers")
        return response.providers
    }

    /// Get a specific AI provider.
    /// - Parameter providerId: Provider identifier
    /// - Returns: Provider details
    /// - Throws: `XAIError` if the request fails
    public func getProvider(providerId: String) async throws -> AIProvider {
        guard !providerId.isEmpty else {
            throw XAIError.validationError("Provider ID is required")
        }
        return try await httpClient.get("/ai/providers/\(providerId)")
    }

    /// List tasks submitted by the current user.
    /// - Parameters:
    ///   - status: Filter by status (optional)
    ///   - page: Page number (1-indexed)
    ///   - limit: Number of tasks per page
    /// - Returns: List of tasks with pagination info
    /// - Throws: `XAIError` if the request fails
    public func listTasks(
        status: AITaskStatus? = nil,
        page: Int = 1,
        limit: Int = 20
    ) async throws -> AITaskListResponse {
        var queryItems = [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String((page - 1) * limit))
        ]
        if let status = status {
            queryItems.append(URLQueryItem(name: "status", value: status.rawValue))
        }
        return try await httpClient.get("/ai/tasks", queryItems: queryItems)
    }

    /// Cancel a pending AI task.
    /// - Parameter taskId: Task identifier
    /// - Returns: Updated task
    /// - Throws: `XAIError` if the request fails
    public func cancelTask(taskId: String) async throws -> AITask {
        guard !taskId.isEmpty else {
            throw XAIError.validationError("Task ID is required")
        }
        return try await httpClient.post("/ai/tasks/\(taskId)/cancel", body: EmptyBody())
    }

    /// Wait for an AI task to complete.
    /// - Parameters:
    ///   - taskId: Task identifier
    ///   - timeout: Maximum time to wait in seconds
    ///   - pollInterval: Time between status checks in seconds
    /// - Returns: Completed task
    /// - Throws: `XAIError` if task fails or times out
    public func waitForCompletion(
        taskId: String,
        timeout: TimeInterval = 300,
        pollInterval: TimeInterval = 2
    ) async throws -> AITask {
        let startTime = Date()

        while Date().timeIntervalSince(startTime) < timeout {
            let task = try await getTask(taskId: taskId)

            switch task.status {
            case .completed:
                return task
            case .failed:
                throw XAIError.aiError(task.error ?? "Task failed")
            case .pending, .processing:
                try await Task.sleep(nanoseconds: UInt64(pollInterval * 1_000_000_000))
            }
        }

        throw XAIError.timeout
    }

    /// Analyze a wallet using AI.
    /// - Parameter address: Wallet address to analyze
    /// - Returns: Analysis result
    /// - Throws: `XAIError` if the request fails
    public func analyzeWallet(address: String) async throws -> [String: AnyCodable] {
        guard !address.isEmpty else {
            throw XAIError.validationError("Address is required")
        }
        return try await httpClient.post("/personal-ai/wallet/analyze", json: ["address": address])
    }

    /// Analyze blockchain data with a custom query.
    /// - Parameters:
    ///   - query: Analysis query or question
    ///   - context: Optional additional context
    /// - Returns: Analysis result
    /// - Throws: `XAIError` if the request fails
    public func analyzeBlockchain(query: String, context: [String: Any]? = nil) async throws -> [String: AnyCodable] {
        var payload: [String: Any] = ["query": query]
        if let context = context {
            payload["context"] = context
        }
        return try await httpClient.post("/personal-ai/analyze", json: payload)
    }

    /// Optimize a transaction using AI.
    /// - Parameters:
    ///   - transaction: Transaction parameters to optimize
    ///   - goals: Optimization goals (e.g., ["low_fee", "fast_confirmation"])
    /// - Returns: Optimized transaction details
    /// - Throws: `XAIError` if the request fails
    public func optimizeTransaction(
        transaction: [String: Any],
        goals: [String]? = nil
    ) async throws -> [String: AnyCodable] {
        var payload: [String: Any] = ["transaction": transaction]
        if let goals = goals {
            payload["optimization_goals"] = goals
        }
        return try await httpClient.post("/personal-ai/transaction/optimize", json: payload)
    }

    /// Get node setup recommendations from AI.
    /// - Parameters:
    ///   - hardwareSpecs: Optional hardware specifications
    ///   - useCase: Optional use case (e.g., "mining", "validator", "archive")
    /// - Returns: Setup recommendations
    /// - Throws: `XAIError` if the request fails
    public func nodeSetupRecommendations(
        hardwareSpecs: [String: Any]? = nil,
        useCase: String? = nil
    ) async throws -> [String: AnyCodable] {
        var payload: [String: Any] = [:]
        if let hardwareSpecs = hardwareSpecs {
            payload["hardware_specs"] = hardwareSpecs
        }
        if let useCase = useCase {
            payload["use_case"] = useCase
        }
        return try await httpClient.post("/personal-ai/node/setup", json: payload)
    }
}

// Helper for empty POST body
private struct EmptyBody: Encodable {}
