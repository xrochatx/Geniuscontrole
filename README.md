# GeniusControle

GeniusControle es un sistema de Web Scraping seguro para e-commerce, diseñado como prueba de concepto para una tesis de Ingeniería Informática. Su objetivo principal es demostrar un flujo completo de extracción ética, almacenamiento seguro y una API de consumo, aplicando estrictos controles de ciberseguridad.

## Arquitectura general

El proyecto se divide en dos módulos principales integrados mediante Docker Compose:

### 1) Backend API (Java 17 + Spring Boot 3.2)
- Actúa como API Gateway.
- Utiliza MongoDB para el almacenamiento de catálogos de productos.
- Utiliza Redis para caché de consultas y rate limiting.
- Incluye medidas de seguridad clave:
  - CORS restrictivo.
  - Headers de seguridad HTTP (HSTS, CSP, X-Frame-Options).
  - Validación de entradas mediante DTOs.
- Ejecuta el scraper Python de forma asíncrona con `ProcessBuilder` para no bloquear la API.

### 2) Motor de Scraping (Python 3.11)
- Construido con BeautifulSoup (`html.parser`) para contenido estático, priorizando portabilidad y evitando dependencias de compilación compleja.
- Usa Selenium WebDriver para contenido dinámico.
- Persiste en MongoDB con cálculo de hash SHA-256 para integridad de datos.
- Incluye medidas de ciberseguridad y cumplimiento ético:
  - Validación obligatoria de `robots.txt`.
  - Rate Limiting usando Token Bucket con backoff exponencial.
  - Rotación aleatoria de User-Agents y Proxies.
  - Sanitización de datos extraídos para prevenir XSS.

## Reglas para sugerencias de código y Pull Requests

- Priorizar siempre la ciberseguridad y el rendimiento.
- En Java, respetar prácticas de Spring Boot 3 y usar Lombok para reducir boilerplate.
- En Python, mantener manejo robusto de excepciones, logging estructurado y tipos estrictos (`typing`).
- Nunca eliminar la validación de `robots.txt` ni los delays del rate limiter.
- Si se sugieren nuevas dependencias de parsing HTML, priorizar opciones de instalación simple; por defecto, usar `html.parser` en BeautifulSoup y justificar explícitamente alternativas con compilación en C (como `lxml`).
