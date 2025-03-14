import json
import telebot
import requests
from io import BytesIO

# ---------------------------
# CONFIGURACIÓN TELEGRAM
# ---------------------------
TELEGRAM_BOT_TOKEN = "7613276325:AAGPgY1kP2L14smmv0-YF5lPjcGwo9s9epc"  # Reemplaza con tu token real
CHAT_ID = -1002277480424  # Reemplaza con el ID del chat, grupo o canal

def load_deals(file_path):
    """
    Carga y retorna la lista de ofertas procesadas desde el archivo JSON.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            deals = json.load(f)
        return deals
    except Exception as e:
        print("❌ Error al cargar el archivo JSON:", e)
        return None

def send_deals_to_telegram(deals):
    """
    Envía cada oferta a través del bot de Telegram.
    Intenta descargar la imagen usando un header User-Agent para simular un navegador.
    Si ocurre algún error, envía solo el mensaje de texto.
    """
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
    
    for deal in deals[:1]:
        caption = (
            f"🔥 *PRECIO MÁS BAJO AMAZON* 🔥\n\n"
            f"🛒 *{deal['Title']}*\n\n"
            f"💰 Precio Original: $ {deal['Precio Original']:.2f} MXN\n"
            f"⚡ Precio con Descuento: $ {deal['Precio con Descuento']:.2f} MXN\n"
            f"📉 Descuento: {deal['Descuento (%)']:.2f}%\n\n"
            f"🔗 [¡Link de Amazon Aquí!]({deal['Link']})"
        )
        
        image_url = deal.get("Image")
        try:
            if image_url:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/99.0.4844.51 Safari/537.36"
                }
                response = requests.get(image_url, headers=headers)
                content_type = response.headers.get("Content-Type", "").lower()
                if "image" not in content_type:
                    raise ValueError("La URL no devuelve contenido de imagen")
                image_bytes = BytesIO(response.content)
                bot.send_photo(CHAT_ID, photo=image_bytes, caption=caption, parse_mode="Markdown")
                print("✅ Oferta enviada con imagen:", deal["Title"])
            else:
                bot.send_message(CHAT_ID, caption, parse_mode="Markdown")
                print("✅ Oferta enviada (sin imagen):", deal["Title"])
        except Exception as e:
            print("⚠️ Error enviando foto para:", deal["Title"], "->", e)
            try:
                bot.send_message(CHAT_ID, caption, parse_mode="Markdown")
                print("✅ Oferta enviada (solo texto):", deal["Title"])
            except Exception as ex:
                print("❌ Error enviando oferta (texto):", deal["Title"], ex)

if __name__ == "__main__":
    file_path = "raw_response.json"
    deals = load_deals(file_path)
    if deals:
        send_deals_to_telegram(deals)
        print("✅ Todas las ofertas han sido enviadas a Telegram")
    else:
        print("❌ No se pudieron cargar las ofertas desde raw_response.json")
