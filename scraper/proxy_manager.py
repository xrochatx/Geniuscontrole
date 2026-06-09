# ============================================================================
# GeniusControle - Gestor de Proxies
# Módulo: proxy_manager.py
# Descripción: Pool de proxies con rotación round-robin, detección de
#              proxies no funcionales y blacklisting automático.
#              Soporta HTTP, HTTPS y SOCKS5.
# ============================================================================

import os
import random
import threading
from typing import Optional

from config import ScraperConfig
from logger_config import setup_logger

logger = setup_logger("proxy_manager")


class ProxyManager:
    """
    Gestor de proxies para evadir bloqueos por IP.
    
    Características de seguridad:
    1. Rotación round-robin para distribuir peticiones.
    2. Blacklist automática de proxies con fallos consecutivos.
    3. Soporte para protocolos HTTP, HTTPS y SOCKS5.
    4. Carga de proxies desde archivo externo (no hardcodeados).
    5. Fallback a conexión directa si no hay proxies disponibles.
    """

    # Umbral de fallos para blacklist de un proxy
    MAX_FAILURES = 3

    def __init__(self, proxy_file: Optional[str] = None):
        """
        Inicializa el gestor de proxies.
        
        Args:
            proxy_file: Ruta al archivo con lista de proxies (uno por línea).
                       Formato: protocolo://ip:puerto (ej: http://1.2.3.4:8080)
        """
        self._lock = threading.Lock()
        self._proxies: list[dict] = []
        self._blacklist: set = set()
        self._failure_count: dict[str, int] = {}
        self._current_index: int = 0
        self._enabled = ScraperConfig.USE_PROXIES

        if self._enabled:
            file_path = proxy_file or ScraperConfig.PROXY_FILE
            self._load_proxies(file_path)

        if not self._enabled or not self._proxies:
            logger.info(
                "ProxyManager: Modo conexión directa (sin proxies). "
                "Para habilitar proxies, configure USE_PROXIES=true y "
                "proporcione un archivo de proxies."
            )

    def _load_proxies(self, file_path: str) -> None:
        """
        Carga proxies desde un archivo de texto.
        
        Formato del archivo (una entrada por línea):
            http://ip:puerto
            https://ip:puerto
            socks5://ip:puerto
            # Líneas con # son comentarios
        
        Args:
            file_path: Ruta al archivo de proxies.
        """
        if not os.path.exists(file_path):
            logger.warning(
                "Archivo de proxies no encontrado: %s. "
                "Continuando sin proxies.", file_path
            )
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Ignorar líneas vacías y comentarios
                    if not line or line.startswith("#"):
                        continue

                    proxy_dict = self._parse_proxy(line)
                    if proxy_dict:
                        self._proxies.append(proxy_dict)

            logger.info(
                "ProxyManager: %d proxies cargados desde archivo.",
                len(self._proxies)
            )
        except IOError as e:
            logger.error("Error al leer archivo de proxies: %s", str(e))

    @staticmethod
    def _parse_proxy(proxy_string: str) -> Optional[dict]:
        """
        Parsea una línea de proxy y la convierte a formato dict para requests.
        
        Args:
            proxy_string: Proxy en formato protocolo://ip:puerto.
        
        Returns:
            Dict con formato compatible con requests.Session.proxies, o None.
        """
        proxy_string = proxy_string.strip()

        if proxy_string.startswith("socks5://"):
            return {
                "http": proxy_string,
                "https": proxy_string,
                "_raw": proxy_string
            }
        elif proxy_string.startswith(("http://", "https://")):
            return {
                "http": proxy_string,
                "https": proxy_string,
                "_raw": proxy_string
            }
        else:
            logger.warning("Formato de proxy no reconocido: %s", proxy_string)
            return None

    def get_proxy(self) -> Optional[dict]:
        """
        Obtiene el siguiente proxy disponible usando rotación round-robin.
        
        Returns:
            Dict de proxy para requests.Session, o None si no hay disponibles.
            
        Thread-safety: Este método es seguro para uso concurrente.
        """
        if not self._enabled or not self._proxies:
            return None

        with self._lock:
            # Filtrar proxies que no están en la blacklist
            available = [
                p for p in self._proxies
                if p["_raw"] not in self._blacklist
            ]

            if not available:
                logger.warning(
                    "Todos los proxies están en blacklist. "
                    "Reseteando blacklist para reintentar."
                )
                self._blacklist.clear()
                self._failure_count.clear()
                available = self._proxies.copy()

            if not available:
                return None

            # Rotación round-robin
            self._current_index = self._current_index % len(available)
            proxy = available[self._current_index]
            self._current_index += 1

            # Retornar copia sin el campo interno _raw
            return {
                "http": proxy["http"],
                "https": proxy["https"]
            }

    def report_success(self, proxy: dict) -> None:
        """
        Reporta uso exitoso de un proxy. Resetea su contador de fallos.
        
        Args:
            proxy: Dict del proxy que fue exitoso.
        """
        if not proxy:
            return

        raw = proxy.get("http", "")
        with self._lock:
            if raw in self._failure_count:
                self._failure_count[raw] = 0
                logger.debug("Proxy exitoso, contador de fallos reseteado.")

    def report_failure(self, proxy: dict) -> None:
        """
        Reporta fallo de un proxy. Si alcanza el umbral, lo blacklistea.
        
        Args:
            proxy: Dict del proxy que falló.
        """
        if not proxy:
            return

        raw = proxy.get("http", "")
        with self._lock:
            self._failure_count[raw] = self._failure_count.get(raw, 0) + 1

            if self._failure_count[raw] >= self.MAX_FAILURES:
                self._blacklist.add(raw)
                logger.warning(
                    "Proxy blacklisteado después de %d fallos consecutivos.",
                    self.MAX_FAILURES
                )
            else:
                logger.debug(
                    "Fallo de proxy registrado (%d/%d).",
                    self._failure_count[raw], self.MAX_FAILURES
                )

    def get_stats(self) -> dict:
        """
        Retorna estadísticas del pool de proxies.
        
        Returns:
            Diccionario con métricas del gestor de proxies.
        """
        with self._lock:
            return {
                "enabled": self._enabled,
                "total_proxies": len(self._proxies),
                "blacklisted": len(self._blacklist),
                "available": len(self._proxies) - len(self._blacklist),
            }
