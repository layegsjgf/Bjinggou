import asyncio
import aiohttp
import os
import json
from datetime import datetime

# ========== 从环境变量读取配置 ==========
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
THRESHOLD_PERCENT = 20  # 涨幅超过 20% 触发提醒

# 检查配置是否完整
if not all([WALLET_ADDRESS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("错误：缺少必要的环境变量配置")
    print("请检查 Secrets 设置")
    exit(1)

STATE_FILE = "last_value.json"
# =======================================

async def get_portfolio_value():
    """通过 Solscan API 获取账户总价值"""
    url = f"https://public-api.solscan.io/account/{WALLET_ADDRESS}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # 总价值在 data 字段中
                    if "data" in data and "totalUsdValue" in data["data"]:
                        return float(data["data"]["totalUsdValue"])
                    elif "totalUsdValue" in data:
                        return float(data["totalUsdValue"])
                    else:
                        print(f"返回数据格式: {data.keys()}")
                        return 0
                else:
                    print(f"Solscan API 返回错误: {resp.status}")
                    return 0
        except Exception as e:
            print(f"获取总价值失败: {e}")
            return 0

async def send_telegram(message):
    """发送 Telegram 通知"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            })
        except Exception as e:
            print(f"发送 Telegram 失败: {e}")

def load_last_value():
    """读取上次保存的总价值"""
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("value", 0)
    except:
        return 0

def save_current_value(value):
    """保存当前总价值"""
    with open(STATE_FILE, "w") as f:
        json.dump({"value": value, "timestamp": datetime.now().isoformat()}, f)

async def monitor():
    """主监控函数"""
    print(f"[{datetime.now()}] 开始监控钱包: {WALLET_ADDRESS}")
    
    # 获取当前总价值
    current_value = await get_portfolio_value()
    
    if current_value == 0:
        print("获取总价值失败，可能是 API 限流或地址无效")
        return
    
    print(f"当前账户总价值: ${current_value:.2f}")
    
    # 读取上次值并比较
    last_value = load_last_value()
    
    if last_value > 0 and current_value > last_value:
        change_percent = (current_value - last_value) / last_value * 100
        change_abs = current_value - last_value
        
        if change_percent >= THRESHOLD_PERCENT:
            message = f"""
🚀 <b>账户价值暴涨提醒！</b> 🚀

💰 <b>上次价值</b>: ${last_value:.2f}
💎 <b>当前价值</b>: ${current_value:.2f}
📈 <b>涨幅</b>: {change_percent:.1f}% (+${change_abs:.2f})

🔗 <a href="https://solscan.io/account/{WALLET_ADDRESS}">点击查看 Solscan</a>

⚡️ 快去操作！
"""
            await send_telegram(message)
            print(f"✅ 已发送提醒！涨幅: {change_percent:.1f}%")
        else:
            print(f"涨幅 {change_percent:.1f}% 未达到阈值 {THRESHOLD_PERCENT}%")
    elif last_value > 0 and current_value <= last_value:
        print(f"价值下降或持平: ${last_value:.2f} → ${current_value:.2f}")
    else:
        print("首次运行，已保存当前值")
    
    # 保存当前值
    save_current_value(current_value)
    print("监控完成")

if __name__ == "__main__":
    asyncio.run(monitor())
