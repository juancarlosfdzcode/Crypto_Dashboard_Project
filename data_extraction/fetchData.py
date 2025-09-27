## Importación de librerías ##

import requests
import pandas as pd
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

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
    interval: str = ''
    timeout: int = 30


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
        
        self.headers = {
            'accept': 'application/json',
            'x-cg-api-key': self.api_token
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self.default_tokens = [
            Token(coin='aave', id='aave'),
            Token(coin='cronos', id='crypto-com-chain'),
            Token(coin='chainlink', id='chainlink')
        ]

    def ping(self) -> bool:

        """Verificar la conectividad con la API"""

        try:
            url = f'{self.config.base_url}/ping'
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            logger.info('Conexión establecida con la API de CoinGecko')

            return True
        
        except requests.RequestException as e:
            logger.error(f'Error conectando con la API: {e}')
            raise CoinGeckoAPIError(f'No se puede establecer conexión con el servidor: {e}')

    def get_token_market_data(self, token: Token) -> Dict:

        """Obtener datos de mercado para un token específico."""

        try:
            url = f'{self.config.base_url}/coins/{token.id}/market_chart/range'
            params = {
                'vs_currency': self.config.vs_currency,
                'interval': self.config.interval,
                'from': self.config.fromDate,
                'to': self.config.toDate
            }

            logger.info(f'Obteniendo información de: {token.coin} desde {self.config.fromDate} hasta {self.config.toDate}')
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            logger.info(f'Información obtenida correctamente para {token.coin}')

            return response.json()

        except requests.RequestException as e:
            logger.error(f'Error fetching token data for {token.coin}. Status code: {response.status_code if "response" in locals() else "N/A"}')            
            if 'response' in locals():
                logger.error(f'Respuesta: {response.text}')

            raise CoinGeckoAPIError(f'Error obteniendo datos para {token.coin}: {e}')
        
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
                logger.warning(f'Error en data_extraction: {e}')
                
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