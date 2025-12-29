# XAI Blockchain Architecture Diagrams

Visual documentation of the XAI blockchain system architecture.

## System Overview

High-level view of the main components and their interactions.

```mermaid
graph TB
    subgraph "External Clients"
        CLI[CLI Commands]
        API_CLIENT[REST API Clients]
        WS_CLIENT[WebSocket Clients]
    end

    subgraph "BlockchainNode"
        FLASK[Flask API Server]
        P2P[P2P Network Manager]
        MINING[Mining Thread]
        CONSENSUS[Consensus Manager]
        METRICS[Metrics Collector]
    end

    subgraph "Blockchain Core"
        BC[Blockchain]
        MEMPOOL[Mempool]
        UTXO[UTXO Manager]
        VALIDATOR[Transaction Validator]
        STORAGE[Blockchain Storage]
    end

    subgraph "Subsystems"
        VM[Smart Contract VM]
        GOV[Governance State]
        GAMIFY[Gamification]
        FINALITY[Finality Manager]
    end

    CLI --> FLASK
    API_CLIENT --> FLASK
    WS_CLIENT --> P2P

    FLASK --> BC
    P2P --> BC
    P2P --> CONSENSUS
    MINING --> BC

    BC --> MEMPOOL
    BC --> UTXO
    BC --> VALIDATOR
    BC --> STORAGE
    BC --> VM
    BC --> GOV
    BC --> GAMIFY
    BC --> FINALITY
```

## Transaction Flow

Complete lifecycle of a transaction from submission to confirmation.

```mermaid
sequenceDiagram
    participant Client
    participant API as Flask API
    participant TV as Transaction Validator
    participant UTXO as UTXO Manager
    participant MP as Mempool
    participant P2P as P2P Network
    participant Miner as Mining Thread
    participant BC as Blockchain

    Client->>API: POST /transaction
    API->>TV: validate_transaction()
    TV->>TV: validate_structure()
    TV->>TV: validate_size()
    TV->>TV: validate_timestamp()
    TV->>TV: validate_signature()
    TV->>UTXO: validate_inputs()
    UTXO-->>TV: inputs valid
    TV->>TV: validate_nonce()
    TV-->>API: validation passed

    API->>MP: add_transaction()
    MP->>MP: check_fee_rate()
    MP->>MP: check_sender_limit()
    MP-->>API: tx accepted

    API->>P2P: broadcast_transaction()
    P2P->>P2P: relay to peers

    API-->>Client: txid

    loop Mining Loop
        Miner->>MP: get pending transactions
        MP-->>Miner: transactions
        Miner->>BC: mine_pending_transactions()
        BC->>BC: create_block()
        BC->>BC: proof_of_work()
        BC->>UTXO: update_utxos()
        BC->>P2P: broadcast_block()
    end
```

## Block Production

Mining and block creation workflow.

```mermaid
flowchart TD
    START([Mining Thread Start]) --> CHECK{Pending TXs?}
    CHECK -->|No| HEARTBEAT{Allow Empty?}
    HEARTBEAT -->|Yes| CREATE_HB[Create Heartbeat TX]
    CREATE_HB --> PREPARE
    HEARTBEAT -->|No| SLEEP[Sleep 1s]
    SLEEP --> CHECK

    CHECK -->|Yes| PREPARE[Prepare Block]
    PREPARE --> SELECT[Select Transactions]
    SELECT --> VALIDATE[Validate All TXs]
    VALIDATE --> CREATE[Create Block Header]
    CREATE --> POW[Proof of Work]

    POW --> FOUND{Valid Hash?}
    FOUND -->|No| ABORT{Abort Flag?}
    ABORT -->|Yes| DISCARD[Discard Work]
    DISCARD --> CHECK
    ABORT -->|No| POW

    FOUND -->|Yes| FINALIZE[Finalize Block]
    FINALIZE --> UPDATE_UTXO[Update UTXO Set]
    UPDATE_UTXO --> UPDATE_NONCE[Update Nonce Tracker]
    UPDATE_NONCE --> PERSIST[Persist to Storage]
    PERSIST --> BROADCAST[Broadcast to Peers]
    BROADCAST --> CHECK
```

## Component Dependencies

Key class relationships in the core blockchain module.

```mermaid
classDiagram
    class Blockchain {
        +chain: List~BlockHeader~
        +pending_transactions: List~Transaction~
        +difficulty: int
        +storage: BlockchainStorage
        +utxo_manager: UTXOManager
        +nonce_tracker: NonceTracker
        +add_transaction()
        +mine_pending_transactions()
        +get_balance()
    }

    class BlockchainNode {
        +blockchain: Blockchain
        +app: Flask
        +p2p_manager: P2PNetworkManager
        +consensus_manager: ConsensusManager
        +start_mining()
        +stop_mining()
        +broadcast_block()
    }

    class Transaction {
        +sender: str
        +recipient: str
        +amount: float
        +fee: float
        +inputs: List
        +outputs: List
        +signature: str
        +verify_signature()
        +calculate_hash()
    }

    class Block {
        +index: int
        +timestamp: float
        +transactions: List~Transaction~
        +previous_hash: str
        +hash: str
        +nonce: int
    }

    class UTXOManager {
        +utxo_set: Dict
        +add_utxo()
        +remove_utxo()
        +get_balance()
        +get_unspent_output()
    }

    class TransactionValidator {
        +blockchain: Blockchain
        +utxo_manager: UTXOManager
        +nonce_tracker: NonceTracker
        +validate_transaction()
    }

    BlockchainNode --> Blockchain
    BlockchainNode --> P2PNetworkManager
    BlockchainNode --> ConsensusManager
    Blockchain --> UTXOManager
    Blockchain --> BlockchainStorage
    Blockchain --> TransactionValidator
    Blockchain --> NonceTracker
    Block --> Transaction
    TransactionValidator --> UTXOManager
```

## Data Flow

UTXO model and mempool data flow.

```mermaid
flowchart LR
    subgraph "Transaction Creation"
        WALLET[Wallet] --> SELECT_UTXO[Select UTXOs]
        SELECT_UTXO --> CREATE_TX[Create Transaction]
        CREATE_TX --> SIGN[Sign Transaction]
    end

    subgraph "Mempool"
        SIGN --> VALIDATE[Validate]
        VALIDATE --> FEE_CHECK[Fee Rate Check]
        FEE_CHECK --> SENDER_CAP[Sender Limit Check]
        SENDER_CAP --> MEMPOOL[(Mempool)]
    end

    subgraph "Block Inclusion"
        MEMPOOL --> MINE[Mining]
        MINE --> NEW_BLOCK[New Block]
    end

    subgraph "State Update"
        NEW_BLOCK --> SPEND[Mark Inputs Spent]
        SPEND --> CREATE_UTXO[Create New UTXOs]
        CREATE_UTXO --> UPDATE_BAL[Update Balances]
        UPDATE_BAL --> UTXO_SET[(UTXO Set)]
    end

    UTXO_SET -.-> SELECT_UTXO
```

## API Layer Organization

Flask routes and their handlers.

```mermaid
graph TB
    subgraph "Flask Application"
        APP[Flask App]
    end

    subgraph "Route Modules"
        CORE[core.py<br/>Health, Stats]
        BLOCKCHAIN[blockchain.py<br/>Blocks, Chain]
        TX[transactions.py<br/>Submit, Query]
        WALLET[wallet.py<br/>Balance, Send]
        MINING[mining.py<br/>Mine, Auto-mine]
        PEER[peer.py<br/>Add Peer, List]
        SYNC[sync.py<br/>Chain Sync]
        CONTRACTS[contracts.py<br/>Deploy, Call]
        GAMIFY[gamification.py<br/>Airdrops, Streaks]
        ADMIN[admin_*.py<br/>Keys, Emergency]
    end

    subgraph "Middleware"
        CORS[CORS Policy]
        RATE[Rate Limiter]
        AUTH[API Auth]
        VALID[Request Validator]
        SEC[Security Middleware]
    end

    APP --> CORS
    CORS --> RATE
    RATE --> AUTH
    AUTH --> VALID
    VALID --> SEC

    SEC --> CORE
    SEC --> BLOCKCHAIN
    SEC --> TX
    SEC --> WALLET
    SEC --> MINING
    SEC --> PEER
    SEC --> SYNC
    SEC --> CONTRACTS
    SEC --> GAMIFY
    SEC --> ADMIN
```

## P2P Network Architecture

Peer-to-peer communication flow.

```mermaid
flowchart TB
    subgraph "Local Node"
        P2P_MGR[P2P Network Manager]
        WS_SERVER[WebSocket Server]
        PEER_MGR[Peer Manager]
        RATE_LIM[Rate Limiter]
        BW_LIM[Bandwidth Limiter]
    end

    subgraph "Message Types"
        TX_MSG[Transaction Broadcast]
        BLOCK_MSG[Block Broadcast]
        SYNC_REQ[Sync Request]
        HANDSHAKE[Handshake]
    end

    subgraph "Remote Peers"
        PEER1[Peer Node 1]
        PEER2[Peer Node 2]
        PEER3[Peer Node 3]
    end

    P2P_MGR --> WS_SERVER
    P2P_MGR --> PEER_MGR
    WS_SERVER --> RATE_LIM
    RATE_LIM --> BW_LIM

    BW_LIM --> TX_MSG
    BW_LIM --> BLOCK_MSG
    BW_LIM --> SYNC_REQ
    BW_LIM --> HANDSHAKE

    TX_MSG --> PEER1
    TX_MSG --> PEER2
    TX_MSG --> PEER3
    BLOCK_MSG --> PEER1
    BLOCK_MSG --> PEER2
    BLOCK_MSG --> PEER3
```

## Smart Contract Execution

Contract deployment and execution flow.

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant TX as Transaction
    participant BC as Blockchain
    participant SCM as SmartContractManager
    participant EXEC as Executor
    participant STATE as Contract State

    Note over Client,STATE: Contract Deployment
    Client->>API: POST /contract/deploy
    API->>TX: create contract_deploy tx
    TX->>BC: add to mempool
    BC->>BC: mine block
    BC->>SCM: process_block()
    SCM->>EXEC: deploy contract
    EXEC->>STATE: store bytecode
    STATE-->>Client: contract address

    Note over Client,STATE: Contract Call
    Client->>API: POST /contract/call
    API->>TX: create contract_call tx
    TX->>BC: add to mempool
    BC->>BC: mine block
    BC->>SCM: process_transaction()
    SCM->>EXEC: execute(msg, gas_limit)
    EXEC->>STATE: read/write state
    EXEC-->>SCM: ExecutionResult
    SCM-->>Client: receipt with logs
```

## Storage Architecture

Persistence and data storage structure.

```mermaid
graph TB
    subgraph "BlockchainStorage"
        BLOCKS[(Block Files<br/>blocks/)]
        META[(Metadata<br/>metadata.json)]
        UTXO_DB[(UTXO State)]
        ADDR_IDX[(Address Index<br/>address_index.db)]
        NONCES[(Nonce Tracker<br/>nonces/)]
    end

    subgraph "Checkpoints"
        CKPT[(Checkpoint Files<br/>checkpoints/)]
        CKPT_MGR[Checkpoint Manager]
    end

    subgraph "Finality"
        FIN_DB[(Finality Certs<br/>finality/)]
        SLASH_DB[(Slashing DB<br/>slashing.db)]
    end

    subgraph "Gamification"
        AIRDROP[(Airdrop State)]
        STREAK[(Streak Data)]
        TREASURE[(Treasure Hunt)]
    end

    BC[Blockchain] --> BLOCKS
    BC --> META
    BC --> UTXO_DB
    BC --> ADDR_IDX
    BC --> NONCES
    BC --> CKPT_MGR
    CKPT_MGR --> CKPT
    BC --> FIN_DB
    BC --> SLASH_DB
    BC --> AIRDROP
    BC --> STREAK
    BC --> TREASURE
```

## Security Layers

Security validation and middleware stack.

```mermaid
flowchart TD
    REQ[Incoming Request] --> CORS{CORS Check}
    CORS -->|Fail| REJECT1[403 Forbidden]
    CORS -->|Pass| SIZE{Size Limit}
    SIZE -->|Exceed| REJECT2[413 Too Large]
    SIZE -->|Pass| RATE{Rate Limit}
    RATE -->|Exceed| REJECT3[429 Too Many]
    RATE -->|Pass| AUTH{API Key Auth}
    AUTH -->|Fail| REJECT4[401 Unauthorized]
    AUTH -->|Pass| VALID{Input Validation}
    VALID -->|Fail| REJECT5[400 Bad Request]
    VALID -->|Pass| SANITIZE[Input Sanitization]
    SANITIZE --> HANDLER[Route Handler]

    subgraph "Transaction Security"
        HANDLER --> SIG{Signature Valid?}
        SIG -->|No| TX_REJECT[Reject TX]
        SIG -->|Yes| UTXO_CHECK{UTXO Valid?}
        UTXO_CHECK -->|No| TX_REJECT
        UTXO_CHECK -->|Yes| NONCE_CHECK{Nonce Valid?}
        NONCE_CHECK -->|No| TX_REJECT
        NONCE_CHECK -->|Yes| ACCEPT[Accept TX]
    end
```

## Sandbox Execution

Secure code execution for mini-apps.

```mermaid
flowchart LR
    subgraph "Input"
        CODE[User Code]
        ARGS[Arguments]
    end

    subgraph "Validation"
        AST[AST Validator]
        PERM[Permission Check]
    end

    subgraph "Isolation"
        RESTRICT[RestrictedPython]
        SUBPROCESS[Subprocess Sandbox]
        SECCOMP[seccomp Filter]
    end

    subgraph "Limits"
        CPU[CPU Limit]
        MEM[Memory Limit]
        TIME[Wall Time]
        FD[File Descriptors]
    end

    subgraph "Output"
        RESULT[Execution Result]
        LOGS[Execution Logs]
    end

    CODE --> AST
    ARGS --> AST
    AST --> PERM
    PERM -->|Simple| RESTRICT
    PERM -->|Complex| SUBPROCESS
    SUBPROCESS --> SECCOMP
    RESTRICT --> CPU
    SECCOMP --> CPU
    CPU --> MEM
    MEM --> TIME
    TIME --> FD
    FD --> RESULT
    FD --> LOGS
```
