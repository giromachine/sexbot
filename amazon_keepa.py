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
            "priceTypes": [0], # 0: Precio de AMAZON
            "isFilterEnabled": True,
            "singleVariation": True,
            "deltaPercentRange": [20, 95], # Rango de descuento
            "sortType":2, # 2: Ordenar por descuento
            "isRangeEnabled": True,
            "currentRange": [15000, 3000000]
        }
        deals_response = api.deals(deal_params)
        # print("\n🔍 Respuesta cruda de Keepa:")
        # print(json.dumps(deals_response, indent=4, default=str))
        
        if isinstance(deals_response, dict):
            if deals_response.get('dr'):
                # print(f"✅ Ofertas encontradas para la categoría {category_id}")
                return deals_response
            else:
                print(f"❌ No se encontraron ofertas para la categoría {category_id}")
                return None
        elif isinstance(deals_response, list):
            if len(deals_response) > 0:
                # print(f"✅ Ofertas encontradas para la categoría {category_id} (respuesta es lista)")
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



def get_image_url_from_integers(image_integers):
    """
    Converts an array of ASCII integer codes to a string to form the image name,
    then constructs the full Amazon image URL.
    
    Args:
        image_integers (list): List of integers representing ASCII character codes
        
    Returns:
        str: Complete Amazon image URL or None if input is empty
    """
    if not image_integers:
        return None
        
    try:
        # Convert each integer to its corresponding ASCII character and join them
        image_name = ''.join(chr(code) for code in image_integers)
        # Construct the full Amazon image URL
        return f"https://m.media-amazon.com/images/I/{image_name}"
    except Exception as e:
        print(f"Error converting image integers to URL: {e}")
        return None
    
    
def process_deals(deals_response, discount_weight=0.4, savings_weight=0.4,three_month_weight = 0.2):
    """
    Procesa la respuesta de Keepa y devuelve una lista de diccionarios con información detallada.
     Ordena los resultados usando un sistema de puntuación ponderada entre descuento, ahorro y bonus de 3 meses.
    
    Args:
        deals_response: La respuesta de la API de Keepa
        discount_weight: Peso para el porcentaje de descuento (0-1)
        savings_weight: Peso para el ahorro absoluto (0-1)
        three_month_weight: Peso para el bonus del precio promedio en 3 meses (0-1)
    """
    processed = []
    total_deals = 0
    skipped_deals = 0
    
    if isinstance(deals_response, dict):
        deals_list = deals_response.get('dr', [])
        if deals_list and len(deals_list) > 0:
            print(f"✅ Encontrados {len(deals_list)} deals en respuesta")
    elif isinstance(deals_response, list):
        deals_list = deals_response
        print(f"✅ Encontrados {len(deals_list)} deals en lista")
    else:
        print("❌ Formato de respuesta inesperado.")
        return processed

    for i, deal in enumerate(deals_list):
        total_deals += 1
        try:
            title = deal.get('title', 'N/A')
            print(f"\nProcesando deal #{i+1}:...")

            # 1) Construir link a Amazon
            asin = deal.get('asin', None)
            if asin:
                link = f"https://www.amazon.com.mx/dp/{asin}"
            else:
                link = "No ASIN disponible"
                print(f"⚠️ Deal sin ASIN")

            # 2) Obtener la imagen usando el array de enteros ASCII
            image_integers = deal.get('image', [])
            if image_integers:
                image_url = get_image_url_from_integers(image_integers)
            else:
                image_url = "No se pudo armar el link"
                print(f"⚠️ No se pudo obtener la imagen")

            # 3) Extraer precios actuales (con descuento)
            current_arr = deal.get('current', [])
            if not isinstance(current_arr, list) or len(current_arr) == 0:
                print(f"❌ No hay array de precios actuales: {current_arr}")
                skipped_deals += 1
                continue
                
            # Precio actual con descuento (Amazon price, index 0)
            current_price_cents = current_arr[0]
            if current_price_cents is None or current_price_cents < 0:
                print(f"❌ Precio actual inválido: {current_price_cents}")
                skipped_deals += 1
                continue
                
            current_price = current_price_cents / 100.0
            print(f"✅ Precio actual: {current_price}")
            
            # 4) Determinando precio original
            original_price = None
            price_source = "unknown"
            
            # Método 1: Intentar usar deltaLast para calcular el precio anterior
            delta_last = deal.get('deltaLast', [])
            if isinstance(delta_last, list) and len(delta_last) > 0 and delta_last[0] is not None and delta_last[0] != 0:
                # El precio original es el precio actual menos la diferencia (delta suele ser negativo en caso de descuento)
                original_price_cents = current_price_cents - delta_last[0]
                original_price = original_price_cents / 100.0
                price_source = "deltaLast"
                print(f"✅ Precio original (desde deltaLast): {original_price}, delta: {delta_last[0]/100.0}")
                
            # Método 2: Intentar usar los campos delta y deltaPercent para verificar si hay descuento
            if original_price is None or original_price <= current_price:
                delta = deal.get('delta', [])
                if isinstance(delta, list) and len(delta) > 0 and isinstance(delta[0], list) and len(delta[0]) > 0:
                    delta_value = delta[0][0]  # [dateRange=0:day][priceType=0:amazon]
                    if delta_value is not None and delta_value < 0:  # Negative delta means price decreased
                        # Calculate original price based on delta (current price - delta)
                        original_price_cents = current_price_cents - delta_value
                        original_price = original_price_cents / 100.0
                        price_source = "delta"
                        print(f"✅ Precio original (desde delta): {original_price}, delta: {delta_value/100.0}")
            
            # Método 3: Fallback a usar el precio promedio como respaldo
            if original_price is None or original_price <= current_price:
                avg_arr = deal.get('avg', [])
                if (isinstance(avg_arr, list) and len(avg_arr) > 0 and 
                    isinstance(avg_arr[0], list) and len(avg_arr[0]) > 0):
                    orig_price_cents = avg_arr[0][0]  # [dateRange=0:day][priceType=0:amazon]
                    if orig_price_cents is not None and orig_price_cents > 0:
                        original_price = orig_price_cents / 100.0
                        price_source = "avg"
                        print(f"✅ Precio original (desde avg): {original_price}")
            
            # Si todo falla, usamos un precio original ligeramente mayor
            if original_price is None or original_price <= current_price:
                # Para evitar filtrar todos los productos, asumimos un pequeño descuento
                original_price = current_price * 1.05  # 5% más que el precio actual
                price_source = "estimated"
                print(f"⚠️ Precio original estimado: {original_price}")
            
            # 5) Calcular ahorro y porcentaje de descuento
            ahorro = original_price - current_price
            
            # Verificar que tenemos un descuento real
            if ahorro <= 0:
                print(f"❌ No hay ahorro real: {ahorro}")
                skipped_deals += 1
                continue
                
            # Calcular porcentaje de descuento
            descuento_porcentaje = (ahorro / original_price) * 100
            print(f"✅ Ahorro: {ahorro}, Descuento: {descuento_porcentaje}%")

            # NUEVO: Comparar precio actual con el mínimo histórico de 3 meses
            data_obj = deal.get('data', {})
            price_history = data_obj.get('priceAmazon', [])
            bonus_value = 0
            if price_history:
                valid_prices = [p for p in price_history if p is not None and p >= 0]
                if valid_prices:
                    min_price = min(valid_prices) / 100.0
                    if current_price <= min_price:
                        bonus_value = 100  # Bonus completo si el precio es el más bajo en 3 meses
                        print("✅ Bonus 3m asignado: Full bonus (precio actual:", current_price, "<= min 3m:", min_price, ")")
                    else:
                        bonus_value = 0
                else:
                    bonus_value = 0
            else:
                bonus_value = 0
            # Guardar el bonus en el deal (campo temporal)
            deal["_three_month_bonus"] = bonus_value
            
            # 6) Categorías
            categories = deal.get('categories', [])
            if isinstance(categories, list) and categories:
                category_str = ", ".join(str(cat) for cat in categories)
            else:
                category_str = "Desconocida"

            # 7) Crear el diccionario de la oferta
            processed.append({
                "Title": title,
                "Precio Original": round(original_price, 2),
                "Precio con Descuento": round(current_price, 2),
                "Ahorro": round(ahorro, 2),
                "Descuento (%)": round(descuento_porcentaje, 1),
                "Three Month Bonus (%)": round(bonus_value, 1),
                "Price Source": price_source,  # Useful for debugging
                "Link": link,
                "Image": image_url,
                # Guardar valores sin redondear para calcular el score después
                "_ahorro_raw": ahorro,
                "_descuento_raw": descuento_porcentaje,
                "_three_month_bonus": bonus_value
            })
            print(f"✅ Deal #{i+1} procesado correctamente")
            
        except Exception as e:
            print(f"❌ Error procesando deal #{i+1}: {str(e)}")
            skipped_deals += 1
            continue
    
    print(f"\n📊 Resumen: {total_deals} deals totales, {skipped_deals} omitidos, {len(processed)} procesados")
    
    # Calcular Deal Score con ponderación entre descuento, ahorro y bonus de 3 meses
    if processed:
        max_ahorro = max(deal["_ahorro_raw"] for deal in processed)
        max_descuento = max(deal["_descuento_raw"] for deal in processed)
        max_bonus = max(deal.get("_three_month_bonus", 0) for deal in processed) if any(deal.get("_three_month_bonus", 0) > 0 for deal in processed) else 0

        three_month_weight = 0.2

        for deal in processed:
            normalized_savings = (deal["_ahorro_raw"] / max_ahorro) * 100 if max_ahorro > 0 else 0
            normalized_bonus = (deal["_three_month_bonus"] / max_bonus) * 100 if max_bonus > 0 else 0
            deal_score = (discount_weight * deal["_descuento_raw"]) + (savings_weight * normalized_savings) + (three_month_weight * normalized_bonus)
            deal["Deal Score"] = round(deal_score, 1)
        
        processed.sort(key=lambda x: x["Deal Score"], reverse=True)
        
        for deal in processed:
            if "_ahorro_raw" in deal:
                del deal["_ahorro_raw"]
            if "_descuento_raw" in deal:
                del deal["_descuento_raw"]
            if "_three_month_bonus" in deal:
                del deal["_three_month_bonus"]
        
        print("✅ Deals ordenados por Deal Score (ponderación: "
              f"{discount_weight*100}% descuento, {savings_weight*100}% ahorro, {three_month_weight*100}% bonus 3m)")
    
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
            print(f"\nSe procesaron {len(deals_processed)} ofertas")
            
            if deals_processed:
                # print("\nListado de ofertas:")
                # for d in deals_processed:
                #     # print(d)
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
