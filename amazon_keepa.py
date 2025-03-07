import keepa
import json

KEEPA_API_KEY = '4ns281h11l6th6dfg6ic193hrb0f1e65lqf64tg1b2d3bje237tnnjs1ln3veeof'

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
    try:
        # Parámetros para obtener las ofertas:
        # - domainId 11: México
        # - includeCategories: filtra por la categoría que se pase
        # - dateRange 0: ofertas dentro de las últimas 12 horas (Keepa solo trae ofertas recientes)
        deal_params = {
            "page": 0,
            "domainId": 11,  
            "includeCategories": category_id,
            "dateRange": 0
        }
        deals_response = api.deals(deal_params)
        if deals_response and deals_response.get('dr'):
            print(f"✅ Ofertas encontradas para la categoría {category_id}")
            return deals_response
        else:
            print(f"❌ No se encontraron ofertas para la categoría {category_id}")
            return None
    except Exception as e:
        print(f"❌ Error obteniendo ofertas para la categoría {category_id}: {e}")
        return None

def process_deals(deals_response):
    """
    Processes the Keepa deals response and returns a list of dictionaries with:
      - ASIN
      - Title
      - Precio Original (in MXN)
      - Precio con Descuento (in MXN)
      - Descuento (monto)
      - Categoría (list of category IDs as a string)
    """
    processed = []
    deals_list = deals_response.get('dr', [])
    for deal in deals_list:
        # Product identification
        # asin = deal.get('asin', 'N/A')
        title = deal.get('title', 'N/A')
        
        # Extract current price from the "current" array (assume index 0)
        current_arr = deal.get('current', [])
        if isinstance(current_arr, list) and len(current_arr) > 0:
            current_price_cents = current_arr[0]
        else:
            continue  # Skip deal if no current price available

        # Skip if price indicates no available offer (-1)
        if current_price_cents is None or current_price_cents < 0:
            continue
        current_price = current_price_cents / 100.0

        # Use the weighted average (avg) as the original price.
        # "avg" is a two-dimensional array: first dimension is the date range,
        # second dimension is the price type. We take avg[0][0] for the day interval.
        avg_arr = deal.get('avg', [])
        if (isinstance(avg_arr, list) and len(avg_arr) > 0 and 
            isinstance(avg_arr[0], list) and len(avg_arr[0]) > 0):
            original_price_cents = avg_arr[0][0]
        else:
            original_price_cents = current_price_cents  # Fallback if not available
        original_price = original_price_cents / 100.0

        discount_amount = original_price - current_price

        # Process categories: join the list of category IDs as a comma-separated string.
        categories = deal.get('categories', [])
        if isinstance(categories, list) and categories:
            category_str = ", ".join(str(cat) for cat in categories)
        else:
            category_str = "Desconocida"
        
        processed.append({
            "Title": title,
            "Precio Original": original_price,
            "Precio con Descuento": current_price,
            "Descuento": discount_amount,
            "Categoría": category_str
        })
    return processed



def manipulate_json(deals_json):
    print(deals_response['dr'][0].keys())




if __name__ == '__main__':
    api = keepa_init()
    if api and count_tokens(api):
        category_id = [9482558011, 9482640011, 16333429011, 11076223011]  
        # deals_response = get_deals_by_category(api, category_id)
        with open('raw_response.json', 'r', encoding='utf-8') as f:
            deals_response = json.loads(f.read())
            
            # Verifica si la respuesta es un diccionario; si no, intenta convertirla a JSON válido
            if deals_response and not isinstance(deals_response, dict):
                print("La respuesta no es un diccionario. Se intentará convertir a JSON válido...")
                try:
                    # Convertir a cadena, reemplazar comillas simples por dobles y parsear
                    deals_response = json.loads(str(deals_response).replace("'", "\""))
                except json.JSONDecodeError as e:
                    print("❌ Error al parsear la respuesta a JSON:", e)
                    deals_response = None
            
            if deals_response:
                # # Guardamos la respuesta cruda en un archivo JSON
                deals_processed = process_deals(deals_response)
                raw_json_str = json.dumps(deals_processed, indent=2)
                with open("raw_response.json", "w", encoding="utf-8") as f:
                    f.write(raw_json_str)
                print(f"\nSe procesaron {len(deals_processed)} ofertas")
                if deals_processed:
                    print("\nListado de ofertas:")
                    for d in deals_processed:
                        print(d)
                else:
                    print("No se pudieron procesar las ofertas.")
            else:
                print("No hay ofertas disponibles o la respuesta no se pudo convertir a JSON.")
    else:
        print('No se pueden obtener ofertas sin tokens disponibles')
