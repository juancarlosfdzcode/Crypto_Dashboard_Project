"""
Tests para DuckDBManager
"""
import pytest
import pandas as pd
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Añadir el directorio raíz al path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.duckDBManager import DuckDBManager


@pytest.fixture
def temp_db_path():
    """Crear base de datos temporal para tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_crypto.duckdb")
        yield db_path


@pytest.fixture
def db_manager(temp_db_path):
    """Crear instancia de DuckDBManager para tests."""
    manager = DuckDBManager(temp_db_path)
    yield manager
    manager.close()


@pytest.fixture
def sample_market_data():
    """Datos de muestra para tests."""
    return pd.DataFrame({
        'timestamp': [1735689836528, 1735693425490, 1735696906963],
        'date': pd.to_datetime(['2025-01-01', '2025-01-01', '2025-01-01']).date,
        'price': [308.65, 312.97, 311.82],
        'market_cap': [4.64e9, 4.69e9, 4.69e9],
        'total_volume': [4.67e8, 5.59e8, 5.07e8]
    })


class TestDuckDBManagerInitialization:
    """Tests de inicialización y configuración."""
    
    def test_connection_creation(self, temp_db_path):
        """Test: Crear conexión exitosamente."""
        manager = DuckDBManager(temp_db_path)
        assert manager.conn is not None
        assert Path(temp_db_path).exists()
        manager.close()
    
    def test_tables_created(self, db_manager):
        """Test: Tablas se crean automáticamente."""
        # Verificar tabla market_data
        result = db_manager.conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'market_data'"
        ).fetchone()
        assert result[0] == 1
        
        # Verificar tabla extraction_log
        result = db_manager.conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'extraction_log'"
        ).fetchone()
        assert result[0] == 1
    
    def test_indexes_created(self, db_manager):
        """Test: Índices se crean correctamente."""
        indexes = db_manager.conn.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE table_name = 'market_data'"
        ).fetchall()
        
        index_names = [idx[0] for idx in indexes]
        assert 'idx_market_data_date' in index_names
        assert 'idx_market_data_coin' in index_names
    
    def test_directory_creation(self):
        """Test: Crear directorio si no existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "test.duckdb")
            manager = DuckDBManager(db_path)
            assert Path(db_path).parent.exists()
            manager.close()


class TestInsertMarketData:
    """Tests de inserción de datos."""
    
    def test_insert_basic_data(self, db_manager, sample_market_data):
        """Test: Insertar datos básicos."""
        records = db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        
        assert records == 3
        
        # Verificar que se insertaron
        result = db_manager.conn.execute(
            "SELECT COUNT(*) FROM market_data WHERE coin_id = 'bitcoin'"
        ).fetchone()
        assert result[0] == 3
    
    def test_insert_empty_dataframe(self, db_manager):
        """Test: Manejar DataFrame vacío."""
        empty_df = pd.DataFrame(columns=['timestamp', 'date', 'price', 'market_cap', 'total_volume'])
        records = db_manager.insert_market_data('bitcoin', 'btc', empty_df)
        
        assert records == 0
    
    def test_insert_multiple_coins(self, db_manager, sample_market_data):
        """Test: Insertar datos de múltiples monedas."""
        db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        db_manager.insert_market_data('ethereum', 'eth', sample_market_data)
        
        # Verificar que hay 2 monedas
        result = db_manager.conn.execute(
            "SELECT COUNT(DISTINCT coin_id) FROM market_data"
        ).fetchone()
        assert result[0] == 2
    
    def test_upsert_updates_existing(self, db_manager, sample_market_data):
        """Test: UPSERT actualiza datos existentes."""
        # Insertar datos iniciales
        db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        
        # Modificar precios
        updated_data = sample_market_data.copy()
        updated_data['price'] = [400.0, 410.0, 420.0]
        
        # Insertar de nuevo (debería actualizar)
        records = db_manager.insert_market_data('bitcoin', 'btc', updated_data)
        
        # Verificar que solo hay 3 registros (no duplicados)
        result = db_manager.conn.execute(
            "SELECT COUNT(*) FROM market_data WHERE coin_id = 'bitcoin'"
        ).fetchone()
        assert result[0] == 3
        
        # Verificar que los precios se actualizaron
        result = db_manager.conn.execute(
            "SELECT AVG(price) FROM market_data WHERE coin_id = 'bitcoin'"
        ).fetchone()
        assert result[0] == pytest.approx(410.0, rel=0.01)
    
    def test_extraction_timestamp_auto_set(self, db_manager, sample_market_data):
        """Test: extraction_timestamp se establece automáticamente."""
        db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        
        result = db_manager.conn.execute(
            "SELECT extraction_timestamp FROM market_data WHERE coin_id = 'bitcoin' LIMIT 1"
        ).fetchone()
        
        assert result[0] is not None


class TestLogExtraction:
    """Tests de logging de extracciones."""
    
    def test_log_successful_extraction(self, db_manager):
        """Test: Registrar extracción exitosa."""
        db_manager.log_extraction(
            coin_id='bitcoin',
            from_date='2025-01-01',
            to_date='2025-01-31',
            records_inserted=100,
            execution_time=2.5,
            status='SUCCESS'
        )
        
        # Verificar registro
        result = db_manager.conn.execute(
            "SELECT * FROM extraction_log WHERE coin_id = 'bitcoin'"
        ).fetchone()
        
        assert result is not None
        assert result[1] == 'bitcoin'  # coin_id
        assert result[4] == 100  # records_inserted
        assert result[6] == 'SUCCESS'  # status
    
    def test_log_failed_extraction(self, db_manager):
        """Test: Registrar extracción fallida."""
        db_manager.log_extraction(
            coin_id='ethereum',
            from_date='2025-01-01',
            to_date='2025-01-31',
            records_inserted=0,
            execution_time=1.0,
            status='ERROR',
            error_message='API rate limit exceeded'
        )
        
        result = db_manager.conn.execute(
            "SELECT status, error_message FROM extraction_log WHERE coin_id = 'ethereum'"
        ).fetchone()
        
        assert result[0] == 'ERROR'
        assert result[1] == 'API rate limit exceeded'
    
    def test_multiple_extraction_logs(self, db_manager):
        """Test: Múltiples logs de extracción."""
        for i in range(3):
            db_manager.log_extraction(
                coin_id='bitcoin',
                from_date='2025-01-01',
                to_date='2025-01-31',
                records_inserted=100 + i,
                execution_time=2.0 + i * 0.5,
                status='SUCCESS'
            )
        
        result = db_manager.conn.execute(
            "SELECT COUNT(*) FROM extraction_log WHERE coin_id = 'bitcoin'"
        ).fetchone()
        
        assert result[0] == 3


class TestQueryMethods:
    """Tests de métodos de consulta."""
    
    def test_get_market_data_all(self, db_manager, sample_market_data):
        """Test: Obtener todos los datos de una moneda."""
        db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        
        result = db_manager.get_market_data('bitcoin')
        
        assert len(result) == 3
        assert list(result.columns) == ['coin_id', 'coin_symbol', 'timestamp', 'date', 
                                         'price', 'market_cap', 'total_volume', 'extraction_timestamp']
    
    def test_get_market_data_with_date_range(self, db_manager):
        """Test: Filtrar por rango de fechas."""
        # Crear datos con diferentes fechas
        data = pd.DataFrame({
            'timestamp': [1735689836528, 1738281836528, 1740960236528],
            'date': pd.to_datetime(['2025-01-01', '2025-01-31', '2025-03-01']).date,
            'price': [100.0, 110.0, 120.0],
            'market_cap': [1e9, 1.1e9, 1.2e9],
            'total_volume': [1e8, 1.1e8, 1.2e8]
        })
        
        db_manager.insert_market_data('bitcoin', 'btc', data)
        
        # Consultar solo enero
        result = db_manager.get_market_data('bitcoin', start_date='2025-01-01', end_date='2025-01-31')
        
        assert len(result) == 2
    
    def test_get_market_data_nonexistent_coin(self, db_manager):
        """Test: Consultar moneda inexistente."""
        result = db_manager.get_market_data('nonexistent')
        
        assert len(result) == 0
    
    def test_get_available_coins(self, db_manager, sample_market_data):
        """Test: Obtener lista de monedas disponibles."""
        db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        db_manager.insert_market_data('ethereum', 'eth', sample_market_data)
        
        coins = db_manager.get_available_coins()
        
        assert len(coins) == 2
        coin_ids = [coin['coin_id'] for coin in coins]
        assert 'bitcoin' in coin_ids
        assert 'ethereum' in coin_ids
    
    def test_get_extraction_stats(self, db_manager):
        """Test: Obtener estadísticas de extracciones."""
        # Crear varios logs
        for i in range(3):
            db_manager.log_extraction(
                coin_id='bitcoin',
                from_date='2025-01-01',
                to_date='2025-01-31',
                records_inserted=100,
                execution_time=2.0,
                status='SUCCESS' if i < 2 else 'ERROR'
            )
        
        stats = db_manager.get_extraction_stats()
        
        assert len(stats) == 1
        assert stats.iloc[0]['coin_id'] == 'bitcoin'
        assert stats.iloc[0]['total_extractions'] == 3
        assert stats.iloc[0]['successful'] == 2.0
        assert stats.iloc[0]['failed'] == 1.0


class TestDataDeletion:
    """Tests de eliminación de datos."""
    
    def test_delete_coin_data(self, db_manager, sample_market_data):
        """Test: Eliminar datos de una moneda."""
        db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        db_manager.insert_market_data('ethereum', 'eth', sample_market_data)
        
        # Eliminar bitcoin
        db_manager.delete_coin_data('bitcoin')
        
        # Verificar que bitcoin se eliminó
        result = db_manager.conn.execute(
            "SELECT COUNT(*) FROM market_data WHERE coin_id = 'bitcoin'"
        ).fetchone()
        assert result[0] == 0
        
        # Verificar que ethereum sigue
        result = db_manager.conn.execute(
            "SELECT COUNT(*) FROM market_data WHERE coin_id = 'ethereum'"
        ).fetchone()
        assert result[0] == 3


class TestContextManager:
    """Tests del context manager."""
    
    def test_context_manager(self, temp_db_path, sample_market_data):
        """Test: Usar DuckDBManager como context manager."""
        with DuckDBManager(temp_db_path) as db:
            db.insert_market_data('bitcoin', 'btc', sample_market_data)
            
            result = db.conn.execute(
                "SELECT COUNT(*) FROM market_data"
            ).fetchone()
            assert result[0] == 3
        
        # Verificar que la conexión se cerró


class TestEdgeCases:
    """Tests de casos extremos."""
    
    def test_large_dataset(self, db_manager):
        """Test: Manejar dataset grande."""
        # Crear 10,000 registros
        large_data = pd.DataFrame({
            'timestamp': range(1735689836528, 1735689836528 + 10000),
            'date': pd.to_datetime(['2025-01-01'] * 10000).date,
            'price': [100.0 + i * 0.1 for i in range(10000)],
            'market_cap': [1e9] * 10000,
            'total_volume': [1e8] * 10000
        })
        
        records = db_manager.insert_market_data('bitcoin', 'btc', large_data)
        
        assert records == 10000
    
    def test_special_characters_in_coin_id(self, db_manager, sample_market_data):
        """Test: Manejar caracteres especiales en IDs."""
        db_manager.insert_market_data('crypto-com-chain', 'cro', sample_market_data)
        
        result = db_manager.get_market_data('crypto-com-chain')
        assert len(result) == 3
    
    def test_concurrent_inserts(self, db_manager, sample_market_data):
        """Test: Múltiples inserciones seguidas."""
        for i in range(5):
            db_manager.insert_market_data(f'coin_{i}', f'c{i}', sample_market_data)
        
        coins = db_manager.get_available_coins()
        assert len(coins) == 5


class TestDataIntegrity:
    """Tests de integridad de datos."""
    
    def test_coin_symbol_lowercase(self, db_manager, sample_market_data):
        """Test: coin_symbol se convierte a minúsculas."""
        db_manager.insert_market_data('bitcoin', 'BTC', sample_market_data)
        
        result = db_manager.conn.execute(
            "SELECT DISTINCT coin_symbol FROM market_data"
        ).fetchone()
        
        assert result[0] == 'btc'
    
    def test_data_types_preserved(self, db_manager, sample_market_data):
        """Test: Tipos de datos se preservan correctamente."""
        db_manager.insert_market_data('bitcoin', 'btc', sample_market_data)
        
        result = db_manager.conn.execute("""
            SELECT 
                typeof(timestamp),
                typeof(date),
                typeof(price),
                typeof(market_cap),
                typeof(total_volume)
            FROM market_data LIMIT 1
        """).fetchone()
        
        assert result[0] == 'BIGINT'  # timestamp
        assert result[1] == 'DATE'  # date
        assert result[2] == 'DOUBLE'  # price


# ==============================================================================
# TESTS DE INTEGRACIÓN
# ==============================================================================

class TestIntegrationScenarios:
    """Tests de escenarios completos de uso."""
    
    def test_full_pipeline_scenario(self, db_manager):
        """Test: Escenario completo de pipeline."""
        # Día 1: Primera extracción
        data_day1 = pd.DataFrame({
            'timestamp': [1735689836528],
            'date': pd.to_datetime(['2025-01-01']).date,
            'price': [100.0],
            'market_cap': [1e9],
            'total_volume': [1e8]
        })
        
        records = db_manager.insert_market_data('bitcoin', 'btc', data_day1)
        db_manager.log_extraction('bitcoin', '2025-01-01', '2025-01-01', records, 1.5, 'SUCCESS')
        
        # Día 2: Segunda extracción
        data_day2 = pd.DataFrame({
            'timestamp': [1738281836528],
            'date': pd.to_datetime(['2025-01-31']).date,
            'price': [110.0],
            'market_cap': [1.1e9],
            'total_volume': [1.1e8]
        })
        
        records = db_manager.insert_market_data('bitcoin', 'btc', data_day2)
        db_manager.log_extraction('bitcoin', '2025-01-31', '2025-01-31', records, 1.8, 'SUCCESS')
        
        # Verificaciones
        market_data = db_manager.get_market_data('bitcoin')
        assert len(market_data) == 2
        
        stats = db_manager.get_extraction_stats()
        assert stats.iloc[0]['total_extractions'] == 2
        assert stats.iloc[0]['successful'] == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])