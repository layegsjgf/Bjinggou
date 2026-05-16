"""
Solana Meme 钱包监控
- 逐 token 监控（不只看总价值），任何一个币起飞或暴跌都报警
- 数据源: Solana RPC (持仓) + DexScreener (价格、涨跌)
- 状态文件 state.json commit 回仓库做持久化
"""

import os
import json
import time
import requests
from datetime import datetime, timezone

# ========== 配置（优先读环境变量；本地/无 Secrets 时使用默认值） ==========
WALLET_ADDRESS     = os.getenv("WALLET_ADDRESS",     "BBsaiHLZBAkVuhm7x52R2gHgn6Tf8HaPcF7ipchee3r3")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8613329028:AAHIQ42bAUI2aFoFB-swNNleFzkgMmfbB7s")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "2113522339")

# 喵提醒配置（微信 + 电话推送）
MIAO_REMIND_ID     = os.getenv("MIAO_REMIND_ID",     "t4yj5WH")

# 报警阈值（百分比）
PUMP_M5  =  30   # 5 分钟涨 30%
PUMP_H1  =  50   # 1 小时涨 50%
PUMP_H6  = 100   # 6 小时翻倍
DUMP_M5  = -30   # 5 分钟跌 30%
DUMP_H1  = -50   # 1 小时跌 50%

MIN_HOLDING_USD  = 1.0     # 持仓低于 $1 的忽略（粉尘）
COOLDOWN_MINUTES = 60      # 同一个币 60 分钟内不重复推送
# ==========================================================================

SOL_RPC       = "https://api.mainnet-beta.solana.com"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
STATE_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


def rpc_call(method, params, retries=3):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    last_err = None
    for i in range(retries):
        try:
            r = requests.post(SOL_RPC, json=payload, timeout=30)
            if r.status_code == 200:
                return r.json()
            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            last_err = str(e)
        time.sleep(2 ** i)
    raise RuntimeError(f"RPC {method} failed: {last_err}")


def get_token_holdings():
    """读取钱包内所有 SPL token: {mint: ui_amount}"""
    data = rpc_call(
        "getTokenAccountsByOwner",
        [WALLET_ADDRESS, {"programId": TOKEN_PROGRAM}, {"encoding": "jsonParsed"}],
    )
    holdings = {}
    for acc in data.get("result", {}).get("value", []):
        info = acc["account"]["data"]["parsed"]["info"]
        mint = info["mint"]
        amount = info["tokenAmount"].get("uiAmount") or 0
        if amount > 0:
            # 同一 mint 多个账户合并
            holdings[mint] = holdings.get(mint, 0) + amount
    return holdings


def get_dex_data(mints):
    """批量查 DexScreener，返回 {mint: pair_info}（取流动性最高的池子）"""
    result = {}
    for i in range(0, len(mints), 30):
        chunk = mints[i:i + 30]
        url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(chunk)}"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print(f"  DexScreener HTTP {r.status_code}")
                continue
            for p in (r.json().get("pairs") or []):
                base = (p.get("baseToken") or {}).get("address")
                if not base:
                    continue
                liq = ((p.get("liquidity") or {}).get("usd") or 0)
                if base not in result or liq > ((result[base].get("liquidity") or {}).get("usd") or 0):
                    result[base] = p
        except Exception as e:
            print(f"  DexScreener error: {e}")
        time.sleep(0.3)
    return result


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  (Telegram 未配置，跳过)")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        if r.status_code != 200:
            print(f"  Telegram HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  Telegram error: {e}")


def send_miao_remind(text):
    """通过喵提醒推送（微信公众号 + 电话呼叫）"""
    if not MIAO_REMIND_ID:
        print("  (喵提醒未配置，跳过)")
        return
    url = "https://miaotixing.com/trigger"
    try:
        r = requests.get(url, params={"id": MIAO_REMIND_ID, "text": text}, timeout=15)
        if r.status_code == 200:
            body = (r.text or "").strip()
            if "完成" in body or body == "":
                print(f"  喵提醒已推送")
            else:
                # 服务端返回如"发送失败：提醒过于频繁..."
                print(f"  喵提醒返回: {body[:200]}")
        else:
            print(f"  喵提醒 HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  喵提醒 error: {e}")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"alerts": {}, "known_tokens": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def fmt_price(p):
    if p == 0: return "0"
    if p < 1e-6: return f"{p:.2e}"
    if p < 1:    return f"{p:.8f}".rstrip("0").rstrip(".")
    return f"{p:.4f}"


def fmt_money(n):
    if n >= 1_000_000: return f"${n / 1_000_000:.2f}M"
    if n >= 1_000:     return f"${n / 1_000:.2f}K"
    return f"${n:.2f}"


def check_alert(chg):
    """根据涨跌幅判断是否报警，返回 (是否暴涨, 描述, 触发规则简写) 或 None"""
    m5 = chg.get("m5") or 0
    h1 = chg.get("h1") or 0
    h6 = chg.get("h6") or 0
    if m5 >= PUMP_M5: return True,  f"5分钟 +{m5:.1f}%",  f"5m≥+{PUMP_M5}%"
    if h1 >= PUMP_H1: return True,  f"1小时 +{h1:.1f}%",  f"1h≥+{PUMP_H1}%"
    if h6 >= PUMP_H6: return True,  f"6小时 +{h6:.1f}%",  f"6h≥+{PUMP_H6}%"
    if m5 <= DUMP_M5: return False, f"5分钟 {m5:.1f}%",   f"5m≤{DUMP_M5}%"
    if h1 <= DUMP_H1: return False, f"1小时 {h1:.1f}%",   f"1h≤{DUMP_H1}%"
    return None


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] 监控钱包 {WALLET_ADDRESS}")

    state = load_state()
    holdings = get_token_holdings()
    print(f"持仓 token 数: {len(holdings)}")
    if not holdings:
        save_state(state)
        return

    dex = get_dex_data(list(holdings.keys()))
    print(f"DexScreener 返回 {len(dex)} 个 token 的数据")

    now = int(time.time())
    prev_known = set(state.get("known_tokens", []))
    new_tokens = [m for m in holdings if m not in prev_known]

    # 新增 token 提醒（首次运行不推，避免一次几十条）
    if new_tokens and prev_known:
        lines = ["🆕 <b>钱包新增 token</b>"]
        for m in new_tokens:
            sym = ((dex.get(m) or {}).get("baseToken") or {}).get("symbol") or m[:6]
            lines.append(f"• {sym}  <code>{m}</code>")
        send_telegram("\n".join(lines))

    alerts_sent = 0
    miao_alerts = []  # 累积本轮所有报警，最后汇总成一条喵提醒

    for mint, balance in holdings.items():
        info = dex.get(mint)
        if not info:
            print(f"  {mint[:8]}.. 无 DEX 数据，跳过")
            continue

        price   = float(info.get("priceUsd") or 0)
        usd_val = price * balance
        if usd_val < MIN_HOLDING_USD and mint not in new_tokens:
            continue

        chg    = info.get("priceChange") or {}
        result = check_alert(chg)
        if not result:
            continue

        is_pump, reason, rule = result

        # 冷却
        last = state.get("alerts", {}).get(mint, 0)
        if now - last < COOLDOWN_MINUTES * 60:
            print(f"  {mint[:8]}.. {reason} (冷却中，跳过)")
            continue

        bt    = info.get("baseToken") or {}
        sym   = bt.get("symbol", "?")
        name  = bt.get("name", "?")
        liq   = (info.get("liquidity") or {}).get("usd") or 0
        mcap  = info.get("fdv") or info.get("marketCap") or 0
        m5    = chg.get("m5")  or 0
        h1    = chg.get("h1")  or 0
        h6    = chg.get("h6")  or 0
        h24   = chg.get("h24") or 0

        emoji = "🚀" if is_pump else "🔻"
        action = "暴涨" if is_pump else "暴跌"
        msg = (
            f"{emoji} <b>{sym} {action}</b>\n"
            f"📌 触发规则: <b>{rule}</b>  (实际 {reason})\n"
            f"<i>{name}</i>\n\n"
            f"💵 价格:    ${fmt_price(price)}\n"
            f"📊 持仓:    {balance:,.4g} ≈ {fmt_money(usd_val)}\n"
            f"💧 流动性: {fmt_money(liq)}\n"
            f"🏷 市值:    {fmt_money(mcap)}\n"
            f"📈 5m / 1h / 6h / 24h:\n"
            f"     {m5:+.1f}% / {h1:+.1f}% / {h6:+.1f}% / {h24:+.1f}%\n\n"
            f"<code>{mint}</code>\n\n"
            f'<a href="https://gmgn.ai/sol/token/{mint}">GMGN</a>'
            f' | <a href="https://dexscreener.com/solana/{mint}">DexScreener</a>'
            f' | <a href="https://photon-sol.tinyastro.io/en/lp/{mint}">Photon</a>'
        )
        send_telegram(msg)
        # 累积喵提醒，本轮最后统一发送（避免触发30秒频控）
        miao_alerts.append(f"{emoji}{sym} {rule}({reason}) 持仓{fmt_money(usd_val)}")
        state.setdefault("alerts", {})[mint] = now
        alerts_sent += 1
        print(f"  ✅ 已推送 {sym}  {reason}")
        time.sleep(1)  # 避免 Telegram 限流

    # 汇总发送喵提醒（本轮所有命中合并成一条，规避30秒频控）
    if miao_alerts:
        if len(miao_alerts) == 1:
            send_miao_remind(miao_alerts[0])
        else:
            head = f"⚠️本轮{len(miao_alerts)}个币异动:\n"
            send_miao_remind(head + "\n".join(miao_alerts[:5]))

    # 清理 24h 之前的 alert 记录
    state["alerts"] = {m: t for m, t in state.get("alerts", {}).items() if now - t < 86400}
    state["known_tokens"] = sorted(holdings.keys())
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print(f"完成。共发送 {alerts_sent} 条提醒。")


if __name__ == "__main__":
    main()
