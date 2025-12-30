import XCTest
@testable import XAI

final class XAIClientTests: XCTestCase {

    // MARK: - Client Initialization Tests

    func testClientInitializationWithDefaults() {
        let client = XAIClient()
        XCTAssertNotNil(client.blocks)
        XCTAssertNotNil(client.transactions)
        XCTAssertNotNil(client.wallet)
        XCTAssertNotNil(client.ai)
        XCTAssertNotNil(client.staking)
    }

    func testClientInitializationWithConfig() {
        let config = XAIClientConfig(
            baseURL: "https://api.xai-blockchain.io",
            apiKey: "test-api-key",
            timeout: 60,
            maxRetries: 5
        )
        let client = XAIClient(config: config)
        XCTAssertNotNil(client)
    }

    func testClientInitializationWithURLAndKey() {
        let client = XAIClient(baseURL: "http://localhost:5000", apiKey: "my-key")
        XCTAssertNotNil(client)
    }

    // MARK: - Config Tests

    func testConfigDefaults() {
        let config = XAIClientConfig()
        XCTAssertEqual(config.baseURL.absoluteString, "http://localhost:12001")
        XCTAssertNil(config.apiKey)
        XCTAssertEqual(config.timeout, 30)
        XCTAssertEqual(config.maxRetries, 3)
    }

    func testConfigCustomValues() {
        let config = XAIClientConfig(
            baseURL: "https://custom.api.com",
            apiKey: "secret-key",
            timeout: 120,
            maxRetries: 10
        )
        XCTAssertEqual(config.baseURL.absoluteString, "https://custom.api.com")
        XCTAssertEqual(config.apiKey, "secret-key")
        XCTAssertEqual(config.timeout, 120)
        XCTAssertEqual(config.maxRetries, 10)
    }
}

// MARK: - Model Tests

final class ModelTests: XCTestCase {

    func testBlockInitialization() {
        let block = Block(
            number: 12345,
            hash: "0xabc123",
            parentHash: "0xdef456",
            timestamp: 1704067200,
            miner: "XAI1abc...",
            difficulty: "12345678"
        )

        XCTAssertEqual(block.number, 12345)
        XCTAssertEqual(block.hash, "0xabc123")
        XCTAssertEqual(block.parentHash, "0xdef456")
        XCTAssertEqual(block.timestamp, 1704067200)
        XCTAssertEqual(block.miner, "XAI1abc...")
        XCTAssertEqual(block.difficulty, "12345678")
        XCTAssertEqual(block.transactions, 0)
    }

    func testBlockDateConversion() {
        let block = Block(
            number: 1,
            hash: "0x1",
            parentHash: "0x0",
            timestamp: 1704067200, // Jan 1, 2024 00:00:00 UTC
            miner: "XAI1...",
            difficulty: "1"
        )

        let date = block.date
        let calendar = Calendar(identifier: .gregorian)
        let components = calendar.dateComponents(in: TimeZone(identifier: "UTC")!, from: date)
        XCTAssertEqual(components.year, 2024)
        XCTAssertEqual(components.month, 1)
        XCTAssertEqual(components.day, 1)
    }

    func testTransactionStatus() {
        let pendingTx = Transaction(
            hash: "0x1",
            from: "XAI1...",
            to: "XAI2...",
            amount: "1000",
            timestamp: Date(),
            status: .pending
        )
        XCTAssertTrue(pendingTx.isPending)
        XCTAssertFalse(pendingTx.isConfirmed)
        XCTAssertFalse(pendingTx.isFailed)

        let confirmedTx = Transaction(
            hash: "0x2",
            from: "XAI1...",
            to: "XAI2...",
            amount: "1000",
            timestamp: Date(),
            status: .confirmed,
            confirmations: 10
        )
        XCTAssertFalse(confirmedTx.isPending)
        XCTAssertTrue(confirmedTx.isConfirmed)
        XCTAssertFalse(confirmedTx.isFailed)

        let failedTx = Transaction(
            hash: "0x3",
            from: "XAI1...",
            to: "XAI2...",
            amount: "1000",
            timestamp: Date(),
            status: .failed
        )
        XCTAssertFalse(failedTx.isPending)
        XCTAssertFalse(failedTx.isConfirmed)
        XCTAssertTrue(failedTx.isFailed)
    }

    func testWalletValidity() {
        let validWallet = Wallet(
            address: "XAI1abc123def456ghi789jkl012mno345p",
            publicKey: "04abc123...",
            createdAt: Date()
        )
        XCTAssertTrue(validWallet.isValid)

        let invalidWallet = Wallet(
            address: "",
            publicKey: "",
            createdAt: Date()
        )
        XCTAssertFalse(invalidWallet.isValid)
    }

    func testBalanceDefaults() {
        let balance = Balance(
            address: "XAI1...",
            balance: "1000000"
        )
        XCTAssertEqual(balance.lockedBalance, "0")
        XCTAssertEqual(balance.availableBalance, "1000000")
        XCTAssertEqual(balance.nonce, 0)
    }

    func testAITaskStatus() {
        let pendingTask = AITask(
            id: "task-1",
            type: .analysis,
            status: .pending,
            prompt: "Analyze",
            createdAt: Date()
        )
        XCTAssertTrue(pendingTask.isProcessing)
        XCTAssertFalse(pendingTask.isCompleted)

        let completedTask = AITask(
            id: "task-2",
            type: .analysis,
            status: .completed,
            prompt: "Analyze",
            createdAt: Date()
        )
        XCTAssertFalse(completedTask.isProcessing)
        XCTAssertTrue(completedTask.isCompleted)
    }

    func testAITaskRequest() {
        let request = AITaskRequest(
            type: .analysis,
            prompt: "Analyze transaction patterns",
            maxCost: "100",
            priority: 5
        )
        XCTAssertEqual(request.type, .analysis)
        XCTAssertEqual(request.prompt, "Analyze transaction patterns")
        XCTAssertEqual(request.maxCost, "100")
        XCTAssertEqual(request.priority, 5)
    }
}

// MARK: - Error Tests

final class ErrorTests: XCTestCase {

    func testErrorDescriptions() {
        let invalidURL = XAIError.invalidURL("/bad/path")
        XCTAssertTrue(invalidURL.errorDescription?.contains("Invalid URL") ?? false)

        let authError = XAIError.authenticationError("Invalid key")
        XCTAssertTrue(authError.errorDescription?.contains("Authentication") ?? false)

        let validationError = XAIError.validationError("Missing field")
        XCTAssertTrue(validationError.errorDescription?.contains("Validation") ?? false)

        let notFound = XAIError.notFound("Block not found")
        XCTAssertTrue(notFound.errorDescription?.contains("Not found") ?? false)

        let rateLimitWithRetry = XAIError.rateLimitError(retryAfter: 60)
        XCTAssertTrue(rateLimitWithRetry.errorDescription?.contains("60") ?? false)

        let rateLimitWithoutRetry = XAIError.rateLimitError(retryAfter: nil)
        XCTAssertTrue(rateLimitWithoutRetry.errorDescription?.contains("Rate limit") ?? false)

        let serverError = XAIError.serverError(500, "Internal error")
        XCTAssertTrue(serverError.errorDescription?.contains("500") ?? false)

        let timeout = XAIError.timeout
        XCTAssertTrue(timeout.errorDescription?.contains("timed out") ?? false)

        let transactionError = XAIError.transactionError("Insufficient funds")
        XCTAssertTrue(transactionError.errorDescription?.contains("Transaction") ?? false)

        let walletError = XAIError.walletError("Invalid address")
        XCTAssertTrue(walletError.errorDescription?.contains("Wallet") ?? false)

        let aiError = XAIError.aiError("Provider unavailable")
        XCTAssertTrue(aiError.errorDescription?.contains("AI") ?? false)
    }
}

// MARK: - AnyCodable Tests

final class AnyCodableTests: XCTestCase {

    func testAnyCodableWithString() {
        let value = AnyCodable("hello")
        XCTAssertEqual(value.stringValue, "hello")
    }

    func testAnyCodableWithInt() {
        let value = AnyCodable(42)
        XCTAssertEqual(value.intValue, 42)
    }

    func testAnyCodableWithDouble() {
        let value = AnyCodable(3.14)
        XCTAssertEqual(value.doubleValue, 3.14)
    }

    func testAnyCodableWithBool() {
        let value = AnyCodable(true)
        XCTAssertEqual(value.boolValue, true)
    }

    func testAnyCodableEquality() {
        let value1 = AnyCodable("test")
        let value2 = AnyCodable("test")
        let value3 = AnyCodable("different")

        XCTAssertEqual(value1, value2)
        XCTAssertNotEqual(value1, value3)
    }

    func testAnyCodableEncoding() throws {
        let value = AnyCodable("test")
        let encoder = JSONEncoder()
        let data = try encoder.encode(value)
        let string = String(data: data, encoding: .utf8)
        XCTAssertEqual(string, "\"test\"")
    }

    func testAnyCodableDecoding() throws {
        let json = "\"hello\""
        let data = json.data(using: .utf8)!
        let decoder = JSONDecoder()
        let value = try decoder.decode(AnyCodable.self, from: data)
        XCTAssertEqual(value.stringValue, "hello")
    }
}

// MARK: - Validation Tests

final class ValidationTests: XCTestCase {

    func testAddressValidation() {
        let client = XAIClient()

        // Valid XAI address (42 chars starting with XAI)
        XCTAssertTrue(client.wallet.validateAddress("XAI1abc123def456ghi789jkl012mno345pqr"))

        // Valid hex address
        XCTAssertTrue(client.wallet.validateAddress("0x1234567890abcdef1234567890abcdef12345678"))

        // Invalid - too short
        XCTAssertFalse(client.wallet.validateAddress("XAI123"))

        // Invalid - wrong prefix
        XCTAssertFalse(client.wallet.validateAddress("BTC1abc123def456ghi789jkl012mno345pqr"))

        // Invalid - non-hex characters in hex address
        XCTAssertFalse(client.wallet.validateAddress("0xGGGG567890abcdef1234567890abcdef12345678"))
    }
}

// MARK: - SendTransactionParams Tests

final class SendTransactionParamsTests: XCTestCase {

    func testBasicParams() {
        let params = SendTransactionParams(
            from: "XAI1...",
            to: "XAI2...",
            amount: "1000"
        )
        XCTAssertEqual(params.from, "XAI1...")
        XCTAssertEqual(params.to, "XAI2...")
        XCTAssertEqual(params.amount, "1000")
        XCTAssertNil(params.data)
        XCTAssertNil(params.gasLimit)
        XCTAssertNil(params.gasPrice)
        XCTAssertNil(params.nonce)
    }

    func testFullParams() {
        let params = SendTransactionParams(
            from: "XAI1...",
            to: "XAI2...",
            amount: "1000",
            data: "0x1234",
            gasLimit: "21000",
            gasPrice: "20000000000",
            nonce: 5,
            signature: "0xsig..."
        )
        XCTAssertEqual(params.data, "0x1234")
        XCTAssertEqual(params.gasLimit, "21000")
        XCTAssertEqual(params.gasPrice, "20000000000")
        XCTAssertEqual(params.nonce, 5)
        XCTAssertEqual(params.signature, "0xsig...")
    }

    func testParamsEncoding() throws {
        let params = SendTransactionParams(
            from: "XAI1abc",
            to: "XAI2def",
            amount: "500"
        )
        let encoder = JSONEncoder()
        let data = try encoder.encode(params)
        let json = try JSONSerialization.jsonObject(with: data) as! [String: Any]

        XCTAssertEqual(json["from"] as? String, "XAI1abc")
        XCTAssertEqual(json["to"] as? String, "XAI2def")
        XCTAssertEqual(json["amount"] as? String, "500")
    }
}
