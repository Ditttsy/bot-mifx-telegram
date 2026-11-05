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
    return "Bot Trading MIFX Aktif 24/7, Cok!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- 2. CONFIG BOT TELEGRAM ---
TOKEN = "9132426420:AAFzMw8G7g-Ev7XQn9NF9tE4zWO_2D-wAbg"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

DAFTAR_PAIR = {
    "eurusd": {"ticker": "EURUSD=X", "nama": "EUR/USD (Forex)", "jarak_sl": 0.0030},
    "gbpusd": {"ticker": "GBPUSD=X", "nama": "GBP/USD (Cable)", "jarak_sl": 0.0040},
    "xauusd": {"ticker": "GC=F", "nama": "XAU/USD (Gold/Emas)", "jarak_sl": 5.00},
    "usdjpy": {"ticker": "USDJPY=X", "nama": "USD/JPY (Yen)", "jarak_sl": 0.35}
}

def generate_chart_dan_analisa(kode_pair):
    if kode_pair not in DAFTAR_PAIR:
        return None
        
    info = DAFTAR_PAIR[kode_pair]
    try:
        ticker = yf.Ticker(info["ticker"])
        df_h1 = ticker.history(period="5d", interval="1h")
        df_m15 = ticker.history(period="1d", interval="15m")
        
        if df_m15.empty or df_h1.empty:
            return None
            
        harga_terakhir = float(df_m15['Close'].iloc[-1])
        ma_h1 = df_h1['Close'].mean()
        ma_m15 = df_m15['Close'].mean()
        
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
        is_gold_or_jpy = "GC" in info["ticker"] or "JPY" in info["ticker"]
        dec = 2 if is_gold_or_jpy else 4
        
        if action_type == "buy":
            sl = round(harga_terakhir - jarak_sl, dec)
            tp1 = round(harga_terakhir + jarak_sl, dec)
            tp2 = round(harga_terakhir + (jarak_sl * 2), dec)
        else:
            sl = round(harga_terakhir + jarak_sl, dec)
            tp1 = round(harga_terakhir - jarak_sl, dec)
            tp2 = round(harga_terakhir - (jarak_sl * 2), dec)

        plt.figure(figsize=(8, 4))
        plt.plot(df_m15.index, df_m15['Close'], label='Harga M15', color='#00d2ff', linewidth=2)
        plt.axhline(ma_m15, color='#ff9900', linestyle='--', label='Rata-rata (MA)')
        plt.title(f"Grafik Live {info['nama']} - Harga: {round(harga_terakhir, dec)}")
        plt.xlabel("Waktu")
        plt.ylabel("Harga")
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.tight_layout()
        
        nama_file_gambar = "chart_analisa.png"
        plt.savefig(nama_file_gambar, dpi=150)
        plt.close()
        
        laporan = (
            f"🚨 *ANALISIS MULTI-TIMEFRAME: {info['nama']}* 🚨\n"
            f"Harga Live: `{round(harga_terakhir, dec)}`\n\n"
            f"🌐 *Tren Utama (H1):* {tren_besar}\n"
            f"⚡ *Tren Eksekusi (M15):* Di atas/bawah rata-rata\n"
            f"*{saran}*\n\n"
            f"🛡️ **Manajemen Risiko (SL / TP):**\n"
            f"❌ **Stop Loss (SL):** `{sl}`\n"
            f"🎯 **Take Profit (TP 1):** `{tp1}`\n"
            f"🎯 **Take Profit (TP 2):** `{tp2}`\n\n"
            f"_Grafik visual terlampir di bawah ya, Cok! Eksekusi di MIFX._"
        )
        
        return laporan, nama_file_gambar
    except Exception as e:
        print(f"Error Analisa: {e}")
        return None, None

def kirim_pesan(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def kirim_foto(chat_id, photo_path, caption=None, reply_markup=None):
    url = f"{TELEGRAM_API}/sendPhoto"
    with open(photo_path, 'rb') as foto:
        files = {"photo": foto}
        data = {"chat_id": chat_id, "parse_mode": "Markdown"}
        if caption:
            data["caption"] = caption
        if reply_markup:
            data["reply_markup"] = reply_markup
        requests.post(url, data=data, files=files)

# --- 3. LONG POLLING LOOP MANUAL ---
def run_telegram_bot():
    print("Bot Telegram Polling Manual Aktif, Cok!")
    offset = 0
    while True:
        try:
            url = f"{TELEGRAM_API}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url, timeout=35)
            data = response.json()
            
            if data.get("ok"):
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    
                    # Handle Callback Query (Tombol diklik)
                    if "callback_query" in result:
                        cq = result["callback_query"]
                        cq_id = cq["id"]
                        chat_id = cq["message"]["chat"]["id"]
                        
                        # Jawab callback query biar loading mutar di tombol ilang
                        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": cq_id})
                        
                        # Edit pesan tombol jadi teks sukses
                        msg_id = cq["message"]["message_id"]
                        requests.post(f"{TELEGRAM_API}/editMessageText", json={
                            "chat_id": chat_id,
                            "message_id": msg_id,
                            "text": "Mantap, Cok! Semoga profit hijau mulus di MIFX! 🚀",
                            "parse_mode": "Markdown"
                        })
                        continue

                    # Handle Pesan Teks biasa / Command
                    if "message" in result:
                        msg = result["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "").strip().lower()
                        
                        if text.startswith("/start") or text.startswith("/analisa"):
                            parts = text.split()
                            pair_pilihan = parts[1] if len(parts) > 1 else "eurusd"
                            
                            hasil = generate_chart_dan_analisa(pair_pilihan)
                            if not hasil or not hasil[0]:
                                kirim_pesan(chat_id, "❌ Gagal menarik data/grafik, Cok! Coba lagi nanti.")
                                continue
                                
                            laporan, path_gambar = hasil
                            keyboard = {
                                "inline_keyboard": [[
                                    {"text": "✅ Siap Eksekusi di MIFX", "callback_data": "oke"}
                                ]]
                            }
                            
                            kirim_foto(chat_id, path_gambar, caption=laporan, reply_markup=keyboard)
                            
                            if os.path.exists(path_gambar):
                                os.remove(path_gambar)
                                
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Jalankan Flask Server di thread terpisah (keep-alive)
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Jalankan Bot Telegram Polling Manual
    run_telegram_bot()