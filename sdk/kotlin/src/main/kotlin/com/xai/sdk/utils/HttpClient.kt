package com.xai.sdk.utils

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * HTTP client configuration
 */
data class HttpClientConfig(
    val baseUrl: String,
    val apiKey: String? = null,
    val timeout: Long = 30,
    val maxRetries: Int = 3,
    val retryDelay: Long = 500,
    val enableLogging: Boolean = false
)

/**
 * Internal HTTP client for making API requests
 */
class HttpClient(private val config: HttpClientConfig) {

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
        coerceInputValues = true
    }

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(config.timeout, TimeUnit.SECONDS)
        .readTimeout(config.timeout, TimeUnit.SECONDS)
        .writeTimeout(config.timeout, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val originalRequest = chain.request()
            val requestBuilder = originalRequest.newBuilder()
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .header("User-Agent", "XAI-SDK-Kotlin/1.0.0")

            config.apiKey?.let {
                requestBuilder.header("Authorization", "Bearer $it")
                requestBuilder.header("X-API-Key", it)
            }

            chain.proceed(requestBuilder.build())
        }
        .apply {
            if (config.enableLogging) {
                val loggingInterceptor = HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BODY
                }
                addInterceptor(loggingInterceptor)
            }
        }
        .build()

    /**
     * Perform a GET request
     */
    suspend inline fun <reified T> get(
        path: String,
        params: Map<String, Any?> = emptyMap()
    ): T = withContext(Dispatchers.IO) {
        val urlBuilder = StringBuilder(config.baseUrl).append(path)
        val filteredParams = params.filterValues { it != null }

        if (filteredParams.isNotEmpty()) {
            urlBuilder.append("?")
            urlBuilder.append(
                filteredParams.entries.joinToString("&") { (key, value) ->
                    "$key=${value.toString()}"
                }
            )
        }

        val request = Request.Builder()
            .url(urlBuilder.toString())
            .get()
            .build()

        executeWithRetry(request)
    }

    /**
     * Perform a POST request
     */
    suspend inline fun <reified T> post(
        path: String,
        body: Any? = null
    ): T = withContext(Dispatchers.IO) {
        val url = config.baseUrl + path
        val jsonBody = body?.let { json.encodeToString(it) } ?: "{}"
        val requestBody = jsonBody.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()

        executeWithRetry(request)
    }

    /**
     * Perform a PUT request
     */
    suspend inline fun <reified T> put(
        path: String,
        body: Any? = null
    ): T = withContext(Dispatchers.IO) {
        val url = config.baseUrl + path
        val jsonBody = body?.let { json.encodeToString(it) } ?: "{}"
        val requestBody = jsonBody.toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url(url)
            .put(requestBody)
            .build()

        executeWithRetry(request)
    }

    /**
     * Perform a DELETE request
     */
    suspend inline fun <reified T> delete(
        path: String
    ): T = withContext(Dispatchers.IO) {
        val url = config.baseUrl + path

        val request = Request.Builder()
            .url(url)
            .delete()
            .build()

        executeWithRetry(request)
    }

    /**
     * Execute request with retry logic
     */
    private suspend inline fun <reified T> executeWithRetry(request: Request): T {
        var lastException: Exception? = null
        var attempt = 0

        while (attempt < config.maxRetries) {
            try {
                return execute(request)
            } catch (e: NetworkException) {
                lastException = e
                attempt++
                if (attempt < config.maxRetries) {
                    kotlinx.coroutines.delay(config.retryDelay * attempt)
                }
            } catch (e: RateLimitException) {
                val waitTime = e.retryAfter ?: (config.retryDelay * attempt)
                attempt++
                if (attempt < config.maxRetries) {
                    kotlinx.coroutines.delay(waitTime)
                } else {
                    throw e
                }
            } catch (e: Exception) {
                throw e
            }
        }

        throw lastException ?: NetworkException("Request failed after ${config.maxRetries} attempts")
    }

    /**
     * Execute a single request
     */
    private inline fun <reified T> execute(request: Request): T {
        try {
            val response = client.newCall(request).execute()
            val responseBody = response.body?.string()

            when {
                response.isSuccessful -> {
                    return if (responseBody.isNullOrBlank()) {
                        throw APIException("Empty response body", response.code)
                    } else {
                        json.decodeFromString(responseBody)
                    }
                }
                response.code == 401 -> {
                    throw AuthenticationException("Authentication failed: ${response.message}")
                }
                response.code == 404 -> {
                    throw NotFoundException("Resource not found: ${request.url.encodedPath}")
                }
                response.code == 429 -> {
                    val retryAfter = response.header("Retry-After")?.toLongOrNull()
                    throw RateLimitException("Rate limit exceeded", retryAfter)
                }
                response.code in 500..599 -> {
                    throw APIException(
                        "Server error: ${response.message}",
                        response.code,
                        parseErrorCode(responseBody)
                    )
                }
                else -> {
                    throw APIException(
                        "API error: ${response.message}",
                        response.code,
                        parseErrorCode(responseBody)
                    )
                }
            }
        } catch (e: IOException) {
            throw NetworkException("Network error: ${e.message}", e)
        }
    }

    private fun parseErrorCode(responseBody: String?): String? {
        return try {
            responseBody?.let {
                val errorObj = json.decodeFromString<Map<String, String>>(it)
                errorObj["error_code"] ?: errorObj["code"]
            }
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Close the HTTP client
     */
    fun close() {
        client.dispatcher.executorService.shutdown()
        client.connectionPool.evictAll()
    }
}
