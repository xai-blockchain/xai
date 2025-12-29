# SDK 集成指南

本指南提供使用 Python 和 JavaScript/TypeScript 与 XAI 区块链集成的示例。

## 安装

### Python SDK

```bash
pip install xai-sdk
# 或从源码安装：
pip install -e ./src/xai/sdk/python
```

### JavaScript/TypeScript SDK

```bash
npm install @xai/sdk
# 或从源码安装：
cd src/xai/sdk/typescript && npm install && npm run build
```

---

## Python 示例

### 初始化客户端

```python
from xai_sdk import XAIClient

# 本地开发节点（默认端口 12001）
client = XAIClient(base_url="http://localhost:12001")

# 测试网（带 API 密钥）
client = XAIClient(
    base_url="https://testnet-api.xai-blockchain.io",
    api_key="您的-api-密钥",
    timeout=30,
    max_retries=3
)

# 使用上下文管理器自动清理
with XAIClient() as client:
    health = client.health_check()
    print(f"节点状态: {health['status']}")
```

### 创建钱包/密钥对

```python
from xai.core.wallet import Wallet

# 生成新钱包（secp256k1 密钥对）
wallet = Wallet()
print(f"地址: {wallet.address}")
print(f"公钥: {wallet.public_key}")
# 警告：生产环境切勿记录或暴露私钥！

# 从现有私钥创建
wallet = Wallet(private_key="您的十六进制私钥")

# 从 BIP-39 助记词创建（24 个单词）
mnemonic = Wallet.generate_mnemonic(strength=256)  # 24 个单词
print(f"助记词: {mnemonic}")  # 安全保存！

# 从助记词恢复钱包
wallet = Wallet.from_mnemonic(
    mnemonic_phrase=mnemonic,
    passphrase="可选额外安全密码",
    account_index=0,
    address_index=0
)

# 保存加密钱包到文件
wallet.save_to_file("我的钱包.json", password="强密码")

# 从加密文件加载钱包
loaded_wallet = Wallet.load_from_file("我的钱包.json", password="强密码")

# 导出为 WIF（钱包导入格式）
wif = wallet.export_to_wif()
restored = Wallet.import_from_wif(wif)

# 签名消息
message = "你好，XAI！"
signature = wallet.sign_message(message)
is_valid = wallet.verify_signature(message, signature, wallet.public_key)
```

### 获取余额

```python
import requests

NODE_URL = "http://localhost:12001"

def get_balance(address: str) -> dict:
    """获取 XAI 地址的余额。"""
    response = requests.get(
        f"{NODE_URL}/balance/{address}",
        headers={"X-API-Key": "您的-api-密钥"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 示例用法
balance_info = get_balance("TXAIabcd1234...")
print(f"地址: {balance_info['address']}")
print(f"余额: {balance_info['balance']} XAI")

# 使用 SDK 客户端
from xai_sdk import XAIClient

with XAIClient() as client:
    balance = client.wallet.get_balance("TXAIabcd1234...")
    print(f"余额: {balance.balance}")
    print(f"可用: {balance.available_balance}")
    print(f"Nonce: {balance.nonce}")
```

### 发送交易

```python
import hashlib
import time
import requests
from xai.core.wallet import Wallet
from xai.core.blockchain import Transaction

NODE_URL = "http://localhost:12001"
API_KEY = "您的-api-密钥"

def send_transaction(
    wallet: Wallet,
    recipient: str,
    amount: float,
    fee: float = 0.001
) -> dict:
    """创建、签名并发送交易。"""

    # 获取发送者当前 nonce
    nonce_resp = requests.get(
        f"{NODE_URL}/address/{wallet.address}/nonce",
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    nonce_resp.raise_for_status()
    nonce = nonce_resp.json()["next_nonce"]

    # 创建交易
    tx = Transaction(
        sender=wallet.address,
        recipient=recipient,
        amount=amount,
        fee=fee,
        public_key=wallet.public_key,
        nonce=nonce
    )
    tx.timestamp = time.time()

    # 计算交易哈希并签名
    tx.txid = tx.calculate_hash()
    tx.signature = wallet.sign_message(tx.txid)

    # 提交交易
    payload = {
        "sender": tx.sender,
        "recipient": tx.recipient,
        "amount": tx.amount,
        "fee": tx.fee,
        "public_key": tx.public_key,
        "signature": tx.signature,
        "nonce": tx.nonce,
        "timestamp": tx.timestamp,
        "txid": tx.txid
    }

    response = requests.post(
        f"{NODE_URL}/send",
        json=payload,
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 示例用法
wallet = Wallet.load_from_file("我的钱包.json", password="强密码")
result = send_transaction(
    wallet=wallet,
    recipient="TXAIrecipient123...",
    amount=10.0,
    fee=0.001
)
print(f"交易 ID: {result['txid']}")
print(f"消息: {result['message']}")
```

### 查询区块和交易

```python
import requests

NODE_URL = "http://localhost:12001"

def get_blocks(limit: int = 10, offset: int = 0) -> dict:
    """获取分页的区块列表。"""
    response = requests.get(
        f"{NODE_URL}/blocks",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def get_block_by_index(index: int) -> dict:
    """按索引获取特定区块。"""
    response = requests.get(f"{NODE_URL}/blocks/{index}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_transaction(txid: str) -> dict:
    """按 ID 获取交易详情。"""
    response = requests.get(f"{NODE_URL}/transaction/{txid}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_address_history(address: str, limit: int = 50, offset: int = 0) -> dict:
    """获取地址的交易历史。"""
    response = requests.get(
        f"{NODE_URL}/history/{address}",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 示例用法
blocks = get_blocks(limit=5)
print(f"总区块数: {blocks['total']}")
for block in blocks['blocks']:
    print(f"区块 {block.get('index')}: {block.get('hash', '')[:16]}...")

# 获取最新区块
latest = get_block_by_index(blocks['total'] - 1)
print(f"最新区块难度: {latest.get('difficulty')}")

# 获取交易历史
history = get_address_history("TXAIabcd1234...", limit=10)
print(f"交易总数: {history['transaction_count']}")
for tx in history['transactions']:
    print(f"  交易: {tx.get('txid', '')[:16]}... 金额: {tx.get('amount')}")
```

### 检查节点健康状态和统计

```python
import requests

NODE_URL = "http://localhost:12001"

def get_health() -> dict:
    """检查节点健康状态。"""
    response = requests.get(f"{NODE_URL}/health", timeout=30)
    return response.json()

def get_stats() -> dict:
    """获取区块链统计信息。"""
    response = requests.get(f"{NODE_URL}/stats", timeout=30)
    response.raise_for_status()
    return response.json()

def get_mempool_stats() -> dict:
    """获取内存池统计和费用建议。"""
    response = requests.get(f"{NODE_URL}/mempool/stats", timeout=30)
    response.raise_for_status()
    return response.json()

# 示例用法
health = get_health()
print(f"状态: {health['status']}")
print(f"区块链高度: {health['blockchain'].get('height')}")
print(f"节点数: {health['network'].get('peers')}")

stats = get_stats()
print(f"链高度: {stats.get('chain_height')}")
print(f"总供应量: {stats.get('total_circulating_supply')}")
print(f"正在挖矿: {stats.get('is_mining')}")

mempool = get_mempool_stats()
print(f"待处理交易: {mempool['pressure']['pending_transactions']}")
print(f"建议费率（标准）: {mempool['fees']['recommended_fee_rates']['standard']}")
```

### 领取测试网水龙头

```python
import requests

NODE_URL = "http://localhost:12001"

def claim_faucet(address: str, api_key: str) -> dict:
    """从水龙头领取测试网代币。"""
    response = requests.post(
        f"{NODE_URL}/faucet/claim",
        json={"address": address},
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 示例用法（仅测试网）
result = claim_faucet("TXAIabcd1234...", "您的-api-密钥")
print(f"收到金额: {result['amount']} XAI")
print(f"交易 ID: {result['txid']}")
print(f"注意: {result['note']}")
```

---

## JavaScript/TypeScript 示例

### 初始化客户端

```typescript
import { XAIClient } from '@xai/sdk';

// 本地开发节点
const client = new XAIClient({
  baseUrl: 'http://localhost:12001',
});

// 测试网（带 API 密钥）
const client = new XAIClient({
  baseUrl: 'https://testnet-api.xai-blockchain.io',
  apiKey: '您的-api-密钥',
  timeout: 30000,
  maxRetries: 3,
});

// 检查节点健康状态
const health = await client.blockchain.getHealth();
console.log(`节点状态: ${health.status}`);
```

### 获取余额

```typescript
const NODE_URL = 'http://localhost:12001';

interface BalanceResponse {
  address: string;
  balance: number;
}

async function getBalance(address: string): Promise<BalanceResponse> {
  const response = await fetch(`${NODE_URL}/balance/${address}`);

  if (!response.ok) {
    throw new Error(`获取余额失败: ${response.statusText}`);
  }

  return response.json();
}

// 示例用法
const balance = await getBalance('TXAIabcd1234...');
console.log(`余额: ${balance.balance} XAI`);

// 使用 SDK
import { XAIClient } from '@xai/sdk';

const client = new XAIClient();
const walletBalance = await client.wallet.getBalance('TXAIabcd1234...');
console.log(`余额: ${walletBalance.balance}`);
console.log(`可用: ${walletBalance.availableBalance}`);
```

### 查询区块和交易

```typescript
const NODE_URL = 'http://localhost:12001';

interface BlocksResponse {
  total: number;
  limit: number;
  offset: number;
  blocks: Block[];
}

interface Block {
  index: number;
  hash: string;
  previous_hash: string;
  timestamp: number;
  difficulty: number;
  transactions: Transaction[];
}

async function getBlocks(limit = 10, offset = 0): Promise<BlocksResponse> {
  const response = await fetch(
    `${NODE_URL}/blocks?limit=${limit}&offset=${offset}`
  );

  if (!response.ok) {
    throw new Error(`获取区块失败: ${response.statusText}`);
  }

  return response.json();
}

async function getBlock(index: number): Promise<Block> {
  const response = await fetch(`${NODE_URL}/blocks/${index}`);

  if (!response.ok) {
    throw new Error(`获取区块失败: ${response.statusText}`);
  }

  return response.json();
}

// 示例用法
const blocks = await getBlocks(5);
console.log(`总区块数: ${blocks.total}`);

for (const block of blocks.blocks) {
  console.log(`区块 ${block.index}: ${block.hash.slice(0, 16)}...`);
}
```

### 检查节点健康状态

```typescript
const NODE_URL = 'http://localhost:12001';

interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  blockchain: {
    accessible: boolean;
    height: number;
    difficulty: number;
    total_supply: number;
  };
  services: {
    api: string;
    storage: string;
    p2p: string;
  };
  network: {
    peers: number;
  };
}

async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${NODE_URL}/health`);
  return response.json();
}

// 示例用法
const health = await getHealth();
console.log(`状态: ${health.status}`);
console.log(`高度: ${health.blockchain.height}`);
console.log(`节点数: ${health.network.peers}`);
```

---

## API 端点参考

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 节点信息和可用端点 |
| `/health` | GET | 带诊断的健康检查 |
| `/stats` | GET | 区块链统计信息 |
| `/balance/<地址>` | GET | 获取地址余额 |
| `/address/<地址>/nonce` | GET | 获取地址 nonce 信息 |
| `/history/<地址>` | GET | 交易历史（分页） |
| `/blocks` | GET | 区块列表（分页） |
| `/blocks/<索引>` | GET | 按索引获取区块 |
| `/block/<哈希>` | GET | 按哈希获取区块 |
| `/transaction/<txid>` | GET | 获取交易详情 |
| `/transactions` | GET | 待处理交易列表 |
| `/send` | POST | 提交签名交易 |
| `/mempool` | GET | 内存池概览 |
| `/mempool/stats` | GET | 费用建议 |
| `/faucet/claim` | POST | 领取测试网代币 |

## 认证

大多数写操作需要 API 密钥认证：

```
X-API-Key: 您的-api-密钥
```

生产环境使用时，还需要按 OpenAPI 规范包含 Bearer token 认证。

## 错误处理

所有端点返回结构化错误响应：

```json
{
  "success": false,
  "error": "错误描述",
  "code": "错误代码",
  "context": {}
}
```

常见错误代码：
- `invalid_payload` - 请求数据格式错误
- `rate_limited` - 请求过多
- `transaction_rejected` - 交易验证失败
- `invalid_signature` - 加密签名无效
