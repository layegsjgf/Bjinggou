# Bjinggou — Solana Meme 钱包监控

每 5 分钟检查一次钱包内所有 SPL token，任何一个币满足下面条件就推送 Telegram：

| 信号 | 阈值 |
| --- | --- |
| 暴涨 | 5m ≥ +30% / 1h ≥ +50% / 6h ≥ +100% |
| 暴跌 | 5m ≤ -30% / 1h ≤ -50% |
| 新增 token | 钱包多了之前没见过的币 |

数据源：
- 持仓：Solana 公共 RPC `getTokenAccountsByOwner`
- 价格 / 涨跌 / 流动性：[DexScreener API](https://docs.dexscreener.com/api/reference)（免费、不需 Key）

状态文件 `state.json` 由 Actions 自动 commit 回仓库做持久化（用于冷却 + 检测新增 token）。

## 配置

`monitor.py` 里有默认值，可以直接跑。**生产环境强烈建议改用 GitHub Secrets**，把以下三个变量加到仓库的 Settings → Secrets and variables → Actions：

- `WALLET_ADDRESS`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 调阈值

直接改 `monitor.py` 顶部的 `PUMP_M5 / PUMP_H1 / PUMP_H6 / DUMP_M5 / DUMP_H1` 和冷却时间 `COOLDOWN_MINUTES`。

## 本地手动跑

```bash
pip install requests
python monitor.py
```

## 手动触发一次

GitHub 仓库 → Actions → Solana Wallet Monitor → Run workflow。
