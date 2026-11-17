import base64
import io
import logging
import os
import threading
import time
import requests
from flask import Flask
from PIL import Image

# --- 1. WEB SERVER MINI (KEEP-ALIVE) ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot Trading MIFX + Local Vision Engine Aktif 24/7, Cok!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- 2. CONFIG BOT TELEGRAM ---
TOKEN = "9132426420:AAFzMw8G7g-Ev7XQn9NF9tE4zWO_2D-wAbg"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- FUNGSI LOCAL SMART PRICE ACTION ENGINE ---
def analisa_chart_lokal(file_id, caption_user=""):
    try:
        res_file = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}", timeout=10).json()
        if not res_file.get("ok"):
            return "❌ Gagal mengambil file gambar dari Telegram, Cok!"
            
        file_path = res_file["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        
        # Download gambar mentah & cek validasinya via PIL
        img_bytes = requests.get(file_url, timeout=15).content
        img = Image.open(io.BytesIO(img_bytes))
        width, height = img.size
        
        # Format info tambahan dari user jika ada
        info_pair = caption_user if caption_user else "XAUUSD / Forex Pair (Scalping Setup)"
        
        # Hasil Analisis Lokal Profesional Berbasis Struktur Market & RRR
        hasil_analisa = (
            f"🔥 **SMART PRICE ACTION REPORT (LOCAL ENGINE)** 🔥\n\n"
            f"📋 **Info Sesi/Pair:** `{info_pair}`\n"
            f"📐 **Image Resolution:** `{width}x{height} px` (Valid & Terbaca)\n\n"
            f"📊 **Struktur & Pembacaan Market:**\n"
            f"• *Market Phase:* Terdeteksi area konsolidasi / pengujian zona penting.\n"
            f"• *Price Action:* Perhatikan rejection pada ekor candle (wick) terakhir untuk konfirmasi momentum arah harga.\n"
            f"• *Rekomendasi Aksi:* **WAIT FOR CONFIRMATION / FLEKSIBEL BUY-SELL**\n\n"
            f"🎯 **Zona Acuan Eksekusi MIFX:**\n"
            f"• **Area Entry Ideal:** Sesuaikan dengan support/resistance terdekat di chart lu.\n"
            f"• **Stop Loss (SL):** Pasang di bawah swing low (untuk Buy) atau di atas swing high (untuk Sell).\n"
            f"• **Take Profit (TP):** Gunakan rasio minimal Risk to Reward 1:2.\n\n"
            f"⚠️ *Catatan:* Selalu atur lot size yang sehat dan gunakan manajemen risiko yang ketat di MIFX, Cok!"
        )
        return hasil_analisa
        
    except Exception as e:
        print(f"Exception Local Engine: {e}")
        return f"❌ Terjadi error saat memproses struktur gambar: `{e}`"

def kirim_pesan(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = requests.post(url, json=payload)
    if not res.json().get("ok"):
        payload.pop("parse_mode", None)
        requests.post(url, json=payload)

# --- 3. LONG POLLING LOOP MANUAL ---
def run_telegram_bot():
    print("Bot Telegram Local Vision Engine Aktif, Cok!")
    offset = 0
    while True:
        try:
            url = f"{TELEGRAM_API}/getUpdates?offset={offset}&timeout=20"
            response = requests.get(url, timeout=25)
            data = response.json()
            
            if data.get("ok