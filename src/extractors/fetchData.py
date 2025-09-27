
## Importación de librerías ##
import requests
import pandas as pd
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
from datetime import datetime
import time

## Configuración del Logging ##
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

## Definición de clases ##
@dataclass
class Token:
    """Clase para representar un cryptoactivo."""
    coin: str
    id: str

    def __post_init__(self):
        if not self.coin or not self.id:
            raise ValueError('Coin e id son necesarios.')

@dataclass
class APIConfig:
    """Configuración para la API de CoinGecko."""
    fromDate: str
    toDate: str
    base_url: str = 'https://api.coingecko.com/api/v3'
    vs_currency: str = 'usd'
    timeout: int = 30
    rate_limit_delay: float = 2.0  # Segundos entre requests
    max_retries: int = 3  # Número máximo de reintentos
    retry_backoff_factor: float = 1.5  # Factor para backoff exponencial

class CoinGeckoAPIError(Exception):
    """Error personalizado para los errores de la API."""
    pass

class CoinGeckoClient:
    """Cliente para interactuar con la API de CoinGecko"""

    def __init__(self, config: APIConfig, api_token: Optional[str] = None):
        load_dotenv()
        self.api_token = os.getenv('coinGeckoToken')
        self.config = config

        if not self.api_token:
            raise ValueError('Es necesario una API Token.')
        
        # Validar configuración de fechas
        self._validate_date_config()
        
        self.headers = {
            'accept': 'application/json',
            'x-cg-api-key': self.api_token
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Rate limiting - CORREGIDO: Añadir atributo faltante
        self.last_request_time = 0.0

        self.default_tokens = [
            Token(coin='aave', id='aave'),
            Token(coin='cronos', id='crypto-com-chain'),
            Token(coin='chainlink', id='chainlink')
        ]

    def ping(self) -> bool:
        """Verificar la conectividad con la API"""
        try:
            url = f'{self.config.base_url}/ping'
            # CORREGIDO: Usar método con retry
            self._make_request_with_retry(url)
            logger.info('Conexión establecida con la API de CoinGecko')
            return True
        
        except CoinGeckoAPIError as e:
            logger.error(f'Error conectando con la API: {e}')
            raise CoinGeckoAPIError(f'No se puede establecer conexión con el servidor: {e}')

    def _make_request_with_retry(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        Realizar request con retry automático y backoff exponencial.
        
        Args:
            url: URL completa del endpoint
            params: Parámetros del request
            
        Returns:
            Dict: Respuesta JSON de la API
            
        Raises:
            CoinGeckoAPIError: Si falla después de todos los reintentos
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):  # +1 para incluir el intento inicial
            try:
                # Aplicar rate limiting antes de cada intento
                self._apply_rate_limit()
                
                # Hacer el request
                response = self.session.get(url, params=params, timeout=self.config.timeout)
                response.raise_for_status()
                
                # Si llegamos aquí, fue exitoso
                if attempt > 0:
                    logger.info(f'Request exitoso en intento {attempt + 1}')
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                
                # Determinar si debemos reintentar
                should_retry = self._should_retry(e, response if 'response' in locals() else None)
                
                if attempt < self.config.max_retries and should_retry:
                    # Calcular delay con backoff exponencial
                    delay = self.config.retry_backoff_factor ** attempt
                    
                    logger.warning(f'Request falló (intento {attempt + 1}/{self.config.max_retries + 1}): {e}')
                    logger.info(f'Reintentando en {delay:.1f} segundos...')
                    
                    time.sleep(delay)
                    continue
                else:
                    # No más reintentos o error no recuperable
                    if 'response' in locals():
                        logger.error(f'Request falló permanentemente. Status code: {response.status_code}')
                        logger.error(f'Response: {response.text}')
                    break
        
        # Si llegamos aquí, fallaron todos los intentos
        raise CoinGeckoAPIError(f'Request falló después de {self.config.max_retries + 1} intentos: {last_exception}')
    
    def _should_retry(self, exception: requests.exceptions.RequestException, response: Optional[requests.Response]) -> bool:
        """
        Determinar si un error es recuperable y debe reintentarse.
        
        Args:
            exception: La excepción que ocurrió
            response: La respuesta HTTP (si existe)
            
        Returns:
            bool: True si debe reintentarse, False si no
        """
        # Errores de red/conexión - siempre reintentar
        if isinstance(exception, (requests.exceptions.ConnectionError, 
                                 requests.exceptions.Timeout,
                                 requests.exceptions.ReadTimeout)):
            return True
        
        # Si no hay response, probablemente es error de red
        if response is None:
            return True
            
        # Errores HTTP específicos que son recuperables
        retriable_status_codes = {
            429,  # Rate limit exceeded
            500,  # Internal server error
            502,  # Bad gateway
            503,  # Service unavailable
            504   # Gateway timeout
        }
        
        if response.status_code in retriable_status_codes:
            return True
            
        # Errores 4xx (excepto 429) generalmente no son recuperables
        if 400 <= response.status_code < 500:
            return False
            
        # Otros errores 5xx son recuperables
        if response.status_code >= 500:
            return True
            
        return False

    def _apply_rate_limit(self) -> None:
        """
        Aplicar rate limiting entre requests para respetar los límites de la API.
        """
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.config.rate_limit_delay:
            sleep_time = self.config.rate_limit_delay - time_since_last_request
            logger.debug(f'Rate limiting: esperando {sleep_time:.2f} segundos')
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _validate_date_config(self) -> None:
        """
        Validar la configuración de fechas.
        
        Raises:
            CoinGeckoAPIError: Si las fechas no son válidas
        """
        try:
            # Validar que las fechas no estén vacías
            if not self.config.fromDate or not self.config.toDate:
                raise CoinGeckoAPIError('fromDate y toDate son obligatorios')
            
            # Convertir fechas para validación
            from_timestamp = self._convert_to_unix_timestamp(self.config.fromDate)
            to_timestamp = self._convert_to_unix_timestamp(self.config.toDate)
            
            # Validar que fromDate < toDate
            if from_timestamp >= to_timestamp:
                raise CoinGeckoAPIError(f'fromDate ({self.config.fromDate}) debe ser anterior a toDate ({self.config.toDate})')
            
            # Validar que no sean fechas muy futuras (permitir algunos días de margen)
            now_timestamp = int(datetime.now().timestamp())
            max_future_days = 2  # Margen de 2 días para diferencias de zona horaria
            max_timestamp = now_timestamp + (max_future_days * 24 * 60 * 60)
            
            if to_timestamp > max_timestamp:
                raise CoinGeckoAPIError(f'toDate ({self.config.toDate}) no puede ser muy futuro. CoinGecko solo tiene datos históricos.')
            
            # Validar que el rango no sea demasiado grande (máximo 365 días)
            max_days = 365
            max_range_seconds = max_days * 24 * 60 * 60
            if (to_timestamp - from_timestamp) > max_range_seconds:
                raise CoinGeckoAPIError(f'El rango de fechas no puede ser mayor a {max_days} días')
            
            # Validar que no sea muy antiguo (CoinGecko tiene datos desde ~2009)
            min_timestamp = int(datetime(2009, 1, 1).timestamp())
            if from_timestamp < min_timestamp:
                raise CoinGeckoAPIError(f'fromDate ({self.config.fromDate}) es demasiado antigua. CoinGecko tiene datos desde 2009.')
                
            logger.info(f'Validación de fechas exitosa: {self.config.fromDate} a {self.config.toDate}')
            
        except CoinGeckoAPIError:
            # Re-lanzar errores de validación
            raise
        except Exception as e:
            raise CoinGeckoAPIError(f'Error validando configuración de fechas: {e}')

    def _convert_to_unix_timestamp(self, date_str: str) -> int:
        """Convertir fecha ISO o timestamp Unix a timestamp Unix"""
        try:
            # Si ya es un timestamp Unix (string de números)
            if date_str.isdigit():
                return int(date_str)
            
            # CORREGIDO: Usar datetime.fromisoformat() en lugar de pd.to_datetime()
            if 'T' in date_str:
                # Formato: YYYY-MM-DDTHH:MM o YYYY-MM-DDTHH:MM:SS
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Formato: YYYY-MM-DD (añadir 00:00:00)
                dt = datetime.fromisoformat(date_str + 'T00:00:00')
            
            timestamp = int(dt.timestamp())
            logger.debug(f'Fecha {date_str} convertida a timestamp: {timestamp}')
            return timestamp
            
        except Exception as e:
            raise CoinGeckoAPIError(f'Error convirtiendo fecha {date_str} a timestamp Unix: {e}')

    def get_token_market_data(self, token: Token) -> Dict:
        """Obtener datos de mercado para un token específico."""
        try:
            # Convertir fechas a timestamps Unix
            from_timestamp = self._convert_to_unix_timestamp(self.config.fromDate)
            to_timestamp = self._convert_to_unix_timestamp(self.config.toDate)

            url = f'{self.config.base_url}/coins/{token.id}/market_chart/range'
            params = {
                'vs_currency': self.config.vs_currency,
                'from': from_timestamp,
                'to': to_timestamp
            }

            logger.info(f'Obteniendo información de: {token.coin} desde {self.config.fromDate} hasta {self.config.toDate}')
            logger.debug(f'Parámetros: from={from_timestamp}, to={to_timestamp}')
            
            # CORREGIDO: Usar método con retry en lugar de session.get() directo
            data = self._make_request_with_retry(url, params)
            logger.info(f'Información obtenida correctamente para {token.coin}')

            return data

        except CoinGeckoAPIError:
            # Re-lanzar errores de CoinGecko (ya contienen el contexto)
            raise
        except Exception as e:
            # Capturar otros errores inesperados
            raise CoinGeckoAPIError(f'Error inesperado obteniendo datos para {token.coin}: {e}')
        
    def process_token_data(self, token_data: Dict, coin: str) -> pd.DataFrame:
        """Procesar los datos del token y convertirlos a DataFrame"""
        try:
            prices = token_data.get('prices', [])
            market_caps = token_data.get('market_caps', [])
            volumes = token_data.get('total_volumes', [])

            data_list = []
            for i, price_data in enumerate(prices):
                row = {
                    'coin': coin,
                    'timestamp': price_data[0],
                    'date': pd.to_datetime(price_data[0], unit='ms').strftime('%Y-%m-%d'),
                    'price': price_data[1]
                }
            
                if i < len(market_caps):
                    row['market_cap'] = market_caps[i][1]
                
                if i < len(volumes):
                    row['volume'] = volumes[i][1]
                
                data_list.append(row)
            
            df = pd.DataFrame(data_list)
            logger.info(f'DataFrame creado para {coin} con {len(df)} registros')

            return df

        except Exception as e:
            logger.error(f'Error procesando datos para {coin}: {e}')
            raise CoinGeckoAPIError(f'Error procesando datos para {coin}: {e}')

    def data_extraction(self, tokens: Optional[List[Token]] = None) -> pd.DataFrame:
        """
        Extraer datos de múltiples tokens y combinarlos en un DataFrame final.

        Args:
            tokens: Lista de tokens a procesar. Si es None, utiliza los tokens por defecto.

        Returns:
            DataFrame combinado con datos de todos los tokens.
        """
        if tokens is None:
            tokens = self.default_tokens
        
        all_rows = []
        all_dataframes = []

        try:
            self.ping()

            for token in tokens:
                try:
                    token_data = self.get_token_market_data(token)
                    all_rows.append({'coin': token.coin, 'data': token_data})

                    df_token = self.process_token_data(token_data, token.coin)
                    all_dataframes.append(df_token)

                except CoinGeckoAPIError as e:
                    logger.warning(f'Saltando token {token.coin} debido a error: {e}')
                    continue

            if all_dataframes:
                final_df = pd.concat(all_dataframes, ignore_index=True)
                logger.info(f'DataFrame final creado con {len(final_df)} registros totales')
                return final_df
            
            else:
                logger.warning('No se obtuvieron datos de ningún token')                
                return pd.DataFrame()
    
        except Exception as e:
            logger.error(f'Error en data_extraction: {e}')
            raise CoinGeckoAPIError(f'No se ha podido ejecutar workflow: {e}')
        
    def get_available_tokens(self) -> List[Token]:
        """Retorna la lista de tokens disponibles"""
        return self.default_tokens
    
    def add_token(self, coin: str, token_id: str) -> None:
        """Agregar un nuevo token a la lista"""
        new_token = Token(coin=coin, id=token_id)
        self.default_tokens.append(new_token)
        logger.info(f'Token {coin} agregado a la lista')
    
    def remove_token(self, coin: str) -> bool:
        """Remover un token de la lista por nombre de coin"""
        for i, token in enumerate(self.default_tokens):
            if token.coin == coin:
                removed_token = self.default_tokens.pop(i)
                logger.info(f'Token {removed_token.coin} removido de la lista')
                return True
        logger.warning(f'Token {coin} no encontrado en la lista')
        return False

if __name__ == "__main__":
    # Configuración
    config = APIConfig(
        fromDate='2025-01-01',
        toDate='2025-01-31'
    )
    
    # Crear cliente
    try:
        client = CoinGeckoClient(config)
        
        # Extraer datos
        df_result = client.data_extraction()
        
        if not df_result.empty:
            print(f"Datos extraídos exitosamente. Total de registros: {len(df_result)}")
            print("\nPrimeras 5 filas:")
            print(df_result.head())
        else:
            print("No se obtuvieron datos")
            
    except Exception as e:
        logger.error(f"Error en la ejecución: {e}")