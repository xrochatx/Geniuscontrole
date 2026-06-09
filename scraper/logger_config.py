# ============================================================================
# GeniusControle - Configuración de Logging Seguro
# Módulo: logger_config.py
# Descripción: Logging estructurado (JSON) con sanitización de datos
#              sensibles y rotación de archivos.
# ============================================================================

import logging
import re
import sys
from logging.handlers import RotatingFileHandler

from config import ScraperConfig


class SensitiveDataFilter(logging.Filter):
    """
    Filtro de logging que sanitiza datos sensibles antes de escribirlos.
    
    Seguridad: Previene la exposición de credenciales, IPs de proxy y
    tokens en los archivos de log. Cumple con principios de OWASP
    para manejo seguro de logs.
    """

    # Patrones de datos sensibles a redactar
    SENSITIVE_PATTERNS = [
        # Contraseñas en URIs (mongodb://user:PASSWORD@host)
        (re.compile(r'(://[^:]+:)[^@]+(@)'), r'\1****\2'),
        # Direcciones IP de proxies
        (re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?'), r'[IP_REDACTED]\2'),
        # Tokens y API keys
        (re.compile(r'(token|api[_-]?key|password|secret)\s*[=:]\s*\S+', re.IGNORECASE),
         r'\1=****'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitiza el mensaje del log antes de emitirlo."""
        if isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        # Sanitizar también los argumentos del mensaje
        if record.args:
            sanitized_args = []
            for arg in (record.args if isinstance(record.args, tuple) else (record.args,)):
                if isinstance(arg, str):
                    for pattern, replacement in self.SENSITIVE_PATTERNS:
                        arg = pattern.sub(replacement, arg)
                sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        return True


def setup_logger(name: str = "geniuscontrole") -> logging.Logger:
    """
    Configura y retorna un logger con las siguientes características:
    
    1. Formato estructurado JSON-like para parseo automatizado.
    2. Filtro de datos sensibles (contraseñas, IPs, tokens).
    3. Rotación de archivos de log (máx. 10 MB, 5 backups).
    4. Salida dual: consola (INFO+) y archivo (DEBUG+).
    
    Args:
        name: Nombre del logger.
    
    Returns:
        logging.Logger: Logger configurado y listo para usar.
    """
    logger = logging.getLogger(name)

    # Evitar configuración duplicada
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, ScraperConfig.LOG_LEVEL.upper(), logging.INFO))

    # Formato estructurado para facilitar análisis y auditoría
    log_format = logging.Formatter(
        fmt=(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(module)s", "function": "%(funcName)s", '
            '"line": %(lineno)d, "message": "%(message)s"}'
        ),
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )

    # --- Handler de consola (stdout) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    console_handler.addFilter(SensitiveDataFilter())

    # --- Handler de archivo con rotación ---
    file_handler = RotatingFileHandler(
        filename=ScraperConfig.LOG_FILE,
        maxBytes=ScraperConfig.LOG_MAX_BYTES,
        backupCount=ScraperConfig.LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    file_handler.addFilter(SensitiveDataFilter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
