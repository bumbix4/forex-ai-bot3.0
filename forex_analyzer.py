import os
import time
import openai
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# API keys din Railway variables
openai.api_key = os.environ["OPENAI_API_KEY"]
telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]
alpha_key = os.environ["ALPHA_VANTAGE_KEY"]

# Valute analizate
pairs = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD",
    "GBP/JPY": "GBPJPY",
    "USD/CHF": "USDCHF"
}

# RSI API call
def get_rsi(symbol):
    url = f"https://www.alphavantage.co/query?function=RSI&symbol={symbol}&interval=15min&time_period=14&series_type=close&apikey={alpha_key}"
    try:
        rsi = requests.get(url).json()["Technical Analysis: RSI"]
        return float(list(rsi.values())[0]["RSI"])
    except:
        return "N/A"

# Price API call
def get_price(pair):
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={pair[:3]}&to_currency={pair[-3:]}&apikey={alpha_key}"
    try:
        data = requests.get(url).json()["Realtime Currency Exchange Rate"]
        return float(data["5. Exchange Rate"])
    except:
        return "N/A"

# Prompt GPT
def build_prompt(data):
    prompt = "You are a professional Forex analyst. Provide a concise intraday forecast:\n\n"
    for pair, info in data.items():
        prompt += f"{pair}: Price={info['price']}, RSI={info['rsi']}\n"
    prompt += "\nReturn: Trend, Entry idea, SL, TP, Confidence for each pair."
    return prompt

# Cerere GPT
def ask_gpt(prompt):
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a financial market strategist."},
            {"role": "user", "content": prompt}
        ]
    )
    return r["choices"][0]["message"]["content"]

# Trimitere text în Telegram
def send_telegram(text):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

# Trimitere imagine în Telegram
def send_telegram_image(image_path):
    url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
    with open(image_path, "rb") as img:
        payload = {"chat_id": chat_id}
        files = {"photo": img}
        requests.post(url, data=payload, files=files)

# Creare imagine RSI + preț
def draw_chart(pair, price, rsi):
    fig, ax1 = plt.subplots(figsize=(6, 4))
    
    ax1.set_title(f"{pair} Analysis ({datetime.now().strftime('%H:%M %d-%m-%Y')})")
    ax1.plot([0, 1], [price, price], label="Current Price", linewidth=2)
    ax1.axhline(70, color='red', linestyle='--', label="RSI Overbought")
    ax1.axhline(30, color='blue', linestyle='--', label="RSI Oversold")
    ax1.axhline(rsi, color='green', label=f"RSI: {rsi}", linewidth=2)

    ax1.set_ylim(price - 50, price + 50)
    ax1.legend()
    
    plt.tight_layout()
    filepath = f"{pair.replace('/', '')}_chart.png"
    plt.savefig(filepath)
    plt.close()
    
    return filepath

# Rulare principală
def main():
    data = {}
    for name, symbol in pairs.items():
        data[name] = {
            "rsi": get_rsi(symbol),
            "price": get_price(name)
        }
        time.sleep(15)  # evită limita de requests Alpha Vantage

    prompt = build_prompt(data)
    result = ask_gpt(prompt)
    print("📊 GPT Response:\n", result)
    send_telegram(result)

    # Imagine pentru XAU/USD dacă are date valide
    if data["XAU/USD"]["price"] != "N/A" and data["XAU/USD"]["rsi"] != "N/A":
        chart_path = draw_chart("XAU/USD", data["XAU/USD"]["price"], data["XAU/USD"]["rsi"])
        send_telegram_image(chart_path)

if __name__ == "__main__":
    main()
