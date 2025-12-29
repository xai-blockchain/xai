# SDK 통합 가이드

이 가이드는 Python과 JavaScript/TypeScript를 사용하여 XAI 블록체인과 통합하는 예제를 제공합니다.

## 설치

### Python SDK

```bash
pip install xai-sdk
# 또는 소스에서 설치:
pip install -e ./src/xai/sdk/python
```

### JavaScript/TypeScript SDK

```bash
npm install @xai/sdk
# 또는 소스에서 설치:
cd src/xai/sdk/typescript && npm install && npm run build
```

---

## Python 예제

### 클라이언트 초기화

```python
from xai_sdk import XAIClient

# 로컬 개발 노드 (기본 포트 12001)
client = XAIClient(base_url="http://localhost:12001")

# API 키가 있는 테스트넷
client = XAIClient(
    base_url="https://testnet-api.xai-blockchain.io",
    api_key="귀하의-api-키",
    timeout=30,
    max_retries=3
)

# 자동 정리를 위한 컨텍스트 관리자 사용
with XAIClient() as client:
    health = client.health_check()
    print(f"노드 상태: {health['status']}")
```

### 지갑/키페어 생성

```python
from xai.core.wallet import Wallet

# secp256k1 키페어로 새 지갑 생성
wallet = Wallet()
print(f"주소: {wallet.address}")
print(f"공개키: {wallet.public_key}")
# 경고: 프로덕션에서 개인키를 로깅하거나 노출하지 마세요!

# 기존 개인키로 생성
wallet = Wallet(private_key="귀하의_16진수_개인키")

# BIP-39 니모닉에서 생성 (24단어)
mnemonic = Wallet.generate_mnemonic(strength=256)  # 24단어
print(f"니모닉: {mnemonic}")  # 안전하게 저장하세요!

# 니모닉에서 지갑 복구
wallet = Wallet.from_mnemonic(
    mnemonic_phrase=mnemonic,
    passphrase="선택적_추가_보안",
    account_index=0,
    address_index=0
)

# 암호화된 지갑을 파일로 저장
wallet.save_to_file("내_지갑.json", password="강력한_비밀번호")

# 암호화된 파일에서 지갑 로드
loaded_wallet = Wallet.load_from_file("내_지갑.json", password="강력한_비밀번호")

# WIF(지갑 가져오기 형식)로 내보내기
wif = wallet.export_to_wif()
restored = Wallet.import_from_wif(wif)

# 메시지 서명
message = "안녕하세요, XAI!"
signature = wallet.sign_message(message)
is_valid = wallet.verify_signature(message, signature, wallet.public_key)
```

### 잔액 조회

```python
import requests

NODE_URL = "http://localhost:12001"

def get_balance(address: str) -> dict:
    """XAI 주소의 잔액을 조회합니다."""
    response = requests.get(
        f"{NODE_URL}/balance/{address}",
        headers={"X-API-Key": "귀하의-api-키"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 사용 예제
balance_info = get_balance("TXAIabcd1234...")
print(f"주소: {balance_info['address']}")
print(f"잔액: {balance_info['balance']} XAI")

# SDK 클라이언트 사용
from xai_sdk import XAIClient

with XAIClient() as client:
    balance = client.wallet.get_balance("TXAIabcd1234...")
    print(f"잔액: {balance.balance}")
    print(f"사용 가능: {balance.available_balance}")
    print(f"Nonce: {balance.nonce}")
```

### 트랜잭션 전송

```python
import hashlib
import time
import requests
from xai.core.wallet import Wallet
from xai.core.blockchain import Transaction

NODE_URL = "http://localhost:12001"
API_KEY = "귀하의-api-키"

def send_transaction(
    wallet: Wallet,
    recipient: str,
    amount: float,
    fee: float = 0.001
) -> dict:
    """트랜잭션을 생성, 서명, 전송합니다."""

    # 발신자의 현재 nonce 가져오기
    nonce_resp = requests.get(
        f"{NODE_URL}/address/{wallet.address}/nonce",
        headers={"X-API-Key": API_KEY},
        timeout=30
    )
    nonce_resp.raise_for_status()
    nonce = nonce_resp.json()["next_nonce"]

    # 트랜잭션 생성
    tx = Transaction(
        sender=wallet.address,
        recipient=recipient,
        amount=amount,
        fee=fee,
        public_key=wallet.public_key,
        nonce=nonce
    )
    tx.timestamp = time.time()

    # 트랜잭션 해시 계산 및 서명
    tx.txid = tx.calculate_hash()
    tx.signature = wallet.sign_message(tx.txid)

    # 트랜잭션 제출
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

# 사용 예제
wallet = Wallet.load_from_file("내_지갑.json", password="강력한_비밀번호")
result = send_transaction(
    wallet=wallet,
    recipient="TXAIrecipient123...",
    amount=10.0,
    fee=0.001
)
print(f"트랜잭션 ID: {result['txid']}")
print(f"메시지: {result['message']}")
```

### 블록 및 트랜잭션 쿼리

```python
import requests

NODE_URL = "http://localhost:12001"

def get_blocks(limit: int = 10, offset: int = 0) -> dict:
    """페이지네이션된 블록 목록을 가져옵니다."""
    response = requests.get(
        f"{NODE_URL}/blocks",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def get_block_by_index(index: int) -> dict:
    """인덱스로 특정 블록을 가져옵니다."""
    response = requests.get(f"{NODE_URL}/blocks/{index}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_transaction(txid: str) -> dict:
    """ID로 트랜잭션 세부정보를 가져옵니다."""
    response = requests.get(f"{NODE_URL}/transaction/{txid}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_address_history(address: str, limit: int = 50, offset: int = 0) -> dict:
    """주소의 트랜잭션 히스토리를 가져옵니다."""
    response = requests.get(
        f"{NODE_URL}/history/{address}",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 사용 예제
blocks = get_blocks(limit=5)
print(f"총 블록 수: {blocks['total']}")
for block in blocks['blocks']:
    print(f"블록 {block.get('index')}: {block.get('hash', '')[:16]}...")

# 최신 블록 가져오기
latest = get_block_by_index(blocks['total'] - 1)
print(f"최신 블록 난이도: {latest.get('difficulty')}")

# 트랜잭션 히스토리 가져오기
history = get_address_history("TXAIabcd1234...", limit=10)
print(f"총 트랜잭션 수: {history['transaction_count']}")
for tx in history['transactions']:
    print(f"  TX: {tx.get('txid', '')[:16]}... 금액: {tx.get('amount')}")
```

### 노드 상태 및 통계 확인

```python
import requests

NODE_URL = "http://localhost:12001"

def get_health() -> dict:
    """노드 상태를 확인합니다."""
    response = requests.get(f"{NODE_URL}/health", timeout=30)
    return response.json()

def get_stats() -> dict:
    """블록체인 통계를 가져옵니다."""
    response = requests.get(f"{NODE_URL}/stats", timeout=30)
    response.raise_for_status()
    return response.json()

def get_mempool_stats() -> dict:
    """멤풀 통계 및 수수료 권장사항을 가져옵니다."""
    response = requests.get(f"{NODE_URL}/mempool/stats", timeout=30)
    response.raise_for_status()
    return response.json()

# 사용 예제
health = get_health()
print(f"상태: {health['status']}")
print(f"블록체인 높이: {health['blockchain'].get('height')}")
print(f"피어 수: {health['network'].get('peers')}")

stats = get_stats()
print(f"체인 높이: {stats.get('chain_height')}")
print(f"총 공급량: {stats.get('total_circulating_supply')}")
print(f"채굴 중: {stats.get('is_mining')}")

mempool = get_mempool_stats()
print(f"대기 중 TX: {mempool['pressure']['pending_transactions']}")
print(f"권장 수수료 (표준): {mempool['fees']['recommended_fee_rates']['standard']}")
```

### 테스트넷 파우셋 요청

```python
import requests

NODE_URL = "http://localhost:12001"

def claim_faucet(address: str, api_key: str) -> dict:
    """파우셋에서 테스트넷 토큰을 요청합니다."""
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

# 사용 예제 (테스트넷 전용)
result = claim_faucet("TXAIabcd1234...", "귀하의-api-키")
print(f"받은 금액: {result['amount']} XAI")
print(f"트랜잭션 ID: {result['txid']}")
print(f"참고: {result['note']}")
```

---

## JavaScript/TypeScript 예제

### 클라이언트 초기화

```typescript
import { XAIClient } from '@xai/sdk';

// 로컬 개발 노드
const client = new XAIClient({
  baseUrl: 'http://localhost:12001',
});

// API 키가 있는 테스트넷
const client = new XAIClient({
  baseUrl: 'https://testnet-api.xai-blockchain.io',
  apiKey: '귀하의-api-키',
  timeout: 30000,
  maxRetries: 3,
});

// 노드 상태 확인
const health = await client.blockchain.getHealth();
console.log(`노드 상태: ${health.status}`);
```

### 잔액 조회

```typescript
const NODE_URL = 'http://localhost:12001';

interface BalanceResponse {
  address: string;
  balance: number;
}

async function getBalance(address: string): Promise<BalanceResponse> {
  const response = await fetch(`${NODE_URL}/balance/${address}`);

  if (!response.ok) {
    throw new Error(`잔액 조회 실패: ${response.statusText}`);
  }

  return response.json();
}

// 사용 예제
const balance = await getBalance('TXAIabcd1234...');
console.log(`잔액: ${balance.balance} XAI`);

// SDK 사용
import { XAIClient } from '@xai/sdk';

const client = new XAIClient();
const walletBalance = await client.wallet.getBalance('TXAIabcd1234...');
console.log(`잔액: ${walletBalance.balance}`);
console.log(`사용 가능: ${walletBalance.availableBalance}`);
```

### 블록 및 트랜잭션 쿼리

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
    throw new Error(`블록 조회 실패: ${response.statusText}`);
  }

  return response.json();
}

async function getBlock(index: number): Promise<Block> {
  const response = await fetch(`${NODE_URL}/blocks/${index}`);

  if (!response.ok) {
    throw new Error(`블록 조회 실패: ${response.statusText}`);
  }

  return response.json();
}

// 사용 예제
const blocks = await getBlocks(5);
console.log(`총 블록 수: ${blocks.total}`);

for (const block of blocks.blocks) {
  console.log(`블록 ${block.index}: ${block.hash.slice(0, 16)}...`);
}
```

### 노드 상태 확인

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

// 사용 예제
const health = await getHealth();
console.log(`상태: ${health.status}`);
console.log(`높이: ${health.blockchain.height}`);
console.log(`피어 수: ${health.network.peers}`);
```

---

## API 엔드포인트 참조

| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/` | GET | 노드 정보 및 사용 가능한 엔드포인트 |
| `/health` | GET | 진단이 포함된 상태 확인 |
| `/stats` | GET | 블록체인 통계 |
| `/balance/<주소>` | GET | 주소 잔액 조회 |
| `/address/<주소>/nonce` | GET | 주소 nonce 정보 조회 |
| `/history/<주소>` | GET | 트랜잭션 히스토리 (페이지네이션) |
| `/blocks` | GET | 블록 목록 (페이지네이션) |
| `/blocks/<인덱스>` | GET | 인덱스로 블록 조회 |
| `/block/<해시>` | GET | 해시로 블록 조회 |
| `/transaction/<txid>` | GET | 트랜잭션 세부정보 조회 |
| `/transactions` | GET | 대기 중 트랜잭션 목록 |
| `/send` | POST | 서명된 트랜잭션 제출 |
| `/mempool` | GET | 멤풀 개요 |
| `/mempool/stats` | GET | 수수료 권장사항 |
| `/faucet/claim` | POST | 테스트넷 토큰 요청 |

## 인증

대부분의 쓰기 작업에는 API 키 인증이 필요합니다:

```
X-API-Key: 귀하의-api-키
```

프로덕션 사용시 OpenAPI 스펙에 지정된 Bearer 토큰 인증도 포함하세요.

## 오류 처리

모든 엔드포인트는 구조화된 오류 응답을 반환합니다:

```json
{
  "success": false,
  "error": "오류 설명",
  "code": "오류_코드",
  "context": {}
}
```

일반적인 오류 코드:
- `invalid_payload` - 잘못된 형식의 요청 데이터
- `rate_limited` - 너무 많은 요청
- `transaction_rejected` - 트랜잭션 검증 실패
- `invalid_signature` - 암호화 서명 무효
