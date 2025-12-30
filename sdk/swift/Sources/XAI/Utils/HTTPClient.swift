import Foundation

/// HTTP client for making API requests to the XAI blockchain.
public actor HTTPClient {
    private let baseURL: URL
    private let apiKey: String?
    private let session: URLSession
    private let timeout: TimeInterval
    private let maxRetries: Int

    /// Creates a new HTTP client.
    /// - Parameters:
    ///   - baseURL: The base URL for API requests
    ///   - apiKey: Optional API key for authentication
    ///   - timeout: Request timeout in seconds (default: 30)
    ///   - maxRetries: Maximum number of retries for failed requests (default: 3)
    public init(
        baseURL: URL,
        apiKey: String? = nil,
        timeout: TimeInterval = 30,
        maxRetries: Int = 3
    ) {
        self.baseURL = baseURL
        self.apiKey = apiKey
        self.timeout = timeout
        self.maxRetries = maxRetries

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = timeout
        config.timeoutIntervalForResource = timeout * 2
        self.session = URLSession(configuration: config)
    }

    /// Performs a GET request.
    /// - Parameters:
    ///   - path: API endpoint path
    ///   - queryItems: Optional query parameters
    /// - Returns: Decoded response
    public func get<T: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        let request = try buildRequest(path: path, method: "GET", queryItems: queryItems)
        return try await execute(request)
    }

    /// Performs a POST request.
    /// - Parameters:
    ///   - path: API endpoint path
    ///   - body: Request body (Encodable)
    /// - Returns: Decoded response
    public func post<T: Decodable, B: Encodable>(
        _ path: String,
        body: B
    ) async throws -> T {
        var request = try buildRequest(path: path, method: "POST")
        request.httpBody = try JSONEncoder().encode(body)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return try await execute(request)
    }

    /// Performs a POST request with raw JSON data.
    /// - Parameters:
    ///   - path: API endpoint path
    ///   - json: Raw JSON dictionary
    /// - Returns: Decoded response
    public func post<T: Decodable>(
        _ path: String,
        json: [String: Any]
    ) async throws -> T {
        var request = try buildRequest(path: path, method: "POST")
        request.httpBody = try JSONSerialization.data(withJSONObject: json)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return try await execute(request)
    }

    /// Performs a DELETE request.
    /// - Parameter path: API endpoint path
    /// - Returns: Decoded response
    public func delete<T: Decodable>(_ path: String) async throws -> T {
        let request = try buildRequest(path: path, method: "DELETE")
        return try await execute(request)
    }

    // MARK: - Private Methods

    private func buildRequest(
        path: String,
        method: String,
        queryItems: [URLQueryItem]? = nil
    ) throws -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: true)
        components?.queryItems = queryItems

        guard let url = components?.url else {
            throw XAIError.invalidURL(path)
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let apiKey = apiKey {
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        }

        return request
    }

    private func execute<T: Decodable>(_ request: URLRequest) async throws -> T {
        var lastError: Error?

        for attempt in 0..<maxRetries {
            do {
                let (data, response) = try await session.data(for: request)

                guard let httpResponse = response as? HTTPURLResponse else {
                    throw XAIError.invalidResponse
                }

                try handleStatusCode(httpResponse.statusCode, data: data)

                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                decoder.dateDecodingStrategy = .iso8601

                return try decoder.decode(T.self, from: data)
            } catch let error as XAIError {
                // Don't retry client errors (4xx)
                if case .httpError(let code, _) = error, code >= 400 && code < 500 {
                    throw error
                }
                lastError = error
            } catch {
                lastError = error
            }

            // Exponential backoff
            if attempt < maxRetries - 1 {
                let delay = pow(2.0, Double(attempt)) * 0.5
                try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            }
        }

        throw lastError ?? XAIError.unknown
    }

    private func handleStatusCode(_ statusCode: Int, data: Data) throws {
        switch statusCode {
        case 200..<300:
            return
        case 400:
            let message = extractErrorMessage(from: data)
            throw XAIError.validationError(message)
        case 401:
            throw XAIError.authenticationError("Invalid or missing API key")
        case 403:
            throw XAIError.authorizationError("Insufficient permissions")
        case 404:
            throw XAIError.notFound("Resource not found")
        case 429:
            let retryAfter = extractRetryAfter(from: data)
            throw XAIError.rateLimitError(retryAfter: retryAfter)
        case 500..<600:
            let message = extractErrorMessage(from: data)
            throw XAIError.serverError(statusCode, message)
        default:
            let message = extractErrorMessage(from: data)
            throw XAIError.httpError(statusCode, message)
        }
    }

    private func extractErrorMessage(from data: Data) -> String {
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let message = json["message"] as? String ?? json["error"] as? String {
            return message
        }
        return String(data: data, encoding: .utf8) ?? "Unknown error"
    }

    private func extractRetryAfter(from data: Data) -> Int? {
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let retryAfter = json["retry_after"] as? Int {
            return retryAfter
        }
        return nil
    }
}
