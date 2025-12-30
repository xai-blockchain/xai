import Foundation

/// Errors that can occur when using the XAI SDK.
public enum XAIError: LocalizedError {
    /// Invalid URL was provided
    case invalidURL(String)

    /// Invalid response received from server
    case invalidResponse

    /// Authentication failed
    case authenticationError(String)

    /// User lacks required permissions
    case authorizationError(String)

    /// Input validation failed
    case validationError(String)

    /// Resource not found
    case notFound(String)

    /// Rate limit exceeded
    case rateLimitError(retryAfter: Int?)

    /// Server error occurred
    case serverError(Int, String)

    /// HTTP error with status code
    case httpError(Int, String)

    /// Network error
    case networkError(String)

    /// Timeout error
    case timeout

    /// Transaction-specific error
    case transactionError(String)

    /// Wallet-specific error
    case walletError(String)

    /// Blockchain-specific error
    case blockchainError(String)

    /// AI operation error
    case aiError(String)

    /// Unknown error
    case unknown

    public var errorDescription: String? {
        switch self {
        case .invalidURL(let path):
            return "Invalid URL: \(path)"
        case .invalidResponse:
            return "Invalid response received from server"
        case .authenticationError(let message):
            return "Authentication error: \(message)"
        case .authorizationError(let message):
            return "Authorization error: \(message)"
        case .validationError(let message):
            return "Validation error: \(message)"
        case .notFound(let message):
            return "Not found: \(message)"
        case .rateLimitError(let retryAfter):
            if let seconds = retryAfter {
                return "Rate limit exceeded. Retry after \(seconds) seconds"
            }
            return "Rate limit exceeded"
        case .serverError(let code, let message):
            return "Server error (\(code)): \(message)"
        case .httpError(let code, let message):
            return "HTTP error (\(code)): \(message)"
        case .networkError(let message):
            return "Network error: \(message)"
        case .timeout:
            return "Request timed out"
        case .transactionError(let message):
            return "Transaction error: \(message)"
        case .walletError(let message):
            return "Wallet error: \(message)"
        case .blockchainError(let message):
            return "Blockchain error: \(message)"
        case .aiError(let message):
            return "AI operation error: \(message)"
        case .unknown:
            return "An unknown error occurred"
        }
    }
}
