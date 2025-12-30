import Foundation

/// Status of an AI task.
public enum AITaskStatus: String, Codable, Sendable {
    case pending = "pending"
    case processing = "processing"
    case completed = "completed"
    case failed = "failed"
}

/// Type of AI task.
public enum AITaskType: String, Codable, Sendable {
    case analysis = "analysis"
    case optimization = "optimization"
    case generation = "generation"
    case prediction = "prediction"
}

/// Represents an AI task submitted to the network.
public struct AITask: Codable, Equatable, Sendable {
    /// Unique task identifier
    public let id: String

    /// Task type
    public let type: AITaskType

    /// Current status
    public let status: AITaskStatus

    /// Task description or prompt
    public let prompt: String

    /// Task result (when completed)
    public let result: [String: AnyCodable]?

    /// Creation timestamp
    public let createdAt: Date

    /// Completion timestamp
    public let completedAt: Date?

    /// Provider that processed the task
    public let providerId: String?

    /// Computation cost
    public let cost: String?

    /// Error message if failed
    public let error: String?

    public init(
        id: String,
        type: AITaskType,
        status: AITaskStatus,
        prompt: String,
        result: [String: AnyCodable]? = nil,
        createdAt: Date,
        completedAt: Date? = nil,
        providerId: String? = nil,
        cost: String? = nil,
        error: String? = nil
    ) {
        self.id = id
        self.type = type
        self.status = status
        self.prompt = prompt
        self.result = result
        self.createdAt = createdAt
        self.completedAt = completedAt
        self.providerId = providerId
        self.cost = cost
        self.error = error
    }

    /// Check if task is completed
    public var isCompleted: Bool {
        status == .completed
    }

    /// Check if task is still processing
    public var isProcessing: Bool {
        status == .pending || status == .processing
    }
}

/// Request parameters for submitting an AI task.
public struct AITaskRequest: Codable, Sendable {
    /// Task type
    public let type: AITaskType

    /// Task prompt or description
    public let prompt: String

    /// Maximum cost willing to pay
    public var maxCost: String?

    /// Preferred provider ID
    public var preferredProvider: String?

    /// Additional parameters
    public var parameters: [String: AnyCodable]?

    /// Priority level (1-10)
    public var priority: Int?

    public init(
        type: AITaskType,
        prompt: String,
        maxCost: String? = nil,
        preferredProvider: String? = nil,
        parameters: [String: AnyCodable]? = nil,
        priority: Int? = nil
    ) {
        self.type = type
        self.prompt = prompt
        self.maxCost = maxCost
        self.preferredProvider = preferredProvider
        self.parameters = parameters
        self.priority = priority
    }
}

/// Represents an AI compute provider on the network.
public struct AIProvider: Codable, Equatable, Sendable {
    /// Provider unique identifier
    public let id: String

    /// Provider name
    public let name: String

    /// Provider description
    public let description: String

    /// Provider capabilities
    public let capabilities: [String]

    /// Price per computation unit
    public let pricePerUnit: String

    /// Availability status
    public let available: Bool

    /// Provider reputation score (0-100)
    public let reputation: Int

    /// Total tasks completed
    public let tasksCompleted: Int

    /// Average response time in seconds
    public let avgResponseTime: Double

    public init(
        id: String,
        name: String,
        description: String,
        capabilities: [String],
        pricePerUnit: String,
        available: Bool,
        reputation: Int,
        tasksCompleted: Int,
        avgResponseTime: Double
    ) {
        self.id = id
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.pricePerUnit = pricePerUnit
        self.available = available
        self.reputation = reputation
        self.tasksCompleted = tasksCompleted
        self.avgResponseTime = avgResponseTime
    }
}

/// Response for listing AI providers.
public struct AIProviderListResponse: Codable, Sendable {
    public let providers: [AIProvider]
    public let total: Int
}

/// Response for listing AI tasks.
public struct AITaskListResponse: Codable, Sendable {
    public let tasks: [AITask]
    public let total: Int
    public let limit: Int
    public let offset: Int
}
