import logging
import os
import threading
import matplotlib
matplotlib.use('Agg') # Biar matplotlib bisa render gambar tanpa layar/GUI di server cloud
import matplotlib.pyplot as plt
import yfinance as yf
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

# --- 1. WEB SERVER MINI (BUAT KEEP-ALIVE PING) ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot Trading MIFX Aktif 24/7, Cok!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port)

# --- 2. CONFIG BOT TELEGRAM ---
TOKEN = "9132426420:AAFzMw8G7g-Ev7XQn9NF9tE4zWO_2D-wAbg"

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
        print(f"Error: {e}")
        return None, None

async def cek_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args
    pair_pilihan = args[0].lower() if args else "eurusd"
    
    hasil = generate_chart_dan_analisa(pair_pilihan)
    
    if not hasil or not hasil[0]:
        await context.bot.send_message(chat_id=chat_id, text="❌ Gagal menarik data/grafik, Cok! Coba lagi nanti.", parse_mode="Markdown")
        return
        
    laporan, path_gambar = hasil
    keyboard = [[InlineKeyboardButton("✅ Siap Eksekusi di MIFX", callback_data="oke")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    with open(path_gambar, 'rb') as foto:
        await context.bot.send_photo(chat_id=chat_id, photo=foto)
        
    await context.bot.send_message(chat_id=chat_id, text=laporan, parse_mode="Markdown", reply_markup=reply_markup)
    
    if os.path.exists(path_gambar):
        os.remove(path_gambar)

async def tombol_diklik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Mantap, Cok! Semoga profit hijau mulus di MIFX! 🚀", parse_mode="Markdown")

if __name__ == "__main__":
    # Jalankan Flask Server di thread terpisah
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Jalankan Bot Telegram
    app = ApplicationBuilder().token(TOKEN).updater(None).token(TOKEN).build()
    app.add_handler(CommandHandler("analisa", cek_market))
    app.add_handler(CommandHandler("start", cek_market))
    app.add_handler(CallbackQueryHandler(tombol_diklik))
    
    print("Bot Cloud-Ready Aktif, Cok!")
    app.run_polling()