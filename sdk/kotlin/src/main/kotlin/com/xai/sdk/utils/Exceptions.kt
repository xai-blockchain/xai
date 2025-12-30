package com.xai.sdk.utils

/**
 * Base exception for all XAI SDK errors
 */
open class XAIException(
    message: String,
    cause: Throwable? = null
) : Exception(message, cause)

/**
 * Exception for API errors
 */
class APIException(
    message: String,
    val statusCode: Int = 0,
    val errorCode: String? = null,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for network errors
 */
class NetworkException(
    message: String,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for validation errors
 */
class ValidationException(
    message: String,
    val field: String? = null,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for wallet errors
 */
class WalletException(
    message: String,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for transaction errors
 */
class TransactionException(
    message: String,
    val txHash: String? = null,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for authentication errors
 */
class AuthenticationException(
    message: String,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for AI operation errors
 */
class AIException(
    message: String,
    val taskId: String? = null,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for timeout errors
 */
class TimeoutException(
    message: String,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for resource not found errors
 */
class NotFoundException(
    message: String,
    val resource: String? = null,
    cause: Throwable? = null
) : XAIException(message, cause)

/**
 * Exception for rate limiting errors
 */
class RateLimitException(
    message: String,
    val retryAfter: Long? = null,
    cause: Throwable? = null
) : XAIException(message, cause)
