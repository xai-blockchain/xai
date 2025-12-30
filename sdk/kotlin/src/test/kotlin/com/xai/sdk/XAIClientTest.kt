package com.xai.sdk

import com.xai.sdk.models.*
import com.xai.sdk.utils.*
import io.mockk.*
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.jupiter.api.*
import org.junit.jupiter.api.Assertions.*
import kotlin.test.assertFailsWith

class XAIClientTest {

    private lateinit var mockServer: MockWebServer
    private lateinit var client: XAIClient

    @BeforeEach
    fun setup() {
        mockServer = MockWebServer()
        mockServer.start()
        client = XAIClient(
            baseUrl = mockServer.url("/").toString().removeSuffix("/")
        )
    }

    @AfterEach
    fun tearDown() {
        client.close()
        mockServer.shutdown()
    }

    @Nested
    @DisplayName("XAIClient")
    inner class MainClientTests {

        @Test
        fun `healthCheck returns health status`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""{"status":"healthy","timestamp":1234567890,"services":{}}""")
                    .setHeader("Content-Type", "application/json")
            )

            val health = client.healthCheck()

            assertEquals("healthy", health.status)
            assertEquals(1234567890L, health.timestamp)
        }

        @Test
        fun `getNodeInfo returns node information`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""{"status":"ok","node":"xai-node","version":"1.0.0","chain_id":"xai-1","peer_count":5}""")
                    .setHeader("Content-Type", "application/json")
            )

            val info = client.getNodeInfo()

            assertEquals("ok", info.status)
            assertEquals("xai-node", info.node)
            assertEquals("1.0.0", info.version)
            assertEquals("xai-1", info.chainId)
            assertEquals(5, info.peerCount)
        }

        @Test
        fun `getSyncStatus returns sync status`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""{"syncing":true,"current_block":1000,"highest_block":2000}""")
                    .setHeader("Content-Type", "application/json")
            )

            val status = client.getSyncStatus()

            assertTrue(status.syncing)
            assertEquals(1000L, status.currentBlock)
            assertEquals(2000L, status.highestBlock)
            assertEquals(50.0, status.syncProgress)
        }

        @Test
        fun `isSynced returns true when not syncing`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""{"syncing":false}""")
                    .setHeader("Content-Type", "application/json")
            )

            assertTrue(client.isSynced())
        }

        @Test
        fun `companion object creates correct client instances`() {
            val local = XAIClient.local()
            val testnet = XAIClient.testnet()
            val mainnet = XAIClient.mainnet("api-key")

            assertNotNull(local)
            assertNotNull(testnet)
            assertNotNull(mainnet)

            local.close()
            testnet.close()
            mainnet.close()
        }
    }

    @Nested
    @DisplayName("BlocksClient")
    inner class BlocksClientTests {

        @Test
        fun `getBlock returns block by hash`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "number": 100,
                            "hash": "0xabc123",
                            "parent_hash": "0xdef456",
                            "timestamp": 1234567890,
                            "miner": "0xminer",
                            "difficulty": "12345",
                            "gas_limit": "8000000",
                            "gas_used": "21000",
                            "transaction_count": 5,
                            "transactions": ["0xtx1", "0xtx2"]
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val block = client.blocks.getBlock("0xabc123")

            assertEquals(100L, block.number)
            assertEquals("0xabc123", block.hash)
            assertEquals("0xdef456", block.parentHash)
            assertEquals("0xminer", block.miner)
            assertEquals(5, block.transactionCount)
            assertEquals(2, block.transactionHashes.size)
        }

        @Test
        fun `getBlock throws ValidationException for blank hash`() = runTest {
            assertFailsWith<ValidationException> {
                client.blocks.getBlock("")
            }
        }

        @Test
        fun `getBlocks returns list of blocks`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "blocks": [
                                {"number": 100, "hash": "0x1", "parent_hash": "0x0", "timestamp": 1234567890, "miner": "0xm", "difficulty": "1"},
                                {"number": 99, "hash": "0x2", "parent_hash": "0x1", "timestamp": 1234567880, "miner": "0xm", "difficulty": "1"}
                            ],
                            "total": 100,
                            "limit": 20,
                            "offset": 0
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val blocks = client.blocks.getBlocks(page = 1, limit = 20)

            assertEquals(2, blocks.size)
            assertEquals(100L, blocks[0].number)
            assertEquals(99L, blocks[1].number)
        }

        @Test
        fun `getLatestBlock returns latest block`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {"number": 1000, "hash": "0xlatest", "parent_hash": "0xprev", "timestamp": 1234567890, "miner": "0xm", "difficulty": "1"}
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val block = client.blocks.getLatestBlock()

            assertEquals(1000L, block.number)
            assertEquals("0xlatest", block.hash)
        }
    }

    @Nested
    @DisplayName("TransactionsClient")
    inner class TransactionsClientTests {

        @Test
        fun `getTransaction returns transaction details`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "hash": "0xtx123",
                            "from": "0xsender",
                            "to": "0xreceiver",
                            "amount": "1000",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "status": "confirmed",
                            "fee": "21",
                            "confirmations": 10
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val tx = client.transactions.getTransaction("0xtx123")

            assertEquals("0xtx123", tx.hash)
            assertEquals("0xsender", tx.from)
            assertEquals("0xreceiver", tx.to)
            assertEquals("1000", tx.amount)
            assertEquals(TransactionStatus.CONFIRMED, tx.status)
            assertEquals(10, tx.confirmations)
        }

        @Test
        fun `getTransaction throws ValidationException for blank txid`() = runTest {
            assertFailsWith<ValidationException> {
                client.transactions.getTransaction("")
            }
        }

        @Test
        fun `sendTransaction submits signed transaction`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""{"hash":"0xnewtx","status":"pending","message":"submitted"}""")
                    .setHeader("Content-Type", "application/json")
            )

            val signedTx = SignedTransaction(
                from = "0xsender",
                to = "0xreceiver",
                amount = "1000",
                signature = "0xsig123",
                nonce = 5
            )

            val result = client.transactions.sendTransaction(signedTx)

            assertEquals("0xnewtx", result.hash)
            assertEquals("pending", result.status)
        }

        @Test
        fun `sendTransaction throws ValidationException for invalid tx`() = runTest {
            val invalidTx = SignedTransaction(
                from = "",
                to = "0xreceiver",
                amount = "1000",
                signature = "0xsig",
                nonce = 0
            )

            assertFailsWith<ValidationException> {
                client.transactions.sendTransaction(invalidTx)
            }
        }

        @Test
        fun `isConfirmed returns true when confirmations met`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""{"status":"confirmed","confirmations":10}""")
                    .setHeader("Content-Type", "application/json")
            )

            assertTrue(client.transactions.isConfirmed("0xtx123", requiredConfirmations = 6))
        }

        @Test
        fun `estimateFee returns fee estimation`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""{"estimated_fee":"21000","gas_limit":"21000","gas_price":"1"}""")
                    .setHeader("Content-Type", "application/json")
            )

            val fee = client.transactions.estimateFee(
                from = "0xsender",
                to = "0xreceiver",
                amount = "1000"
            )

            assertEquals("21000", fee.estimatedFee)
            assertEquals("21000", fee.gasLimit)
        }
    }

    @Nested
    @DisplayName("WalletClient")
    inner class WalletClientTests {

        @Test
        fun `getBalance returns wallet balance`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "address": "0x1234",
                            "balance": "10000",
                            "locked_balance": "1000",
                            "available_balance": "9000",
                            "nonce": 5
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val balance = client.wallet.getBalance("0x1234")

            assertEquals("0x1234", balance.address)
            assertEquals("10000", balance.balance)
            assertEquals("1000", balance.lockedBalance)
            assertEquals("9000", balance.availableBalance)
            assertEquals(5, balance.nonce)
        }

        @Test
        fun `getBalance throws ValidationException for blank address`() = runTest {
            assertFailsWith<ValidationException> {
                client.wallet.getBalance("")
            }
        }

        @Test
        fun `getUTXOs returns list of UTXOs`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "utxos": [
                                {"tx_hash": "0xtx1", "output_index": 0, "amount": "500", "address": "0x1234", "block_height": 100},
                                {"tx_hash": "0xtx2", "output_index": 1, "amount": "300", "address": "0x1234", "block_height": 99}
                            ],
                            "total": 2
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val utxos = client.wallet.getUTXOs("0x1234")

            assertEquals(2, utxos.size)
            assertEquals("0xtx1", utxos[0].txHash)
            assertEquals("500", utxos[0].amount)
        }

        @Test
        fun `createTransaction returns unsigned transaction`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "from": "0xsender",
                            "to": "0xreceiver",
                            "amount": "1000",
                            "nonce": 10,
                            "gas_limit": "21000",
                            "gas_price": "1",
                            "estimated_fee": "21000"
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val unsignedTx = client.wallet.createTransaction(
                from = "0xsender",
                to = "0xreceiver",
                amount = "1000"
            )

            assertEquals("0xsender", unsignedTx.from)
            assertEquals("0xreceiver", unsignedTx.to)
            assertEquals("1000", unsignedTx.amount)
            assertEquals(10, unsignedTx.nonce)
            assertEquals("21000", unsignedTx.estimatedFee)
        }
    }

    @Nested
    @DisplayName("AIClient")
    inner class AIClientTests {

        @Test
        fun `submitTask returns task with ID`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "id": "task-123",
                            "type": "text_generation",
                            "status": "pending",
                            "created_at": "2024-01-01T00:00:00Z",
                            "progress": 0
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val task = client.ai.submitTask(
                AITaskRequest(
                    type = "text_generation",
                    prompt = "Hello world"
                )
            )

            assertEquals("task-123", task.id)
            assertEquals("text_generation", task.type)
            assertEquals(AITaskStatus.PENDING, task.status)
        }

        @Test
        fun `submitTask throws ValidationException for blank type`() = runTest {
            assertFailsWith<ValidationException> {
                client.ai.submitTask(
                    AITaskRequest(type = "", prompt = "Hello")
                )
            }
        }

        @Test
        fun `getTask returns task status`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "id": "task-123",
                            "type": "analysis",
                            "status": "completed",
                            "created_at": "2024-01-01T00:00:00Z",
                            "completed_at": "2024-01-01T00:01:00Z",
                            "result": {"output": "analysis result"},
                            "progress": 100
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val task = client.ai.getTask("task-123")

            assertEquals("task-123", task.id)
            assertEquals(AITaskStatus.COMPLETED, task.status)
            assertEquals(100, task.progress)
            assertNotNull(task.result)
        }

        @Test
        fun `listProviders returns available providers`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "providers": [
                                {
                                    "id": "openai",
                                    "name": "OpenAI",
                                    "description": "OpenAI GPT models",
                                    "capabilities": ["text_generation", "analysis"],
                                    "models": ["gpt-4", "gpt-3.5-turbo"],
                                    "available": true
                                }
                            ]
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val providers = client.ai.listProviders()

            assertEquals(1, providers.size)
            assertEquals("openai", providers[0].id)
            assertEquals("OpenAI", providers[0].name)
            assertEquals(2, providers[0].capabilities.size)
            assertTrue(providers[0].available)
        }
    }

    @Nested
    @DisplayName("StakingClient")
    inner class StakingClientTests {

        @Test
        fun `getStakingInfo returns staking details`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "address": "0x1234",
                            "staked_amount": "10000",
                            "rewards": "500",
                            "validator_address": "0xvalidator",
                            "apy_rate": "12.5"
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val info = client.staking.getStakingInfo("0x1234")

            assertEquals("0x1234", info.address)
            assertEquals("10000", info.stakedAmount)
            assertEquals("500", info.rewards)
            assertEquals("0xvalidator", info.validatorAddress)
            assertEquals("12.5", info.apyRate)
        }

        @Test
        fun `listValidators returns validator list`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setBody("""
                        {
                            "validators": [
                                {
                                    "address": "0xval1",
                                    "name": "Validator 1",
                                    "total_stake": "100000",
                                    "delegator_count": 50,
                                    "commission": "5",
                                    "status": "active",
                                    "uptime": 99.9
                                }
                            ],
                            "total": 1,
                            "limit": 50,
                            "offset": 0
                        }
                    """.trimIndent())
                    .setHeader("Content-Type", "application/json")
            )

            val validators = client.staking.listValidators()

            assertEquals(1, validators.size)
            assertEquals("0xval1", validators[0].address)
            assertEquals("Validator 1", validators[0].name)
            assertEquals(50, validators[0].delegatorCount)
            assertEquals(99.9, validators[0].uptime)
        }
    }

    @Nested
    @DisplayName("Error Handling")
    inner class ErrorHandlingTests {

        @Test
        fun `handles 401 authentication error`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setResponseCode(401)
                    .setBody("""{"error":"Unauthorized"}""")
            )

            assertFailsWith<AuthenticationException> {
                client.healthCheck()
            }
        }

        @Test
        fun `handles 404 not found error`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setResponseCode(404)
                    .setBody("""{"error":"Not found"}""")
            )

            assertFailsWith<NotFoundException> {
                client.blocks.getBlock("nonexistent")
            }
        }

        @Test
        fun `handles 429 rate limit error`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setResponseCode(429)
                    .setHeader("Retry-After", "60")
                    .setBody("""{"error":"Rate limit exceeded"}""")
            )

            assertFailsWith<RateLimitException> {
                client.healthCheck()
            }
        }

        @Test
        fun `handles 500 server error`() = runTest {
            mockServer.enqueue(
                MockResponse()
                    .setResponseCode(500)
                    .setBody("""{"error":"Internal server error"}""")
            )

            assertFailsWith<APIException> {
                client.healthCheck()
            }
        }
    }
}
