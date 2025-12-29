# XAI ブロックチェーン

[![CI](https://github.com/xai-blockchain/xai/actions/workflows/ci.yml/badge.svg)](https://github.com/xai-blockchain/xai/actions/workflows/ci.yml) [![Security](https://github.com/xai-blockchain/xai/actions/workflows/security.yml/badge.svg)](https://github.com/xai-blockchain/xai/actions/workflows/security.yml) [![codecov](https://codecov.io/gh/xai-blockchain/xai/branch/main/graph/badge.svg)](https://codecov.io/gh/xai-blockchain/xai) [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/) [![XAI Testnet](https://img.shields.io/badge/Testnet-Active-success)](https://faucet.xai.network)

**[English](../../../README.md)** | **[简体中文](../zh-CN/README.md)** | **[한국어](../ko/README.md)** | **日本語**

## AIガバナンスと統合ウォレットを備えたProof-of-Workブロックチェーン

XAIは、Proof-of-Work合意メカニズム、インテリジェントAIガバナンスシステム、クロスチェーンアトミックスワップサポート、包括的なウォレット管理機能を備えた本番環境対応のブロックチェーン実装です。個人ユーザーと企業コンプライアンス要件の両方に適しています。

---

## 5分でスタート

### インタラクティブセットアップウィザード（推奨）

XAIノードをセットアップする最も簡単な方法は、インタラクティブウィザードを使用することです：

```bash
# リポジトリをクローンして移動
git clone https://github.com/xai-blockchain/xai.git
cd xai

# セットアップウィザードを実行
python scripts/setup_wizard.py
```

ウィザードがガイドする内容：
- ネットワーク選択（テストネット/メインネット）
- ノードモード構成（フル/プルーニング/ライト/アーカイブ）
- ポート構成と競合検出
- ウォレット作成
- セキュリティ構成
- オプションのsystemdサービスインストール

**[→ セットアップウィザードドキュメントを見る](../../scripts/SETUP_WIZARD.md)**

### 手動セットアップ

**XAIが初めてですか？** **[クイックスタートガイド](QUICKSTART.md)**に従ってください - 5分で実行可能：
- 複数のインストールオプション（pip、Docker、パッケージ）
- 最初のウォレット作成
- フォーセットから無料テストネットトークンを取得
- 最初のトランザクションを送信
- ブロックエクスプローラーで確認

**[→ ここからスタート：クイックスタートガイド](QUICKSTART.md)** ← **完全な初心者ガイド**

---

## テストネットフォーセット - 無料XAIを入手

**公式パブリックフォーセット：** https://faucet.xai.network

テストと開発用に100個の無料テストネットXAIトークンを即座に入手！

### クイックアクセス方法

**1. Web UI（最も簡単）：**
```
アクセス：https://faucet.xai.network
TXAIアドレスを入力
「トークンをリクエスト」をクリック
```

**2. コマンドライン：**
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_あなたのアドレス
```

**3. 直接API呼び出し：**
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_あなたのアドレス"}'
```

### フォーセット仕様

| パラメータ | 値 |
|------------|-----|
| **金額** | リクエストごとに100 XAI |
| **レート制限** | アドレスごとに1時間1回 |
| **配達時間** | 次のブロック（約2分） |
| **トークン価値** | テストネット専用 - 実際の価値なし |
| **パブリックフォーセット** | https://faucet.xai.network |
| **ローカルエンドポイント** | `http://localhost:12001/faucet/claim` |

**注意：** テストネットXAIには実際の価値がありません。開発とテストに自由にお使いください。

---

## 概要

XAIは、UTXOトランザクションモデル、モジュラーノード、ウォレットCLI、ガバナンスプリミティブ、シンプルなWebエクスプローラーを備えた本番グレードのProof-of-Work（PoW）チェーンを実装するPythonベースのブロックチェーンです。コードベースは、明確な関心事の分離とテストを備えたプロフェッショナルなPythonプロジェクトとして構造化されています。

---

## 主な機能

- 調整可能な難易度を持つProof-of-Work（SHA-256）
- 署名、入力/出力、RBFフラグをサポートするUTXOベースのトランザクション
- ライトクライアント検証用のマークル証明
- ウォレットCLI：生成、残高、送信、インポート/エクスポート、フォーセットヘルパー
- CORSポリシーとリクエスト検証を備えたノードAPI（Flask）
- P2Pネットワーキングとコンセンサスマネージャーフレームワーク
- ガバナンスモジュール（提案マネージャー、投票ロック、二次投票）
- セキュリティミドルウェアと構造化メトリクス
- 基本ブロックエクスプローラー（Flask）
- 高度な注文タイプをサポートするウォレット取引マネージャー（TWAPスケジューラー、VWAPプロファイル、アイスバーグ、トレーリングストップ）

## クイックスタート（5分以内）

### 前提条件

- Python 3.10以上
- 最小2GB RAM
- ブロックチェーンデータ用に10GB以上のディスク容量

### インストール

```bash
# プロジェクトルートから依存関係をインストール（再現性のための制約付き）
pip install -c constraints.txt -e ".[dev]"
# オプション：QUICサポートを有効化
pip install -e ".[network]"

# インストールを確認
python -m pytest --co -q
```

### ノードを起動

```bash
# ノードを実行（デフォルト値を表示）
export XAI_NETWORK=development
xai-node
```

ノードはポート12001（RPC）、12002（P2P）、12003（WebSocket）で起動します。

### マイニングを開始

```bash
# まずウォレットアドレスを生成（または既存のものを使用）
xai-wallet generate-address

# あなたのアドレスでマイニングを開始
export MINER_ADDRESS=あなたのXAIアドレス
xai-node --miner $MINER_ADDRESS
```

### CLIツール

パッケージをインストール後（`pip install -e .`）、3つのコンソールコマンドが利用可能です：

- `xai` - ブロックチェーン、ウォレット、マイニング、AI、ネットワークコマンドを含むメインCLI
- `xai-wallet` - ウォレット専用CLI（レガシーインターフェース）
- `xai-node` - ノード管理

```bash
# メインCLI（推奨）
xai wallet balance --address あなたのXAIアドレス
xai blockchain info
xai ai submit-job --model gpt-4 --data "..."

# レガシーウォレットCLI（引き続きサポート）
xai-wallet request-faucet --address あなたのXAIアドレス
xai-wallet generate-address
```

---

## 構成

### ネットワーク選択

```bash
# 開発環境（デフォルト）
export XAI_NETWORK=development
export XAI_RPC_PORT=18546
```

### 環境変数

```bash
XAI_NETWORK          # テストネットまたはメインネット（デフォルト：テストネット）
XAI_PORT             # P2Pポート（デフォルト：テストネット18545、メインネット8545）
XAI_RPC_PORT         # RPCポート（デフォルト：テストネット18546、メインネット8546）
XAI_LOG_LEVEL        # DEBUG, INFO, WARNING, ERROR（デフォルト：INFO）
XAI_DATA_DIR         # ブロックチェーンデータディレクトリ
MINER_ADDRESS        # マイニング報酬を受け取るアドレス
```

追加の構成オプションについては`src/xai/config/`を参照してください。

---

## ネットワークパラメータ

### テストネット構成

| パラメータ | 値 |
|------------|-----|
| ネットワークID | 0xABCD |
| ポート | 18545 |
| RPCポート | 18546 |
| アドレスプレフィックス | TXAI |
| ブロック時間 | 2分 |
| 最大供給量 | 121,000,000 XAI |

### メインネット構成

| パラメータ | 値 |
|------------|-----|
| ネットワークID | 0x5841 |
| ポート | 8545 |
| RPCポート | 8546 |
| アドレスプレフィックス | XAI |
| ブロック時間 | 2分 |
| 最大供給量 | 121,000,000 XAI |

---

## 貢献

開発者、研究者、ブロックチェーン愛好家からの貢献を歓迎します。

**貢献する前に：**

1. 開発ガイドラインについて[CONTRIBUTING.md](../../../CONTRIBUTING.md)をお読みください
2. セキュリティ考慮事項について[SECURITY.md](../../../SECURITY.md)を確認してください
3. 既存のissueとプルリクエストをチェックしてください
4. コードスタイルとテスト要件に従ってください

---

## ライセンス

MITライセンス - 完全なテキストは[LICENSE](../../../LICENSE)ファイルを参照してください。

このプロジェクトは、商用および非商用使用の両方を許可するMITライセンスの下でリリースされています。

---

## セキュリティに関するお知らせ

**重要：** このソフトウェアは実験的であり、活発に開発中です。暗号通貨システムには固有のリスクがあります：

- メインネットで使用する前にテストネットで十分にテストしてください
- 秘密鍵を安全に保管してください
- シードフレーズや秘密鍵を決して共有しないでください
- 資金を投入する前に技術を理解してください
- セキュリティに関する懸念については[SECURITY.md](../../../SECURITY.md)を参照してください

---

## 免責事項

XAIは概念実証のブロックチェーン実装です。本番品質を目指していますが、ユーザーは暗号通貨システムの実験的な性質を理解する必要があります。ネットワークは活発に開発中であり、適切な注意を払って使用する必要があります。開発者は、将来の実行可能性、機能の可用性、またはネットワークの安定性について保証しません。

---

**最終更新**：2025年1月 | **バージョン**：0.2.0 | **ステータス**：テストネット稼働中
