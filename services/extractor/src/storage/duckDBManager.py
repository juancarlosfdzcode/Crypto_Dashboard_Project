"""
DuckDB Manager - Capa de almacenamiento para datos de criptomonedas
"""
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DuckDBManager:
    """Gestor de base de datos DuckDB para datos de criptomonedas."""
    
    def __init__(self, db_path: str = "data/crypto_data.duckdb"):
        """
        Inicializar conexión a DuckDB.
        
        Args:
            db_path: Ruta al archivo de base de datos
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = duckdb.connect(str(self.db_path))
        logger.info(f"Conexión a DuckDB establecida: {self.db_path}")
        
        self._create_tables()
    
    def _create_tables(self):
        """Crear tablas si no existen."""
        
        # Tabla principal de datos de mercado
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                coin_id VARCHAR NOT NULL,
                coin_symbol VARCHAR NOT NULL,
                timestamp BIGINT NOT NULL,
                date DATE NOT NULL,
                price DOUBLE,
                market_cap DOUBLE,
                total_volume DOUBLE,
                extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (coin_id, timestamp)
            )
        """)
        
        # Tabla de metadatos de extracción
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS extraction_log_seq START 1
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS extraction_log (
                id INTEGER PRIMARY KEY DEFAULT nextval('extraction_log_seq'),
                coin_id VARCHAR NOT NULL,
                from_date DATE NOT NULL,
                to_date DATE NOT NULL,
                records_inserted INTEGER,
                execution_time_seconds DOUBLE,
                status VARCHAR,
                error_message VARCHAR,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crear índices para mejorar rendimiento
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_data_date 
            ON market_data(date)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_data_coin 
            ON market_data(coin_id)
        """)
        
        logger.info("Tablas creadas/verificadas correctamente")
    
    def insert_market_data(self, coin_id: str, coin_symbol: str, data: pd.DataFrame) -> int:
        """
        Insertar datos de mercado en DuckDB.
        
        Args:
            coin_id: ID del token (ej: 'bitcoin')
            coin_symbol: Símbolo del token (ej: 'btc')
            data: DataFrame con datos de mercado
        
        Returns:
            Número de registros insertados
        """
        if data.empty:
            logger.warning(f"DataFrame vacío para {coin_id}, no se insertaron datos")
            return 0
        
        # Preparar datos
        data_to_insert = data.copy()
        
        # Mapear columnas flexiblemente
        column_mapping = {
            'timestamp': ['timestamp', 'time', 'date_timestamp'],
            'date': ['date', 'datetime', 'day'],
            'price': ['price', 'prices', 'close', 'value'],
            'market_cap': ['market_cap', 'market_caps', 'marketcap', 'mcap'],
            'total_volume': ['total_volume', 'total_volumes', 'volume', 'volumes']  # ← 'volume' añadido
        }
        
        # Renombrar columnas según mapeo
        for target_col, possible_names in column_mapping.items():
            for possible_name in possible_names:
                if possible_name in data_to_insert.columns:
                    if possible_name != target_col:
                        data_to_insert = data_to_insert.rename(columns={possible_name: target_col})
                    break
        
        # Verificar que tenemos las columnas esenciales
        required_cols = ['timestamp', 'date', 'price', 'market_cap', 'total_volume']
        missing_cols = [col for col in required_cols if col not in data_to_insert.columns]
        
        if missing_cols:
            logger.error(f"❌ Faltan columnas requeridas: {missing_cols}")
            logger.error(f"Columnas disponibles: {data_to_insert.columns.tolist()}")
            raise ValueError(f"Faltan columnas: {missing_cols}. Disponibles: {data_to_insert.columns.tolist()}")
        
        # Añadir columnas de identificación
        data_to_insert['coin_id'] = coin_id
        data_to_insert['coin_symbol'] = coin_symbol.lower()
        
        # Reordenar columnas
        columns = ['coin_id', 'coin_symbol', 'timestamp', 'date', 
                   'price', 'market_cap', 'total_volume']
        data_to_insert = data_to_insert[columns]
        
        try:
            # Insertar usando UPSERT (actualizar si existe, insertar si no)
            self.conn.execute("""
                INSERT INTO market_data 
                    (coin_id, coin_symbol, timestamp, date, price, market_cap, total_volume)
                SELECT coin_id, coin_symbol, timestamp, date, price, market_cap, total_volume
                FROM data_to_insert
                ON CONFLICT (coin_id, timestamp) 
                DO UPDATE SET
                    price = EXCLUDED.price,
                    market_cap = EXCLUDED.market_cap,
                    total_volume = EXCLUDED.total_volume
            """)
            
            records_inserted = len(data_to_insert)
            logger.info(f"✅ Insertados/actualizados {records_inserted} registros para {coin_id}")
            return records_inserted
            
        except Exception as e:
            logger.error(f"❌ Error insertando datos para {coin_id}: {e}")
            raise
    
    def log_extraction(self, coin_id: str, from_date: str, to_date: str,
                      records_inserted: int, execution_time: float,
                      status: str = "SUCCESS", error_message: str = None):
        """
        Registrar metadatos de extracción.
        
        Args:
            coin_id: ID del token
            from_date: Fecha inicio (YYYY-MM-DD)
            to_date: Fecha fin (YYYY-MM-DD)
            records_inserted: Número de registros insertados
            execution_time: Tiempo de ejecución en segundos
            status: Estado de la extracción (SUCCESS/ERROR)
            error_message: Mensaje de error si aplica
        """
        self.conn.execute("""
            INSERT INTO extraction_log 
            (coin_id, from_date, to_date, records_inserted, 
             execution_time_seconds, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [coin_id, from_date, to_date, records_inserted, 
              execution_time, status, error_message])
        
        logger.info(f"📝 Log de extracción registrado para {coin_id}")
    
    def get_market_data(self, coin_id: str, 
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Consultar datos de mercado almacenados.
        
        Args:
            coin_id: ID del token
            start_date: Fecha inicio (YYYY-MM-DD), opcional
            end_date: Fecha fin (YYYY-MM-DD), opcional
        
        Returns:
            DataFrame con los datos
        """
        query = f"SELECT * FROM market_data WHERE coin_id = '{coin_id}'"
        
        if start_date:
            query += f" AND date >= '{start_date}'"
        if end_date:
            query += f" AND date <= '{end_date}'"
        
        query += " ORDER BY date ASC"
        
        result = self.conn.execute(query).fetchdf()
        logger.info(f"📊 Consultados {len(result)} registros para {coin_id}")
        return result
    
    def get_available_coins(self) -> List[Dict]:
        """
        Obtener lista de monedas disponibles en la base de datos.
        
        Returns:
            Lista de diccionarios con información de monedas
        """
        result = self.conn.execute("""
            SELECT 
                coin_id,
                coin_symbol,
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(*) as total_records
            FROM market_data
            GROUP BY coin_id, coin_symbol
            ORDER BY coin_id
        """).fetchdf()
        
        return result.to_dict('records')
    
    def get_extraction_stats(self) -> pd.DataFrame:
        """
        Obtener estadísticas de extracciones.
        
        Returns:
            DataFrame con estadísticas
        """
        return self.conn.execute("""
            SELECT 
                coin_id,
                COUNT(*) as total_extractions,
                SUM(records_inserted) as total_records,
                AVG(execution_time_seconds) as avg_execution_time,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as failed,
                MAX(timestamp) as last_extraction
            FROM extraction_log
            GROUP BY coin_id
            ORDER BY total_records DESC
        """).fetchdf()
    
    def delete_coin_data(self, coin_id: str):
        """
        Eliminar todos los datos de una moneda.
        
        Args:
            coin_id: ID del token a eliminar
        """
        self.conn.execute("DELETE FROM market_data WHERE coin_id = ?", [coin_id])
        logger.warning(f"🗑️ Eliminados todos los datos para {coin_id}")
    
    def vacuum(self):
        """Optimizar base de datos (compactar espacio)."""
        self.conn.execute("VACUUM")
        logger.info("🧹 Base de datos optimizada")
    
    def close(self):
        """Cerrar conexión a base de datos."""
        self.conn.close()
        logger.info("Conexión a DuckDB cerrada")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Función auxiliar para uso rápido
def quick_insert(coin_id: str, coin_symbol: str, data: pd.DataFrame, 
                db_path: str = "data/crypto_data.duckdb"):
    """
    Función auxiliar para insertar datos rápidamente.
    
    Args:
        coin_id: ID del token
        coin_symbol: Símbolo del token
        data: DataFrame con datos
        db_path: Ruta a la base de datos
    """
    with DuckDBManager(db_path) as db:
        return db.insert_market_data(coin_id, coin_symbol, data)