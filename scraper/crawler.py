# ============================================================================
# GeniusControle - Motor de Crawling para E-Commerce
# Módulo: crawler.py
# Descripción: Lógica de extracción de productos de sitios e-commerce.
#              Soporta dos modos: estático (BeautifulSoup) para HTML
#              renderizado en servidor, y dinámico (Selenium) para
#              contenido cargado con JavaScript/AJAX.
# ============================================================================

import re
import hashlib
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException
)

from config import ScraperConfig
from logger_config import setup_logger
from rate_limiter import RateLimiter
from proxy_manager import ProxyManager
from user_agent import UserAgentRotator
from robots_validator import RobotsValidator

logger = setup_logger("crawler")


class EcommerceCrawler:
    """
    Motor de crawling para sitios de e-commerce.
    
    Modos de operación:
    - ESTÁTICO (BeautifulSoup): Parseo rápido de HTML estático. Ideal para
      sitios que renderizan todo en el servidor (SSR).
    - DINÁMICO (Selenium): Renderizado completo con navegador headless.
      Necesario para sitios con contenido cargado por JavaScript.
    
    Medidas de seguridad:
    - Validación de robots.txt antes de cada petición.
    - Rate limiting con backoff exponencial.
    - Rotación de User-Agents y proxies.
    - Sanitización de datos extraídos (prevención de XSS).
    """

    def __init__(
        self,
        base_url: str,
        mode: str = "static",
        max_pages: int = ScraperConfig.DEFAULT_MAX_PAGES
    ):
        """
        Inicializa el crawler para un sitio de e-commerce.
        
        Args:
            base_url: URL raíz del sitio objetivo.
            mode: Modo de operación ('static' o 'dynamic').
            max_pages: Número máximo de páginas a recorrer.
        """
        self.base_url = base_url.rstrip("/")
        self.mode = mode.lower()
        self.max_pages = max_pages
        self._session: Optional[requests.Session] = None
        self._driver: Optional[webdriver.Remote] = None

        # Módulos de seguridad y evasión
        self.robots = RobotsValidator(base_url)
        self.rate_limiter: Optional[RateLimiter] = None
        self.proxy_manager = ProxyManager()
        self.ua_rotator = UserAgentRotator()

        # Estadísticas de ejecución
        self._stats = {
            "pages_crawled": 0,
            "products_found": 0,
            "errors": 0,
            "blocked_by_robots": 0,
        }

        logger.info(
            "EcommerceCrawler inicializado. URL: %s | Modo: %s | Páginas máx: %d",
            self.base_url, self.mode, self.max_pages
        )

    def initialize(self) -> bool:
        """
        Inicializa todos los componentes del crawler.
        
        Flujo:
        1. Cargar y validar robots.txt.
        2. Configurar rate limiter (con crawl-delay de robots.txt).
        3. Inicializar sesión HTTP o Selenium WebDriver.
        
        Returns:
            True si la inicialización fue exitosa.
        """
        # Paso 1: Validar robots.txt (cumplimiento ético)
        logger.info("=== FASE 1: Validación de robots.txt ===")
        self.robots.load()
        compliance = self.robots.get_compliance_report()
        logger.info("Reporte de cumplimiento: %s", str(compliance))

        # Paso 2: Configurar rate limiter
        logger.info("=== FASE 2: Configuración de Rate Limiter ===")
        crawl_delay = self.robots.get_crawl_delay()
        self.rate_limiter = RateLimiter(crawl_delay=crawl_delay)

        # Paso 3: Inicializar motor de scraping
        logger.info("=== FASE 3: Inicialización del motor (%s) ===", self.mode)
        if self.mode == "dynamic":
            return self._init_selenium()
        else:
            return self._init_requests_session()

    def _init_requests_session(self) -> bool:
        """
        Inicializa una sesión HTTP con requests para modo estático.
        
        Returns:
            True si la sesión fue creada correctamente.
        """
        try:
            self._session = requests.Session()
            self._session.headers.update(self.ua_rotator.get_headers())
            logger.info("Sesión HTTP (requests) inicializada.")
            return True
        except Exception as e:
            logger.error("Error al inicializar sesión HTTP: %s", str(e))
            return False

    def _init_selenium(self) -> bool:
        """
        Inicializa Selenium WebDriver remoto (Selenium Grid).
        
        Configuración de seguridad del navegador:
        - Modo headless (sin interfaz gráfica).
        - Deshabilitación de imágenes (optimización).
        - User-Agent personalizado.
        - Deshabilitación de WebRTC (previene leak de IP real).
        
        Returns:
            True si el WebDriver fue inicializado correctamente.
        """
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            # Seguridad: Prevenir leak de IP real mediante WebRTC
            chrome_options.add_argument("--disable-webrtc")
            # Optimización: Deshabilitar carga de imágenes
            chrome_options.add_argument("--blink-settings=imagesEnabled=false")
            # User-Agent personalizado
            ua = self.ua_rotator.get_random_user_agent()
            chrome_options.add_argument(f"--user-agent={ua}")

            # Conectar al Selenium Grid remoto (Docker)
            self._driver = webdriver.Remote(
                command_executor=ScraperConfig.SELENIUM_HUB_URL,
                options=chrome_options
            )
            self._driver.set_page_load_timeout(ScraperConfig.REQUEST_TIMEOUT)

            logger.info("Selenium WebDriver inicializado (remoto).")
            return True

        except WebDriverException as e:
            logger.error("Error al inicializar Selenium: %s", str(e))
            return False

    def crawl(self) -> list[dict]:
        """
        Ejecuta el proceso de crawling completo.
        
        Flujo:
        1. Recorrer páginas de lista de productos (PLP).
        2. Extraer productos de cada página.
        3. Navegar a la siguiente página.
        4. Repetir hasta max_pages o fin de paginación.
        
        Returns:
            Lista de diccionarios con los productos extraídos.
        """
        all_products = []
        current_url = self._get_first_page_url()

        for page_num in range(1, self.max_pages + 1):
            if not current_url:
                logger.info("No hay más páginas. Fin del crawling.")
                break

            # Validar contra robots.txt
            if not self.robots.can_fetch(current_url):
                self._stats["blocked_by_robots"] += 1
                logger.warning("Página bloqueada por robots.txt: %s", current_url)
                break

            logger.info("--- Crawling página %d/%d: %s ---", page_num, self.max_pages, current_url)

            # Aplicar rate limiting antes de la petición
            self.rate_limiter.wait()

            # Obtener HTML de la página
            html = self._fetch_page(current_url)
            if not html:
                self._stats["errors"] += 1
                logger.error("Error al obtener página %d. Continuando...", page_num)
                current_url = None
                continue

            self._stats["pages_crawled"] += 1

            # Extraer productos de la página
            products = self._extract_products(html, current_url)
            all_products.extend(products)
            self._stats["products_found"] += len(products)

            logger.info(
                "Página %d: %d productos extraídos (total acumulado: %d)",
                page_num, len(products), len(all_products)
            )

            # Obtener URL de la siguiente página
            current_url = self._get_next_page_url(html, current_url)

        logger.info(
            "=== Crawling completado. Total: %d productos de %d páginas ===",
            self._stats["products_found"], self._stats["pages_crawled"]
        )
        return all_products

    def _get_first_page_url(self) -> str:
        """
        Construye la URL de la primera página del catálogo.
        Para books.toscrape.com, el catálogo comienza en /catalogue/page-1.html
        
        Returns:
            URL de la primera página.
        """
        # Adaptación para books.toscrape.com
        if "books.toscrape.com" in self.base_url:
            return f"{self.base_url}/catalogue/page-1.html"
        return self.base_url

    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Obtiene el HTML de una página usando el modo configurado.
        
        Args:
            url: URL de la página a descargar.
        
        Returns:
            String con el HTML de la página, o None si hubo error.
        """
        for attempt in range(ScraperConfig.MAX_RETRIES):
            try:
                if self.mode == "dynamic":
                    return self._fetch_with_selenium(url)
                else:
                    return self._fetch_with_requests(url)

            except Exception as e:
                logger.warning(
                    "Intento %d/%d fallido para %s: %s",
                    attempt + 1, ScraperConfig.MAX_RETRIES, url, str(e)
                )
                if not self.rate_limiter.report_error():
                    logger.error("Máximo de reintentos alcanzado.")
                    return None
                # Esperar backoff antes de reintentar
                self.rate_limiter.wait()

        return None

    def _fetch_with_requests(self, url: str) -> Optional[str]:
        """
        Descarga una página usando requests (modo estático).
        
        Args:
            url: URL de la página.
        
        Returns:
            HTML de la página como string.
        """
        # Rotar User-Agent para cada petición
        headers = self.ua_rotator.get_headers()
        self._session.headers.update(headers)

        # Configurar proxy si está disponible
        proxy = self.proxy_manager.get_proxy()
        proxies = proxy if proxy else None

        response = self._session.get(
            url,
            timeout=ScraperConfig.REQUEST_TIMEOUT,
            proxies=proxies
        )

        # Manejar códigos de error específicos
        if response.status_code == 429:
            self.rate_limiter.report_error(status_code=429)
            return None
        elif response.status_code == 403:
            logger.warning("HTTP 403 Forbidden — Posible bloqueo anti-bot.")
            self.rate_limiter.report_error(status_code=403)
            return None

        response.raise_for_status()
        self.rate_limiter.report_success()

        if proxy:
            self.proxy_manager.report_success(proxy)

        return response.text

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """
        Descarga una página usando Selenium (modo dinámico).
        Espera a que el contenido dinámico se cargue completamente.
        
        Args:
            url: URL de la página.
        
        Returns:
            HTML renderizado de la página como string.
        """
        try:
            self._driver.get(url)

            # Esperar a que el body esté presente (indica carga completa)
            WebDriverWait(self._driver, ScraperConfig.REQUEST_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Espera adicional para contenido lazy-loaded
            WebDriverWait(self._driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            self.rate_limiter.report_success()
            return self._driver.page_source

        except TimeoutException:
            logger.warning("Timeout al cargar página con Selenium: %s", url)
            return None

    def _extract_products(self, html: str, page_url: str) -> list[dict]:
        """
        Extrae productos del HTML de una página de lista (PLP).
        
        Adaptado para books.toscrape.com. Para otros sitios, los
        selectores CSS deben ser ajustados.
        
        Args:
            html: HTML de la página.
            page_url: URL de la página (para resolver URLs relativas).
        
        Returns:
            Lista de diccionarios con los datos de los productos.
        """
        soup = BeautifulSoup(html, "html.parser")
        products = []

        # Selectores para books.toscrape.com
        product_cards = soup.select("article.product_pod")

        if not product_cards:
            logger.warning("No se encontraron productos en la página.")
            return products

        for card in product_cards:
            try:
                product = self._parse_product_card(card, page_url)
                if product:
                    # Sanitización de seguridad
                    product = self._sanitize_product(product)
                    products.append(product)
            except Exception as e:
                logger.warning("Error al parsear producto: %s", str(e))
                self._stats["errors"] += 1
                continue

        return products

    def _parse_product_card(self, card, page_url: str) -> Optional[dict]:
        """
        Parsea un card de producto individual (books.toscrape.com).
        
        Args:
            card: Elemento BeautifulSoup del card de producto.
            page_url: URL de la página contenedora.
        
        Returns:
            Diccionario con datos del producto, o None si no es válido.
        """
        # Nombre del producto
        title_tag = card.select_one("h3 > a")
        if not title_tag:
            return None
        name = title_tag.get("title", title_tag.get_text(strip=True))

        # URL del producto
        product_url = title_tag.get("href", "")
        product_url = urljoin(page_url, product_url)

        # Precio
        price_tag = card.select_one("p.price_color")
        price_text = price_tag.get_text(strip=True) if price_tag else "0"
        price = self._parse_price(price_text)

        # Imagen
        img_tag = card.select_one("img.thumbnail")
        image_url = ""
        if img_tag:
            image_url = urljoin(self.base_url, img_tag.get("src", ""))

        # Disponibilidad
        stock_tag = card.select_one("p.instock, p.availability")
        in_stock = bool(stock_tag and "in stock" in stock_tag.get_text(strip=True).lower())

        # Rating (estrelas)
        rating_tag = card.select_one("p.star-rating")
        rating = self._parse_rating(rating_tag)

        # Generar SKU único basado en la URL del producto
        sku = self._generate_sku(product_url)

        # Categoría (extraída de la URL o breadcrumb)
        category = self._extract_category(page_url)

        return {
            "sku": sku,
            "name": name,
            "price": price,
            "url": product_url,
            "image_url": image_url,
            "category": category,
            "in_stock": in_stock,
            "rating": rating,
            "source_url": page_url,
        }

    @staticmethod
    def _parse_price(price_text: str) -> float:
        """
        Convierte un string de precio a float.
        Maneja formatos como: £51.77, $19.99, €15.50, 1.234,56
        
        Args:
            price_text: String con el precio.
        
        Returns:
            Precio como float.
        """
        # Eliminar símbolos de moneda y espacios
        cleaned = re.sub(r'[^\d.,]', '', price_text)
        # Manejar formato europeo (1.234,56 -> 1234.56)
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rindex(',') > cleaned.rindex('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Solo coma: podría ser decimal o separador de miles
            parts = cleaned.split(',')
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')

        try:
            return round(float(cleaned), 2)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_rating(rating_tag) -> int:
        """
        Extrae el rating numérico de un elemento de estrellas.
        
        Args:
            rating_tag: Elemento BeautifulSoup con la clase star-rating.
        
        Returns:
            Rating numérico (1-5), o 0 si no se puede extraer.
        """
        if not rating_tag:
            return 0

        rating_map = {
            "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5
        }
        classes = rating_tag.get("class", [])
        for cls in classes:
            if cls in rating_map:
                return rating_map[cls]
        return 0

    @staticmethod
    def _generate_sku(product_url: str) -> str:
        """
        Genera un SKU único basado en la URL del producto.
        Usa los primeros 12 caracteres del hash MD5 de la URL.
        
        Args:
            product_url: URL del producto.
        
        Returns:
            SKU único como string.
        """
        url_hash = hashlib.md5(product_url.encode()).hexdigest()[:12].upper()
        return f"GC-{url_hash}"

    @staticmethod
    def _extract_category(page_url: str) -> str:
        """
        Extrae la categoría del producto desde la URL.
        
        Args:
            page_url: URL de la página de lista.
        
        Returns:
            Nombre de la categoría, o 'General' por defecto.
        """
        parsed = urlparse(page_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if "category" in parsed.path:
            for i, part in enumerate(path_parts):
                if part == "category" and i + 1 < len(path_parts):
                    return path_parts[i + 1].replace("-", " ").title()
        return "General"

    @staticmethod
    def _sanitize_product(product: dict) -> dict:
        """
        Sanitiza los datos de un producto para prevenir XSS y
        otros ataques de inyección en los datos almacenados.
        
        Args:
            product: Diccionario del producto a sanitizar.
        
        Returns:
            Diccionario sanitizado.
        """
        # Campos de texto a sanitizar
        text_fields = ["name", "category", "sku"]

        for field in text_fields:
            if field in product and isinstance(product[field], str):
                # Eliminar tags HTML
                product[field] = re.sub(r'<[^>]+>', '', product[field])
                # Eliminar caracteres de control
                product[field] = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', product[field])
                # Escapar caracteres potencialmente peligrosos
                product[field] = (
                    product[field]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#x27;")
                )

        # Validar URLs
        url_fields = ["url", "image_url", "source_url"]
        for field in url_fields:
            if field in product and isinstance(product[field], str):
                parsed = urlparse(product[field])
                if parsed.scheme not in ("http", "https", ""):
                    product[field] = ""

        return product

    def _get_next_page_url(self, html: str, current_url: str) -> Optional[str]:
        """
        Encuentra la URL de la siguiente página de paginación.
        
        Args:
            html: HTML de la página actual.
            current_url: URL de la página actual.
        
        Returns:
            URL de la siguiente página, o None si no existe.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Buscar botón/enlace "next" en la paginación
        next_link = soup.select_one("li.next > a")
        if next_link:
            href = next_link.get("href", "")
            if href:
                next_url = urljoin(current_url, href)
                logger.debug("Siguiente página encontrada: %s", next_url)
                return next_url

        logger.info("No se encontró enlace a la siguiente página.")
        return None

    def get_stats(self) -> dict:
        """
        Retorna estadísticas completas del crawling.
        
        Returns:
            Diccionario con métricas de ejecución.
        """
        stats = self._stats.copy()
        stats["rate_limiter"] = self.rate_limiter.get_stats() if self.rate_limiter else {}
        stats["proxy_manager"] = self.proxy_manager.get_stats()
        stats["robots_compliance"] = self.robots.get_compliance_report()
        return stats

    def close(self) -> None:
        """Libera todos los recursos del crawler."""
        if self._session:
            self._session.close()
            logger.debug("Sesión HTTP cerrada.")

        if self._driver:
            try:
                self._driver.quit()
                logger.debug("Selenium WebDriver cerrado.")
            except Exception as e:
                logger.warning("Error al cerrar Selenium: %s", str(e))

        logger.info("Crawler cerrado. Recursos liberados.")
