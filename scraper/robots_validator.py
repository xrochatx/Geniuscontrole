# ============================================================================
# GeniusControle - Validador de robots.txt
# Módulo: robots_validator.py
# Descripción: Módulo de cumplimiento ético que verifica el archivo robots.txt
#              del dominio objetivo antes de iniciar el scraping. Garantiza
#              que el crawler respete las directivas del sitio web.
# ============================================================================

import urllib.robotparser
from urllib.parse import urlparse
from typing import Optional

from logger_config import setup_logger

logger = setup_logger("robots_validator")


class RobotsValidator:
    """
    Validador de cumplimiento ético basado en robots.txt.
    
    Este módulo implementa las siguientes medidas de seguridad:
    1. Parseo y cache del archivo robots.txt del dominio.
    2. Verificación de permisos de acceso por URL.
    3. Extracción del crawl-delay recomendado por el sitio.
    4. Logging de todas las decisiones de cumplimiento (auditoría).
    
    Ref: RFC 9309 - Robots Exclusion Protocol
    """

    def __init__(self, base_url: str, user_agent: str = "GeniusControle/1.0"):
        """
        Inicializa el validador con la URL base del sitio objetivo.
        
        Args:
            base_url: URL raíz del sitio (ej: https://books.toscrape.com).
            user_agent: Identificador del crawler para robots.txt.
        """
        self.base_url = base_url
        self.user_agent = user_agent
        self._parser = urllib.robotparser.RobotFileParser()
        self._robots_url = self._build_robots_url(base_url)
        self._loaded = False
        self._crawl_delay: Optional[float] = None

        logger.info(
            "RobotsValidator inicializado para dominio: %s",
            urlparse(base_url).netloc
        )

    @staticmethod
    def _build_robots_url(base_url: str) -> str:
        """
        Construye la URL del archivo robots.txt a partir de la URL base.
        
        Args:
            base_url: URL raíz del sitio.
        
        Returns:
            URL completa del robots.txt (ej: https://example.com/robots.txt).
        """
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def load(self) -> bool:
        """
        Descarga y parsea el archivo robots.txt del dominio objetivo.
        
        Returns:
            True si el archivo se cargó correctamente, False si hubo error.
            
        Nota de seguridad: Si robots.txt no existe o no es accesible,
        se asume que TODO está permitido (estándar de la industria).
        """
        try:
            logger.info("Descargando robots.txt desde: %s", self._robots_url)
            self._parser.set_url(self._robots_url)
            self._parser.read()
            self._loaded = True

            # Extraer crawl-delay si está definido
            self._crawl_delay = self._parser.crawl_delay(self.user_agent)

            logger.info(
                "robots.txt cargado exitosamente. Crawl-delay: %s segundos",
                self._crawl_delay if self._crawl_delay else "No especificado"
            )
            return True

        except Exception as e:
            logger.warning(
                "No se pudo cargar robots.txt (%s). "
                "Se asumirá acceso permitido por defecto.",
                str(e)
            )
            self._loaded = False
            return False

    def can_fetch(self, url: str) -> bool:
        """
        Verifica si una URL específica está permitida para scraping
        según las directivas del robots.txt.
        
        Args:
            url: URL completa a verificar.
        
        Returns:
            True si el acceso está permitido, False si está bloqueado.
            
        Decisión ética: Si robots.txt no se pudo cargar, se permite
        el acceso pero se registra una advertencia en el log.
        """
        if not self._loaded:
            logger.warning(
                "robots.txt no cargado. Permitiendo acceso a: %s "
                "(se recomienda cargar robots.txt primero)", url
            )
            return True

        allowed = self._parser.can_fetch(self.user_agent, url)

        if allowed:
            logger.debug("PERMITIDO por robots.txt: %s", url)
        else:
            logger.warning(
                "BLOQUEADO por robots.txt: %s — "
                "Esta URL será omitida para cumplimiento ético.", url
            )

        return allowed

    def get_crawl_delay(self) -> Optional[float]:
        """
        Obtiene el crawl-delay recomendado por el sitio en robots.txt.
        
        Returns:
            Delay en segundos, o None si no está especificado.
            
        Nota: El rate_limiter.py usará este valor como delay mínimo
        si es mayor que el delay configurado por defecto.
        """
        if not self._loaded:
            logger.debug("robots.txt no cargado. Crawl-delay no disponible.")
            return None

        return self._crawl_delay

    def get_sitemaps(self) -> list:
        """
        Extrae las URLs de sitemaps declaradas en robots.txt.
        
        Returns:
            Lista de URLs de sitemaps encontrados.
        """
        if not self._loaded:
            return []

        sitemaps = self._parser.site_maps() or []
        if sitemaps:
            logger.info("Sitemaps encontrados: %d", len(sitemaps))
        return sitemaps

    def get_compliance_report(self) -> dict:
        """
        Genera un reporte de cumplimiento para auditoría.
        
        Returns:
            Diccionario con el estado de cumplimiento del crawler.
        """
        return {
            "robots_url": self._robots_url,
            "loaded": self._loaded,
            "user_agent": self.user_agent,
            "crawl_delay": self._crawl_delay,
            "sitemaps_found": len(self.get_sitemaps()),
            "compliance_status": "ACTIVE" if self._loaded else "DEGRADED"
        }
