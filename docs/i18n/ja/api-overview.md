# SDK統合ガイド

このガイドでは、PythonとJavaScript/TypeScriptを使用してXAIブロックチェーンと統合する例を提供します。

## インストール

### Python SDK

```bash
pip install xai-sdk
# またはソースからインストール：
pip install -e ./src/xai/sdk/python
```

### JavaScript/TypeScript SDK

```bash
npm install @xai/sdk
# またはソースからインストール：
cd src/xai/sdk/typescript && npm install && npm run build
```

---

## Python例

### クライアントの初期化

```python
from xai_sdk import XAIClient

# ローカル開発ノード（デフォルトポート12001）
client = XAIClient(base_url="http://localhost:12001")

# APIキー付きテストネット
client = XAIClient(
    base_url="https://testnet-api.xai-blockchain.io",
    api_key="あなたのAPIキー",
    timeout=30,
    max_retries=3
)

# 自動クリーンアップ用のコンテキストマネージャーを使用
with XAIClient() as client:
    health = client.health_check()
    print(f"ノードステータス: {health['status']}")
```

### ウォレット/キーペアの作成

```python
from xai.core.wallet import Wallet

# secp256k1キーペアで新しいウォレットを生成
wallet = Wallet()
print(f"アドレス: {wallet.address}")
print(f"公開鍵: {wallet.public_key}")
# 警告：本番環境では秘密鍵をログに記録したり公開したりしないでください！

# 既存の秘密鍵から作成
wallet = Wallet(private_key="あなたの16進数秘密鍵")

# BIP-39ニーモニックから作成（24単語）
mnemonic = Wallet.generate_mnemonic(strength=256)  # 24単語
print(f"ニーモニック: {mnemonic}")  # 安全に保存してください！

# ニーモニックからウォレットを復元
wallet = Wallet.from_mnemonic(
    mnemonic_phrase=mnemonic,
    passphrase="オプションの追加セキュリティ",
    account_index=0,
    address_index=0
)

# 暗号化されたウォレットをファイルに保存
wallet.save_to_file("私のウォレット.json", password="強力なパスワード")

# 暗号化されたファイルからウォレットを読み込み
loaded_wallet = Wallet.load_from_file("私のウォレット.json", password="強力なパスワード")

# WIF（ウォレットインポート形式）にエクスポート
wif = wallet.export_to_wif()
restored = Wallet.import_from_wif(wif)

# メッセージに署名
message = "こんにちは、XAI！"
signature = wallet.sign_message(message)
is_valid = wallet.verify_signature(message, signature, wallet.public_key)
```

### 残高を取得

```python
import requests

NODE_URL = "http://localhost:12001"

def get_balance(address: str) -> dict:
    """XAIアドレスの残高を取得します。"""
    response = requests.get(
        f"{NODE_URL}/balance/{address}",
        headers={"X-API-Key": "あなたのAPIキー"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 使用例
balance_info = get_balance("TXAIabcd1234...")
print(f"アドレス: {balance_info['address']}")
print(f"残高: {balance_info['balance']} XAI")

# SDKクライアントを使用
from xai_sdk import XAIClient

with XAIClient() as client:
    balance = client.wallet.get_balance("TXAIabcd1234...")
    print(f"残高: {balance.balance}")
    print(f"利用可能: {balance.available_balance}")
    print(f"Nonce: {balance.nonce}")
```

### トランザクションを送信

```python
import hashlib
import time
import requests
from xai.core.wallet import Wallet
from xai.core.blockchain import Transaction

NODE_URL = "http://localhost:12001"
API_KEY = "あなたのAPIキー"

def send_transaction(
    wallet: Wallet,
    recipient: str,
    amount: float,
    fee: float = 0.001
) -> dict:
    """トランザクションを作成、署名、送信します。"""

    # 送信者の現在のnonceを取得
    nonce_resp = requests.get(
        f"{NODE_URL}/address/{wallet.address}/nonce",
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    nonce_resp.raise_for_status()
    nonce = nonce_resp.json()["next_nonce"]

    # トランザクションを作成
    tx = Transaction(
        sender=wallet.address,
        recipient=recipient,
        amount=amount,
        fee=fee,
        public_key=wallet.public_key,
        nonce=nonce
    )
    tx.timestamp = time.time()

    # トランザクションハッシュを計算して署名
    tx.txid = tx.calculate_hash()
    tx.signature = wallet.sign_message(tx.txid)

    # トランザクションを送信
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

# 使用例
wallet = Wallet.load_from_file("私のウォレット.json", password="強力なパスワード")
result = send_transaction(
    wallet=wallet,
    recipient="TXAIrecipient123...",
    amount=10.0,
    fee=0.001
)
print(f"トランザクションID: {result['txid']}")
print(f"メッセージ: {result['message']}")
```

### ブロックとトランザクションをクエリ

```python
import requests

NODE_URL = "http://localhost:12001"

def get_blocks(limit: int = 10, offset: int = 0) -> dict:
    """ページネーションされたブロックリストを取得します。"""
    response = requests.get(
        f"{NODE_URL}/blocks",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def get_block_by_index(index: int) -> dict:
    """インデックスで特定のブロックを取得します。"""
    response = requests.get(f"{NODE_URL}/blocks/{index}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_transaction(txid: str) -> dict:
    """IDでトランザクション詳細を取得します。"""
    response = requests.get(f"{NODE_URL}/transaction/{txid}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_address_history(address: str, limit: int = 50, offset: int = 0) -> dict:
    """アドレスのトランザクション履歴を取得します。"""
    response = requests.get(
        f"{NODE_URL}/history/{address}",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 使用例
blocks = get_blocks(limit=5)
print(f"総ブロック数: {blocks['total']}")
for block in blocks['blocks']:
    print(f"ブロック {block.get('index')}: {block.get('hash', '')[:16]}...")

# 最新ブロックを取得
latest = get_block_by_index(blocks['total'] - 1)
print(f"最新ブロックの難易度: {latest.get('difficulty')}")

# トランザクション履歴を取得
history = get_address_history("TXAIabcd1234...", limit=10)
print(f"総トランザクション数: {history['transaction_count']}")
for tx in history['transactions']:
    print(f"  TX: {tx.get('txid', '')[:16]}... 金額: {tx.get('amount')}")
```

### ノードの健全性と統計を確認

```python
import requests

NODE_URL = "http://localhost:12001"

def get_health() -> dict:
    """ノードの健全性ステータスを確認します。"""
    response = requests.get(f"{NODE_URL}/health", timeout=30)
    return response.json()

def get_stats() -> dict:
    """ブロックチェーン統計を取得します。"""
    response = requests.get(f"{NODE_URL}/stats", timeout=30)
    response.raise_for_status()
    return response.json()

def get_mempool_stats() -> dict:
    """メンプール統計と手数料の推奨を取得します。"""
    response = requests.get(f"{NODE_URL}/mempool/stats", timeout=30)
    response.raise_for_status()
    return response.json()

# 使用例
health = get_health()
print(f"ステータス: {health['status']}")
print(f"ブロックチェーン高さ: {health['blockchain'].get('height')}")
print(f"ピア数: {health['network'].get('peers')}")

stats = get_stats()
print(f"チェーン高さ: {stats.get('chain_height')}")
print(f"総供給量: {stats.get('total_circulating_supply')}")
print(f"マイニング中: {stats.get('is_mining')}")

mempool = get_mempool_stats()
print(f"保留中TX: {mempool['pressure']['pending_transactions']}")
print(f"推奨手数料（標準）: {mempool['fees']['recommended_fee_rates']['standard']}")
```

### テストネットフォーセットを請求

```python
import requests

NODE_URL = "http://localhost:12001"

def claim_faucet(address: str, api_key: str) -> dict:
    """フォーセットからテストネットトークンを請求します。"""
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

# 使用例（テストネットのみ）
result = claim_faucet("TXAIabcd1234...", "あなたのAPIキー")
print(f"受け取った金額: {result['amount']} XAI")
print(f"トランザクションID: {result['txid']}")
print(f"注意: {result['note']}")
```

---

## JavaScript/TypeScript例

### クライアントの初期化

```typescript
import { XAIClient } from '@xai/sdk';

// ローカル開発ノード
const client = new XAIClient({
  baseUrl: 'http://localhost:12001',
});

// APIキー付きテストネット
const client = new XAIClient({
  baseUrl: 'https://testnet-api.xai-blockchain.io',
  apiKey: 'あなたのAPIキー',
  timeout: 30000,
  maxRetries: 3,
});

// ノードの健全性を確認
const health = await client.blockchain.getHealth();
console.log(`ノードステータス: ${health.status}`);
```

### 残高を取得

```typescript
const NODE_URL = 'http://localhost:12001';

interface BalanceResponse {
  address: string;
  balance: number;
}

async function getBalance(address: string): Promise<BalanceResponse> {
  const response = await fetch(`${NODE_URL}/balance/${address}`);

  if (!response.ok) {
    throw new Error(`残高の取得に失敗: ${response.statusText}`);
  }

  return response.json();
}

// 使用例
const balance = await getBalance('TXAIabcd1234...');
console.log(`残高: ${balance.balance} XAI`);

// SDKを使用
import { XAIClient } from '@xai/sdk';

const client = new XAIClient();
const walletBalance = await client.wallet.getBalance('TXAIabcd1234...');
console.log(`残高: ${walletBalance.balance}`);
console.log(`利用可能: ${walletBalance.availableBalance}`);
```

### ブロックとトランザクションをクエリ

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
    throw new Error(`ブロックの取得に失敗: ${response.statusText}`);
  }

  return response.json();
}

async function getBlock(index: number): Promise<Block> {
  const response = await fetch(`${NODE_URL}/blocks/${index}`);

  if (!response.ok) {
    throw new Error(`ブロックの取得に失敗: ${response.statusText}`);
  }

  return response.json();
}

// 使用例
const blocks = await getBlocks(5);
console.log(`総ブロック数: ${blocks.total}`);

for (const block of blocks.blocks) {
  console.log(`ブロック ${block.index}: ${block.hash.slice(0, 16)}...`);
}
```

### ノードの健全性を確認

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

// 使用例
const health = await getHealth();
console.log(`ステータス: ${health.status}`);
console.log(`高さ: ${health.blockchain.height}`);
console.log(`ピア数: ${health.network.peers}`);
```

---

## APIエンドポイントリファレンス

| エンドポイント | メソッド | 説明 |
|----------------|----------|------|
| `/` | GET | ノード情報と利用可能なエンドポイント |
| `/health` | GET | 診断付き健全性チェック |
| `/stats` | GET | ブロックチェーン統計 |
| `/balance/<アドレス>` | GET | アドレス残高を取得 |
| `/address/<アドレス>/nonce` | GET | アドレスnonce情報を取得 |
| `/history/<アドレス>` | GET | トランザクション履歴（ページネーション） |
| `/blocks` | GET | ブロックリスト（ページネーション） |
| `/blocks/<インデックス>` | GET | インデックスでブロックを取得 |
| `/block/<ハッシュ>` | GET | ハッシュでブロックを取得 |
| `/transaction/<txid>` | GET | トランザクション詳細を取得 |
| `/transactions` | GET | 保留中のトランザクションリスト |
| `/send` | POST | 署名済みトランザクションを送信 |
| `/mempool` | GET | メンプール概要 |
| `/mempool/stats` | GET | 手数料の推奨 |
| `/faucet/claim` | POST | テストネットトークンを請求 |

## 認証

ほとんどの書き込み操作にはAPIキー認証が必要です：

```
X-API-Key: あなたのAPIキー
```

本番使用の場合は、OpenAPI仕様で指定されているBearer token認証も含めてください。

## エラー処理

すべてのエンドポイントは構造化されたエラー応答を返します：

```json
{
  "success": false,
  "error": "エラーの説明",
  "code": "エラーコード",
  "context": {}
}
```

一般的なエラーコード：
- `invalid_payload` - 不正なリクエストデータ
- `rate_limited` - リクエストが多すぎます
- `transaction_rejected` - トランザクション検証に失敗
- `invalid_signature` - 暗号署名が無効
