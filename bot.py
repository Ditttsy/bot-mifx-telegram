import base64
import logging
import os
import threading
import time
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yfinance as yf
from flask import Flask

# --- 1. WEB SERVER MINI (KEEP-ALIVE) ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot Trading MIFX + AI Chart Vision Aktif 24/7, Cok!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- 2. CONFIG BOT TELEGRAM & GEMINI AI ---
TOKEN = "9132426420:AAFzMw8G7g-Ev7XQn9NF9tE4zWO_2D-wAbg"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"
GEMINI_API_KEY = "f57f304431a74285892e8cce6b66dd7b"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

DAFTAR_PAIR = {
    "eurusd": {"ticker": "EURUSD=X", "nama": "EUR/USD (Forex)", "jarak_sl": 0.0030},
    "gbpusd": {"ticker": "GBPUSD=X", "nama": "GBP/USD (Cable)", "jarak_sl": 0.0040},
    "xauusd": {"ticker": "GC=F", "nama": "XAU/USD (Gold/Emas)", "jarak_sl": 5.00},
    "usdjpy": {"ticker": "USDJPY=X", "nama": "USD/JPY (Yen)", "jarak_sl": 0.35}
}

# --- FUNGSI ANALISA SCREENSHOT CANDLESTICK VIA GEMINI VISION ---
def analisa_gambar_chart(file_id, caption_user=""):
    try:
        res_file = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}", timeout=10).json()
        if not res_file.get("ok"):
            return "❌ Gagal mengambil file gambar dari Telegram, Cok!"
            
        file_path = res_file["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        
        img_bytes = requests.get(file_url, timeout=15).content
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        prompt_trader = (
            "Kamu adalah analis teknikal forex & gold (XAUUSD) profesional dengan gaya bahasa santai tapi tajam. "
            "Analisa screenshot chart candlestick ini secara objektif:\n"
            "1. Identifikasi Pair & Timeframe (jika terlihat di gambar) serta Harga Terakhir.\n"
            "2. Baca struktur market saat ini (Bullish, Bearish, atau Sideways), perhatikan bentuk candlestick terakhir (wick/ekor, momentum, rejection), area Support/Resistance, atau indikator yang terlihat.\n"
            "3. Berikan keputusan tegas: REKOMENDASI BUY (Long), SELL (Short), atau WAIT & SEE (jangan paksakan entry kalau market jelek).\n"
            "4. Berikan estimasi area Entry, Stop Loss (SL), dan Take Profit (TP 1 & TP 2) yang masuk akal berdasarkan skala harga di sumbu kanan chart.\n"
            "Gunakan format rapi dengan bullet points dan bold agar mudah dibaca di Telegram."
        )
        if caption_user:
            prompt_trader += f"\n\nCatatan tambahan dari user: {caption_user}"
            
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_trader},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_b64
                        }
                    }
                ]
            }]
        }
        
        response = requests.post(gemini_url, json=payload, timeout=30)
        data_ai = response.json()
        
        if "candidates" in data_ai:
            hasil_analisa = data_ai["candidates"][0]["content"]["parts"][0]["text"]
            return hasil_analisa
        else:
            err_msg = data_ai.get("error", {}).get("message", "Unknown Error")
            print(f"Gemini API Error: {err_msg}")
            return f"❌ AI gagal baca gambar, Cok! Error: `{err_msg}`"
            
    except Exception as e:
        print(f"Exception Vision: {e}")
        return f"❌ Terjadi error pas proses gambar: `{e}`"

# --- FUNGSI GENERATE CHART MANUAL (/analisa) ---
def generate_chart_dan_analisa(kode_pair):
    if kode_pair not in DAFTAR_PAIR:
        kode_pair = "eurusd"
        
    info = DAFTAR_PAIR[kode_pair]
    ticker_symbol = info["ticker"]
    
    df_m15 = None
    df_h1 = None
    
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/53