import keepa

API_KEY = "4ns281h11l6th6dfg6ic193hrb0f1e65lqf64tg1b2d3bje237tnnjs1ln3veeof"

try:
    api = keepa.Keepa(API_KEY)
    print("✅ Conexión exitosa a Keepa")
except Exception as e:
    print(f"❌ Error conectando a Keepa: {e}")
