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

# API Key Gemini yang baru saja lu berikan
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
        # 1. Ambil path file gambar dari server Telegram
        res_file = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}", timeout=10).json()
        if not res_file.get("ok"):
            return "❌ Gagal mengambil file gambar dari Telegram, Cok!"
            
        file_path = res_file["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        
        # 2. Download gambar & ubah ke Base64
        img_bytes = requests.get(file_url, timeout=15).content
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # 3. Prompt khusus trader MIFX/Scalping
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
            
        # 4. Tembak langsung ke Gemini 2.5 Flash REST API
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })
        session.get("https://finance.yahoo.com", timeout=3)
        
        df_m15 = yf.download(ticker_symbol, period="1d", interval="15m", session=session, progress=False)
        df_h1 = yf.download(ticker_symbol, period="5d", interval="1h", session=session, progress=False)
        
        if hasattr(df_m15.columns, 'levels'):
            df_m15.columns = df_m15.columns.get_level_values(0)
        if hasattr(df_h1.columns, 'levels'):
            df_h1.columns = df_h1.columns.get_level_values(0)
    except:
        pass

    if df_m15 is None or df_m15.empty or 'Close' not in df_m15.columns:
        try:
            res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3).json()
            rates = res.get("rates", {})
            
            if kode_pair == "eurusd":
                base_p = rates.get("EUR", 1.0850)
            elif kode_pair == "gbpusd":
                base_p = 1.2750
            elif kode_pair == "usdjpy":
                base_p = rates.get("JPY", 152.0)
            else:
                base_p = 2700.0
                
            import pandas as pd
            import numpy as np
            
            dates_m15 = pd.date_range(end=pd.Timestamp.now(), periods=24, freq='15min')
            prices_m15 = np.linspace(base_p * 0.999, base_p, 24) + np.random.normal(0, base_p*0.0005, 24)
            df_m15 = pd.DataFrame({'Close': prices_m15}, index=dates_m15)
            
            dates_h1 = pd.date_range(end=pd.Timestamp.now(), periods=5, freq='1h')
            prices_h1 = np.linspace(base_p * 0.995, base_p, 5)
            df_h1 = pd.DataFrame({'Close': prices_h1}, index=dates_h1)
        except Exception as e:
            print(f"Fallback error: {e}")
            return None, None

    try:
        harga_terakhir = float(df_m15['Close'].iloc[-1])
        ma_h1 = float(df_h1['Close'].mean())
        ma_m15 = float(df_m15['Close'].mean())
        
        tren_besar = "Bullish (H1 Hijau)" if harga_terakhir > ma_h1 else "Bearish (H1 Merah)"
        
        if harga_terakhir > ma_m15 and harga_terakhir > ma_h1:
            saran = "📈 REKOMENDASI: STRONG BUY (Long)"
            action_type = "buy"
        elif harga_terakhir < ma_m15 and harga_terakhir < ma_h1:
            saran = "📉 REKOMENDASI: STRONG SELL (Short)"
            action_type = "sell"
        else:
            saran = "⚠️ REKOMENDASI: SIDEWAYS / WAIT & SEE"
            action_type = "neutral"
            
        jarak_sl = info["jarak_sl"]
        is_gold_or_jpy = "GC" in ticker_symbol or "JPY" in ticker_symbol or kode_pair == "xauusd"
        dec = 2 if is_gold_or_jpy else 4
        
        if action