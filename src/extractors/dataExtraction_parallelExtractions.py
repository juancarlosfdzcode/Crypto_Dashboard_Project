"""
Proof of Concept: Parallel Extractions
Compara extracción secuencial vs paralela con ThreadPoolExecutor y asyncio
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'extractors')))

from dataExtraction import CoinGeckoClient, APIConfig, Token, CoinGeckoAPIError
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
from typing import List, Dict
from dataclasses import dataclass

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Resultados de benchmark"""
    method: str
    duration: float
    tokens_processed: int
    records_extracted: int
    tokens_per_second: float
    records_per_second: float
    success: bool
    errors: int


class ParallelCoinGeckoClient(CoinGeckoClient):
    """
    Cliente extendido con capacidades de extracción paralela.
    Usa ThreadPoolExecutor para paralelizar requests.
    """
    
    def __init__(self, config: APIConfig, api_token=None):
        super().__init__(config, api_token)
        # Lock para thread-safety en rate limiting
        self.rate_limit_lock = threading.Lock()
    
    def _apply_rate_limit_threadsafe(self):
        """Rate limiting thread-safe para uso en múltiples threads"""
        with self.rate_limit_lock:
            self._apply_rate_limit()
    
    def _extract_single_token_parallel(self, token: Token) -> Dict:
        """
        Extrae datos de un solo token (thread-safe).
        
        Returns:
            Dict con {'token': Token, 'data': Dict, 'df': DataFrame, 'error': Optional[str]}
        """
        result = {
            'token': token,
            'data': None,
            'df': None,
            'error': None
        }
        
        try:
            # Rate limiting thread-safe
            self._apply_rate_limit_threadsafe()
            
            # Obtener datos
            token_data = self.get_token_market_data(token)
            result['data'] = token_data
            
            # Procesar a DataFrame
            df_token = self.process_token_data(token_data, token.coin)
            result['df'] = df_token
            
            logger.info(f"✓ Thread completado para {token.coin}: {len(df_token)} registros")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ Error en thread para {token.coin}: {e}")
        
        return result
    
    def data_extraction_parallel(self, tokens: List[Token] = None, max_workers: int = 3) -> pd.DataFrame:
        """
        Extracción paralela usando ThreadPoolExecutor.
        
        Args:
            tokens: Lista de tokens a procesar
            max_workers: Número máximo de threads paralelos
            
        Returns:
            DataFrame combinado con datos de todos los tokens
        """
        if tokens is None:
            tokens = self.default_tokens
        
        logger.info(f"Iniciando extracción PARALELA con {max_workers} workers para {len(tokens)} tokens")
        
        all_dataframes = []
        errors = 0
        
        try:
            # Ping inicial
            self.ping()
            
            # Crear ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Enviar todos los tokens a procesar
                future_to_token = {
                    executor.submit(self._extract_single_token_parallel, token): token 
                    for token in tokens
                }
                
                # Recoger resultados conforme se completan
                for future in as_completed(future_to_token):
                    result = future.result()
                    
                    if result['error']:
                        errors += 1
                        logger.warning(f"Saltando {result['token'].coin} debido a error: {result['error']}")
                    elif result['df'] is not None:
                        all_dataframes.append(result['df'])
            
            # Combinar resultados
            if all_dataframes:
                final_df = pd.concat(all_dataframes, ignore_index=True)
                logger.info(f"DataFrame final creado con {len(final_df)} registros totales ({errors} errores)")
                return final_df
            else:
                logger.warning('No se obtuvieron datos de ningún token')
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f'Error en data_extraction_parallel: {e}')
            raise CoinGeckoAPIError(f'No se ha podido ejecutar workflow paralelo: {e}')


def benchmark_sequential(client: CoinGeckoClient, tokens: List[Token]) -> BenchmarkResult:
    """Ejecutar y medir extracción secuencial"""
    logger.info("\n=== BENCHMARK: Extracción SECUENCIAL ===")
    
    start_time = time.time()
    errors = 0
    
    try:
        df = client.data_extraction(tokens)
        success = True
        records = len(df) if not df.empty else 0
    except Exception as e:
        logger.error(f"Error en extracción secuencial: {e}")
        success = False
        records = 0
        errors = 1
    
    duration = time.time() - start_time
    tokens_processed = len(tokens)
    
    result = BenchmarkResult(
        method="Secuencial",
        duration=duration,
        tokens_processed=tokens_processed,
        records_extracted=records,
        tokens_per_second=tokens_processed / duration if duration > 0 else 0,
        records_per_second=records / duration if duration > 0 else 0,
        success=success,
        errors=errors
    )
    
    logger.info(f"Completado en {duration:.2f}s")
    return result


def benchmark_parallel(client: ParallelCoinGeckoClient, tokens: List[Token], max_workers: int) -> BenchmarkResult:
    """Ejecutar y medir extracción paralela"""
    logger.info(f"\n=== BENCHMARK: Extracción PARALELA ({max_workers} workers) ===")
    
    start_time = time.time()
    errors = 0
    
    try:
        df = client.data_extraction_parallel(tokens, max_workers=max_workers)
        success = True
        records = len(df) if not df.empty else 0
    except Exception as e:
        logger.error(f"Error en extracción paralela: {e}")
        success = False
        records = 0
        errors = 1
    
    duration = time.time() - start_time
    tokens_processed = len(tokens)
    
    result = BenchmarkResult(
        method=f"Paralelo ({max_workers}w)",
        duration=duration,
        tokens_processed=tokens_processed,
        records_extracted=records,
        tokens_per_second=tokens_processed / duration if duration > 0 else 0,
        records_per_second=records / duration if duration > 0 else 0,
        success=success,
        errors=errors
    )
    
    logger.info(f"Completado en {duration:.2f}s")
    return result


def print_benchmark_report(results: List[BenchmarkResult]):
    """Imprimir reporte comparativo de benchmarks"""
    print("\n" + "="*80)
    print("REPORTE DE BENCHMARK: Secuencial vs Paralelo")
    print("="*80)
    
    # Tabla de resultados
    print(f"\n{'Método':<20} {'Duración':<12} {'Tokens':<10} {'Registros':<12} {'T/s':<10} {'R/s':<10}")
    print("-"*80)
    
    for result in results:
        print(f"{result.method:<20} {result.duration:>10.2f}s {result.tokens_processed:>8} "
              f"{result.records_extracted:>10} {result.tokens_per_second:>8.2f} "
              f"{result.records_per_second:>8.1f}")
    
    # Análisis comparativo
    if len(results) >= 2:
        sequential = results[0]
        parallel = results[1]
        
        speedup = sequential.duration / parallel.duration if parallel.duration > 0 else 0
        time_saved = sequential.duration - parallel.duration
        improvement_pct = ((sequential.duration - parallel.duration) / sequential.duration * 100) if sequential.duration > 0 else 0
        
        print("\n" + "-"*80)
        print("ANÁLISIS COMPARATIVO:")
        print(f"  Speedup: {speedup:.2f}x")
        print(f"  Tiempo ahorrado: {time_saved:.2f}s ({improvement_pct:.1f}% más rápido)")
        
        if speedup > 1.5:
            print(f"  ✓ Paralelización EFECTIVA - Vale la pena usar")
        elif speedup > 1.1:
            print(f"  ~ Paralelización MARGINAL - Beneficio mínimo")
        else:
            print(f"  ✗ Paralelización NO EFECTIVA - No vale la pena")
        
        # Consideraciones
        print("\nCONSIDERACIONES:")
        print(f"  - Rate limit delay: {sequential.duration / sequential.tokens_processed:.2f}s por token")
        print(f"  - Con rate limiting, el speedup máximo teórico es ~{1 / (sequential.duration / sequential.tokens_processed / 2):.2f}x")
        print(f"  - Complejidad añadida: Threading, locks, sincronización")
        print(f"  - Recomendación: {'USAR paralelo' if speedup > 1.5 else 'MANTENER secuencial'}")
    
    print("="*80 + "\n")


def create_test_tokens(count: int = 10) -> List[Token]:
    """Crear lista de tokens para testing"""
    # Tokens reales para testing
    test_tokens = [
        Token(coin='aave', id='aave'),
        Token(coin='cronos', id='crypto-com-chain'),
        Token(coin='chainlink', id='chainlink')    
    ]
    
    return test_tokens[:count]


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PROOF OF CONCEPT: PARALLEL EXTRACTIONS")
    print("="*80 + "\n")
    
    # Configuración
    config = APIConfig(
        fromDate='2025-01-01',
        toDate='2025-01-07',  # Solo 1 semana para testing
        rate_limit_delay=3.0   # Delay estándar
    )
    
    # Crear tokens de prueba
    num_tokens = 3  # Ajusta según tu plan API
    tokens = create_test_tokens(num_tokens)
    
    print(f"Configuración:")
    print(f"  - Tokens a procesar: {len(tokens)}")
    print(f"  - Fechas: {config.fromDate} a {config.toDate}")
    print(f"  - Rate limit delay: {config.rate_limit_delay}s")
    print(f"  - Tiempo esperado secuencial: ~{len(tokens) * config.rate_limit_delay:.0f}s")
    print()
    
    results = []
    
    try:
        # Benchmark 1: Secuencial
        client_seq = CoinGeckoClient(config)
        result_seq = benchmark_sequential(client_seq, tokens)
        results.append(result_seq)
        
        # Esperar un poco entre benchmarks
        print("\nEsperando 30 segundos antes del siguiente benchmark...")
        time.sleep(60)
        
        # Benchmark 2: Paralelo con 2 workers
        client_par2 = ParallelCoinGeckoClient(config)
        result_par2 = benchmark_parallel(client_par2, tokens, max_workers=1)
        results.append(result_par2)
        
        time.sleep(60)
        
        # Benchmark 3: Paralelo con 3 workers
        client_par3 = ParallelCoinGeckoClient(config)
        result_par3 = benchmark_parallel(client_par3, tokens, max_workers=2)
        results.append(result_par3)
        
        # Imprimir reporte
        print_benchmark_report(results)
        
        # Conclusiones específicas
        print("CONCLUSIONES PARA ESTE CASO:")
        print(f"  Con {len(tokens)} tokens y rate limit de {config.rate_limit_delay}s:")
        
        if results[1].duration < results[0].duration * 0.7:
            print("  ✓ La paralelización mejora significativamente el performance")
            print("  ✓ Recomendación: Usar paralelización en producción")
        else:
            print("  ✗ La paralelización NO mejora significativamente el performance")
            print("  ✗ Razón: El rate limiting domina el tiempo de ejecución")
            print("  ✗ Recomendación: Mantener versión secuencial (más simple)")
        
    except Exception as e:
        logger.error(f"Error ejecutando benchmarks: {e}")
        print(f"\n✗ Error: {e}")
        print("\nVerifica:")
        print("  1. Que tengas API token válido en .env")
        print("  2. Que los tokens existan en CoinGecko")
        print("  3. Que no hayas excedido rate limits")