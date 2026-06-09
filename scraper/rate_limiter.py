# ============================================================================
# GeniusControle - Rate Limiter (Control de Tasa de Peticiones)
# Módulo: rate_limiter.py
# Descripción: Implementa el algoritmo Token Bucket para controlar la
#              frecuencia de peticiones HTTP. Previene ataques DDoS
#              involuntarios y respeta el crawl-delay de robots.txt.
# ============================================================================

import time
import random
import threading
from typing import Optional

from config import ScraperConfig
from logger_config import setup_logger

logger = setup_logger("rate_limiter")


class RateLimiter:
    """
    Controlador de tasa de peticiones basado en Token Bucket.
    
    Medidas de seguridad implementadas:
    1. Delay aleatorio entre peticiones (evita patrones detectables).
    2. Respeto del crawl-delay de robots.txt como mínimo.
    3. Backoff exponencial ante respuestas 429 (Too Many Requests).
    4. Thread-safe para uso en entornos concurrentes.
    
    Referencia: RFC 6585 - HTTP 429 Too Many Requests
    """

    def __init__(
        self,
        min_delay: float = ScraperConfig.REQUEST_DELAY_MIN,
        max_delay: float = ScraperConfig.REQUEST_DELAY_MAX,
        crawl_delay: Optional[float] = None,
        backoff_factor: float = ScraperConfig.BACKOFF_FACTOR,
        max_retries: int = ScraperConfig.MAX_RETRIES
    ):
        """
        Inicializa el rate limiter.
        
        Args:
            min_delay: Delay mínimo entre peticiones (segundos).
            max_delay: Delay máximo entre peticiones (segundos).
            crawl_delay: Crawl-delay de robots.txt (sobreescribe min_delay si es mayor).
            backoff_factor: Factor multiplicador para backoff exponencial.
            max_retries: Número máximo de reintentos ante error 429.
        """
        # Si robots.txt especifica un crawl-delay mayor, usarlo como mínimo
        if crawl_delay and crawl_delay > min_delay:
            logger.info(
                "Usando crawl-delay de robots.txt: %.1f seg (mayor que min_delay: %.1f seg)",
                crawl_delay, min_delay
            )
            min_delay = crawl_delay

        self.min_delay = min_delay
        self.max_delay = max(max_delay, min_delay + 1.0)
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries

        # Estado interno (thread-safe)
        self._lock = threading.Lock()
        self._last_request_time: float = 0.0
        self._consecutive_errors: int = 0
        self._total_requests: int = 0
        self._total_waits: float = 0.0

        logger.info(
            "RateLimiter inicializado: delay=[%.1f, %.1f] seg, "
            "backoff_factor=%.1f, max_retries=%d",
            self.min_delay, self.max_delay, self.backoff_factor, self.max_retries
        )

    def wait(self) -> float:
        """
        Espera el tiempo necesario antes de la siguiente petición.
        
        Aplica un delay aleatorio entre min_delay y max_delay, más un
        componente adicional de backoff si hay errores consecutivos.
        
        Returns:
            Tiempo de espera efectivo (segundos).
            
        Thread-safety: Este método es seguro para uso concurrente.
        """
        with self._lock:
            # Calcular delay base aleatorio (evita patrones detectables)
            base_delay = random.uniform(self.min_delay, self.max_delay)

            # Agregar backoff exponencial si hay errores consecutivos
            if self._consecutive_errors > 0:
                backoff_delay = base_delay * (
                    self.backoff_factor ** self._consecutive_errors
                )
                # Limitar backoff a 60 segundos máximo
                delay = min(backoff_delay, 60.0)
                logger.warning(
                    "Backoff exponencial aplicado: %.1f seg "
                    "(errores consecutivos: %d)",
                    delay, self._consecutive_errors
                )
            else:
                delay = base_delay

            # Calcular tiempo transcurrido desde la última petición
            elapsed = time.time() - self._last_request_time
            actual_wait = max(0, delay - elapsed)

        # Esperar fuera del lock para no bloquear otros hilos
        if actual_wait > 0:
            logger.debug("Rate limiter: esperando %.2f segundos...", actual_wait)
            time.sleep(actual_wait)

        # Actualizar estado
        with self._lock:
            self._last_request_time = time.time()
            self._total_requests += 1
            self._total_waits += actual_wait

        return actual_wait

    def report_success(self) -> None:
        """
        Notifica una petición exitosa. Resetea el contador de errores.
        """
        with self._lock:
            if self._consecutive_errors > 0:
                logger.info(
                    "Petición exitosa después de %d errores consecutivos. "
                    "Reseteando backoff.",
                    self._consecutive_errors
                )
            self._consecutive_errors = 0

    def report_error(self, status_code: Optional[int] = None) -> bool:
        """
        Notifica un error en la petición. Incrementa el backoff.
        
        Args:
            status_code: Código de estado HTTP del error (ej: 429, 503).
        
        Returns:
            True si se puede reintentar, False si se alcanzó max_retries.
        """
        with self._lock:
            self._consecutive_errors += 1
            can_retry = self._consecutive_errors <= self.max_retries

        if status_code == 429:
            logger.warning(
                "HTTP 429 (Too Many Requests) recibido. "
                "Error consecutivo #%d de %d. %s",
                self._consecutive_errors, self.max_retries,
                "Reintentando con backoff..." if can_retry else "Máximo de reintentos alcanzado."
            )
        elif status_code:
            logger.warning(
                "Error HTTP %d recibido. Error consecutivo #%d de %d.",
                status_code, self._consecutive_errors, self.max_retries
            )
        else:
            logger.warning(
                "Error de conexión. Error consecutivo #%d de %d.",
                self._consecutive_errors, self.max_retries
            )

        return can_retry

    def get_stats(self) -> dict:
        """
        Retorna estadísticas del rate limiter para monitoreo.
        
        Returns:
            Diccionario con métricas de uso.
        """
        with self._lock:
            avg_wait = (
                self._total_waits / self._total_requests
                if self._total_requests > 0
                else 0.0
            )
            return {
                "total_requests": self._total_requests,
                "total_wait_time_seconds": round(self._total_waits, 2),
                "average_wait_seconds": round(avg_wait, 2),
                "consecutive_errors": self._consecutive_errors,
                "current_delay_range": f"[{self.min_delay}, {self.max_delay}] seg"
            }
