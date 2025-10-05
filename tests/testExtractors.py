"""
Tests unitarios para CoinGeckoClient
Ejecutar con: python -m pytest test_coingecko_client.py -v
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests
import time
import sys
import os

## Configuración path ##

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'extractors')))

# Importar las clases a testear
from fetchData import CoinGeckoClient, APIConfig, Token, CoinGeckoAPIError

class TestToken:
    """Tests para la clase Token"""
    
    def test_token_creation_valid(self):
        """Test: Crear token con datos válidos"""
        token = Token(coin="bitcoin", id="bitcoin")
        assert token.coin == "bitcoin"
        assert token.id == "bitcoin"
    
    def test_token_creation_empty_coin(self):
        """Test: Error al crear token con coin vacío"""
        with pytest.raises(ValueError, match="Coin e id son necesarios"):
            Token(coin="", id="bitcoin")
    
    def test_token_creation_empty_id(self):
        """Test: Error al crear token con id vacío"""
        with pytest.raises(ValueError, match="Coin e id son necesarios"):
            Token(coin="bitcoin", id="")


class TestAPIConfig:
    """Tests para la clase APIConfig"""
    
    def test_api_config_creation(self):
        """Test: Crear configuración válida"""
        config = APIConfig(
            fromDate="2024-01-01",
            toDate="2024-01-31"
        )
        assert config.fromDate == "2024-01-01"
        assert config.toDate == "2024-01-31"
        assert config.vs_currency == "usd"  # Default
        assert config.rate_limit_delay == 2.0  # Default
    
    def test_api_config_custom_values(self):
        """Test: Configuración con valores personalizados"""
        config = APIConfig(
            fromDate="2024-01-01",
            toDate="2024-01-31",
            vs_currency="eur",
            rate_limit_delay=1.0,
            max_retries=5
        )
        assert config.vs_currency == "eur"
        assert config.rate_limit_delay == 1.0
        assert config.max_retries == 5


class TestCoinGeckoClient:
    """Tests para la clase CoinGeckoClient"""
    
    @pytest.fixture
    def valid_config(self):
        """Configuración válida para tests"""
        return APIConfig(
            fromDate="2024-01-01",
            toDate="2024-01-31"
        )
    
    @pytest.fixture
    def mock_env_token(self):
        """Mock del token de API desde env"""
        with patch.dict('os.environ', {'coinGeckoToken': 'test_token_123'}):
            yield
    
    def test_client_creation_with_valid_config(self, valid_config, mock_env_token):
        """Test: Crear cliente con configuración válida"""
        client = CoinGeckoClient(valid_config)
        assert client.config == valid_config
        assert client.api_token == 'test_token_123'
        assert len(client.default_tokens) == 3
    
    def test_client_creation_without_token(self, valid_config):
        """Test: Error al crear cliente sin token"""
        with patch.dict('os.environ', {'coinGeckoToken': ''}, clear=True):
            with pytest.raises(ValueError, match="Es necesario una API Token"):
                CoinGeckoClient(valid_config)
    
    def test_client_creation_invalid_dates(self, mock_env_token):
        """Test: Error con fechas inválidas"""
        config = APIConfig(
            fromDate="2024-01-31",  # Fecha posterior
            toDate="2024-01-01"     # Fecha anterior
        )
        with pytest.raises(CoinGeckoAPIError, match="debe ser anterior"):
            CoinGeckoClient(config)


class TestDateValidation:
    """Tests para validación de fechas"""
    
    @pytest.fixture
    def mock_env_token(self):
        with patch.dict('os.environ', {'coinGeckoToken': 'test_token_123'}):
            yield
    
    def test_convert_iso_date(self, mock_env_token):
        """Test: Convertir fecha ISO a timestamp"""
        config = APIConfig(fromDate="2024-01-01", toDate="2024-01-02")
        client = CoinGeckoClient(config)
        
        timestamp = client._convert_to_unix_timestamp("2024-01-01")
        expected = int(datetime(2024, 1, 1).timestamp())
        assert timestamp == expected
    
    def test_convert_iso_datetime(self, mock_env_token):
        """Test: Convertir fecha-hora ISO a timestamp"""
        config = APIConfig(fromDate="2024-01-01", toDate="2024-01-02")
        client = CoinGeckoClient(config)
        
        timestamp = client._convert_to_unix_timestamp("2024-01-01T10:30:00")
        expected = int(datetime(2024, 1, 1, 10, 30, 0).timestamp())
        assert timestamp == expected
    
    def test_convert_unix_timestamp_string(self, mock_env_token):
        """Test: Convertir string de timestamp a int"""
        config = APIConfig(fromDate="2024-01-01", toDate="2024-01-02")
        client = CoinGeckoClient(config)
        
        timestamp = client._convert_to_unix_timestamp("1704067200")
        assert timestamp == 1704067200
    
    def test_convert_invalid_date(self, mock_env_token):
        """Test: Error con fecha inválida"""
        config = APIConfig(fromDate="2024-01-01", toDate="2024-01-02")
        client = CoinGeckoClient(config)
        
        with pytest.raises(CoinGeckoAPIError, match="Error convirtiendo fecha"):
            client._convert_to_unix_timestamp("fecha-invalida")
    
    def test_future_date_validation(self, mock_env_token):
        """Test: Error con fecha muy futura"""
        future_date = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
        config = APIConfig(fromDate="2024-01-01", toDate=future_date)
        
        with pytest.raises(CoinGeckoAPIError, match="no puede ser muy futuro"):
            CoinGeckoClient(config)
    
    def test_date_range_too_large(self, mock_env_token):
        """Test: Error con rango de fechas muy grande"""
        config = APIConfig(
            fromDate="2023-01-01",
            toDate="2024-12-31"  # Más de 365 días
        )
        
        with pytest.raises(CoinGeckoAPIError, match="no puede ser mayor a 365 días"):
            CoinGeckoClient(config)


class TestRateLimiting:
    """Tests para rate limiting"""
    
    @pytest.fixture
    def client(self):
        config = APIConfig(
            fromDate="2024-01-01",
            toDate="2024-01-02",
            rate_limit_delay=0.1  # Delay corto para tests
        )
        with patch.dict('os.environ', {'coinGeckoToken': 'test_token_123'}):
            return CoinGeckoClient(config)
    
    def test_rate_limiting_first_call(self, client):
        """Test: Primer call no tiene delay"""
        start_time = time.time()
        client._apply_rate_limit()
        elapsed = time.time() - start_time
        
        # Primer call debería ser casi instantáneo
        assert elapsed < 0.01
    
    def test_rate_limiting_subsequent_calls(self, client):
        """Test: Calls subsecuentes respetan delay"""
        # Primer call
        client._apply_rate_limit()
        
        # Segundo call inmediato debería tener delay
        start_time = time.time()
        client._apply_rate_limit()
        elapsed = time.time() - start_time
        
        # Debería haber esperado aproximadamente el delay configurado
        assert elapsed >= client.config.rate_limit_delay * 0.9  # Margen de error


class TestRetryLogic:
    """Tests para lógica de reintentos"""
    
    @pytest.fixture
    def client(self):
        config = APIConfig(
            fromDate="2024-01-01",
            toDate="2024-01-02",
            rate_limit_delay=0.01,  # Delay mínimo para tests
            max_retries=2,
            retry_backoff_factor=1.5
        )
        with patch.dict('os.environ', {'coinGeckoToken': 'test_token_123'}):
            return CoinGeckoClient(config)
    
    def test_should_retry_connection_error(self, client):
        """Test: ConnectionError debe reintentarse"""
        exception = requests.exceptions.ConnectionError("Connection failed")
        assert client._should_retry(exception, None) is True
    
    def test_should_retry_timeout(self, client):
        """Test: Timeout debe reintentarse"""
        exception = requests.exceptions.Timeout("Request timeout")
        assert client._should_retry(exception, None) is True
    
    def test_should_retry_server_error(self, client):
        """Test: Error 500 debe reintentarse"""
        mock_response = Mock()
        mock_response.status_code = 500
        exception = requests.exceptions.HTTPError("Server error")
        
        assert client._should_retry(exception, mock_response) is True
    
    def test_should_not_retry_client_error(self, client):
        """Test: Error 400 NO debe reintentarse"""
        mock_response = Mock()
        mock_response.status_code = 400
        exception = requests.exceptions.HTTPError("Bad request")
        
        assert client._should_retry(exception, mock_response) is False
    
    def test_should_retry_rate_limit(self, client):
        """Test: Rate limit (429) debe reintentarse"""
        mock_response = Mock()
        mock_response.status_code = 429
        exception = requests.exceptions.HTTPError("Rate limit exceeded")
        
        assert client._should_retry(exception, mock_response) is True


class TestDataProcessing:
    """Tests para procesamiento de datos"""
    
    @pytest.fixture
    def client(self):
        config = APIConfig(fromDate="2024-01-01", toDate="2024-01-02")
        with patch.dict('os.environ', {'coinGeckoToken': 'test_token_123'}):
            return CoinGeckoClient(config)
    
    @pytest.fixture
    def sample_token_data(self):
        """Datos de ejemplo de la API de CoinGecko"""
        return {
            "prices": [
                [1704067200000, 42000.0],  # 2024-01-01 00:00:00 UTC
                [1704153600000, 43000.0]   # 2024-01-02 00:00:00 UTC
            ],
            "market_caps": [
                [1704067200000, 820000000000.0],
                [1704153600000, 840000000000.0]
            ],
            "total_volumes": [
                [1704067200000, 15000000000.0],
                [1704153600000, 16000000000.0]
            ]
        }
    
    def test_process_token_data_structure(self, client, sample_token_data):
        """Test: Estructura correcta del DataFrame procesado"""
        df = client.process_token_data(sample_token_data, "bitcoin")
        
        # Verificar columnas
        expected_columns = ['coin', 'timestamp', 'date', 'price', 'market_cap', 'volume']
        assert all(col in df.columns for col in expected_columns)
        
        # Verificar número de filas
        assert len(df) == 2
        
        # Verificar valores
        assert df.iloc[0]['coin'] == 'bitcoin'
        assert df.iloc[0]['price'] == 42000.0
        assert df.iloc[0]['market_cap'] == 820000000000.0
        assert df.iloc[0]['volume'] == 15000000000.0
    
    def test_process_token_data_date_format(self, client, sample_token_data):
        """Test: Formato correcto de fechas"""
        df = client.process_token_data(sample_token_data, "bitcoin")
        
        # Verificar formato de fecha
        assert df.iloc[0]['date'] == '2024-01-01'
        assert df.iloc[1]['date'] == '2024-01-02'
    
    def test_process_empty_data(self, client):
        """Test: Manejar datos vacíos"""
        empty_data = {"prices": [], "market_caps": [], "total_volumes": []}
        df = client.process_token_data(empty_data, "bitcoin")
        
        assert len(df) == 0
        assert isinstance(df, pd.DataFrame)


class TestTokenManagement:
    """Tests para gestión de tokens"""
    
    @pytest.fixture
    def client(self):
        config = APIConfig(fromDate="2024-01-01", toDate="2024-01-02")
        with patch.dict('os.environ', {'coinGeckoToken': 'test_token_123'}):
            return CoinGeckoClient(config)
    
    def test_get_available_tokens(self, client):
        """Test: Obtener tokens disponibles"""
        tokens = client.get_available_tokens()
        assert len(tokens) == 3
        assert any(token.coin == 'aave' for token in tokens)
    
    def test_add_token(self, client):
        """Test: Agregar nuevo token"""
        initial_count = len(client.default_tokens)
        client.add_token("ethereum", "ethereum")
        
        assert len(client.default_tokens) == initial_count + 1
        assert any(token.coin == 'ethereum' for token in client.default_tokens)
    
    def test_remove_existing_token(self, client):
        """Test: Remover token existente"""
        initial_count = len(client.default_tokens)
        result = client.remove_token("aave")
        
        assert result is True
        assert len(client.default_tokens) == initial_count - 1
        assert not any(token.coin == 'aave' for token in client.default_tokens)
    
    def test_remove_nonexistent_token(self, client):
        """Test: Intentar remover token inexistente"""
        initial_count = len(client.default_tokens)
        result = client.remove_token("nonexistent")
        
        assert result is False
        assert len(client.default_tokens) == initial_count


# Fixtures globales para tests de integración
@pytest.fixture
def mock_successful_api_response():
    """Mock de respuesta exitosa de la API"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "prices": [[1704067200000, 42000.0]],
        "market_caps": [[1704067200000, 820000000000.0]],
        "total_volumes": [[1704067200000, 15000000000.0]]
    }
    return mock_response


class TestIntegration:
    """Tests de integración (con mocks)"""
    
    @pytest.fixture
    def client(self):
        config = APIConfig(
            fromDate="2024-01-01",
            toDate="2024-01-02",
            rate_limit_delay=0.01  # Muy rápido para tests
        )
        with patch.dict('os.environ', {'coinGeckoToken': 'test_token_123'}):
            return CoinGeckoClient(config)
    
    @patch('requests.Session.get')
    def test_successful_data_extraction(self, mock_get, client, mock_successful_api_response):
        """Test: Extracción exitosa de datos completa"""
        # Mock ping y data requests
        mock_get.return_value = mock_successful_api_response
        
        # Ejecutar extracción
        df = client.data_extraction()
        
        # Verificar resultado
        assert not df.empty
        assert len(df) == 3  # 3 tokens por defecto
        assert 'coin' in df.columns
        assert 'price' in df.columns
        
        # Verificar que se hicieron las llamadas correctas
        assert mock_get.call_count == 4  # 1 ping + 3 tokens


if __name__ == "__main__":
    # Ejecutar tests
    import subprocess
    import sys
    
    try:
        subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], check=True)
    except subprocess.CalledProcessError:
        print("Algunos tests fallaron. Revisa los resultados arriba.")