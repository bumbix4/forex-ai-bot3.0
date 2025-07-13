import os
import time
import openai
import requests
import matplotlib.pyplot as plt
from datetime import datetime

openai.api_key = os.environ["OPENAI_API_KEY"]
telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]
alpha_key = os.environ["ALPHA_VANTAGE_KEY"]

pairs = {
    "XAU/USD": "XAUUSD",
    "EUR/USD": "EURUSD",
    "GBP/JPY": "GBPJPY",
    "USD/CHF": "USDCHF"
}

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
    prompt = "You're a Forex analyst. For each pair below, give structured intraday setups in this format:\n"
    prompt += "{PAIR}: Trend, Entry, SL, TP, Confidence\n\n"
    for pair, info in data.items():
        prompt += f"{pair}: Price={info['price']}, RSI={info['rsi']}\n"
    prompt += "\nRespond first with JSON only, then text forecast."
    return prompt

def ask_gpt(prompt):
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You're a financial market strategist."},
            {"role": "user", "content": prompt}
        ]
    )
    return r["choices"][0]["message"]["content"]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def send_telegram_image(image_path):
    url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
    with open(image_path, "rb") as img:
        payload = {"chat_id": chat_id}
        files = {"photo": img}
        requests.post(url, data=payload, files=files)

def draw_chart(pair, price, rsi, entry=None, sl=None, tp=None):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 6), gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(f"{pair} | {datetime.now().strftime('%H:%M %d-%m-%Y')}", fontsize=12)

    # --- ZONA DE PREȚ ---
    ax1.plot([0, 1], [price, price], 'black', linewidth=2, label=f"Price: {price:.4f}")
    if entry: ax1.axhline(entry, color='orange', linestyle='--', label=f"Entry: {entry}")
    if sl:    ax1.axhline(sl, color='red', linestyle=':', label=f"SL: {sl}")
    if tp:    ax1.axhline(tp, color='green', linestyle=':', label=f"TP: {tp}")
    ax1.legend(loc='upper left')
    ax1.set_ylabel("Price")
    ax1.grid(True)

    range_padding = abs(price * 0.01)
    ax1.set_ylim(price - range_padding, price + range_padding)

    # --- ZONA DE RSI ---
    ax2.axhline(70, color='red', linestyle='--')
    ax2.axhline(30, color='blue', linestyle='--')
    ax2.axhline(rsi, color='green', linewidth=2, label=f"RSI: {rsi:.2f}")
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI")
    ax2.legend(loc='upper left')
    ax2.grid(True)

    fig.text(0.01, 0.01, "RDÉLUX FX AI", fontsize=8, color='gray', alpha=0.5)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    filepath = f"{pair.replace('/', '')}_chart.png"
    plt.savefig(filepath)
    plt.close()
    return filepath

def extract_json_and_text(response):
    import re, json
    match = re.search(r'({.*})', response, re.DOTALL)
    try:
        json_data = json.loads(match.group(1))
    except:
        json_data = {}
    text_start = response.find("\n\n", match.end()) if match else 0
    return json_data, response[text_start:].strip()

def main():
    data = {}
    for name, symbol in pairs.items():
        data[name] = {
            "rsi": get_rsi(symbol),
            "price": get_price(name)
        }
        time.sleep(15)

    prompt = build_prompt(data)
    raw_response = ask_gpt(prompt)
    strategy_data, full_text = extract_json_and_text(raw_response)

    send_telegram(full_text)

    for pair in pairs:
        price = data[pair]["price"]
        rsi = data[pair]["rsi"]
        strat = strategy_data.get(pair, {})

        if price != "N/A" and rsi != "N/A":
            chart = draw_chart(
                pair,
                price,
                rsi,
                strat.get("entry"),
                strat.get("sl"),
                strat.get("tp")
            )
            send_telegram_image(chart)

if __name__ == "__main__":
    main()

