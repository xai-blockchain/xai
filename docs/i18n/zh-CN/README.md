# XAI 区块链

[![CI](https://github.com/xai-blockchain/xai/actions/workflows/ci.yml/badge.svg)](https://github.com/xai-blockchain/xai/actions/workflows/ci.yml) [![Security](https://github.com/xai-blockchain/xai/actions/workflows/security.yml/badge.svg)](https://github.com/xai-blockchain/xai/actions/workflows/security.yml) [![codecov](https://codecov.io/gh/xai-blockchain/xai/branch/main/graph/badge.svg)](https://codecov.io/gh/xai-blockchain/xai) [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/) [![XAI Testnet](https://img.shields.io/badge/Testnet-Active-success)](https://faucet.xai.network)

**[English](../../../README.md)** | **简体中文** | **[한국어](../ko/README.md)** | **[日本語](../ja/README.md)**

## 基于工作量证明的区块链，集成 AI 治理与钱包系统

XAI 是一个生产就绪的区块链实现，具备工作量证明共识机制、智能 AI 治理系统、跨链原子交换支持以及全面的钱包管理功能。适用于个人用户和企业合规需求。

---

## 5 分钟快速开始

### 交互式安装向导（推荐）

使用交互式向导是设置 XAI 节点最简单的方式：

```bash
# 克隆并进入仓库
git clone https://github.com/xai-blockchain/xai.git
cd xai

# 运行安装向导
python scripts/setup_wizard.py
```

向导将指导您完成：
- 网络选择（测试网/主网）
- 节点模式配置（完整/精简/轻量/归档）
- 端口配置与冲突检测
- 钱包创建
- 安全配置
- 可选的 systemd 服务安装

**[→ 查看安装向导文档](../../scripts/SETUP_WIZARD.md)**

### 手动安装

**XAI 新手？** 请阅读我们的 **[快速入门指南](QUICKSTART.md)** - 5 分钟内即可运行：
- 多种安装选项（pip、Docker、软件包）
- 创建您的第一个钱包
- 从水龙头获取免费测试网代币
- 发送您的第一笔交易
- 在区块浏览器中查看

**[→ 从这里开始：快速入门指南](QUICKSTART.md)** ← **完整新手指南**

---

## 测试网水龙头 - 获取免费 XAI

**官方公共水龙头：** https://faucet.xai.network

立即获取 100 个免费测试网 XAI 代币，用于测试和开发！

### 快速获取方式

**1. 网页界面（最简单）：**
```
访问：https://faucet.xai.network
输入您的 TXAI 地址
点击"请求代币"
```

**2. 命令行：**
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_您的地址
```

**3. 直接 API 调用：**
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_您的地址"}'
```

### 水龙头规格

| 参数 | 值 |
|------|-----|
| **数量** | 每次请求 100 XAI |
| **频率限制** | 每个地址每小时 1 次 |
| **到账时间** | 下一个区块（约 2 分钟） |
| **代币价值** | 仅限测试网 - 无真实价值 |
| **公共水龙头** | https://faucet.xai.network |
| **本地端点** | `http://localhost:12001/faucet/claim` |

**注意：** 测试网 XAI 没有真实价值。请放心用于开发和测试。

---

## 概述

XAI 是一个基于 Python 的区块链，实现了生产级工作量证明（PoW）链，采用 UTXO 交易模型、模块化节点、钱包 CLI、治理原语和简单的网页浏览器。代码库采用专业 Python 项目结构，具有清晰的关注点分离和测试。

---

## 主要特性

- 工作量证明（SHA-256）可调难度
- 基于 UTXO 的交易，支持签名、输入/输出和 RBF 标志
- Merkle 证明用于轻客户端验证
- 钱包 CLI：生成、余额、发送、导入/导出、水龙头助手
- 节点 API（Flask）带 CORS 策略和请求验证
- P2P 网络和共识管理器框架
- 治理模块（提案管理、投票锁定、二次方投票）
- 安全中间件和结构化指标
- 基础区块浏览器（Flask）
- 钱包交易管理器，支持高级订单类型（TWAP 调度器、VWAP 配置、冰山订单、跟踪止损）

## 快速开始（< 5 分钟）

### 前置要求

- Python 3.10 或更高版本
- 最低 2GB 内存
- 10GB+ 磁盘空间用于存储区块链数据

### 安装

```bash
# 从项目根目录安装依赖（使用约束确保可重现性）
pip install -c constraints.txt -e ".[dev]"
# 可选：启用 QUIC 支持
pip install -e ".[network]"

# 验证安装
python -m pytest --co -q
```

### 启动节点

```bash
# 运行节点（显示默认值）
export XAI_NETWORK=development
xai-node
```

节点将在端口 12001（RPC）、12002（P2P）和 12003（WebSocket）启动。

### 开始挖矿

```bash
# 首先生成钱包地址（或使用现有地址）
xai-wallet generate-address

# 使用您的地址开始挖矿
export MINER_ADDRESS=您的_XAI_地址
xai-node --miner $MINER_ADDRESS
```

### CLI 工具

安装包后（`pip install -e .`），可使用三个控制台命令：

- `xai` - 主 CLI，包含区块链、钱包、挖矿、AI 和网络命令
- `xai-wallet` - 钱包专用 CLI（旧接口）
- `xai-node` - 节点管理

```bash
# 主 CLI（推荐）
xai wallet balance --address 您的_XAI_地址
xai blockchain info
xai ai submit-job --model gpt-4 --data "..."

# 旧版钱包 CLI（仍支持）
xai-wallet request-faucet --address 您的_XAI_地址
xai-wallet generate-address
```

---

## 配置

### 网络选择

```bash
# 开发环境（默认）
export XAI_NETWORK=development
export XAI_RPC_PORT=18546
```

### 环境变量

```bash
XAI_NETWORK          # 测试网或主网（默认：测试网）
XAI_PORT             # P2P 端口（默认：测试网 18545，主网 8545）
XAI_RPC_PORT         # RPC 端口（默认：测试网 18546，主网 8546）
XAI_LOG_LEVEL        # DEBUG, INFO, WARNING, ERROR（默认：INFO）
XAI_DATA_DIR         # 区块链数据目录
MINER_ADDRESS        # 接收挖矿奖励的地址
```

更多配置选项请参阅 `src/xai/config/`。

---

## 网络参数

### 测试网配置

| 参数 | 值 |
|------|-----|
| 网络 ID | 0xABCD |
| 端口 | 18545 |
| RPC 端口 | 18546 |
| 地址前缀 | TXAI |
| 出块时间 | 2 分钟 |
| 最大供应量 | 121,000,000 XAI |

### 主网配置

| 参数 | 值 |
|------|-----|
| 网络 ID | 0x5841 |
| 端口 | 8545 |
| RPC 端口 | 8546 |
| 地址前缀 | XAI |
| 出块时间 | 2 分钟 |
| 最大供应量 | 121,000,000 XAI |

---

## 贡献

我们欢迎开发者、研究人员和区块链爱好者的贡献。

**贡献前，请：**

1. 阅读 [CONTRIBUTING.md](../../../CONTRIBUTING.md) 了解开发指南
2. 查看 [SECURITY.md](../../../SECURITY.md) 了解安全注意事项
3. 检查现有的 issues 和 pull requests
4. 遵循代码风格和测试要求

---

## 许可证

MIT 许可证 - 完整条款请参阅 [LICENSE](../../../LICENSE) 文件。

本项目采用 MIT 许可证发布，允许商业和非商业用途。

---

## 安全声明

**重要：** 本软件为实验性质，正在积极开发中。加密货币系统存在固有风险：

- 在主网使用前请在测试网上充分测试
- 妥善保管您的私钥
- 切勿分享助记词或私钥
- 在投入资金前了解相关技术
- 安全问题请查阅 [SECURITY.md](../../../SECURITY.md)

---

## 免责声明

XAI 是一个概念验证区块链实现。虽然我们力求生产质量，但用户应理解加密货币系统的实验性质。网络正在积极开发中，使用时请保持适当谨慎。开发者不对未来可行性、功能可用性或网络稳定性作任何保证。

---

**最新更新**：2025 年 1 月 | **版本**：0.2.0 | **状态**：测试网运行中
