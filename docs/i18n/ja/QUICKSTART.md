# XAI ブロックチェーン - クイックスタートガイド

**5分でXAIを始めましょう！** このガイドでは、インストール、ウォレット作成、テストネットトークンの取得、最初のトランザクションの送信について説明します。

---

## XAIとは？

XAIは、AIガバナンス、アトミックスワップ、包括的なウォレットサポートを備えたProof-of-Workブロックチェーンです。このガイドは、テストネットで素早く実行するのに役立ちます。

**パスを選択：**
- **デスクトップ/サーバーユーザー** → 以下のステップ1-6に従う
- **モバイル開発者** → [モバイルクイックスタート](../../user-guides/mobile_quickstart.md)を参照
- **IoT/Raspberry Pi** → [ライトウェイトノードガイド](../../user-guides/lightweight_node_guide.md)を参照
- **ライトクライアント** → [ライトクライアントモード](../../user-guides/light_client_mode.md)を参照

---

## インストールオプション

最適な方法を選択してください：

### オプションA：ワンラインインストール（推奨）

**Linux/macOS：**
```bash
curl -sSL https://install.xai.network | bash
```

**Windows PowerShell：**
```powershell
iwr -useb https://install.xai.network/install.ps1 | iex
```

### オプションB：ソースからインストール（開発者向け）

```bash
git clone https://github.com/your-org/xai.git
cd xai
pip install -c constraints.txt -e ".[dev]"
```

### オプションC：Docker（隔離環境）

```bash
docker pull xai/node:latest
docker run -d -p 18545:18545 -p 18546:18546 xai/node:testnet
```

### オプションD：パッケージマネージャー

**Debian/Ubuntu：**
```bash
wget https://releases.xai.network/xai_latest_amd64.deb
sudo dpkg -i xai_latest_amd64.deb
```

**Homebrew（macOS）：**
```bash
brew tap xai-blockchain/xai
brew install xai
```

---

## ステップ1：最初のウォレットを作成（30秒）

```bash
# 新しいウォレットアドレスを生成
python src/xai/wallet/cli.py generate-address

# 出力：
# ウォレット作成成功！
# アドレス：TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
# 秘密鍵：5KYZdUEo39z3FPrtuX2QbbwGnNP5zTd7yyr2SC1j299sBCnWjss
# 重要：秘密鍵を安全に保管してください！紛失した場合、回復できません。
```

**セキュリティ警告：**
- 秘密鍵があなたの資金を管理します
- 誰とも共有しないでください
- パスワードマネージャーまたは暗号化ファイルに保存してください
- 書き留めて安全な場所に保管してください

---

## ステップ2：無料テストネットトークンを取得（1分）

**公式テストネットフォーセット：** https://faucet.xai.network

### 方法A：Web UI（最も簡単）
1. https://faucet.xai.network にアクセス
2. TXAIアドレスを入力
3. CAPTCHAを完了
4. 約2分で100 XAIを受け取る

### 方法B：コマンドライン
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_あなたのアドレス

# 出力：
# フォーセットリクエスト成功！
# 100 XAIが次のブロックで届きます（約2分）
# 注意：これは実際の価値のないテストネットXAIです
```

### 方法C：直接API呼び出し
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_あなたのアドレス"}'
```

**フォーセット詳細：**
- **金額：** リクエストごとに100 XAI
- **レート制限：** アドレスごとに1時間1回
- **配達時間：** 次のブロック（約2分）
- **テストネット専用：** これらのトークンには実際の価値がありません

---

## ステップ3：残高を確認（30秒）

次のブロックを待って（約2分）から確認：

```bash
python src/xai/wallet/cli.py balance --address TXAI_あなたのアドレス

# 出力：
# 残高：100.00000000 XAI
# 保留中：0.00000000 XAI
```

**API経由：**
```bash
curl http://localhost:12001/account/TXAI_あなたのアドレス
```

---

## ステップ4：最初のトランザクションを送信（1分）

```bash
python src/xai/wallet/cli.py send \
  --from TXAI_あなたのアドレス \
  --to TXAI_受信者アドレス \
  --amount 10.0

# CLIが実行する内容：
# 1. レビュー用にトランザクションハッシュを表示
# 2. ハッシュプレフィックスを入力して確認を求める（セキュリティ機能）
# 3. 秘密鍵の入力を求める（ネットワークには送信されない）
# 4. ローカルでトランザクションに署名
# 5. ネットワークにブロードキャスト
#
# 出力：
# トランザクションハッシュ：0xabc123...
# トランザクションのブロードキャスト成功！
# 確認：保留中（約2分）
```

**トランザクション確認の推奨：**
- **少額（<100 XAI）：** 1確認（2分）
- **中額（100-1000 XAI）：** 3確認（6分）
- **大額（>1000 XAI）：** 6確認（12分）

---

## ステップ5：ブロックエクスプローラーで表示（30秒）

### Webエクスプローラー（推奨）
**テストネットエクスプローラー：** https://explorer.xai.network/testnet

検索可能：
- あなたのアドレス
- トランザクションハッシュ
- ブロック番号

### ローカルエクスプローラー（オプション）
```bash
# ローカルエクスプローラーを起動
python src/xai/explorer.py

# ブラウザで開く
# http://localhost:12080
```

**エクスプローラー機能：**
- リアルタイムブロック更新
- トランザクション詳細
- アドレス残高検索
- ネットワーク統計
- メンプールビューア

---

## ステップ6：自分のノードを実行（オプション、2分）

フル参加者としてネットワークに参加：

```bash
# 環境を設定
export XAI_NETWORK=testnet

# ノードを起動
python -m xai.core.node

# ノードが起動する場所：
# - P2Pポート：18545
# - RPCポート：18546
#
# 出力：
# [INFO] XAIノード起動中...
# [INFO] ネットワーク：テストネット
# [INFO] ブロックチェーン同期中（0 / 22341ブロック）...
```

**マイニングを開始（オプション）：**
```bash
export MINER_ADDRESS=TXAI_あなたのアドレス
python -m xai.core.node --miner $MINER_ADDRESS

# マイニング報酬：ブロックごとに50 XAI
# ブロック時間：約2分
# 難易度：2016ブロックごとに調整
```

---

## 構成

### 環境変数

```bash
# ネットワーク選択
export XAI_NETWORK=testnet           # または'mainnet'

# ポート
export XAI_PORT=18545                # P2Pポート（メインネットは8545）
export XAI_RPC_PORT=18546            # RPCポート（メインネットは8546）

# ノード動作
export XAI_LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
export XAI_DATA_DIR=~/.xai           # ブロックチェーンデータディレクトリ
export MINER_ADDRESS=TXAI_...        # マイニング報酬アドレス

# パフォーマンス
export XAI_CACHE_TTL=60              # レスポンスキャッシュTTL（秒）
export XAI_PARTIAL_SYNC_ENABLED=1    # チェックポイント同期を有効化
```

### ネットワークエンドポイント

**テストネット：**
- RPC：`http://localhost:12001` または `https://testnet-rpc.xai.network`
- WebSocket：`ws://localhost:12003`
- フォーセット：`https://faucet.xai.network`
- エクスプローラー：`https://explorer.xai.network/testnet`

**メインネット：**
- RPC：`http://localhost:12001` または `https://rpc.xai.network`
- WebSocket：`ws://localhost:12003`
- エクスプローラー：`https://explorer.xai.network`

---

## よく使うコマンド

### ウォレット操作
```bash
# 新しいウォレットを生成
python src/xai/wallet/cli.py generate-address

# 残高を確認
python src/xai/wallet/cli.py balance --address TXAI_アドレス

# トランザクションを送信
python src/xai/wallet/cli.py send --from TXAI_送信者 --to TXAI_受信者 --amount 10.0

# 秘密鍵をエクスポート（安全に保管！）
python src/xai/wallet/cli.py export-key --address TXAI_アドレス

# ウォレットをインポート
python src/xai/wallet/cli.py import-key --private-key あなたの秘密鍵

# テストネットトークンをリクエスト
python src/xai/wallet/cli.py request-faucet --address TXAI_アドレス
```

### ノード操作
```bash
# フルノードを起動
python -m xai.core.node

# マイニングで起動
python -m xai.core.node --miner TXAI_アドレス

# ノードの健全性を確認
curl http://localhost:12001/health

# 接続されたピアを表示
curl http://localhost:12001/peers

# ブロックチェーン情報を取得
curl http://localhost:12001/blockchain/stats
```

### ブロックチェーンクエリ
```bash
# 番号でブロックを取得
curl http://localhost:12001/block/12345

# トランザクションを取得
curl http://localhost:12001/transaction/TX_ハッシュ

# アドレス残高を取得
curl http://localhost:12001/account/TXAI_アドレス
```

---

## トラブルシューティング

### インストールの問題

**「コマンドが見つかりません」**
- xaiディレクトリにいることを確認してください
- 仮想環境を使用している場合は有効化：`source venv/bin/activate`
- Pythonバージョンを確認：`python --version`（3.10+が必要）

**「権限が拒否されました」**
- システム全体のインストールに`sudo`を使用：`sudo pip install -e .`
- またはユーザーディレクトリにインストール：`pip install --user -e .`

### ウォレットの問題

**「フォーセットレート制限を超過」**
- フォーセットはアドレスごとに1時間1回の請求を許可
- 60分待ってから再試行
- またはテスト用に新しいアドレスを作成

**「残高不足」**
- 残高を確認：`python src/xai/wallet/cli.py balance --address TXAI_アドレス`
- 金額+手数料（通常0.001 XAI）が十分か確認
- 必要に応じてフォーセットからさらにリクエスト

### ノードの問題

**「ノードに接続できません」**
- ノードが実行中か確認：`python -m xai.core.node`
- 正しいポートを確認（テストネット18546、メインネット8546）
- ファイアウォールが接続を許可しているか確認

**「トランザクションが確認されない」**
- XAIのブロック時間は2分です - お待ちください
- メンプールを確認：`curl http://localhost:12001/mempool`
- トランザクションがブロードキャストされたか確認：`curl http://localhost:12001/transaction/TX_ハッシュ`

**「同期が遅すぎる」**
- チェックポイント同期を有効化：`export XAI_PARTIAL_SYNC_ENABLED=1`
- より速い起動にライトクライアントを使用
- インターネット接続を確認

---

## 次のステップ

セットアップが完了したので、XAIの高度な機能を探索してください：

### ユーザー向け
- **[テストネットガイド](../../user-guides/TESTNET_GUIDE.md)** - 完全なテストネットウォークスルー
- **[ウォレットセットアップ](../../user-guides/wallet-setup.md)** - マルチシグ、HDウォレット、高度な機能
- **[マイニングガイド](../../user-guides/mining.md)** - 詳細なマイニング手順
- **[ライトクライアントガイド](../../user-guides/LIGHT_CLIENT_GUIDE.md)** - ライトウェイトノードを実行

### 開発者向け
- **[APIドキュメント](../../api/rest-api.md)** - XAIでdAppを構築
- **[TypeScript SDK](../../api/sdk.md)** - JavaScript/TypeScript統合
- **[Python SDK](../../../src/xai/sdk/python/README.md)** - Python開発
- **[モバイルクイックスタート](../../user-guides/mobile_quickstart.md)** - React Native/Flutter SDK

### 高度なトピック
- **[アトミックスワップ](../../advanced/atomic-swaps.md)** - クロスチェーン取引
- **[スマートコントラクト](../../architecture/evm_interpreter.md)** - コントラクトをデプロイ
- **[ガバナンス](../../user-guides/staking.md)** - ガバナンスに参加

---

## ネットワーク情報

### テストネットパラメータ

| パラメータ | 値 |
|------------|-----|
| ネットワークID | 0xABCD |
| アドレスプレフィックス | TXAI |
| P2Pポート | 18545 |
| RPCポート | 18546 |
| ブロック時間 | 2分 |
| ブロック報酬 | 50 XAI |
| 難易度調整 | 2016ブロックごと |
| 最大供給量 | 121,000,000 XAI |
| 半減期 | 210,000ブロックごと |

### メインネットパラメータ（将来）

| パラメータ | 値 |
|------------|-----|
| ネットワークID | 0x5841 |
| アドレスプレフィックス | XAI |
| P2Pポート | 8545 |
| RPCポート | 8546 |
| ブロック時間 | 2分 |
| ブロック報酬 | 50 XAI（半減） |
| 最大供給量 | 121,000,000 XAI |

---

## 完了！

**準備完了：**
- XAIブロックチェーンがインストールされました
- テストネットトークンを持つウォレット
- 最初のトランザクションを送信しました
- 基本操作を理解しました

**旅を続けましょう：**
1. [マイニング](../../user-guides/mining.md)を試して報酬を獲得
2. XAIで[dApp](../../api/rest-api.md)を構築
3. Raspberry Piで[ライトクライアント](../../user-guides/light_client_mode.md)を実行
4. ドキュメントで高度な機能を探索
5. GitHubでプロジェクトに貢献

**XAIブロックチェーン開発へようこそ！**

---

*最終更新：2025年1月 | XAIバージョン：0.2.0*
