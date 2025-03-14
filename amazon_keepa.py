import keepa
import json
import numpy as np
import os

# ---------------------------
# CONFIGURACIÓN
# ---------------------------
KEEPA_API_KEY = '4ns281h11l6th6dfg6ic193hrb0f1e65lqf64tg1b2d3bje237tnnjs1ln3veeof'
PERSISTENCE_FILE = "current_page.txt"  # Archivo para guardar el número de página

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
# Función para controlar la paginación
# ---------------------------
def get_next_page():
    """
    Recupera el número de página actual desde un archivo persistente,
    lo incrementa (volviendo a 0 al llegar a 12) y lo actualiza.
    En un entorno serverless, se recomienda usar un almacenamiento externo.
    """
    # Si el archivo no existe, se inicia en 0
    if not os.path.exists(PERSISTENCE_FILE):
        current_page = 0
    else:
        try:
            with open(PERSISTENCE_FILE, "r") as f:
                current_page = int(f.read().strip())
        except Exception as e:
            print("❌ Error al leer el número de página:", e)
            current_page = 0

    next_page = current_page
    # Incrementar y reiniciar a 0 si es 11 (ya que 0-11 son 12 páginas)
    current_page = (current_page + 1) % 12
    try:
        with open(PERSISTENCE_FILE, "w") as f:
            f.write(str(current_page))
    except Exception as e:
        print("❌ Error al guardar el número de página:", e)
    print(f"Usando página: {next_page}")
    return next_page

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
      - page: se usa el número de página obtenido de get_next_page()
    """
    try:
        deal_params = {
            "page": get_next_page(),  # Se obtiene la página de forma dinámica
            "domainId": 11,  
            "includeCategories": category_id,
            "dateRange": 0,
            "priceTypes": [0],  # 0: Precio de AMAZON
            "isFilterEnabled": True,
            "singleVariation": True,
            "deltaPercentRange": [15, 95],  # Rango de descuento
            "sortType": 2,  # Ordenar por descuento
            "isRangeEnabled": True,
            "currentRange": [15000, 3000000],
            "salesRankRange": [500, -1]
        }
        deals_response = api.deals(deal_params)
        
        if isinstance(deals_response, dict):
            if deals_response.get('dr'):
                return deals_response
            else:
                print(f"❌ No se encontraron ofertas para la categoría {category_id}")
                return None
        elif isinstance(deals_response, list):
            if len(deals_response) > 0:
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
    Convierte un array de enteros (códigos ASCII) en una cadena para formar el nombre de la imagen,
    y construye la URL completa de la imagen de Amazon.
    """
    if not image_integers:
        return None
        
    try:
        image_name = ''.join(chr(code) for code in image_integers)
        return f"https://m.media-amazon.com/images/I/{image_name}"
    except Exception as e:
        print(f"Error al convertir enteros de imagen a URL: {e}")
        return None

def process_deals(deals_response, discount_weight=0.4, savings_weight=0.4):
    """
    Procesa la respuesta de Keepa y devuelve una lista de diccionarios con información detallada.
    Ordena los resultados usando un sistema de puntuación ponderada entre descuento y ahorro.
    
    Args:
        deals_response: La respuesta de la API de Keepa.
        discount_weight: Peso para el porcentaje de descuento (0-1).
        savings_weight: Peso para el ahorro absoluto (0-1).
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
                
            current_price_cents = current_arr[0]
            if current_price_cents is None or current_price_cents < 0:
                print(f"❌ Precio actual inválido: {current_price_cents}")
                skipped_deals += 1
                continue
                
            current_price = current_price_cents / 100.0
            print(f"✅ Precio actual: {current_price}")
            
            # 4) Determinar el precio original
            original_price = None
            price_source = "unknown"
            
            # Método 1: Usar deltaLast
            delta_last = deal.get('deltaLast', [])
            if isinstance(delta_last, list) and len(delta_last) > 0 and delta_last[0] is not None and delta_last[0] != 0:
                original_price_cents = current_price_cents - delta_last[0]
                original_price = original_price_cents / 100.0
                price_source = "deltaLast"
                print(f"✅ Precio original (desde deltaLast): {original_price}, delta: {delta_last[0]/100.0}")
                
            # Método 2: Usar delta
            if original_price is None or original_price <= current_price:
                delta = deal.get('delta', [])
                if isinstance(delta, list) and len(delta) > 0 and isinstance(delta[0], list) and len(delta[0]) > 0:
                    delta_value = delta[0][0]
                    if delta_value is not None and delta_value < 0:
                        original_price_cents = current_price_cents - delta_value
                        original_price = original_price_cents / 100.0
                        price_source = "delta"
                        print(f"✅ Precio original (desde delta): {original_price}, delta: {delta_value/100.0}")
            
            # Método 3: Usar avg como respaldo
            if original_price is None or original_price <= current_price:
                avg_arr = deal.get('avg', [])
                if (isinstance(avg_arr, list) and len(avg_arr) > 0 and 
                    isinstance(avg_arr[0], list) and len(avg_arr[0]) > 0):
                    orig_price_cents = avg_arr[0][0]
                    if orig_price_cents is not None and orig_price_cents > 0:
                        original_price = orig_price_cents / 100.0
                        price_source = "avg"
                        print(f"✅ Precio original (desde avg): {original_price}")
            
            # Fallback: estimar precio original
            if original_price is None or original_price <= current_price:
                original_price = current_price * 1.05  # 5% más que el precio actual
                price_source = "estimated"
                print(f"⚠️ Precio original estimado: {original_price}")
            
            # 5) Calcular ahorro y porcentaje de descuento
            ahorro = original_price - current_price
            if ahorro <= 0:
                print(f"❌ No hay ahorro real: {ahorro}")
                skipped_deals += 1
                continue
                
            descuento_porcentaje = (ahorro / original_price) * 100
            print(f"✅ Ahorro: {ahorro}, Descuento: {descuento_porcentaje}%")

            # Se elimina la referencia a bonus de 3 meses

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
                "Price Source": price_source,
                "Link": link,
                "Image": image_url,
                # Guardar valores sin redondear para el cálculo del Deal Score
                "_ahorro_raw": ahorro,
                "_descuento_raw": descuento_porcentaje
            })
            print(f"✅ Deal #{i+1} procesado correctamente")
            
        except Exception as e:
            print(f"❌ Error procesando deal #{i+1}: {str(e)}")
            skipped_deals += 1
            continue
    
    print(f"\n📊 Resumen: {total_deals} deals totales, {skipped_deals} omitidos, {len(processed)} procesados")
    
    # Calcular Deal Score ponderando descuento y ahorro
    if processed:
        max_ahorro = max(deal["_ahorro_raw"] for deal in processed)
        max_descuento = max(deal["_descuento_raw"] for deal in processed)
        for deal in processed:
            normalized_savings = (deal["_ahorro_raw"] / max_ahorro) * 100 if max_ahorro > 0 else 0
            deal_score = (discount_weight * deal["_descuento_raw"]) + (savings_weight * normalized_savings)
            deal["Deal Score"] = round(deal_score, 1)
        
        processed.sort(key=lambda x: x["Deal Score"], reverse=True)
        
        for deal in processed:
            if "_ahorro_raw" in deal:
                del deal["_ahorro_raw"]
            if "_descuento_raw" in deal:
                del deal["_descuento_raw"]
        
        print("✅ Deals ordenados por Deal Score (ponderación: "
              f"{discount_weight*100}% descuento, {savings_weight*100}% ahorro)")
    
    return processed

# ---------------------------
# Bloque Principal
# ---------------------------
if __name__ == '__main__':
    api = keepa_init()
    if api and count_tokens(api):
        # Define la(s) categoría(s) de interés.
        category_id = [9482558011, 9482640011, 9482690011, 16333429011, 482670011, 11260442011]
        # Opción A: Consulta directa a la API de Keepa
        deals_response = get_deals_by_category(api, category_id)
        
        # Opción B: Cargar la respuesta desde un archivo JSON (descomenta si deseas usarlo)
        # file_path = 'raw_response.json'
        # deals_response = load_json_file(file_path)
        
        if deals_response:
            deals_processed = process_deals(deals_response)
            deals_processed = deals_processed[:5]
            print(f"\nSe procesaron {len(deals_processed)} ofertas")
            
            if deals_processed:
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
