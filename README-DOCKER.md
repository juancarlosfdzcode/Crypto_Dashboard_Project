🐋 Docker - Crypto Dashboard Extractor
📦 Prerrequisitos

Docker 20.10+ instalado
Docker Compose V2 instalado
Token de API de CoinGecko

🚀 Quick Start
1. Configurar variables de entorno
Crea un archivo .env en la raíz del proyecto:
bashcoinGeckoToken=TU_TOKEN_AQUI
2. Ejecutar el extractor
bash# Desde la raíz del proyecto
docker compose run --rm extractor
Esto ejecutará el pipeline de extracción una vez y guardará los datos en ./data/crypto_data.duckdb.
📊 Comandos Disponibles
Ejecutar extractor
bash# Ejecutar una vez y salir
docker compose run --rm extractor
Ver logs en tiempo real
bashdocker compose logs -f extractor
Rebuild de la imagen (después de cambios en código)
bashdocker compose build extractor
Ejecutar sin docker-compose
bashdocker run --rm \
  -v $(pwd)/data:/app/data \
  -e coinGeckoToken=TU_TOKEN_AQUI \
  crypto-extractor
📁 Estructura de Volúmenes
Los datos persisten en:

./data/crypto_data.duckdb - Base de datos DuckDB

🔧 Configuración
Tokens configurados en el ejemplo
El pipeline está configurado para extraer:

AAVE (aave)
Cronos (crypto-com-chain)
Chainlink (chainlink)

Modificar tokens
Edita services/extractor/src/cryptoPipeline.py:
pythontokens = [
    Token(coin='btc', id='bitcoin'),
    Token(coin='eth', id='ethereum'),
    # Añade más aquí
]
Modificar fechas
Edita las variables en el archivo cryptoPipeline.py:
pythonfrom_date = "2025-01-01"
to_date = "2025-03-31"
🐛 Troubleshooting
Error: "coinGeckoToken not configured"
Asegúrate de que el archivo .env existe y tiene el formato correcto:
bash# Verificar .env
cat .env

# Debe mostrar (sin espacios, sin comillas):
coinGeckoToken=CG-xxxxx
Error: Permisos de Docker
Si ves errores de permisos:
bash# Añadir usuario al grupo docker
sudo usermod -aG docker $USER

# Aplicar cambios
newgrp docker
Rebuild completo
bash# Limpiar todo
docker compose down
docker system prune -f

# Rebuild desde cero
docker compose build --no-cache extractor
Ver base de datos
bash# Desde el host (si tienes Python)
python view_database.py

# O con DuckDB CLI
duckdb data/crypto_data.duckdb
📈 Próximos Pasos

Fase 2: API REST para consultar datos
Fase 2: Scheduler para extracciones automáticas
Fase 3: Dashboard con Streamlit

🔍 Verificar Instalación
bash# Verificar Docker
docker --version
# Debe mostrar: Docker version 20.10+ o superior

# Verificar Docker Compose
docker compose version
# Debe mostrar: Docker Compose version v2.x.x
💡 Notas

El contenedor usa Python 3.11-slim para tamaño reducido
Los datos persisten en volúmenes, no dentro del contenedor
El archivo .dockerignore optimiza los builds