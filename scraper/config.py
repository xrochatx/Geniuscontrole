# ============================================================================
# GeniusControle - Configuración Centralizada del Scraper
# Módulo: config.py
# Descripción: Variables de entorno y parámetros de configuración del sistema
#              de scraping. Usa valores por defecto seguros.
# ============================================================================

import os
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env (si existe)
load_dotenv()


class ScraperConfig:
    """
    Configuración centralizada del motor de scraping.
    Los valores se leen de variables de entorno con fallback a defaults seguros.
    """

    # -----------------------------------------------------------------------
    # Conexión a MongoDB
    # -----------------------------------------------------------------------
    MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
    MONGO_USERNAME = os.getenv("MONGO_USERNAME", "geniusadmin")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "G3n1u5S3cur3P@ss")
    MONGO_DATABASE = os.getenv("MONGO_DATABASE", "geniuscontrole")
    MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "products")
    MONGO_AUTH_SOURCE = os.getenv("MONGO_AUTH_SOURCE", "admin")

    @classmethod
    def get_mongo_uri(cls) -> str:
        """Construye la URI de conexión a MongoDB con autenticación."""
        import urllib.parse
        username = urllib.parse.quote_plus(cls.MONGO_USERNAME)
        password = urllib.parse.quote_plus(cls.MONGO_PASSWORD)
        return (
            f"mongodb://{username}:{password}"
            f"@{cls.MONGO_HOST}:{cls.MONGO_PORT}"
            f"/{cls.MONGO_DATABASE}?authSource={cls.MONGO_AUTH_SOURCE}"
        )

    # -----------------------------------------------------------------------
    # Conexión a Redis
    # -----------------------------------------------------------------------
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "R3d1sS3cur3P@ss")
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))

    # -----------------------------------------------------------------------
    # Selenium WebDriver (remoto)
    # -----------------------------------------------------------------------
    SELENIUM_HUB_URL = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444/wd/hub")

    # -----------------------------------------------------------------------
    # Rate Limiting — Prevención de DDoS involuntario
    # -----------------------------------------------------------------------
    # Delay mínimo entre peticiones (segundos)
    REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "2.0"))
    # Delay máximo entre peticiones (segundos)
    REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "5.0"))
    # Máximo de reintentos ante error
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    # Timeout por petición HTTP (segundos)
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    # Factor de backoff exponencial
    BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "2.0"))

    # -----------------------------------------------------------------------
    # Scraping — Parámetros generales
    # -----------------------------------------------------------------------
    # Número máximo de páginas a recorrer por defecto
    DEFAULT_MAX_PAGES = int(os.getenv("DEFAULT_MAX_PAGES", "5"))
    # URL objetivo por defecto (sitio legal para práctica)
    DEFAULT_TARGET_URL = os.getenv(
        "DEFAULT_TARGET_URL", "https://books.toscrape.com"
    )

    # -----------------------------------------------------------------------
    # Proxies — Archivo de configuración externo
    # -----------------------------------------------------------------------
    PROXY_FILE = os.getenv("PROXY_FILE", "proxies.txt")
    USE_PROXIES = os.getenv("USE_PROXIES", "false").lower() == "true"

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "scraper.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10 MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
