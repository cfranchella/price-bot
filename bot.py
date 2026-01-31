import telebot
import requests
import schedule
import time
import threading
import os
from flask import Flask

# --- CONFIGURACIÓN ---
# Ahora usamos os.environ.get para leer las variables desde Koyeb
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = int(os.environ.get('TELEGRAM_CHAT_ID', 2017725004)) 

if not TOKEN:
    print("❌ ERROR: No se encontró la variable TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Servidor web para Koyeb
@app.route('/')
def health_check():
    return "Bot vivo y coleando", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- LÓGICA DE PRECIOS ---

def obtener_datos(ticker):
    try:
        url = f"https://api.exchange.coinbase.com/products/{ticker}-USD/stats"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        actual = float(data['last'])
        apertura = float(data['open'])
        variacion = ((actual - apertura) / apertura) * 100
        return actual, variacion
    except Exception as e:
        print(f"Error en {ticker}: {e}")
        return None, None

# --- COMANDOS ---

@bot.message_handler(commands=['precio'])
def comando_precio(message):
    btc, btc_v = obtener_datos("BTC")
    eth, eth_v = obtener_datos("ETH")
    if btc:
        e_btc = "🟢" if btc_v >= 0 else "🔴"
        e_eth = "🟢" if eth_v >= 0 else "🔴"
        msg = (f"💰 **Precios (24h):**\n\n"
               f"₿ **BTC:** `${btc:,.2f}` ({e_btc} {btc_v:+.2f}%)\n"
               f"♦️ **ETH:** `${eth:,.2f}` ({e_eth} {eth_v:+.2f}%)")
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- TAREAS PROGRAMADAS ---

def reporte_diario():
    btc, btc_v = obtener_datos("BTC")
    if btc:
        e_btc = "🟢" if btc_v >= 0 else "🔴"
        bot.send_message(CHAT_ID, f"📊 **REPORTE MATINAL**\nBTC: `${btc:,.2f}` ({e_btc} {btc_v:+.2f}%)", parse_mode="Markdown")

def verificar_alertas():
    btc, _ = obtener_datos("BTC")
    if btc:
        if btc < 80000:
            bot.send_message(CHAT_ID, f"📉 **ALERTA:** BTC bajo 80k! (${btc:,.2f})", parse_mode="Markdown")
        elif btc > 85000:
            bot.send_message(CHAT_ID, f"🚀 **ALERTA:** BTC sobre 85k! (${btc:,.2f})", parse_mode="Markdown")

def loop_reloj():
    # 12:30 UTC es 9:30 AM Argentina
    schedule.every().day.at("12:30").do(reporte_diario)
    schedule.every().hour.do(verificar_alertas)
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- INICIO ---

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=loop_reloj, daemon=True).start()
    print("🚀 Bot iniciado correctamente...")
    bot.infinity_polling()