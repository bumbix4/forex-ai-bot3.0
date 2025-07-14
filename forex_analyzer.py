import os
import time
import openai
import requests
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# 🔐 API Keys din ENV
# =========================
openai.api_key = os.environ["OPENAI_API_KEY"]
telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]
alpha_key = os.environ["ALPHA_VANTAGE_KEY"]

# =========================
# 🔧 Setări Google Sheets
# =========================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Forex Logs").sheet1

# =========================
# 🪙 Valute urmărite
# =========================
pairs = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD",
    "GBP/JPY": "GBPJPY",
    "USD/CHF": "USDCHF"
}

# =========================
# 🔁 Funcții de date
# =========================
def get_rsi(symbol):
    url = f"https://www.alphavantage.co/query?function=RSI&symbol={symbol}&interval=15min&time_period=14&series_type=close&apikey={alpha_key}"
    try:
        rsi = requests.get(url).json()["Technical Analysis: RSI"]
        return float(list(rsi.values())[0]["RSI"])
    except:
        return "N/A"

def get_price(pair):
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={pair[:3]}&to_currency={pair[-3:]}&apikey={alpha_key}"
    try:
        data = requests.get(url).json()["Realtime Currency Exchange Rate"]
        return float(data["5. Exchange Rate"])
    except:
        return "N/A"

# =========================
# 🧠 Prompt GPT
# =========================
def build_prompt(data):
    prompt = "You are a professional Forex analyst. Provide conservative + aggressive setups for each pair:\n\n"
    for pair, info in data.items():
        prompt += f"{pair}: Price={info['price']}, RSI={info['rsi']}\n"
    prompt += "\nFormat: Trend, Entry (conservative/aggressive), SL, TP, Confidence."
    return prompt

def ask_gpt(prompt):
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a disciplined institutional Forex analyst."},
            {"role": "user", "content": prompt}
        ]
    )
    return r["choices"][0]["message"]["content"]

# =========================
# 📲 Telegram Functions
# =========================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

# =========================
# 📈 Logging în Sheets
# =========================
def log_to_sheet(gpt_response):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    lines = gpt_response.split("\n\n")
    for block in lines:
        if any(pair in block for pair in pairs):
            row = [now, block.strip()]
            sheet.append_row(row)

# =========================
# 🧩 MAIN
# =========================
def main():
    data = {}
    for name, symbol in pairs.items():
        data[name] = {
            "rsi": get_rsi(symbol),
            "price": get_price(name)
        }
        time.sleep(15)  # Delay to avoid Alpha Vantage limit

    prompt = build_prompt(data)
    result = ask_gpt(prompt)
    print("📊 GPT Response:\n", result)
    send_telegram(result)
    log_to_sheet(result)

if __name__ == "__main__":
    main()

