# test.py
from data_extraction.fetchData import CoinGeckoClient, APIConfig

# Crear configuración
config = APIConfig(
    fromDate='2024-01-01',
    toDate='2024-01-31'
)

# Crear cliente
client = CoinGeckoClient(config)

# Probar ping
try:
    if client.ping():
        print("✅ API funcionando")
    else:
        print("❌ API no funciona")
except Exception as e:
    print(f"❌ Error: {e}")