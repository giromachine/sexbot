import keepa
import json
import numpy as np

# ---------------------------
# CONFIGURACIÓN
# ---------------------------
KEEPA_API_KEY = '4ns281h11l6th6dfg6ic193hrb0f1e65lqf64tg1b2d3bje237tnnjs1ln3veeof'

# ---------------------------
# Funciones para manejo seguro del JSON (payload)
# ---------------------------
def safe_load_json(payload_str):
    """
    Intenta cargar un JSON a partir de una cadena.
    Si falla, intenta reemplazar comillas simples por dobles y cargarlo nuevamente.
    Retorna el objeto JSON o None en caso de error.
    """
    try:
        return json.loads(payload_str)
    except json.JSONDecodeError as e:
        print("❌ Error al decodificar JSON:", e)
        try:
            fixed_payload = payload_str.replace("'", "\"")
            return json.loads(fixed_payload)
        except Exception as e2:
            print("❌ Error al intentar arreglar el JSON:", e2)
            return None

def load_json_file(file_path):
    """
    Carga el contenido de un archivo y lo convierte a JSON de forma segura.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw = f.read()
        data = safe_load_json(raw)
        if data is None:
            print("❌ No se pudo cargar el JSON correctamente.")
        return data
    except Exception as e:
        print("❌ Error al leer el archivo JSON:", e)
        return None

# ---------------------------
# Funciones para Keepa API
# ---------------------------
def keepa_init():
    try:
        api = keepa.Keepa(KEEPA_API_KEY)
        print("✅ Conexión exitosa a Keepa")
        return api
    except Exception as e:
        print(f"❌ Error conectando a Keepa: {e}")
        return None

def count_tokens(api):
    response_status = api.update_status()
    print('Tokens Left:', response_status['tokensLeft'])
    print('Refill In:', response_status['refillIn'])
    print('Refill Rate:', response_status['refillRate'])
    if response_status['tokensLeft'] == 0:
        print('❌ No hay tokens disponibles')
        return False
    else:
        print('✅ Tokens disponibles')
        return True

def get_deals_by_category(api, category_id):
    """
    Consulta ofertas en Keepa usando:
      - domainId 11: Amazon México
      - includeCategories: la lista de categorías a filtrar
      - dateRange 0: ofertas dentro de las últimas 12 horas (ofertas recientes)
    """
    try:
        deal_params = {
            "page": 0,
            "domainId": 11,  
            "includeCategories": category_id,
            "dateRange": 0,
            # Si deseas también aPlus aquí, Keepa no siempre lo soporta en deals,
            # pero si lo hiciera, podrías añadir: "aPlus": 1
        }
        deals_response = api.deals(deal_params)
        print("\n🔍 Respuesta cruda de Keepa:")
        print(json.dumps(deals_response, indent=4, default=str))
        
        if isinstance(deals_response, dict):
            if deals_response.get('dr'):
                print(f"✅ Ofertas encontradas para la categoría {category_id}")
                return deals_response
            else:
                print(f"❌ No se encontraron ofertas para la categoría {category_id}")
                return None
        elif isinstance(deals_response, list):
            if len(deals_response) > 0:
                print(f"✅ Ofertas encontradas para la categoría {category_id} (respuesta es lista)")
                return deals_response
            else:
                print(f"❌ La lista de ofertas para la categoría {category_id} está vacía.")
                return None
        else:
            print("❌ La respuesta de Keepa tiene un formato inesperado.")
            return None

    except Exception as e:
        print(f"❌ Error obteniendo ofertas para la categoría {category_id}: {e}")
        return None

def process_deals(deals_response):
    """
    Procesa la respuesta de Keepa y devuelve una lista de diccionarios con:
      - Title
      - Precio Original (MXN)
      - Precio con Descuento (MXN)
      - Descuento (monto en MXN)
      - Categoría (IDs concatenados)
      - Link (URL de Amazon)
      - Image (URL de la imagen; se intenta extraer desde aPlus según doc, luego imagesCSV, luego ASIN)
    """
    processed = []
    if isinstance(deals_response, dict):
        deals_list = deals_response.get('dr', [])
    elif isinstance(deals_response, list):
        deals_list = deals_response
    else:
        print("❌ Formato de respuesta inesperado.")
        return processed

    for deal in deals_list:
        title = deal.get('title', 'N/A')

        # 1) Construir link a Amazon
        asin = deal.get('asin', None)
        if asin:
            link = f"https://www.amazon.com.mx/dp/{asin}"
        else:
            link = "No ASIN disponible"

        # 2) Intentar extraer la imagen desde aPlus
        image_url = None
        a_plus = deal.get("aPlus", [])
        if a_plus and isinstance(a_plus, list):
            # Según doc: "aPlus": [{ "module": { "title": "...", "text": "...", "image": ... } }]
            for module in a_plus:
                module_data = module.get("module", {})
                if "image" in module_data:
                    # Puede ser string o array de strings
                    image_field = module_data["image"]
                    if isinstance(image_field, str):
                        # Caso: "image" es un string con la URL
                        image_url = image_field
                        break
                    elif isinstance(image_field, list) and len(image_field) > 0:
                        # Caso: "image" es un array de URLs, tomamos la primera
                        image_url = image_field[0]
                        break

        # 3) Fallback: usar imagesCSV
        if not image_url:
            images_csv = deal.get('imagesCSV', "")
            if images_csv:
                image_list = images_csv.split(',')
                if len(image_list) > 0 and image_list[0]:
                    # Depuración: imprimir el primer valor
                    print(f"DEBUG: image_list[0] = {image_list[0].strip()}")
                    image_url = f"https://images-na.ssl-images-amazon.com/images/I/{image_list[0].strip()}._SL1500_.jpg"

        # 4) Fallback final: construir la URL a partir del ASIN (no siempre funciona)
        if not image_url and asin:
            image_url = f"https://images-na.ssl-images-amazon.com/images/I/{asin}._SL1500_.jpg"

        # 5) Extraer precios
        current_arr = deal.get('current', [])
        if isinstance(current_arr, list) and len(current_arr) > 0:
            current_price_cents = current_arr[0]
        else:
            continue

        if current_price_cents is None or current_price_cents < 0:
            continue
        current_price = current_price_cents / 100.0

        # Usar el precio promedio (avg) como precio original
        avg_arr = deal.get('avg', [])
        if (isinstance(avg_arr, list) and len(avg_arr) > 0 and 
            isinstance(avg_arr[0], list) and len(avg_arr[0]) > 0):
            original_price_cents = avg_arr[0][0]
        else:
            original_price_cents = current_price_cents
        original_price = original_price_cents / 100.0

        discount_amount = original_price - current_price

        # 6) Categorías
        categories = deal.get('categories', [])
        if isinstance(categories, list) and categories:
            category_str = ", ".join(str(cat) for cat in categories)
        else:
            category_str = "Desconocida"

        # 7) Crear el diccionario de la oferta
        processed.append({
            "Title": title,
            "Precio Original": original_price,
            "Precio con Descuento": current_price,
            "Descuento": discount_amount,
            "Categoría": category_str,
            "Link": link,
            "Image": image_url
        })
    return processed

# ---------------------------
# Bloque Principal
# ---------------------------
if __name__ == '__main__':
    api = keepa_init()
    if api and count_tokens(api):
        # Define la(s) categoría(s) de interés.
        category_id = [9482558011, 9482640011, 16333429011, 11076223011]
        
        # Opción A: Consulta directa a la API de Keepa
        deals_response = get_deals_by_category(api, category_id)
        
        # Opción B: Cargar la respuesta desde un archivo JSON (descomenta si deseas usarlo)
        # file_path = 'raw_response.json'
        # deals_response = load_json_file(file_path)
        
        if deals_response:
            deals_processed = process_deals(deals_response)
            # Limitar el resultado a solo 5 ofertas
            deals_processed = deals_processed[:5]
            print(f"\nSe procesaron {len(deals_processed)} ofertas")
            if deals_processed:
                print("\nListado de ofertas:")
                for d in deals_processed:
                    print(d)
                # Guardar el resultado en un archivo JSON
                raw_json_str = json.dumps(deals_processed, indent=2)
                with open("raw_response.json", "w", encoding="utf-8") as f:
                    f.write(raw_json_str)
                print("\n✅ Datos guardados en raw_response.json")
            else:
                print("No se pudieron procesar las ofertas.")
        else:
            print("No hay ofertas disponibles o la respuesta no es válida.")
    else:
        print('No se pueden obtener ofertas sin tokens disponibles')
