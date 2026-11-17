import base64
import logging
import os
import threading
import time
import requests
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
GEMINI_API_KEY = "AQ.Ab8RN6IPkcJUuHy3H7R-lbewBtoWRNfgH4FKGv_pkRG9Locv5Q"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

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
            
        # UPDATE KE MODEL TERBARU SESUAI PESAN ERROR: gemini-3.8-flash
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
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
    print("Bot Telegram AI Vision Murni Aktif, Cok!")
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
                            kirim_pesan(chat_id, "🔍 *Sabar Cok, AI lagi ngebaca struktur candlestick lu...*")
                            file_id_tertinggi = msg["photo"][-1]["file_id"]
                            caption_user = msg.get("caption", "")
                            
                            hasil_vision = analisa_gambar_chart(file_id_tertinggi, caption_user)
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
                                "🔥 *Bot Trading MIFX + AI Chart Reader Aktif, Cok!*\n\n"
                                "Cara pakainya super gampang:\n"
                                "📸 *Kirim Screenshot Chart* langsung ke chat ini (dari TradingView atau MIFX), nanti AI langsung baca polanya & kasih arahan *Buy / Sell + SL/TP* secara akurat!\n\n"
                                "_Tips: Lu bisa tambahin caption pas kirim foto, misal: 'XAUUSD scalping M15'._"
                            )
                            kirim_pesan(chat_id, pesan_welcome)
                                
        except Exception as e:
            print(f"Polling Loop Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_telegram_bot()