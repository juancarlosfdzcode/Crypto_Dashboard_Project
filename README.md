# 📊 Crypto Dashboard Project


El objetivo de este proyecto es construir un pipeline robusto y listo para producción que permita la extracción, almacenamiento y análisis de datos históricos de criptomonedas desde la API de CoinGecko. Con una arquitectura dockerizada y DuckDB como base de datos analítica.

## 🎯 Características.

### Pipeline Principal.

* Extracción de datos históricos desde CoinGecko API.
* Rate Limiting Proactivo: Respeta automáticamente los límites de la API.
* Retry Logic con Backoff Exponencial: Reintentos inteligentes ante fallos transitorios.
* Almacenamiento en DuckDB: Base de datos analítica embebida de alto rendimiento.
* Validación de Configuración: Validación exhaustiva de fechas y parámetros.
* Manejo Robusto de Errores: Clasificación inteligente entre errores recuperables y permanentes.
* Connection Pooling: Reutilización de conexiones HTTP para mejor rendimiento.
* Logging Detallado: Trazabilidad completa del proceso de extracción.

### Arquitectura.

🐋 Dockerizado: Contenedor optimizado con Python 3.11-slim
🐋 Docker Compose: Orquestación lista para multi-servicio
📦 Volúmenes Persistentes: Datos que sobreviven reinicios de contenedores
🔄 Pipeline Completo: Extracción → Transformación → Almacenamiento

Experimentos de Optimización

🔬 Parallel Extractions: Análisis comparativo de extracción secuencial vs paralela
🔬 Circuit Breaker Pattern: Implementación de protección contra fallos en cascada

Testing

✅ Suite Comprehensiva: 55+ tests unitarios e integración

29 tests del extractor
26 tests de DuckDB


✅ Cobertura >95%: Alta cobertura de código
✅ Tests de Integración: Validación con mocks de la API

📁 Estructura del Proyecto
Crypto_Dashboard_Project/
├── services/
│   └── extractor/              # Servicio de extracción dockerizado
│       ├── Dockerfile          # Imagen Docker optimizada
│       ├── .dockerignore       # Exclusiones para build
│       ├── requirements.txt    # Dependencias Python
│       └── src/
│           ├── extractors/
│           │   └── dataExtraction.py      # Cliente CoinGecko API
│           ├── storage/
│           │   └── duckDBManager.py       # Manager de DuckDB
│           └── cryptoPipeline.py          # Pipeline completo
├── tests/                      # Suite de tests
│   ├── testExtractors.py      # Tests del extractor (29 tests)
│   └── testDuckDB.py          # Tests de DuckDB (26 tests)
├── experiments/                # Pruebas de concepto
│   ├── circuit_breaker_poc.py
│   └── parallel_extraction_poc.py
├── data/                       # Base de datos (volumen Docker)
│   └── crypto_data.duckdb
├── docker-compose.yml          # Orquestación Docker
├── README-DOCKER.md           # Guía de uso Docker
├── .env                        # Variables de entorno
└── README.md                   # Este archivo
📋 Requisitos
Para uso con Docker (Recomendado)

Docker 20.10+
Docker Compose V2
Token de API de CoinGecko (obtener aquí)

Para uso local

Python 3.11+
Token de API de CoinGecko

🚀 Quick Start
Opción 1: Docker (Recomendado)
bash# 1. Clonar repositorio
git clone https://github.com/tu-usuario/crypto-dashboard-project.git
cd Crypto_Dashboard_Project

# 2. Configurar token
echo "coinGeckoToken=TU_TOKEN_AQUI" > .env

# 3. Ejecutar con Docker Compose
docker compose run --rm extractor
Ver README-DOCKER.md para documentación completa de Docker.
Opción 2: Instalación Local
bash# 1. Clonar repositorio
git clone https://github.com/tu-usuario/crypto-dashboard-project.git
cd Crypto_Dashboard_Project

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar token
echo "coinGeckoToken=TU_TOKEN_AQUI" > .env

# 5. Ejecutar pipeline
python cryptoPipeline.py
💻 Uso
Pipeline Completo
pythonfrom cryptoPipeline import CryptoPipeline
from src.extractors.dataExtraction import Token

# Definir tokens
tokens = [
    Token(coin='btc', id='bitcoin'),
    Token(coin='eth', id='ethereum'),
    Token(coin='sol', id='solana')
]

# Ejecutar pipeline
with CryptoPipeline() as pipeline:
    pipeline.extract_and_store(tokens, "2025-01-01", "2025-03-31")
    pipeline.get_stats()
Consultar Datos Almacenados
pythonfrom src.storage.duckDBManager import DuckDBManager

# Conectar a la base de datos
with DuckDBManager() as db:
    # Obtener datos de Bitcoin
    btc_data = db.get_market_data('bitcoin', 
                                   start_date='2025-01-01',
                                   end_date='2025-03-31')
    
    # Ver estadísticas
    stats = db.get_extraction_stats()
    print(stats)
Visualizar Datos
bash# Script de visualización
python view_database.py

# Con DuckDB CLI
duckdb data/crypto_data.duckdb
🧪 Tests
Ejecutar Todos los Tests
bash# Suite completa
pytest tests/ -v

# Con cobertura
pytest tests/ -v --cov=src --cov-report=html
Tests Específicos
bash# Solo tests del extractor
pytest tests/testExtractors.py -v

# Solo tests de DuckDB
pytest tests/testDuckDB.py -v

# Test específico
pytest tests/testExtractors.py::TestDateValidation::test_valid_date_range -v
Resultados actuales:

✅ 29/29 tests del extractor
✅ 26/26 tests de DuckDB
✅ Cobertura >95%

🔬 Experimentos
Parallel Extractions
Análisis comparativo entre extracción secuencial y paralela:
bashpython experiments/parallel_extraction_poc.py
Conclusión: Con rate limiting, la paralelización no mejora el rendimiento.
Circuit Breaker
Implementación del patrón para protección contra fallos:
bashpython experiments/circuit_breaker_poc.py
Estados: CLOSED → OPEN → HALF_OPEN
📊 Estructura de Datos
Tabla: market_data
sqlCREATE TABLE market_data (
    coin_id VARCHAR,
    coin_symbol VARCHAR,
    timestamp BIGINT,
    date DATE,
    price DOUBLE,
    market_cap DOUBLE,
    total_volume DOUBLE,
    extraction_timestamp TIMESTAMP,
    PRIMARY KEY (coin_id, timestamp)
)
Tabla: extraction_log
sqlCREATE TABLE extraction_log (
    id INTEGER PRIMARY KEY,
    coin_id VARCHAR,
    from_date DATE,
    to_date DATE,
    records_inserted INTEGER,
    execution_time_seconds DOUBLE,
    status VARCHAR,
    error_message VARCHAR,
    timestamp TIMESTAMP
)
🏗️ Arquitectura
Fase 1: Extractor + Storage (✅ Completado)

✅ Extracción de datos de CoinGecko
✅ Almacenamiento en DuckDB
✅ Dockerización completa
✅ Tests comprehensivos
✅ Docker Compose configurado

Fase 2: API + Scheduler (🔜 Próximo)

🔜 API REST con FastAPI
🔜 Scheduler para extracciones automáticas
🔜 Multi-servicio con Docker Compose

Fase 3: Dashboard (📋 Planificado)

📋 Visualización con Streamlit
📋 Gráficos interactivos
📋 KPIs y métricas en tiempo real

🛠️ Tecnologías

Python 3.11: Lenguaje principal
DuckDB 0.9.2: Base de datos analítica embebida
Docker: Containerización
Docker Compose: Orquestación de servicios
Requests: Cliente HTTP con rate limiting
Pandas: Procesamiento de datos
Pytest: Testing framework

⚙️ Configuración Avanzada
Rate Limiting Personalizado
pythonconfig = APIConfig(
    fromDate='2024-01-01',
    toDate='2024-12-31',
    rate_limit_delay=3.0  # 3 segundos entre requests
)
Retry Logic Personalizado
pythonconfig = APIConfig(
    fromDate='2024-01-01',
    toDate='2024-12-31',
    max_retries=5,              # 5 reintentos
    retry_backoff_factor=1.5    # Factor backoff
)
Modificar Tokens Extraídos
Edita services/extractor/src/cryptoPipeline.py:
pythontokens = [
    Token(coin='btc', id='bitcoin'),
    Token(coin='eth', id='ethereum'),
    Token(coin='ada', id='cardano'),
    # Añade más aquí
]
🚨 Manejo de Errores
Errores Recuperables (se reintenta)

ConnectionError: Problemas de red
Timeout: Request timeout
429: Rate limit exceeded
500-504: Errores de servidor

Errores Permanentes (no se reintenta)

400: Bad request
401: Unauthorized
404: Not found

📈 Datos Extraídos
Criptomonedas Actuales

AAVE (aave)
Cronos (crypto-com-chain)
Chainlink (chainlink)

Métricas por Token

Precio (USD)
Market Cap
Volumen de trading 24h
Timestamps y fechas

Ejemplo de Datos
🪙 Monedas en base de datos: 3
  • aave: 2,133 registros (2025-01-01 → 2025-03-30)
  • chainlink: 2,132 registros (2025-01-01 → 2025-03-30)
  • crypto-com-chain: 2,133 registros (2025-01-01 → 2025-03-30)
🐋 Docker
Comandos Útiles
bash# Ejecutar extractor
docker compose run --rm extractor

# Ver logs
docker compose logs -f extractor

# Rebuild imagen
docker compose build extractor

# Limpiar
docker compose down
docker system prune -f
Ver README-DOCKER.md para documentación completa.
🤝 Contribuir

Fork el proyecto
Crea una rama (git checkout -b feature/AmazingFeature)
Commit cambios (git commit -m 'Add AmazingFeature')
Push a la rama (git push origin feature/AmazingFeature)
Abre un Pull Request

📝 Licencia
Este proyecto está bajo la Licencia MIT. Ver archivo LICENSE para más detalles.
👤 Autor
Juan Carlos

GitHub: https://github.com/juancarlosfdzcode
LinkedIn: https://www.linkedin.com/in/juan-carlos-fdz/
Medium: https://medium.com/@juancarlosfdzgarcode

🙏 Agradecimientos

CoinGecko por proporcionar la API gratuita
DuckDB por la excelente base de datos analítica
Comunidad de Python por las excelentes librerías

📚 Recursos Adicionales

Documentación de CoinGecko API
Documentación de DuckDB
Docker Best Practices


⭐ Si este proyecto te resultó útil, considera darle una estrella en GitHub
