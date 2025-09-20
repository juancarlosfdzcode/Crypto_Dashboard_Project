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
        if not self.coin or self.id:
            raise ValueError('Coin e id son necesarios.')

@dataclass
class APIConfig:

    """Configuración para la API de CoinGecko."""

    base_url: str = 'https://api.coingecko.com/api/v3'
    vs_currency: str = 'usd'
    interval: str = 'daily'
    fromDate: str
    toDate: str

class CoinGeckoAPIError(Exception):
    """Error personalizado para los errores de la API."""

    pass

class CoinGeckoClient:

    """Cliente para interactuar con la API de CoinGecko"""

