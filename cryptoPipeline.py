"""
Pipeline completo: Extracción de CoinGecko → Almacenamiento en DuckDB
"""
import time
from datetime import datetime
import logging
from typing import List
import pandas as pd

# Imports de tus módulos existentes
from src.extractors.dataExtraction import CoinGeckoClient, APIConfig, Token
from src.storage.duckDBManager import DuckDBManager

logger = logging.getLogger(__name__)


class CryptoPipeline:
    """Pipeline para extraer datos de CoinGecko y almacenarlos en DuckDB."""
    
    def __init__(self, db_path: str = "data/crypto_data.duckdb"):
        """
        Inicializar pipeline.
        
        Args:
            db_path: Ruta a la base de datos DuckDB
        """
        self.db = DuckDBManager(db_path)
        logger.info("✅ Pipeline inicializado")
    
    def _transform_coingecko_data(self, raw_data: dict) -> pd.DataFrame:
        """
        Transformar datos de formato CoinGecko a DataFrame normalizado.
        
        Entrada esperada:
        {
            'prices': [[timestamp, price], ...],
            'market_caps': [[timestamp, mcap], ...],
            'total_volumes': [[timestamp, volume], ...]
        }
        
        Salida:
        DataFrame con columnas: timestamp, date, price, market_cap, total_volume
        """
        import pandas as pd
        from datetime import datetime
        
        # Extraer timestamps y valores
        timestamps = [item[0] for item in raw_data.get('prices', [])]
        prices = [item[1] for item in raw_data.get('prices', [])]
        market_caps = [item[1] for item in raw_data.get('market_caps', [])]
        total_volumes = [item[1] for item in raw_data.get('total_volumes', [])]
        
        # Crear DataFrame
        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': prices,
            'market_cap': market_caps,
            'total_volume': total_volumes
        })
        
        # Convertir timestamp (milisegundos) a fecha
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        
        return df
    
    def extract_and_store(self, tokens: List[Token], from_date: str, to_date: str):
        """
        Extraer datos de múltiples tokens y almacenarlos en DuckDB.
        
        Args:
            tokens: Lista de tokens a extraer
            from_date: Fecha inicio (YYYY-MM-DD)
            to_date: Fecha fin (YYYY-MM-DD)
        """
        # Crear configuración para la API
        config = APIConfig(fromDate=from_date, toDate=to_date)
        client = CoinGeckoClient(config)
        
        total_start = time.time()
        total_records = 0
        successful = 0
        failed = 0
        
        logger.info(f"🚀 Iniciando extracción de {len(tokens)} tokens")
        logger.info(f"📅 Período: {from_date} → {to_date}")
        
        for i, token in enumerate(tokens, 1):
            logger.info(f"\n[{i}/{len(tokens)}] Procesando {token.coin} ({token.id})...")
            
            start_time = time.time()
            
            try:
                # Extraer datos de la API
                raw_data = client.get_token_market_data(token)
                execution_time = time.time() - start_time
                
                # Transformar datos de formato CoinGecko
                if isinstance(raw_data, dict) and 'prices' in raw_data:
                    data = self._transform_coingecko_data(raw_data)
                elif isinstance(raw_data, dict):
                    import pandas as pd
                    data = pd.DataFrame(raw_data)
                else:
                    data = raw_data
                
                if data.empty:
                    logger.warning(f"⚠️ No hay datos para {token.id}")
                    self.db.log_extraction(
                        coin_id=token.id,
                        from_date=from_date,
                        to_date=to_date,
                        records_inserted=0,
                        execution_time=execution_time,
                        status="NO_DATA",
                        error_message="No data returned from API"
                    )
                    continue
                
                # Almacenar en DuckDB
                records = self.db.insert_market_data(
                    coin_id=token.id,
                    coin_symbol=token.coin,
                    data=data
                )
                
                # Registrar extracción exitosa
                self.db.log_extraction(
                    coin_id=token.id,
                    from_date=from_date,
                    to_date=to_date,
                    records_inserted=records,
                    execution_time=execution_time,
                    status="SUCCESS"
                )
                
                total_records += records
                successful += 1
                logger.info(f"✅ {token.id}: {records} registros en {execution_time:.2f}s")
                
            except Exception as e:
                execution_time = time.time() - start_time
                failed += 1
                logger.error(f"❌ Error con {token.id}: {e}")
                
                # Registrar error
                self.db.log_extraction(
                    coin_id=token.id,
                    from_date=from_date,
                    to_date=to_date,
                    records_inserted=0,
                    execution_time=execution_time,
                    status="ERROR",
                    error_message=str(e)
                )
        
        total_time = time.time() - total_start
        
        # Resumen final
        logger.info("\n" + "="*60)
        logger.info("📊 RESUMEN DE EXTRACCIÓN")
        logger.info("="*60)
        logger.info(f"✅ Exitosas: {successful}/{len(tokens)}")
        logger.info(f"❌ Fallidas: {failed}/{len(tokens)}")
        logger.info(f"📝 Total registros: {total_records}")
        logger.info(f"⏱️ Tiempo total: {total_time:.2f}s")
        logger.info(f"⚡ Promedio por token: {total_time/len(tokens):.2f}s")
        logger.info("="*60)
    
    def update_token(self, token: Token, from_date: str, to_date: str):
        """
        Actualizar datos de un solo token.
        
        Args:
            token: Token a actualizar
            from_date: Fecha inicio
            to_date: Fecha fin
        """
        config = APIConfig(fromDate=from_date, toDate=to_date)
        client = CoinGeckoClient(config)
        
        start_time = time.time()
        
        try:
            raw_data = client.get_token_market_data(token)
            execution_time = time.time() - start_time
            
            # Transformar datos de formato CoinGecko
            if isinstance(raw_data, dict) and 'prices' in raw_data:
                data = self._transform_coingecko_data(raw_data)
            elif isinstance(raw_data, dict):
                import pandas as pd
                data = pd.DataFrame(raw_data)
            else:
                data = raw_data
            
            records = self.db.insert_market_data(
                coin_id=token.id,
                coin_symbol=token.coin,
                data=data
            )
            
            self.db.log_extraction(
                coin_id=token.id,
                from_date=from_date,
                to_date=to_date,
                records_inserted=records,
                execution_time=execution_time,
                status="SUCCESS"
            )
            
            logger.info(f"✅ Actualizado {token.id}: {records} registros")
            return records
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Error actualizando {token.id}: {e}")
            
            self.db.log_extraction(
                coin_id=token.id,
                from_date=from_date,
                to_date=to_date,
                records_inserted=0,
                execution_time=execution_time,
                status="ERROR",
                error_message=str(e)
            )
            raise
    
    def get_stats(self):
        """Mostrar estadísticas de la base de datos."""
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DE LA BASE DE DATOS")
        print("="*60)
        
        # Monedas disponibles
        coins = self.db.get_available_coins()
        print(f"\n🪙 Monedas en base de datos: {len(coins)}")
        for coin in coins:
            print(f"  • {coin['coin_id']}: {coin['total_records']} registros "
                  f"({coin['first_date']} → {coin['last_date']})")
        
        # Estadísticas de extracciones
        print("\n📈 Historial de extracciones:")
        stats = self.db.get_extraction_stats()
        print(stats.to_string(index=False))
        print("="*60 + "\n")
    
    def close(self):
        """Cerrar conexión a base de datos."""
        self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ==============================================================================
# EJEMPLO DE USO
# ==============================================================================

def main():
    """Ejemplo de uso del pipeline."""
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Definir tokens a extraer
    tokens = [
            Token(coin='aave', id='aave'),
            Token(coin='cronos', id='crypto-com-chain'),
            Token(coin='chainlink', id='chainlink')
    ]
    
    # Fechas de extracción
    from_date = "2025-01-01"
    to_date = "2025-03-31"
    
    # Ejecutar pipeline
    with CryptoPipeline() as pipeline:
        # Extraer y almacenar
        pipeline.extract_and_store(tokens, from_date, to_date)
        
        # Mostrar estadísticas
        pipeline.get_stats()
        
        # Ejemplo: consultar datos de Bitcoin
        print("\n📊 Datos de Bitcoin:")
        btc_data = pipeline.db.get_market_data('bitcoin', start_date='2024-01-01')
        print(btc_data.head())


if __name__ == "__main__":
    main()