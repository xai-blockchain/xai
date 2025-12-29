# XAI 블록체인

[![CI](https://github.com/xai-blockchain/xai/actions/workflows/ci.yml/badge.svg)](https://github.com/xai-blockchain/xai/actions/workflows/ci.yml) [![Security](https://github.com/xai-blockchain/xai/actions/workflows/security.yml/badge.svg)](https://github.com/xai-blockchain/xai/actions/workflows/security.yml) [![codecov](https://codecov.io/gh/xai-blockchain/xai/branch/main/graph/badge.svg)](https://codecov.io/gh/xai-blockchain/xai) [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/) [![XAI Testnet](https://img.shields.io/badge/Testnet-Active-success)](https://faucet.xai.network)

**[English](../../../README.md)** | **[简体中文](../zh-CN/README.md)** | **한국어** | **[日本語](../ja/README.md)**

## AI 거버넌스와 통합 지갑을 갖춘 작업증명 블록체인

XAI는 작업증명 합의 메커니즘, 지능형 AI 거버넌스 시스템, 크로스체인 원자 스왑 지원, 종합적인 지갑 관리 기능을 갖춘 프로덕션 준비 블록체인 구현입니다. 개인 사용자와 기업 규정 준수 요구 사항 모두에 적합합니다.

---

## 5분 만에 시작하기

### 대화형 설치 마법사 (권장)

XAI 노드를 설정하는 가장 쉬운 방법은 대화형 마법사를 사용하는 것입니다:

```bash
# 저장소 복제 및 이동
git clone https://github.com/xai-blockchain/xai.git
cd xai

# 설치 마법사 실행
python scripts/setup_wizard.py
```

마법사가 안내하는 내용:
- 네트워크 선택 (테스트넷/메인넷)
- 노드 모드 구성 (전체/간소/라이트/아카이브)
- 포트 구성 및 충돌 감지
- 지갑 생성
- 보안 구성
- 선택적 systemd 서비스 설치

**[→ 설치 마법사 문서 보기](../../scripts/SETUP_WIZARD.md)**

### 수동 설치

**XAI가 처음이신가요?** **[빠른 시작 가이드](QUICKSTART.md)**를 따라하세요 - 5분 만에 실행:
- 다양한 설치 옵션 (pip, Docker, 패키지)
- 첫 번째 지갑 생성
- 파우셋에서 무료 테스트넷 토큰 받기
- 첫 번째 트랜잭션 전송
- 블록 탐색기에서 확인

**[→ 여기서 시작: 빠른 시작 가이드](QUICKSTART.md)** ← **완전한 초보자 가이드**

---

## 테스트넷 파우셋 - 무료 XAI 받기

**공식 공개 파우셋:** https://faucet.xai.network

테스트 및 개발을 위해 100개의 무료 테스트넷 XAI 토큰을 즉시 받으세요!

### 빠른 접근 방법

**1. 웹 UI (가장 쉬움):**
```
방문: https://faucet.xai.network
TXAI 주소 입력
"토큰 요청" 클릭
```

**2. 명령줄:**
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_귀하의_주소
```

**3. 직접 API 호출:**
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_귀하의_주소"}'
```

### 파우셋 사양

| 매개변수 | 값 |
|----------|-----|
| **금액** | 요청당 100 XAI |
| **속도 제한** | 주소당 시간당 1회 |
| **전달 시간** | 다음 블록 (~2분) |
| **토큰 가치** | 테스트넷 전용 - 실제 가치 없음 |
| **공개 파우셋** | https://faucet.xai.network |
| **로컬 엔드포인트** | `http://localhost:12001/faucet/claim` |

**참고:** 테스트넷 XAI는 실제 가치가 없습니다. 개발 및 테스트에 자유롭게 사용하세요.

---

## 개요

XAI는 Python 기반 블록체인으로, UTXO 트랜잭션 모델, 모듈식 노드, 지갑 CLI, 거버넌스 프리미티브, 간단한 웹 탐색기를 갖춘 프로덕션급 작업증명(PoW) 체인을 구현합니다. 코드베이스는 명확한 관심사 분리와 테스트를 갖춘 전문 Python 프로젝트로 구성되어 있습니다.

---

## 주요 기능

- 조정 가능한 난이도의 작업증명 (SHA-256)
- 서명, 입력/출력, RBF 플래그를 지원하는 UTXO 기반 트랜잭션
- 라이트 클라이언트 검증을 위한 머클 증명
- 지갑 CLI: 생성, 잔액, 전송, 가져오기/내보내기, 파우셋 도우미
- CORS 정책 및 요청 유효성 검사를 갖춘 노드 API (Flask)
- P2P 네트워킹 및 합의 관리자 프레임워크
- 거버넌스 모듈 (제안 관리자, 투표 잠금, 제곱 투표)
- 보안 미들웨어 및 구조화된 메트릭
- 기본 블록 탐색기 (Flask)
- 고급 주문 유형을 지원하는 지갑 거래 관리자 (TWAP 스케줄러, VWAP 프로파일, 아이스버그, 추적 스탑)

## 빠른 시작 (< 5분)

### 사전 요구 사항

- Python 3.10 이상
- 최소 2GB RAM
- 블록체인 데이터용 10GB+ 디스크 공간

### 설치

```bash
# 프로젝트 루트에서 의존성 설치 (재현성을 위한 제약 조건 포함)
pip install -c constraints.txt -e ".[dev]"
# 선택 사항: QUIC 지원 활성화
pip install -e ".[network]"

# 설치 확인
python -m pytest --co -q
```

### 노드 시작

```bash
# 노드 실행 (기본값 표시)
export XAI_NETWORK=development
xai-node
```

노드는 포트 12001 (RPC), 12002 (P2P), 12003 (WebSocket)에서 시작됩니다.

### 채굴 시작

```bash
# 먼저 지갑 주소 생성 (또는 기존 주소 사용)
xai-wallet generate-address

# 귀하의 주소로 채굴 시작
export MINER_ADDRESS=귀하의_XAI_주소
xai-node --miner $MINER_ADDRESS
```

### CLI 도구

패키지 설치 후 (`pip install -e .`), 세 가지 콘솔 명령을 사용할 수 있습니다:

- `xai` - 블록체인, 지갑, 채굴, AI, 네트워크 명령이 포함된 메인 CLI
- `xai-wallet` - 지갑 전용 CLI (레거시 인터페이스)
- `xai-node` - 노드 관리

```bash
# 메인 CLI (권장)
xai wallet balance --address 귀하의_XAI_주소
xai blockchain info
xai ai submit-job --model gpt-4 --data "..."

# 레거시 지갑 CLI (여전히 지원)
xai-wallet request-faucet --address 귀하의_XAI_주소
xai-wallet generate-address
```

---

## 구성

### 네트워크 선택

```bash
# 개발 환경 (기본값)
export XAI_NETWORK=development
export XAI_RPC_PORT=18546
```

### 환경 변수

```bash
XAI_NETWORK          # 테스트넷 또는 메인넷 (기본값: 테스트넷)
XAI_PORT             # P2P 포트 (기본값: 테스트넷 18545, 메인넷 8545)
XAI_RPC_PORT         # RPC 포트 (기본값: 테스트넷 18546, 메인넷 8546)
XAI_LOG_LEVEL        # DEBUG, INFO, WARNING, ERROR (기본값: INFO)
XAI_DATA_DIR         # 블록체인 데이터 디렉토리
MINER_ADDRESS        # 채굴 보상을 받을 주소
```

추가 구성 옵션은 `src/xai/config/`를 참조하세요.

---

## 네트워크 매개변수

### 테스트넷 구성

| 매개변수 | 값 |
|----------|-----|
| 네트워크 ID | 0xABCD |
| 포트 | 18545 |
| RPC 포트 | 18546 |
| 주소 접두사 | TXAI |
| 블록 시간 | 2분 |
| 최대 공급량 | 121,000,000 XAI |

### 메인넷 구성

| 매개변수 | 값 |
|----------|-----|
| 네트워크 ID | 0x5841 |
| 포트 | 8545 |
| RPC 포트 | 8546 |
| 주소 접두사 | XAI |
| 블록 시간 | 2분 |
| 최대 공급량 | 121,000,000 XAI |

---

## 기여하기

개발자, 연구원, 블록체인 애호가의 기여를 환영합니다.

**기여하기 전에:**

1. [CONTRIBUTING.md](../../../CONTRIBUTING.md)를 읽고 개발 가이드라인 확인
2. [SECURITY.md](../../../SECURITY.md)를 검토하여 보안 고려사항 확인
3. 기존 이슈 및 풀 리퀘스트 확인
4. 코드 스타일 및 테스트 요구 사항 준수

---

## 라이선스

MIT 라이선스 - 전체 텍스트는 [LICENSE](../../../LICENSE) 파일을 참조하세요.

이 프로젝트는 상업적 및 비상업적 사용을 모두 허용하는 MIT 라이선스로 배포됩니다.

---

## 보안 공지

**중요:** 이 소프트웨어는 실험적이며 활발히 개발 중입니다. 암호화폐 시스템에는 고유한 위험이 있습니다:

- 메인넷 사용 전에 테스트넷에서 충분히 테스트하세요
- 개인키를 안전하게 보관하세요
- 시드 문구나 개인키를 절대 공유하지 마세요
- 자금을 투입하기 전에 기술을 이해하세요
- 보안 문제는 [SECURITY.md](../../../SECURITY.md)를 참조하세요

---

## 면책 조항

XAI는 개념 증명 블록체인 구현입니다. 프로덕션 품질을 추구하지만, 사용자는 암호화폐 시스템의 실험적 특성을 이해해야 합니다. 네트워크는 활발히 개발 중이며 적절한 주의를 기울여 사용해야 합니다. 개발자는 미래 실행 가능성, 기능 가용성 또는 네트워크 안정성에 대해 보장하지 않습니다.

---

**최종 업데이트**: 2025년 1월 | **버전**: 0.2.0 | **상태**: 테스트넷 활성
