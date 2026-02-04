import telebot
import requests
import schedule
import time
import threading
import os
from flask import Flask

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
# Asegúrate de configurar estas dos en el panel de Koyeb
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# El ID debe ser un número entero
try:
    CHAT_ID = int(os.environ.get('TELEGRAM_CHAT_ID', 2017725004))
except:
    CHAT_ID = 2017725004

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ESTADO GLOBAL ---
# Esta variable evita que el bot te mande alertas repetidas cada hora
estado_alerta = None  # Puede ser "bajo", "alto" o None

# --- SERVIDOR WEB (Para el Health Check de Koyeb) ---
@app.route('/')
def health_check():
    return "Bot de Cripto: Activo y Monitoreando", 200

def run_flask():
    # Koyeb usa el puerto 8080 por defecto
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- LÓGICA DE DATOS ---

def obtener_datos(ticker):
    """Obtiene precio y variación de 24h desde Coinbase Exchange"""
    try:
        url = f"https://api.exchange.coinbase.com/products/{ticker}-USD/stats"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        actual = float(data['last'])
        apertura = float(data['open'])
        variacion = ((actual - apertura) / apertura) * 100
        return actual, variacion
    except Exception as e:
        print(f"❌ Error consultando {ticker}: {e}")
        return None, None

# --- COMANDOS INTERACTIVOS ---

@bot.message_handler(commands=['start', 'help'])
def bienvenida(message):
    bot.reply_to(message, "✅ **Bot de Monitoreo Cripto Activo**\n\nComandos:\n- /precio: Ver valores actuales y variación 24h.")

@bot.message_handler(commands=['precio'])
def comando_precio(message):
    btc, btc_v = obtener_datos("BTC")
    eth, eth_v = obtener_datos("ETH")
    
    if btc and eth:
        e_btc = "🟢" if btc_v >= 0 else "🔴"
        e_eth = "🟢" if eth_v >= 0 else "🔴"
        msg = (f"💰 **Precios Actuales (24h):**\n\n"
               f"**BTC:** `${btc:,.2f}` ({e_btc} {btc_v:+.2f}%)\n"
               f"**ETH:** `${eth:,.2f}` ({e_eth} {eth_v:+.2f}%)")
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "⚠️ Error al obtener precios. Intenta de nuevo en unos segundos.")

# --- TAREAS AUTOMÁTICAS ---

def reporte_diario():
    """Se ejecuta a las 9:30 AM ART (12:30 UTC)"""
    btc, btc_v = obtener_datos("BTC")
    eth, eth_v = obtener_datos("ETH")
    
    if btc and eth:
        e_btc = "🟢" if btc_v >= 0 else "🔴"
        e_eth = "🟢" if eth_v >= 0 else "🔴"
        mensaje = (f"📊 **REPORTE DIARIO MATINAL**\n\n"
                   f"Bitcoin: `${btc:,.2f}` ({e_btc} {btc_v:+.2f}%)\n"
                   f"Ethereum: `${eth:,.2f}` ({e_eth} {eth_v:+.2f}%)")
        bot.send_message(CHAT_ID, mensaje, parse_mode="Markdown")

def verificar_alertas():
    """Revisa cada hora si el BTC rompió los límites"""
    global estado_alerta
    btc, _ = obtener_datos("BTC")
    
    if btc:
        # Lógica para BTC menor a 72,000
        if btc < 72000:
            if estado_alerta != "bajo":
                bot.send_message(CHAT_ID, f"📉 **ALERTA BAJISTA:** BTC cayó por debajo de 72k! Valor actual: `${btc:,.2f}`", parse_mode="Markdown")
                estado_alerta = "bajo"
        
        # Lógica para BTC mayor a 80,000
        elif btc > 80000:
            if estado_alerta != "alto":
                bot.send_message(CHAT_ID, f"🚀 **ALERTA ALCISTA:** BTC superó los 80k! Valor actual: `${btc:,.2f}`", parse_mode="Markdown")
                estado_alerta = "alto"
        
        # Resetear estado si vuelve al rango normal (entre 72k y 80k)
        else:
            estado_alerta = None

def loop_planificador():
    """Hilo encargado de manejar el reloj y los horarios"""
    # 9:30 AM Argentina es 12:30 UTC
    schedule.every().day.at("12:30").do(reporte_diario)
    # Revisión de alertas cada hora
    schedule.every().hour.do(verificar_alertas)
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Revisa el planificador cada minuto

# --- INICIO DEL BOT ---

if __name__ == "__main__":
    # 1. Hilo para el servidor Flask (Salud de Koyeb)
    threading.Thread(target=run_flask, daemon=True).start()
    
    # 2. Hilo para las tareas automáticas (Reportes y Alertas)
    threading.Thread(target=loop_planificador, daemon=True).start()
    
    # 3. Hilo principal para recibir mensajes de Telegram
    print("🚀 Bot iniciado correctamente...")
    bot.infinity_polling()
