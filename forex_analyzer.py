import os
import time
import openai
import requests
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Chei API din Railway
openai.api_key = os.environ["OPENAI_API_KEY"]
telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]
alpha_key = os.environ["ALPHA_VANTAGE_KEY"]

# Perechi analizate
pairs = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD",
    "GBP/JPY": "GBPJPY",
    "USD/CHF": "USDCHF"
}

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Forex Logs").sheet1

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

def build_prompt(data):
    prompt = "You're a Forex analyst. For each pair below, return two intraday setups:\n"
    prompt += "- Conservative: safe entry, tight SL, lower TP\n"
    prompt += "- Aggressive: higher risk/reward, looser SL, ambitious TP\n"
    prompt += "Include trend and confidence level for both.\n\n"
    for pair, info in data.items():
        prompt += f"{pair}: Price={info['price']}, RSI={info['rsi']}\n"
    return prompt

def ask_gpt(prompt):
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You're a professional financial analyst."},
            {"role": "user", "content": prompt}
        ]
    )
    return r["choices"][0]["message"]["content"]

def smart_alert(result):
    text = result.lower()
    if "breakout" in text or "confirmation" in text:
        return "🚨 POSIBILĂ OPORTUNITATE:\n\n" + result
    elif "overbought" in text or "oversold" in text:
        return "⚠️ RSI EXTREM DETECTAT:\n\n" + result
    else:
        return "ℹ️ Actualizare piețe:\n\n" + result

def send_telegram(text):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def log_to_sheet(raw_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = raw_text.strip().split('\n')
    for line in lines:
        if ":" in line and any(x in line for x in ["XAU", "EUR", "GBP", "USD"]):
            pair = line.split(":")[0]
        elif "Trend:" in line:
            trend = line.split(":")[1].strip()
        elif "Entry" in line:
            entry = line.split(":")[1].strip()
        elif "SL" in line:
            sl = line.split(":")[1].strip()
        elif "TP" in line:
            tp = line.split(":")[1].strip()
        elif "Confidence" in line:
            confidence = line.split(":")[1].strip()
            sheet.append_row([timestamp, pair, trend, entry, sl, tp, confidence])

def main():
    data = {}
    for name, symbol in pairs.items():
        data[name] = {
            "rsi": get_rsi(symbol),
            "price": get_price(name)
        }
        time.sleep(15)

    prompt = build_prompt(data)
    result = ask_gpt(prompt)
    send_telegram(smart_alert(result))
    log_to_sheet(result)
    print("✅ Analiză trimisă și logată.")

if __name__ == "__main__":
    main()
