package com.xai.sdk.api

import com.xai.sdk.models.AIProvider
import com.xai.sdk.models.AITask
import com.xai.sdk.models.AITaskRequest
import com.xai.sdk.models.AITaskStatus
import com.xai.sdk.utils.AIException
import com.xai.sdk.utils.HttpClient
import com.xai.sdk.utils.TimeoutException
import com.xai.sdk.utils.ValidationException
import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable

/**
 * Client for AI operations
 *
 * Provides methods for submitting AI tasks, querying task status,
 * and listing available AI providers.
 *
 * Example:
 * ```kotlin
 * val client = XAIClient(baseUrl = "http://localhost:12001")
 * val task = client.ai.submitTask(
 *     AITaskRequest(
 *         type = "text_generation",
 *         prompt = "Analyze this transaction pattern..."
 *     )
 * )
 * val result = client.ai.waitForCompletion(task.id)
 * ```
 */
class AIClient internal constructor(private val httpClient: HttpClient) {

    @Serializable
    private data class TaskResponse(
        val id: String,
        val type: String,
        val status: AITaskStatus = AITaskStatus.PENDING,
        val created_at: String,
        val completed_at: String? = null,
        val result: Map<String, String>? = null,
        val error: String? = null,
        val progress: Int = 0
    )

    @Serializable
    private data class ProvidersResponse(
        val providers: List<ProviderItem>
    )

    @Serializable
    private data class ProviderItem(
        val id: String,
        val name: String,
        val description: String,
        val capabilities: List<String> = emptyList(),
        val models: List<String> = emptyList(),
        val price_per_token: String = "0",
        val available: Boolean = true
    )

    @Serializable
    private data class SubmitTaskRequest(
        val type: String,
        val prompt: String,
        val provider_id: String? = null,
        val model: String? = null,
        val parameters: Map<String, String> = emptyMap(),
        val max_tokens: Int? = null,
        val priority: String = "normal"
    )

    /**
     * Submit an AI task for processing
     *
     * @param request Task request with type, prompt, and parameters
     * @return Submitted task with ID for tracking
     * @throws ValidationException if request is invalid
     * @throws AIException if submission fails
     *
     * Example:
     * ```kotlin
     * val task = client.ai.submitTask(
     *     AITaskRequest(
     *         type = "smart_contract_audit",
     *         prompt = "Analyze this contract for vulnerabilities...",
     *         providerId = "openai",
     *         model = "gpt-4",
     *         maxTokens = 2000
     *     )
     * )
     * println("Task submitted: ${task.id}")
     * ```
     */
    suspend fun submitTask(request: AITaskRequest): AITask {
        validateTaskRequest(request)

        val submitRequest = SubmitTaskRequest(
            type = request.type,
            prompt = request.prompt,
            provider_id = request.providerId,
            model = request.model,
            parameters = request.parameters,
            max_tokens = request.maxTokens,
            priority = request.priority
        )

        val response: TaskResponse = httpClient.post("/ai/tasks", submitRequest)
        return response.toAITask()
    }

    /**
     * Get task status and result
     *
     * @param taskId Task ID
     * @return Current task status
     * @throws ValidationException if taskId is blank
     * @throws AIException if task not found
     *
     * Example:
     * ```kotlin
     * val task = client.ai.getTask("task-123")
     * when (task.status) {
     *     AITaskStatus.COMPLETED -> println("Result: ${task.result}")
     *     AITaskStatus.FAILED -> println("Error: ${task.error}")
     *     AITaskStatus.PROCESSING -> println("Progress: ${task.progress}%")
     *     else -> println("Waiting...")
     * }
     * ```
     */
    suspend fun getTask(taskId: String): AITask {
        if (taskId.isBlank()) {
            throw ValidationException("Task ID is required", "taskId")
        }

        val response: TaskResponse = httpClient.get("/ai/tasks/$taskId")
        return response.toAITask()
    }

    /**
     * List available AI providers
     *
     * @return List of available AI providers with their capabilities
     *
     * Example:
     * ```kotlin
     * val providers = client.ai.listProviders()
     * providers.forEach { provider ->
     *     println("${provider.name}: ${provider.capabilities.joinToString()}")
     * }
     * ```
     */
    suspend fun listProviders(): List<AIProvider> {
        val response: ProvidersResponse = httpClient.get("/ai/providers")
        return response.providers.map { provider ->
            AIProvider(
                id = provider.id,
                name = provider.name,
                description = provider.description,
                capabilities = provider.capabilities,
                models = provider.models,
                pricePerToken = provider.price_per_token,
                available = provider.available
            )
        }
    }

    /**
     * Get a specific AI provider by ID
     *
     * @param providerId Provider ID
     * @return Provider details
     * @throws ValidationException if providerId is blank
     *
     * Example:
     * ```kotlin
     * val provider = client.ai.getProvider("openai")
     * println("Models: ${provider.models.joinToString()}")
     * ```
     */
    suspend fun getProvider(providerId: String): AIProvider {
        if (providerId.isBlank()) {
            throw ValidationException("Provider ID is required", "providerId")
        }

        val response: ProviderItem = httpClient.get("/ai/providers/$providerId")
        return AIProvider(
            id = response.id,
            name = response.name,
            description = response.description,
            capabilities = response.capabilities,
            models = response.models,
            pricePerToken = response.price_per_token,
            available = response.available
        )
    }

    /**
     * Cancel a pending or processing task
     *
     * @param taskId Task ID to cancel
     * @return Cancelled task
     * @throws ValidationException if taskId is blank
     * @throws AIException if task cannot be cancelled
     *
     * Example:
     * ```kotlin
     * val cancelledTask = client.ai.cancelTask("task-123")
     * println("Task ${cancelledTask.id} cancelled")
     * ```
     */
    suspend fun cancelTask(taskId: String): AITask {
        if (taskId.isBlank()) {
            throw ValidationException("Task ID is required", "taskId")
        }

        val response: TaskResponse = httpClient.post("/ai/tasks/$taskId/cancel", null)
        return response.toAITask()
    }

    /**
     * Wait for task completion
     *
     * Polls the task status until it completes or fails.
     *
     * @param taskId Task ID to wait for
     * @param timeoutSeconds Maximum time to wait in seconds
     * @param pollIntervalSeconds Interval between status checks
     * @return Completed task with result
     * @throws TimeoutException if task doesn't complete in time
     * @throws AIException if task fails
     *
     * Example:
     * ```kotlin
     * val task = client.ai.submitTask(request)
     * try {
     *     val completedTask = client.ai.waitForCompletion(
     *         taskId = task.id,
     *         timeoutSeconds = 120
     *     )
     *     println("Result: ${completedTask.result}")
     * } catch (e: TimeoutException) {
     *     println("Task timed out")
     * }
     * ```
     */
    suspend fun waitForCompletion(
        taskId: String,
        timeoutSeconds: Int = 300,
        pollIntervalSeconds: Int = 2
    ): AITask {
        if (taskId.isBlank()) {
            throw ValidationException("Task ID is required", "taskId")
        }

        val startTime = System.currentTimeMillis()
        val timeoutMillis = timeoutSeconds * 1000L
        val pollIntervalMillis = pollIntervalSeconds * 1000L

        while (true) {
            val elapsed = System.currentTimeMillis() - startTime
            if (elapsed > timeoutMillis) {
                throw TimeoutException("Task completion timeout after $timeoutSeconds seconds")
            }

            val task = getTask(taskId)

            when (task.status) {
                AITaskStatus.COMPLETED -> return task
                AITaskStatus.FAILED -> throw AIException(
                    task.error ?: "Task failed",
                    taskId
                )
                AITaskStatus.PENDING, AITaskStatus.PROCESSING -> {
                    // Continue waiting
                }
            }

            delay(pollIntervalMillis)
        }
    }

    /**
     * Analyze blockchain data with AI
     *
     * @param query Analysis query
     * @param context Optional context data
     * @return Analysis result
     *
     * Example:
     * ```kotlin
     * val result = client.ai.analyzeBlockchain(
     *     query = "What patterns do you see in the last 100 transactions?",
     *     context = mapOf("address" to "0x1234...")
     * )
     * ```
     */
    suspend fun analyzeBlockchain(
        query: String,
        context: Map<String, String>? = null
    ): AITask {
        if (query.isBlank()) {
            throw ValidationException("Query is required", "query")
        }

        @Serializable
        data class AnalyzeRequest(
            val query: String,
            val context: Map<String, String>?
        )

        val response: TaskResponse = httpClient.post(
            "/personal-ai/analyze",
            AnalyzeRequest(query, context)
        )
        return response.toAITask()
    }

    /**
     * Analyze a wallet with AI
     *
     * @param address Wallet address to analyze
     * @return Analysis task
     *
     * Example:
     * ```kotlin
     * val analysis = client.ai.analyzeWallet("0x1234...")
     * val completed = client.ai.waitForCompletion(analysis.id)
     * println("Risk score: ${completed.result?.get("risk_score")}")
     * ```
     */
    suspend fun analyzeWallet(address: String): AITask {
        if (address.isBlank()) {
            throw ValidationException("Address is required", "address")
        }

        @Serializable
        data class WalletRequest(val address: String)

        val response: TaskResponse = httpClient.post(
            "/personal-ai/wallet/analyze",
            WalletRequest(address)
        )
        return response.toAITask()
    }

    /**
     * Optimize a transaction with AI
     *
     * @param transaction Transaction data to optimize
     * @param goals Optimization goals (e.g., "low_fee", "fast_confirmation")
     * @return Optimization result
     *
     * Example:
     * ```kotlin
     * val result = client.ai.optimizeTransaction(
     *     transaction = mapOf(
     *         "from" to "0x1234...",
     *         "to" to "0x5678...",
     *         "amount" to "1000"
     *     ),
     *     goals = listOf("low_fee")
     * )
     * ```
     */
    suspend fun optimizeTransaction(
        transaction: Map<String, String>,
        goals: List<String>? = null
    ): AITask {
        @Serializable
        data class OptimizeRequest(
            val transaction: Map<String, String>,
            val optimization_goals: List<String>?
        )

        val response: TaskResponse = httpClient.post(
            "/personal-ai/transaction/optimize",
            OptimizeRequest(transaction, goals)
        )
        return response.toAITask()
    }

    private fun validateTaskRequest(request: AITaskRequest) {
        if (request.type.isBlank()) {
            throw ValidationException("Task type is required", "type")
        }
        if (request.prompt.isBlank()) {
            throw ValidationException("Prompt is required", "prompt")
        }
        if (request.maxTokens != null && request.maxTokens <= 0) {
            throw ValidationException("Max tokens must be positive", "maxTokens")
        }
    }

    private fun TaskResponse.toAITask() = AITask(
        id = id,
        type = type,
        status = status,
        createdAt = created_at,
        completedAt = completed_at,
        result = result,
        error = error,
        progress = progress
    )
}
