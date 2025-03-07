import telebot
from amazon_scraper import obtener_ofertas_amazon
from dotenv import load_dotenv
import os

# Configuración del bot con el token de @BotFather
TELEGRAM_BOT_TOKEN = "7613276325:AAGPgY1kP2L14smmv0-YF5lPjcGwo9s9epc"
CHAT_ID = -1002277480424

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def enviar_mensaje(mensaje):
    bot.send_message(CHAT_ID, mensaje, parse_mode="Markdown")

if __name__ == "__main__":
    # Obtener ofertas de Amazon
    ofertas = obtener_ofertas_amazon()

    # Enviar cada oferta a Telegram
    for oferta in ofertas:
        enviar_mensaje(oferta)
