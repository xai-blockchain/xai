# XAI 블록체인 - 빠른 시작 가이드

**5분 만에 XAI 시작하기!** 이 가이드는 설치, 지갑 생성, 테스트넷 토큰 받기, 첫 번째 트랜잭션 전송을 다룹니다.

---

## XAI란?

XAI는 AI 거버넌스, 원자 스왑, 종합적인 지갑 지원을 갖춘 작업증명 블록체인입니다. 이 가이드는 테스트넷에서 빠르게 시작할 수 있도록 도와줍니다.

**경로 선택:**
- **데스크톱/서버 사용자** → 아래 1-6단계 따라하기
- **모바일 개발자** → [모바일 빠른 시작](../../user-guides/mobile_quickstart.md) 참조
- **IoT/라즈베리 파이** → [경량 노드 가이드](../../user-guides/lightweight_node_guide.md) 참조
- **라이트 클라이언트** → [라이트 클라이언트 모드](../../user-guides/light_client_mode.md) 참조

---

## 설치 옵션

가장 적합한 방법을 선택하세요:

### 옵션 A: 원라인 설치 (권장)

**Linux/macOS:**
```bash
curl -sSL https://install.xai.network | bash
```

**Windows PowerShell:**
```powershell
iwr -useb https://install.xai.network/install.ps1 | iex
```

### 옵션 B: 소스에서 설치 (개발자)

```bash
git clone https://github.com/your-org/xai.git
cd xai
pip install -c constraints.txt -e ".[dev]"
```

### 옵션 C: Docker (격리 환경)

```bash
docker pull xai/node:latest
docker run -d -p 18545:18545 -p 18546:18546 xai/node:testnet
```

### 옵션 D: 패키지 관리자

**Debian/Ubuntu:**
```bash
wget https://releases.xai.network/xai_latest_amd64.deb
sudo dpkg -i xai_latest_amd64.deb
```

**Homebrew (macOS):**
```bash
brew tap xai-blockchain/xai
brew install xai
```

---

## 1단계: 첫 번째 지갑 생성 (30초)

```bash
# 새 지갑 주소 생성
python src/xai/wallet/cli.py generate-address

# 출력:
# 지갑 생성 성공!
# 주소: TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
# 개인키: 5KYZdUEo39z3FPrtuX2QbbwGnNP5zTd7yyr2SC1j299sBCnWjss
# 중요: 개인키를 안전하게 보관하세요! 분실 시 복구할 수 없습니다.
```

**보안 알림:**
- 개인키가 자금을 관리합니다
- 누구와도 공유하지 마세요
- 비밀번호 관리자나 암호화된 파일에 저장하세요
- 적어서 안전한 곳에 보관하세요

---

## 2단계: 무료 테스트넷 토큰 받기 (1분)

**공식 테스트넷 파우셋:** https://faucet.xai.network

### 방법 A: 웹 UI (가장 쉬움)
1. https://faucet.xai.network 방문
2. TXAI 주소 입력
3. CAPTCHA 완료
4. ~2분 내에 100 XAI 수령

### 방법 B: 명령줄
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_귀하의_주소

# 출력:
# 파우셋 요청 성공!
# 100 XAI가 다음 블록에 전달됩니다 (~2분)
# 참고: 이것은 실제 가치가 없는 테스트넷 XAI입니다
```

### 방법 C: 직접 API 호출
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_귀하의_주소"}'
```

**파우셋 상세:**
- **금액:** 요청당 100 XAI
- **속도 제한:** 주소당 시간당 1회
- **전달 시간:** 다음 블록 (~2분)
- **테스트넷 전용:** 이 토큰은 실제 가치가 없습니다

---

## 3단계: 잔액 확인 (30초)

다음 블록을 위해 ~2분 기다린 후 확인:

```bash
python src/xai/wallet/cli.py balance --address TXAI_귀하의_주소

# 출력:
# 잔액: 100.00000000 XAI
# 대기 중: 0.00000000 XAI
```

**API를 통해:**
```bash
curl http://localhost:12001/account/TXAI_귀하의_주소
```

---

## 4단계: 첫 번째 트랜잭션 전송 (1분)

```bash
python src/xai/wallet/cli.py send \
  --from TXAI_귀하의_주소 \
  --to TXAI_수신자_주소 \
  --amount 10.0

# CLI가 수행하는 작업:
# 1. 검토를 위해 트랜잭션 해시 표시
# 2. 해시 접두사 입력으로 확인 요청 (보안 기능)
# 3. 개인키 입력 요청 (네트워크로 전송되지 않음)
# 4. 로컬에서 트랜잭션 서명
# 5. 네트워크에 브로드캐스트
#
# 출력:
# 트랜잭션 해시: 0xabc123...
# 트랜잭션 브로드캐스트 성공!
# 확인: 대기 중 (~2분)
```

**트랜잭션 확인 권장:**
- **소액 (<100 XAI):** 1 확인 (2분)
- **중간 금액 (100-1000 XAI):** 3 확인 (6분)
- **대액 (>1000 XAI):** 6 확인 (12분)

---

## 5단계: 블록 탐색기에서 보기 (30초)

### 웹 탐색기 (권장)
**테스트넷 탐색기:** https://explorer.xai.network/testnet

검색 가능:
- 귀하의 주소
- 트랜잭션 해시
- 블록 번호

### 로컬 탐색기 (선택 사항)
```bash
# 로컬 탐색기 시작
python src/xai/explorer.py

# 브라우저에서 열기
# http://localhost:12080
```

**탐색기 기능:**
- 실시간 블록 업데이트
- 트랜잭션 세부정보
- 주소 잔액 조회
- 네트워크 통계
- 멤풀 뷰어

---

## 6단계: 자체 노드 실행 (선택 사항, 2분)

전체 참여자로 네트워크에 참여:

```bash
# 환경 설정
export XAI_NETWORK=testnet

# 노드 시작
python -m xai.core.node

# 노드 시작 위치:
# - P2P 포트: 18545
# - RPC 포트: 18546
#
# 출력:
# [INFO] XAI 노드 시작 중...
# [INFO] 네트워크: 테스트넷
# [INFO] 블록체인 동기화 중 (0 / 22341 블록)...
```

**채굴 시작 (선택 사항):**
```bash
export MINER_ADDRESS=TXAI_귀하의_주소
python -m xai.core.node --miner $MINER_ADDRESS

# 채굴 보상: 블록당 50 XAI
# 블록 시간: ~2분
# 난이도: 2016 블록마다 조정
```

---

## 구성

### 환경 변수

```bash
# 네트워크 선택
export XAI_NETWORK=testnet           # 또는 'mainnet'

# 포트
export XAI_PORT=18545                # P2P 포트 (메인넷은 8545)
export XAI_RPC_PORT=18546            # RPC 포트 (메인넷은 8546)

# 노드 동작
export XAI_LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
export XAI_DATA_DIR=~/.xai           # 블록체인 데이터 디렉토리
export MINER_ADDRESS=TXAI_...        # 채굴 보상 주소

# 성능
export XAI_CACHE_TTL=60              # 응답 캐시 TTL (초)
export XAI_PARTIAL_SYNC_ENABLED=1    # 체크포인트 동기화 활성화
```

### 네트워크 엔드포인트

**테스트넷:**
- RPC: `http://localhost:12001` 또는 `https://testnet-rpc.xai.network`
- WebSocket: `ws://localhost:12003`
- 파우셋: `https://faucet.xai.network`
- 탐색기: `https://explorer.xai.network/testnet`

**메인넷:**
- RPC: `http://localhost:12001` 또는 `https://rpc.xai.network`
- WebSocket: `ws://localhost:12003`
- 탐색기: `https://explorer.xai.network`

---

## 자주 사용하는 명령어

### 지갑 작업
```bash
# 새 지갑 생성
python src/xai/wallet/cli.py generate-address

# 잔액 확인
python src/xai/wallet/cli.py balance --address TXAI_주소

# 트랜잭션 전송
python src/xai/wallet/cli.py send --from TXAI_발신자 --to TXAI_수신자 --amount 10.0

# 개인키 내보내기 (안전하게 보관!)
python src/xai/wallet/cli.py export-key --address TXAI_주소

# 지갑 가져오기
python src/xai/wallet/cli.py import-key --private-key 귀하의_개인키

# 테스트넷 토큰 요청
python src/xai/wallet/cli.py request-faucet --address TXAI_주소
```

### 노드 작업
```bash
# 전체 노드 시작
python -m xai.core.node

# 채굴로 시작
python -m xai.core.node --miner TXAI_주소

# 노드 상태 확인
curl http://localhost:12001/health

# 연결된 피어 보기
curl http://localhost:12001/peers

# 블록체인 정보 가져오기
curl http://localhost:12001/blockchain/stats
```

### 블록체인 쿼리
```bash
# 번호로 블록 가져오기
curl http://localhost:12001/block/12345

# 트랜잭션 가져오기
curl http://localhost:12001/transaction/TX_해시

# 주소 잔액 가져오기
curl http://localhost:12001/account/TXAI_주소
```

---

## 문제 해결

### 설치 문제

**"명령을 찾을 수 없음"**
- xai 디렉토리에 있는지 확인하세요
- 가상 환경을 사용 중이라면 활성화: `source venv/bin/activate`
- Python 버전 확인: `python --version` (3.10+ 필요)

**"권한 거부"**
- 시스템 전체 설치에 `sudo` 사용: `sudo pip install -e .`
- 또는 사용자 디렉토리에 설치: `pip install --user -e .`

### 지갑 문제

**"파우셋 속도 제한 초과"**
- 파우셋은 주소당 시간당 1회 요청 허용
- 60분 기다린 후 다시 시도
- 또는 테스트용 새 주소 생성

**"잔액 부족"**
- 잔액 확인: `python src/xai/wallet/cli.py balance --address TXAI_주소`
- 금액 + 수수료 (일반적으로 0.001 XAI)가 충분한지 확인
- 필요 시 파우셋에서 더 요청

### 노드 문제

**"노드에 연결할 수 없음"**
- 노드가 실행 중인지 확인: `python -m xai.core.node`
- 올바른 포트 확인 (테스트넷 18546, 메인넷 8546)
- 방화벽이 연결을 허용하는지 확인

**"트랜잭션이 확인되지 않음"**
- XAI는 2분 블록 시간입니다 - 기다려 주세요
- 멤풀 확인: `curl http://localhost:12001/mempool`
- 트랜잭션 브로드캐스트 확인: `curl http://localhost:12001/transaction/TX_해시`

**"동기화가 너무 느림"**
- 체크포인트 동기화 활성화: `export XAI_PARTIAL_SYNC_ENABLED=1`
- 더 빠른 시작을 위해 라이트 클라이언트 사용
- 인터넷 연결 확인

---

## 다음 단계

이제 설정이 완료되었으니 XAI의 고급 기능을 탐색하세요:

### 사용자 가이드
- **[테스트넷 가이드](../../user-guides/TESTNET_GUIDE.md)** - 완전한 테스트넷 안내
- **[지갑 설정](../../user-guides/wallet-setup.md)** - 다중 서명, HD 지갑, 고급 기능
- **[채굴 가이드](../../user-guides/mining.md)** - 상세한 채굴 지침
- **[라이트 클라이언트 가이드](../../user-guides/LIGHT_CLIENT_GUIDE.md)** - 경량 노드 실행

### 개발자 가이드
- **[API 문서](../../api/rest-api.md)** - XAI에서 dApp 구축
- **[TypeScript SDK](../../api/sdk.md)** - JavaScript/TypeScript 통합
- **[Python SDK](../../../src/xai/sdk/python/README.md)** - Python 개발
- **[모바일 빠른 시작](../../user-guides/mobile_quickstart.md)** - React Native/Flutter SDK

### 고급 주제
- **[원자 스왑](../../advanced/atomic-swaps.md)** - 크로스체인 거래
- **[스마트 컨트랙트](../../architecture/evm_interpreter.md)** - 컨트랙트 배포
- **[거버넌스](../../user-guides/staking.md)** - 거버넌스 참여

---

## 네트워크 정보

### 테스트넷 매개변수

| 매개변수 | 값 |
|----------|-----|
| 네트워크 ID | 0xABCD |
| 주소 접두사 | TXAI |
| P2P 포트 | 18545 |
| RPC 포트 | 18546 |
| 블록 시간 | 2분 |
| 블록 보상 | 50 XAI |
| 난이도 조정 | 2016 블록마다 |
| 최대 공급량 | 121,000,000 XAI |
| 반감기 | 210,000 블록마다 |

### 메인넷 매개변수 (향후)

| 매개변수 | 값 |
|----------|-----|
| 네트워크 ID | 0x5841 |
| 주소 접두사 | XAI |
| P2P 포트 | 8545 |
| RPC 포트 | 8546 |
| 블록 시간 | 2분 |
| 블록 보상 | 50 XAI (반감됨) |
| 최대 공급량 | 121,000,000 XAI |

---

## 완료!

**이제 준비 완료:**
- XAI 블록체인 설치됨
- 테스트넷 토큰이 있는 지갑
- 첫 번째 트랜잭션 전송 완료
- 기본 작업 이해

**여정을 계속하세요:**
1. [채굴](../../user-guides/mining.md)을 시도하여 보상 획득
2. XAI에서 [dApp](../../api/rest-api.md) 구축
3. 라즈베리 파이에서 [라이트 클라이언트](../../user-guides/light_client_mode.md) 실행
4. 문서에서 고급 기능 탐색
5. GitHub에서 프로젝트에 기여

**XAI 블록체인 개발에 오신 것을 환영합니다!**

---

*마지막 업데이트: 2025년 1월 | XAI 버전: 0.2.0*
