# Bjinggou

## 捡尸监控

每 5 分钟自动检查钱包内所有 SPL token，任何一个标的出现异动即推送 Telegram 通知。

### 报警规则

| 信号 | 触发条件 |
| --- | --- |
| 🚀 暴涨 | 5分钟涨 ≥ 30% / 1小时涨 ≥ 50% / 6小时涨 ≥ 100% |
| 🔻 暴跌 | 5分钟跌 ≤ -30% / 1小时跌 ≤ -50% |
| 🆕 新增 | 钱包出现之前没见过的 token |

### 数据源

- **持仓**: Solana 公共 RPC `getTokenAccountsByOwner`
- **价格/涨跌/流动性**: [DexScreener API](https://docs.dexscreener.com/api/reference)（免费无需 Key）

### 快速开始

1. 在仓库 Settings → Secrets 中配置:
   - `WALLET_ADDRESS`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. 合并代码后 Actions 自动每 5 分钟运行
3. 或手动触发：Actions → Solana Wallet Monitor → Run workflow

详细方案设计见 [`捡尸监控/方案设计.md`](捡尸监控/方案设计.md)
