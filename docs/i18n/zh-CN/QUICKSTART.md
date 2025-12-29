# XAI 区块链 - 快速入门指南

**5 分钟开始使用 XAI！** 本指南涵盖安装、钱包创建、获取测试网代币和发送您的第一笔交易。

---

## 什么是 XAI？

XAI 是一个具有 AI 治理、原子交换和全面钱包支持的工作量证明区块链。本指南帮助您快速在测试网上运行。

**选择您的路径：**
- **桌面/服务器用户** → 按照下面的步骤 1-6 操作
- **移动开发者** → 查看 [移动快速入门](../../user-guides/mobile_quickstart.md)
- **物联网/树莓派** → 查看 [轻量节点指南](../../user-guides/lightweight_node_guide.md)
- **轻客户端** → 查看 [轻客户端模式](../../user-guides/light_client_mode.md)

---

## 安装选项

选择最适合您的方式：

### 选项 A：一键安装（推荐）

**Linux/macOS：**
```bash
curl -sSL https://install.xai.network | bash
```

**Windows PowerShell：**
```powershell
iwr -useb https://install.xai.network/install.ps1 | iex
```

### 选项 B：从源码安装（开发者）

```bash
git clone https://github.com/your-org/xai.git
cd xai
pip install -c constraints.txt -e ".[dev]"
```

### 选项 C：Docker（隔离环境）

```bash
docker pull xai/node:latest
docker run -d -p 18545:18545 -p 18546:18546 xai/node:testnet
```

### 选项 D：包管理器

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

## 步骤 1：创建您的第一个钱包（30 秒）

```bash
# 生成新钱包地址
python src/xai/wallet/cli.py generate-address

# 输出：
# 钱包创建成功！
# 地址：TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
# 私钥：5KYZdUEo39z3FPrtuX2QbbwGnNP5zTd7yyr2SC1j299sBCnWjss
# 重要：请妥善保管您的私钥！一旦丢失无法恢复。
```

**安全提示：**
- 您的私钥控制着您的资金
- 切勿与任何人分享
- 存储在密码管理器或加密文件中
- 写下来并保存在安全的地方

---

## 步骤 2：获取免费测试网代币（1 分钟）

**官方测试网水龙头：** https://faucet.xai.network

### 方法 A：网页界面（最简单）
1. 访问 https://faucet.xai.network
2. 输入您的 TXAI 地址
3. 完成验证码
4. 约 2 分钟内收到 100 XAI

### 方法 B：命令行
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_您的地址

# 输出：
# 水龙头请求成功！
# 100 XAI 将在下一个区块送达（约 2 分钟）
# 注意：这是测试网 XAI，没有真实价值
```

### 方法 C：直接 API 调用
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_您的地址"}'
```

**水龙头详情：**
- **数量：** 每次请求 100 XAI
- **频率限制：** 每个地址每小时 1 次
- **到账时间：** 下一个区块（约 2 分钟）
- **仅限测试网：** 这些代币没有真实价值

---

## 步骤 3：查询余额（30 秒）

等待约 2 分钟出下一个区块，然后查询：

```bash
python src/xai/wallet/cli.py balance --address TXAI_您的地址

# 输出：
# 余额：100.00000000 XAI
# 待确认：0.00000000 XAI
```

**通过 API 查询：**
```bash
curl http://localhost:12001/account/TXAI_您的地址
```

---

## 步骤 4：发送您的第一笔交易（1 分钟）

```bash
python src/xai/wallet/cli.py send \
  --from TXAI_您的地址 \
  --to TXAI_收款地址 \
  --amount 10.0

# CLI 将：
# 1. 显示交易哈希供审核
# 2. 要求您输入哈希前缀确认（安全功能）
# 3. 提示输入私钥（不会发送到网络）
# 4. 本地签名交易
# 5. 广播到网络
#
# 输出：
# 交易哈希：0xabc123...
# 交易广播成功！
# 确认数：待确认（约 2 分钟）
```

**交易确认建议：**
- **小额（<100 XAI）：** 1 个确认（2 分钟）
- **中额（100-1000 XAI）：** 3 个确认（6 分钟）
- **大额（>1000 XAI）：** 6 个确认（12 分钟）

---

## 步骤 5：在区块浏览器中查看（30 秒）

### 网页浏览器（推荐）
**测试网浏览器：** https://explorer.xai.network/testnet

可以搜索：
- 您的地址
- 交易哈希
- 区块编号

### 本地浏览器（可选）
```bash
# 启动本地浏览器
python src/xai/explorer.py

# 在浏览器中打开
# http://localhost:12080
```

**浏览器功能：**
- 实时区块更新
- 交易详情
- 地址余额查询
- 网络统计
- 内存池查看器

---

## 步骤 6：运行您自己的节点（可选，2 分钟）

作为完整参与者加入网络：

```bash
# 设置环境
export XAI_NETWORK=testnet

# 启动节点
python -m xai.core.node

# 节点启动在：
# - P2P 端口：18545
# - RPC 端口：18546
#
# 输出：
# [INFO] XAI 节点启动中...
# [INFO] 网络：测试网
# [INFO] 同步区块链（0 / 22341 个区块）...
```

**开始挖矿（可选）：**
```bash
export MINER_ADDRESS=TXAI_您的地址
python -m xai.core.node --miner $MINER_ADDRESS

# 挖矿奖励：每区块 50 XAI
# 出块时间：约 2 分钟
# 难度：每 2016 个区块调整
```

---

## 配置

### 环境变量

```bash
# 网络选择
export XAI_NETWORK=testnet           # 或 'mainnet'

# 端口
export XAI_PORT=18545                # P2P 端口（主网为 8545）
export XAI_RPC_PORT=18546            # RPC 端口（主网为 8546）

# 节点行为
export XAI_LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
export XAI_DATA_DIR=~/.xai           # 区块链数据目录
export MINER_ADDRESS=TXAI_...        # 挖矿奖励地址

# 性能
export XAI_CACHE_TTL=60              # 响应缓存 TTL（秒）
export XAI_PARTIAL_SYNC_ENABLED=1    # 启用检查点同步
```

### 网络端点

**测试网：**
- RPC：`http://localhost:12001` 或 `https://testnet-rpc.xai.network`
- WebSocket：`ws://localhost:12003`
- 水龙头：`https://faucet.xai.network`
- 浏览器：`https://explorer.xai.network/testnet`

**主网：**
- RPC：`http://localhost:12001` 或 `https://rpc.xai.network`
- WebSocket：`ws://localhost:12003`
- 浏览器：`https://explorer.xai.network`

---

## 常用命令速查表

### 钱包操作
```bash
# 生成新钱包
python src/xai/wallet/cli.py generate-address

# 查询余额
python src/xai/wallet/cli.py balance --address TXAI_地址

# 发送交易
python src/xai/wallet/cli.py send --from TXAI_发送方 --to TXAI_接收方 --amount 10.0

# 导出私钥（妥善保管！）
python src/xai/wallet/cli.py export-key --address TXAI_地址

# 导入钱包
python src/xai/wallet/cli.py import-key --private-key 您的私钥

# 请求测试网代币
python src/xai/wallet/cli.py request-faucet --address TXAI_地址
```

### 节点操作
```bash
# 启动完整节点
python -m xai.core.node

# 启动挖矿节点
python -m xai.core.node --miner TXAI_地址

# 检查节点健康状态
curl http://localhost:12001/health

# 查看连接的节点
curl http://localhost:12001/peers

# 获取区块链信息
curl http://localhost:12001/blockchain/stats
```

### 查询区块链
```bash
# 按编号获取区块
curl http://localhost:12001/block/12345

# 获取交易
curl http://localhost:12001/transaction/交易哈希

# 获取地址余额
curl http://localhost:12001/account/TXAI_地址
```

---

## 故障排除

### 安装问题

**"找不到命令"**
- 确保您在 xai 目录中
- 如使用虚拟环境，请激活：`source venv/bin/activate`
- 检查 Python 版本：`python --version`（需要 3.10+）

**"权限被拒绝"**
- 使用 `sudo` 进行系统级安装：`sudo pip install -e .`
- 或安装到用户目录：`pip install --user -e .`

### 钱包问题

**"超出水龙头频率限制"**
- 水龙头允许每个地址每小时领取 1 次
- 等待 60 分钟后重试
- 或创建新地址用于测试

**"余额不足"**
- 检查余额：`python src/xai/wallet/cli.py balance --address TXAI_地址`
- 确保您有足够的金额 + 手续费（通常为 0.001 XAI）
- 如需要可从水龙头获取更多

### 节点问题

**"无法连接到节点"**
- 确保节点正在运行：`python -m xai.core.node`
- 检查正确端口（测试网 18546，主网 8546）
- 验证防火墙允许连接

**"交易未确认"**
- XAI 出块时间约 2 分钟 - 请耐心等待
- 检查内存池：`curl http://localhost:12001/mempool`
- 验证交易已广播：`curl http://localhost:12001/transaction/交易哈希`

**"同步太慢"**
- 启用检查点同步：`export XAI_PARTIAL_SYNC_ENABLED=1`
- 使用轻客户端加快启动
- 检查您的网络连接

---

## 下一步

现在您已设置完成，探索 XAI 的高级功能：

### 用户指南
- **[测试网指南](../../user-guides/TESTNET_GUIDE.md)** - 完整测试网教程
- **[钱包设置](../../user-guides/wallet-setup.md)** - 多签、HD 钱包、高级功能
- **[挖矿指南](../../user-guides/mining.md)** - 详细挖矿说明
- **[轻客户端指南](../../user-guides/LIGHT_CLIENT_GUIDE.md)** - 运行轻量节点

### 开发者指南
- **[API 文档](../../api/rest-api.md)** - 在 XAI 上构建 dApp
- **[TypeScript SDK](../../api/sdk.md)** - JavaScript/TypeScript 集成
- **[Python SDK](../../../src/xai/sdk/python/README.md)** - Python 开发
- **[移动快速入门](../../user-guides/mobile_quickstart.md)** - React Native/Flutter SDK

### 高级主题
- **[原子交换](../../advanced/atomic-swaps.md)** - 跨链交易
- **[智能合约](../../architecture/evm_interpreter.md)** - 部署合约
- **[治理](../../user-guides/staking.md)** - 参与治理

---

## 网络信息

### 测试网参数

| 参数 | 值 |
|------|-----|
| 网络 ID | 0xABCD |
| 地址前缀 | TXAI |
| P2P 端口 | 18545 |
| RPC 端口 | 18546 |
| 出块时间 | 2 分钟 |
| 区块奖励 | 50 XAI |
| 难度调整 | 每 2016 个区块 |
| 最大供应量 | 121,000,000 XAI |
| 减半周期 | 每 210,000 个区块 |

### 主网参数（未来）

| 参数 | 值 |
|------|-----|
| 网络 ID | 0x5841 |
| 地址前缀 | XAI |
| P2P 端口 | 8545 |
| RPC 端口 | 8546 |
| 出块时间 | 2 分钟 |
| 区块奖励 | 50 XAI（会减半） |
| 最大供应量 | 121,000,000 XAI |

---

## 完成！

**您现在拥有：**
- XAI 区块链已安装
- 带有测试网代币的钱包
- 已发送第一笔交易
- 基本操作知识

**继续您的旅程：**
1. 尝试[挖矿](../../user-guides/mining.md)获取奖励
2. 在 XAI 上构建 [dApp](../../api/rest-api.md)
3. 在树莓派上运行[轻客户端](../../user-guides/light_client_mode.md)
4. 探索文档中的高级功能
5. 在 GitHub 上贡献项目

**欢迎来到 XAI 区块链开发！**

---

*最后更新：2025 年 1 月 | XAI 版本：0.2.0*
