#!/usr/bin/env python3
# ============================================================================
# GeniusControle - Orquestador Principal del Scraper
# Módulo: main.py
# Descripción: Punto de entrada del motor de scraping. Orquesta el flujo
#              completo: validación ética → configuración → crawling →
#              almacenamiento → reporte.
# ============================================================================

import argparse
import json
import signal
import sys
import time
from datetime import datetime, timezone

from config import ScraperConfig
from logger_config import setup_logger
from crawler import EcommerceCrawler
from storage import MongoStorage

logger = setup_logger("main")

# Flag global para shutdown graceful
_shutdown_requested = False


def signal_handler(signum, frame):
    """
    Manejador de señales para shutdown graceful.
    Captura SIGINT (Ctrl+C) y SIGTERM para cerrar recursos limpiamente.
    """
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning(
        "Señal de terminación recibida (%s). Finalizando de forma segura...",
        signal.Signals(signum).name
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parsea argumentos de línea de comandos.
    
    Argumentos disponibles:
        --url:    URL objetivo del sitio e-commerce.
        --mode:   Modo de scraping (static/dynamic).
        --pages:  Número máximo de páginas a recorrer.
        --output: Formato de salida del reporte (json/text).
    
    Returns:
        Namespace con los argumentos parseados.
    """
    parser = argparse.ArgumentParser(
        description=(
            "GeniusControle - Motor de Web Scraping Seguro para E-Commerce. "
            "Proyecto de Titulación en Ingeniería Informática."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos de uso:\n"
            "  python main.py --url https://books.toscrape.com --mode static --pages 3\n"
            "  python main.py --url https://example.com --mode dynamic --pages 5\n"
            "  python main.py  (usa configuración por defecto)\n"
        )
    )

    parser.add_argument(
        "--url",
        type=str,
        default=ScraperConfig.DEFAULT_TARGET_URL,
        help=f"URL objetivo del sitio e-commerce (default: {ScraperConfig.DEFAULT_TARGET_URL})"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["static", "dynamic"],
        default="static",
        help="Modo de scraping: 'static' (BeautifulSoup) o 'dynamic' (Selenium). Default: static"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=ScraperConfig.DEFAULT_MAX_PAGES,
        help=f"Número máximo de páginas a recorrer (default: {ScraperConfig.DEFAULT_MAX_PAGES})"
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="Formato de salida del reporte (default: json)"
    )

    return parser.parse_args()


def run_scraper(url: str, mode: str, max_pages: int) -> dict:
    """
    Ejecuta el flujo completo de scraping.
    
    Flujo de ejecución:
    1. Inicializar crawler (validar robots.txt, rate limiter, etc.)
    2. Conectar a MongoDB
    3. Ejecutar crawling
    4. Almacenar productos en MongoDB
    5. Generar reporte de ejecución
    
    Args:
        url: URL objetivo del sitio e-commerce.
        mode: Modo de scraping ('static' o 'dynamic').
        max_pages: Número máximo de páginas.
    
    Returns:
        Diccionario con el reporte de ejecución.
    """
    start_time = time.time()
    report = {
        "status": "STARTED",
        "target_url": url,
        "mode": mode,
        "max_pages": max_pages,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "products_extracted": 0,
        "products_stored": 0,
        "errors": 0,
    }

    crawler = None
    storage = None

    try:
        # =================================================================
        # FASE 1: Inicialización del Crawler
        # =================================================================
        logger.info("=" * 70)
        logger.info("  GeniusControle - Motor de Web Scraping Seguro")
        logger.info("  Objetivo: %s", url)
        logger.info("  Modo: %s | Páginas: %d", mode, max_pages)
        logger.info("=" * 70)

        crawler = EcommerceCrawler(
            base_url=url,
            mode=mode,
            max_pages=max_pages
        )

        if not crawler.initialize():
            report["status"] = "FAILED"
            report["error_message"] = "Error al inicializar el crawler."
            logger.error("Fallo en la inicialización del crawler.")
            return report

        # =================================================================
        # FASE 2: Conexión a MongoDB
        # =================================================================
        logger.info("=== FASE 4: Conexión a MongoDB ===")
        storage = MongoStorage()
        storage.connect()
        logger.info("MongoDB conectado. Productos existentes: %d", storage.get_product_count())

        # =================================================================
        # FASE 3: Ejecución del Crawling
        # =================================================================
        logger.info("=== FASE 5: Ejecutando Crawling ===")
        products = crawler.crawl()

        if _shutdown_requested:
            report["status"] = "INTERRUPTED"
            logger.warning("Scraping interrumpido por el usuario.")
        else:
            report["status"] = "COMPLETED"

        report["products_extracted"] = len(products)

        # =================================================================
        # FASE 4: Almacenamiento en MongoDB
        # =================================================================
        if products:
            logger.info("=== FASE 6: Almacenamiento en MongoDB ===")
            storage_stats = storage.save_products_bulk(products)
            report["products_stored"] = storage_stats["inserted"]
            report["storage_errors"] = storage_stats["errors"]
            logger.info(
                "Almacenamiento completado: %d guardados, %d errores",
                storage_stats["inserted"], storage_stats["errors"]
            )
        else:
            logger.warning("No se extrajeron productos para almacenar.")

        # Agregar estadísticas del crawler al reporte
        report["crawler_stats"] = crawler.get_stats()
        report["storage_stats"] = storage.get_stats()

    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
        logger.warning("Scraping interrumpido por el usuario (Ctrl+C).")

    except Exception as e:
        report["status"] = "FAILED"
        report["error_message"] = str(e)
        logger.error("Error fatal durante el scraping: %s", str(e), exc_info=True)

    finally:
        # Calcular duración total
        elapsed = time.time() - start_time
        report["duration_seconds"] = round(elapsed, 2)
        report["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Liberar recursos
        if crawler:
            crawler.close()
        if storage:
            storage.close()

        logger.info("Duración total: %.2f segundos", elapsed)

    return report


def main():
    """
    Punto de entrada principal del scraper.
    Parsea argumentos, registra señales y ejecuta el flujo completo.
    """
    # Registrar handler de señales para shutdown graceful
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parsear argumentos CLI
    args = parse_arguments()

    # Ejecutar scraping
    report = run_scraper(
        url=args.url,
        mode=args.mode,
        max_pages=args.pages
    )

    # Generar reporte final
    logger.info("=" * 70)
    logger.info("  REPORTE FINAL DE EJECUCIÓN")
    logger.info("=" * 70)

    if args.output_format == "json":
        report_json = json.dumps(report, indent=2, default=str)
        print(report_json)
    else:
        print(f"\n{'='*50}")
        print(f"  Estado: {report['status']}")
        print(f"  URL objetivo: {report['target_url']}")
        print(f"  Modo: {report['mode']}")
        print(f"  Productos extraídos: {report['products_extracted']}")
        print(f"  Productos almacenados: {report.get('products_stored', 0)}")
        print(f"  Duración: {report.get('duration_seconds', 0):.2f} seg")
        print(f"{'='*50}\n")

    # Código de salida basado en el estado
    if report["status"] == "COMPLETED":
        sys.exit(0)
    elif report["status"] == "INTERRUPTED":
        sys.exit(130)  # Convención para SIGINT
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
