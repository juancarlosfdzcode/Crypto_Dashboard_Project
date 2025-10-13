# Crypto Data Pipeline

Un pipeline robusto y listo para producción para la extracción de datos históricos de criptomonedas desde la API de CoinGecko. Diseñado con patrones de resiliencia, rate limiting inteligente y reintentos automáticos.

## 🎯 Características

### Pipeline Principal
- ✅ **Rate Limiting Proactivo**: Respeta automáticamente los límites de la API
- ✅ **Retry Logic con Backoff Exponencial**: Reintentos inteligentes ante fallos transitorios
- ✅ **Validación de Configuración**: Validación exhaustiva de fechas y parámetros
- ✅ **Manejo Robusto de Errores**: Clasificación inteligente entre errores recuperables y permanentes
- ✅ **Connection Pooling**: Reutilización de conexiones HTTP para mejor rendimiento
- ✅ **Logging Detallado**: Trazabilidad completa del proceso de extracción

### Experimentos de Optimización
- 🔬 **Parallel Extractions**: Análisis comparativo de extracción secuencial vs paralela
- 🔬 **Circuit Breaker Pattern**: Implementación de protección contra fallos en cascada

### Testing
- ✅ **Suite Comprehensiva**: 28/29 tests unitarios pasando
- ✅ **Cobertura ~97%**: Alta cobertura de código
- ✅ **Tests de Integración**: Validación con mocks de la API

## 📋 Requisitos

- Python 3.10+
- API Key de CoinGecko ([obtener aquí](https://www.coingecko.com/en/api/pricing))

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/crypto-data-pipeline.git
cd crypto-data-pipeline
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar API Key
Crear un archivo `.env` en la raíz del proyecto:
```bash
coinGeckoToken=tu_api_key_aqui
```

## 💻 Uso Básico

### Extracción Simple
```python
from src.extractors.dataExtraction import CoinGeckoClient, APIConfig

# Configurar parámetros
config = APIConfig(
    fromDate='2024-01-01',
    toDate='2024-12-31'
)

# Crear cliente
client = CoinGeckoClient(config)

# Extraer datos (tokens por defecto: AAVE, Cronos, Chainlink)
df = client.data_extraction()

print(f"Datos extraídos: {len(df)} registros")
print(df.head())
```

### Extracción con Tokens Personalizados
```python
from src.extractors.dataExtraction import Token

# Definir tokens personalizados
tokens = [
    Token(coin='bitcoin', id='bitcoin'),
    Token(coin='ethereum', id='ethereum'),
    Token(coin='cardano', id='cardano')
]

# Extraer datos
df = client.data_extraction(tokens=tokens)
```

### Gestión Dinámica de Tokens
```python
# Añadir token
client.add_token('solana', 'solana')

# Listar tokens disponibles
tokens = client.get_available_tokens()

# Remover token
client.remove_token('cronos')
```

## 🏗️ Arquitectura

### Estructura del Proyecto
```
crypto-data-pipeline/
├── src/
│   └── extractors/
│       └── dataExtraction.py      # Pipeline principal
├── experiments/
│   ├── parallel_extraction_poc.py # Análisis de paralelización
│   └── circuit_breaker_poc.py     # Implementación Circuit Breaker
├── tests/
│   └── testExtractors.py          # Suite de tests
├── .env                            # API credentials (no incluir en git)
├── requirements.txt                # Dependencias
└── README.md
```

### Componentes Principales

#### 1. Token
Representa un criptoactivo con validación automática:
```python
@dataclass
class Token:
    coin: str  # Nombre de la moneda
    id: str    # Identificador de CoinGecko
```

#### 2. APIConfig
Configuración centralizada del cliente:
```python
@dataclass
class APIConfig:
    fromDate: str                    # Fecha inicio (YYYY-MM-DD)
    toDate: str                      # Fecha fin (YYYY-MM-DD)
    rate_limit_delay: float = 2.0    # Delay entre requests (segundos)
    max_retries: int = 3             # Reintentos máximos
    retry_backoff_factor: float = 2.0  # Factor de backoff exponencial
```

#### 3. CoinGeckoClient
Cliente principal con funcionalidades completas:
- `ping()`: Verificación de conectividad
- `get_token_market_data()`: Extracción de datos de mercado
- `process_token_data()`: Transformación a DataFrame
- `data_extraction()`: Pipeline completo de extracción

## 🔬 Experimentos

### Parallel Extractions
Análisis comparativo entre extracción secuencial y paralela:

```bash
cd experiments
python parallel_extraction_poc.py
```

**Resultados:** Con rate limiting de 3 segundos y 3 tokens:
- Secuencial: 9 segundos
- Paralelo (2 workers): 12 segundos
- **Conclusión:** La paralelización NO mejora el rendimiento debido al rate limiting

### Circuit Breaker
Implementación del patrón para protección contra fallos:

```bash
cd experiments
python circuit_breaker_poc.py
```

**Estados:**
- `CLOSED`: Funcionamiento normal
- `OPEN`: Rechaza requests (servicio caído)
- `HALF_OPEN`: Probando recuperación

## 🧪 Tests

### Ejecutar Suite Completa
```bash
pytest tests/testExtractors.py -v
```

### Ejecutar Tests Específicos
```bash
# Solo tests de validación de fechas
pytest tests/testExtractors.py::TestDateValidation -v

# Solo tests de rate limiting
pytest tests/testExtractors.py::TestRateLimiting -v
```

### Cobertura de Código
```bash
pytest tests/testExtractors.py --cov=src.extractors --cov-report=html
```

## 📊 Estructura de Datos

### DataFrame Resultante
```python
| coin      | timestamp      | date       | price    | market_cap       | volume        |
|-----------|----------------|------------|----------|------------------|---------------|
| aave      | 1704067200000  | 2024-01-01 | 123.45   | 1234567890.00   | 12345678.90  |
| chainlink | 1704067200000  | 2024-01-01 | 15.67    | 9876543210.00   | 98765432.10  |
```

**Columnas:**
- `coin`: Nombre de la criptomoneda
- `timestamp`: Unix timestamp en milisegundos
- `date`: Fecha formateada (YYYY-MM-DD)
- `price`: Precio en USD
- `market_cap`: Capitalización de mercado
- `volume`: Volumen de trading en 24h

## ⚙️ Configuración Avanzada

### Rate Limiting Personalizado
```python
config = APIConfig(
    fromDate='2024-01-01',
    toDate='2024-12-31',
    rate_limit_delay=3.0  # 3 segundos entre requests
)
```

### Retry Logic Personalizado
```python
config = APIConfig(
    fromDate='2024-01-01',
    toDate='2024-12-31',
    max_retries=5,              # 5 reintentos
    retry_backoff_factor=1.5    # Factor más conservador
)
```

## 🚨 Manejo de Errores

El sistema clasifica automáticamente los errores:

### Errores Recuperables (se reintenta)
- `ConnectionError`: Problemas de red
- `Timeout`: Request timeout
- `429`: Rate limit exceeded
- `500-504`: Errores de servidor

### Errores Permanentes (no se reintenta)
- `400`: Bad request
- `401`: Unauthorized
- `404`: Not found

## 📈 Consideraciones de Performance

### Rate Limiting
- **Plan Gratuito**: ~30 requests/minuto → `rate_limit_delay=2.0`
- **Plan Pro**: ~500 requests/minuto → `rate_limit_delay=0.12`

### Validaciones de Fechas
- Rango máximo: 365 días
- Fecha mínima: 2009-01-01 (inicio de Bitcoin)
- Fechas futuras: rechazadas (solo datos históricos)

### Connection Pooling
El sistema usa `requests.Session()` que mantiene automáticamente un pool de conexiones, reduciendo la latencia de handshake TCP/TLS.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👤 Autor

**Juan Carlos Fernández**
- GitHub: [@tu-usuario](https://github.com/tu-usuario)
- LinkedIn: [Tu LinkedIn](https://linkedin.com/in/tu-perfil)
- Medium: [Tu Medium](https://medium.com/@tu-usuario)

## 🙏 Agradecimientos

- [CoinGecko](https://www.coingecko.com) por proporcionar la API
- Comunidad de Python por las excelentes librerías

## 📚 Recursos Adicionales

- [Documentación de CoinGecko API](https://docs.coingecko.com/reference/introduction)
- [Artículo en Medium](link-al-articulo) - Explicación detallada del desarrollo
- [Guía de Contribución](CONTRIBUTING.md)

---

⭐ Si este proyecto te resultó útil, considera darle una estrella en GitHub