# ============================================================================
# GeniusControle - Pool de User-Agents
# Módulo: user_agent.py
# Descripción: Rotación aleatoria de User-Agents realistas para evitar
#              detección y bloqueo por fingerprinting de headers HTTP.
# ============================================================================

import random
from typing import Optional

from logger_config import setup_logger

logger = setup_logger("user_agent")


class UserAgentRotator:
    """
    Rotador de User-Agents para evasión de detección.
    
    Estrategia de seguridad:
    1. Pool de 25+ User-Agents de navegadores reales y actualizados.
    2. Headers HTTP completos y consistentes por tipo de navegador.
    3. Rotación aleatoria por cada petición.
    4. Previene fingerprinting por User-Agent estático.
    """

    # Pool de User-Agents realistas (navegadores populares, versiones recientes)
    USER_AGENTS = [
        # --- Google Chrome (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",

        # --- Google Chrome (macOS) ---
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

        # --- Google Chrome (Linux) ---
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

        # --- Mozilla Firefox (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",

        # --- Mozilla Firefox (macOS) ---
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",

        # --- Mozilla Firefox (Linux) ---
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",

        # --- Apple Safari (macOS) ---
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",

        # --- Microsoft Edge (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",

        # --- Microsoft Edge (macOS) ---
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",

        # --- Opera (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",

        # --- Brave (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Brave/1.61",

        # --- Vivaldi (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.5",
    ]

    # Mapeo de User-Agent a tipo de navegador para headers consistentes
    _BROWSER_TYPES = {
        "Chrome": "chrome",
        "Firefox": "firefox",
        "Safari": "safari",
        "Edg": "edge",
        "OPR": "opera",
        "Brave": "brave",
        "Vivaldi": "vivaldi",
    }

    def __init__(self):
        """Inicializa el rotador de User-Agents."""
        self._last_ua: Optional[str] = None
        logger.info(
            "UserAgentRotator inicializado con %d User-Agents.",
            len(self.USER_AGENTS)
        )

    def get_random_user_agent(self) -> str:
        """
        Selecciona un User-Agent aleatorio del pool.
        Evita repetir el mismo User-Agent consecutivamente.
        
        Returns:
            String del User-Agent seleccionado.
        """
        available = [ua for ua in self.USER_AGENTS if ua != self._last_ua]
        selected = random.choice(available)
        self._last_ua = selected
        return selected

    def _detect_browser_type(self, user_agent: str) -> str:
        """
        Detecta el tipo de navegador a partir del User-Agent.
        
        Args:
            user_agent: String del User-Agent.
        
        Returns:
            Identificador del tipo de navegador.
        """
        for identifier, browser_type in self._BROWSER_TYPES.items():
            if identifier in user_agent:
                return browser_type
        return "chrome"  # Default

    def get_headers(self, user_agent: Optional[str] = None) -> dict:
        """
        Genera un conjunto completo de headers HTTP consistentes
        con el User-Agent seleccionado.
        
        Los headers son diseñados para simular un navegador real y evitar
        detección por análisis de headers incompletos o inconsistentes.
        
        Args:
            user_agent: User-Agent específico, o None para aleatorio.
        
        Returns:
            Dict con headers HTTP completos y realistas.
        """
        if user_agent is None:
            user_agent = self.get_random_user_agent()

        browser_type = self._detect_browser_type(user_agent)

        # Headers base comunes a todos los navegadores
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

        # Headers específicos por navegador para mayor realismo
        if browser_type == "chrome":
            headers.update({
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        elif browser_type == "firefox":
            headers.update({
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "DNT": "1",
            })
        elif browser_type == "safari":
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        elif browser_type == "edge":
            headers.update({
                "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })

        logger.debug("Headers generados para navegador: %s", browser_type)
        return headers
