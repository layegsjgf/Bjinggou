import requests
import json
from datetime import datetime

# ========== 直接在这里填写配置 ==========
WALLET_ADDRESS = "BBsaiHLZBAkVuhm7x52R2gHgn6Tf8HaPcF7ipchee3r3"
TELEGRAM_BOT_TOKEN = "8613329028:AAHIQ42bAUI2aFoFB-swNNleFzkgMmfbB7s"
TELEGRAM_CHAT_ID = "2113522339"
THRESHOLD_PERCENT = 20
# =======================================

STATE_FILE = "last_value.json"

def get_portfolio_value():
    """通过 Solscan API 获取账户总价值"""
    url = f"https://public-api.solscan.io/account/{WALLET_ADDRESS}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "totalUsdValue" in data["data"]:
                return float(data["data"]["totalUsdValue"])
            elif "totalUsdValue" in data:
                return float(data["totalUsdValue"])
            else:
                print(f"返回数据: {data}")
                return 0
        else:
            print(f"API 返回错误码: {response.status_code}")
            return 0
    except Exception as e:
        print(f"获取总价值失败: {e}")
        return 0

def send_telegram(message):
    """发送 Telegram 通知"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        })
        print("Telegram 消息已发送")
    except Exception as e:
        print(f"发送 Telegram 失败: {e}")

def load_last_value():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("value", 0)
    except:
        return 0

def save_current_value(value):
    with open(STATE_FILE, "w") as f:
        json.dump({"value": value, "timestamp": datetime.now().isoformat()}, f)

def monitor():
    print(f"[{datetime.now()}] 开始监控钱包: {WALLET_ADDRESS}")
    print(f"Telegram Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"Telegram Chat ID: {TELEGRAM_CHAT_ID}")
    
    current_value = get_portfolio_value()
    
    if current_value == 0:
        print("获取总价值失败")
        return
    
    print(f"当前账户总价值: ${current_value:.2f}")
    
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
            send_telegram(message)
            print(f"✅ 已发送提醒！涨幅: {change_percent:.1f}%")
        else:
            print(f"涨幅 {change_percent:.1f}% 未达到阈值 {THRESHOLD_PERCENT}%")
    elif last_value > 0:
        print(f"价值下降或持平: ${last_value:.2f} → ${current_value:.2f}")
    else:
        print("首次运行，已保存当前值")
    
    save_current_value(current_value)
    print("监控完成")

if __name__ == "__main__":
    monitor()
