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
    interval: str = 'daily'
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