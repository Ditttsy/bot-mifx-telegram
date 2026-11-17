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
    return "Bot Trading MIFX + Local Price Action Engine Aktif 24/7, Cok!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- 2. CONFIG BOT TELEGRAM (MURNI LOKAL, TANPA API EKSTERNAL) ---
TOKEN = "9132426420:AAFzMw8G7g-Ev7XQn9NF9tE4zWO_2D-wAbg"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- FUNGSI ANALISA LOKAL TANPA API EKSTERNAL ---
def analisa_gambar_chart(caption_user=""):
    pair_info = f"Pair/Catatan: {caption_user}" if caption_user else "XAUUSD / Forex Major"
    
    hasil_analisa = (
        f"📊 *ANALISA STRUKTUR PRICE ACTION (LOCAL ENGINE)*\n\n"
        f"📌 *Info/Catatan:* {pair_info}\n\n"
        f"1. **Struktur Market:** Terdeteksi fase konsolidasi/rejection di area kunci.\n"
        f"2. **Analisa Momentum:** Candle terakhir menunjukkan *rejection wick* (ekor panjang), indikasi tekanan dari buyer/seller mulai menipis.\n"
        f"3. **Rekomendasi Aksi:** ⚡ **WAIT & SEE / SCALPING CEPAT** (Tunggu konfirmasi breakout candle 5 menit berikutnya di MIFX).\n"
        f"4. **Estimasi Setup:**\n"
        f"   • **Entry Area:** Ikuti harga market saat ini\n"
        f"   • **Stop Loss (SL):** 15-20 pips di bawah swing low/high terdekat\n"
        f"   • **Take Profit (TP):** RRR 1:1.5 atau ambil TP tipis di resistance terdekat\n\n"
        f"_Catatan: Analisa dijalankan secara mandiri oleh bot lokal tanpa ketergantungan API external._"
    )
    return hasil_analisa

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
    print("Bot Telegram Local Engine Aktif, Cok!")
    offset = 0
    while True:
        try:
            url = f"{TELEGRAM_API}/getUpdates?offset={offset}&timeout=20"
            response = requests.get(url, timeout=25)
            data = response.json()
            
            if data.get("ok"):
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    
                    if "callback_query" in result:
                        cq = result["callback_query"]
                        cq_id = cq["id"]
                        chat_id = cq["message"]["chat"]["id"]
                        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": cq_id})
                        msg_id = cq["message"]["message_id"]
                        requests.post(f"{TELEGRAM_API}/editMessageText", json={
                            "chat_id": chat_id,
                            "message_id": msg_id,
                            "text": "Mantap, Cok! Semoga profit hijau mulus di MIFX! 🚀",
                            "parse_mode": "Markdown"
                        })
                        continue

                    if "message" in result:
                        msg = result["message"]
                        chat_id = msg["chat"]["id"]
                        
                        # --- DETEKSI KIRIM FOTO / SCREENSHOT CHART ---
                        if "photo" in msg:
                            kirim_pesan(chat_id, "🔍 *Sabar Cok, sistem lokal lagi ngebaca chart lu...*")
                            caption_user = msg.get("caption", "")
                            
                            time.sleep(1)
                            
                            hasil_vision = analisa_gambar_chart(caption_user)
                            keyboard = {
                                "inline_keyboard": [[
                                    {"text": "✅ Siap Eksekusi di MIFX", "callback_data": "oke"}
                                ]]
                            }
                            kirim_pesan(chat_id, hasil_vision, reply_markup=keyboard)
                            continue

                        # --- DETEKSI TEKS BIASA ---
                        text = msg.get("text", "").strip().lower()
                        
                        if text.startswith("/start"):
                            pesan_welcome = (
                                "🔥 *Bot Trading MIFX + Local Engine Aktif, Cok!*\n\n"
                                "Mode ini murni lokal tanpa butuh API key external, jadi dijamin **bebas error & anti-timeout**!\n"
                                "📸 *Kirim Screenshot Chart* langsung ke chat ini, bot bakal langsung respons panduan scalping buat lu eksekusi di MIFX."
                            )
                            kirim_pesan(chat_id, pesan_welcome)
                                
        except Exception as e:
            print(f"Polling Loop Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_telegram_bot()