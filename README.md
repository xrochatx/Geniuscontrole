# 🛡️ GeniusControle — Sistema de Web Scraping Seguro para E-Commerce

[![Java](https://img.shields.io/badge/Java-17-orange?logo=openjdk)](https://openjdk.org/)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.2-green?logo=springboot)](https://spring.io/projects/spring-boot)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green?logo=mongodb)](https://www.mongodb.com/)
[![Redis](https://img.shields.io/badge/Redis-7.2-red?logo=redis)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://docker.com)

> **Proyecto de Titulación** — Ingeniería Informática  
> **Autor**: Juan Rochat  
> **Objetivo**: Demostrar un flujo completo de extracción ética, almacenamiento seguro y API de consumo para datos de e-commerce.

---

## 📋 Tabla de Contenidos

1. [Arquitectura del Sistema](#-arquitectura-del-sistema)
2. [Requisitos Previos](#-requisitos-previos)
3. [Paso a Paso — Instalación y Ejecución](#-paso-a-paso--instalación-y-ejecución)
4. [Endpoints de la API](#-endpoints-de-la-api)
5. [Pruebas con Postman](#-pruebas-con-postman)
6. [Medidas de Ciberseguridad](#-medidas-de-ciberseguridad)
7. [Estructura del Proyecto](#-estructura-del-proyecto)
8. [Análisis de Calidad (SonarQube)](#-análisis-de-calidad-sonarqube)

---

## 🏗️ Arquitectura del Sistema

```
┌──────────────────┐     HTTP/REST     ┌──────────────────────────────┐
│   Postman/cURL   │◄──────────────────►│   Spring Boot API Gateway   │
│   (Cliente)      │                    │   - ProductController       │
└──────────────────┘                    │   - ScraperController       │
                                        │   - SecurityConfig (HSTS,   │
                                        │     CSP, X-Frame-Options)   │
                                        └──────┬───────────┬──────────┘
                                               │           │
                                    Subprocess │           │ Queries
                                               │           │
                              ┌────────────────▼──┐   ┌───▼──────────┐
                              │  Python Scraper   │   │   MongoDB    │
                              │  - BeautifulSoup  │──►│   (Products) │
                              │  - Selenium       │   └──────────────┘
                              │  - robots.txt ✓   │
                              │  - Rate Limiting  │   ┌──────────────┐
                              │  - Proxy Rotation │   │    Redis     │
                              └───────────────────┘   │   (Cache)    │
                                                       └──────────────┘
```

**Stack Tecnológico:**
| Capa | Tecnología | Propósito |
|------|-----------|-----------|
| API Gateway | Java 17 + Spring Boot 3.2 | Endpoints REST, seguridad HTTP |
| Motor de Scraping | Python 3.11 + BeautifulSoup + Selenium | Extracción de datos |
| Base de Datos | MongoDB 7.0 | Almacenamiento de catálogos JSON |
| Caché | Redis 7.2 | Caché de consultas, rate limiting |
| Contenedores | Docker Compose | Infraestructura local |
| Calidad | SonarQube + JaCoCo | Análisis estático de código |

---

## 📦 Requisitos Previos

Asegúrate de tener instalados los siguientes componentes:

| Software | Versión Mínima | Verificar |
|----------|---------------|-----------|
| **Java JDK** | 17+ | `java -version` |
| **Maven** | 3.8+ | `mvn -version` |
| **Python** | 3.11+ | `python --version` |
| **Docker** | 20.10+ | `docker --version` |
| **Docker Compose** | 2.0+ | `docker compose version` |

---

## 🚀 Paso a Paso — Instalación y Ejecución

### Paso 1: Clonar o acceder al proyecto

```bash
cd d:\xrochatx\Proyectos\Geniuscontrole
```

### Paso 2: Levantar la infraestructura (MongoDB + Redis + Selenium)

```bash
# Levantar los contenedores en segundo plano
docker compose up -d

# Verificar que los servicios estén saludables
docker compose ps
```

**Servicios levantados:**
| Servicio | Puerto | Credenciales |
|----------|--------|-------------|
| MongoDB | `27017` | user: `geniusadmin` / pass: `G3n1u5S3cur3P@ss` |
| Redis | `6379` | pass: `R3d1sS3cur3P@ss` |
| Selenium | `4444` (WebDriver), `7900` (noVNC) | — |

> **Tip**: Puedes ver el navegador Selenium en acción accediendo a `http://localhost:7900` (password: `secret`).

### Paso 3: Instalar dependencias del Scraper (Python)

```bash
# Crear entorno virtual (recomendado)
cd scraper
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 4: Probar el Scraper directamente (opcional)

```bash
# Ejecutar scraping estático de 2 páginas
python main.py --url https://books.toscrape.com --mode static --pages 2

# Ejecutar scraping dinámico (requiere Selenium activo)
python main.py --url https://books.toscrape.com --mode dynamic --pages 1
```

**Salida esperada:**
```json
{
  "status": "COMPLETED",
  "target_url": "https://books.toscrape.com",
  "products_extracted": 40,
  "products_stored": 40,
  "duration_seconds": 15.32
}
```

### Paso 5: Compilar y ejecutar el Backend (Spring Boot)

```bash
cd ../backend

# Compilar el proyecto
mvn clean install -DskipTests

# Ejecutar la aplicación
mvn spring-boot:run
```

> La API estará disponible en `http://localhost:8080`

### Paso 6: Probar la API

```bash
# Health Check
curl http://localhost:8080/actuator/health

# Iniciar scraping desde la API
curl -X POST http://localhost:8080/api/v1/scraper/start \
  -H "Content-Type: application/json" \
  -d '{"targetUrl": "https://books.toscrape.com", "mode": "static", "maxPages": 3}'

# Consultar productos extraídos
curl http://localhost:8080/api/v1/products?page=0&size=10

# Buscar productos por nombre
curl "http://localhost:8080/api/v1/products/search?q=the"

# Estadísticas del catálogo
curl http://localhost:8080/api/v1/products/stats
```

---

## 📡 Endpoints de la API

### Scraper

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/scraper/start` | Inicia un proceso de scraping (asíncrono) |
| `GET` | `/api/v1/scraper/status/{taskId}` | Consulta estado de una tarea |
| `GET` | `/api/v1/scraper/tasks` | Lista tareas recientes |

**Body para POST /start:**
```json
{
  "targetUrl": "https://books.toscrape.com",
  "mode": "static",
  "maxPages": 5
}
```

### Productos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/products` | Lista productos (paginado) |
| `GET` | `/api/v1/products/{sku}` | Detalle por SKU |
| `GET` | `/api/v1/products/search?q=` | Búsqueda por nombre |
| `GET` | `/api/v1/products/category/{cat}` | Filtrar por categoría |
| `GET` | `/api/v1/products/price-range?minPrice=&maxPrice=` | Filtrar por precio |
| `GET` | `/api/v1/products/stats` | Estadísticas del catálogo |

**Parámetros de paginación** (aplica a todos los GET con listas):
- `page`: Número de página (default: 0)
- `size`: Tamaño de página (default: 20, max: 100)
- `sortBy`: Campo de ordenamiento (default: "name")
- `direction`: Dirección (asc/desc)

### Health Check

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/actuator/health` | Estado de salud del servicio |

---

## 🧪 Pruebas con Postman

1. Abre Postman e importa la colección:
   ```
   File → Import → postman/GeniusControle.postman_collection.json
   ```

2. **Flujo de prueba recomendado:**
   1. **Start Scraping** → Obtiene `taskId` automáticamente.
   2. **Check Status** → Espera hasta estado `COMPLETED`.
   3. **Get Products** → Verifica los datos extraídos.
   4. **Search Products** → Prueba búsqueda por nombre.
   5. **Get Stats** → Verifica estadísticas del catálogo.
   6. **Verify Security Headers** → Valida headers de seguridad.

3. Cada request incluye **tests automatizados** que verifican:
   - Códigos de respuesta HTTP correctos.
   - Estructura de la respuesta JSON.
   - Headers de seguridad presentes.
   - Paginación funcional.

---

## 🔒 Medidas de Ciberseguridad

| # | Capa | Medida | Implementación |
|---|------|--------|---------------|
| 1 | **Transporte** | Headers HTTP seguros | HSTS, CSP, X-Frame-Options, X-Content-Type-Options |
| 2 | **Transporte** | CORS restrictivo | Solo orígenes autorizados |
| 3 | **Aplicación** | Validación de input | Bean Validation en DTOs + sanitización regex |
| 4 | **Aplicación** | Sanitización de comandos | Limpieza de parámetros antes de subprocess |
| 5 | **Datos** | Hash de integridad | SHA-256 por cada producto almacenado |
| 6 | **Datos** | Sanitización XSS | Limpieza de HTML/scripts en datos extraídos |
| 7 | **Ética** | Cumplimiento robots.txt | Validación obligatoria antes del scraping |
| 8 | **Ética** | Rate Limiting | Token Bucket + backoff exponencial |
| 9 | **Evasión** | Rotación de identidad | Pool de User-Agents + proxies rotativos |
| 10 | **Infraestructura** | Autenticación DB | MongoDB y Redis con contraseñas |
| 11 | **Logging** | Logs seguros | Sanitización de datos sensibles (IPs, passwords) |
| 12 | **API** | Paginación limitada | Máx. 100 resultados por página |

---

## 📁 Estructura del Proyecto

```
GeniusControle/
├── backend/                              # API Gateway (Spring Boot)
│   ├── pom.xml                           # Dependencias Maven
│   └── src/main/java/com/geniuscontrole/
│       ├── GeniusControleApplication.java
│       ├── config/
│       │   ├── SecurityConfig.java       # CORS, HSTS, CSP
│       │   ├── RedisConfig.java          # Caché Redis
│       │   └── MongoConfig.java          # MongoDB
│       ├── controller/
│       │   ├── ProductController.java    # GET /api/v1/products
│       │   └── ScraperController.java    # POST /api/v1/scraper/start
│       ├── model/
│       │   ├── Product.java              # Entidad MongoDB
│       │   ├── ScraperTask.java          # Estado del scraping
│       │   └── dto/
│       │       ├── ScraperRequest.java   # DTO de entrada
│       │       └── ScraperResponse.java  # DTO de salida
│       ├── repository/
│       │   ├── ProductRepository.java    # Spring Data MongoDB
│       │   └── ScraperTaskRepository.java
│       └── service/
│           ├── ProductService.java       # Consultas + caché
│           └── ScraperService.java       # Ejecución del scraper
│
├── scraper/                              # Motor de Scraping (Python)
│   ├── requirements.txt                  # Dependencias pip
│   ├── main.py                           # Orquestador principal
│   ├── config.py                         # Configuración centralizada
│   ├── crawler.py                        # BeautifulSoup + Selenium
│   ├── robots_validator.py               # Cumplimiento robots.txt
│   ├── rate_limiter.py                   # Control de tasa (Token Bucket)
│   ├── proxy_manager.py                  # Rotación de proxies
│   ├── user_agent.py                     # Pool de User-Agents
│   ├── storage.py                        # Persistencia MongoDB
│   └── logger_config.py                  # Logging seguro
│
├── postman/
│   └── GeniusControle.postman_collection.json
│
├── docker-compose.yml                    # MongoDB + Redis + Selenium
├── sonar-project.properties              # Configuración SonarQube
└── README.md                             # Este archivo
```

---

## 📊 Análisis de Calidad (SonarQube)

### Configuración incluida

El archivo `sonar-project.properties` configura el análisis para ambos módulos:

- **Backend (Java)**: Análisis con JaCoCo para cobertura de código.
- **Scraper (Python)**: Análisis con pytest-cov.

### Ejecutar análisis (requiere SonarQube server)

```bash
# Backend - Generar reporte de cobertura
cd backend
mvn clean verify

# Ejecutar análisis SonarQube (requiere servidor SonarQube activo)
mvn sonar:sonar -Dsonar.host.url=http://localhost:9000
```

---

## ⚠️ Notas Importantes

1. **Uso Ético**: Este sistema está diseñado como **prueba de concepto académica**. Siempre respeta el `robots.txt` y los términos de servicio de los sitios web.

2. **Sitio de prueba**: El sitio `https://books.toscrape.com` está diseñado específicamente para practicar web scraping de forma legal.

3. **Proxies**: El sistema soporta rotación de proxies, pero viene deshabilitado por defecto. Para habilitarlo, configure `USE_PROXIES=true` y proporcione un archivo `proxies.txt`.

4. **Producción**: Para uso en producción, asegúrese de:
   - Cambiar todas las contraseñas por defecto.
   - Habilitar autenticación en la API (JWT/OAuth2).
   - Configurar HTTPS con certificados TLS.
   - Limitar los orígenes CORS a dominios autorizados.

---

## 📄 Licencia

Proyecto académico para Tesis de Ingeniería Informática — Universidad.  
**Autor**: Juan Rochat | **Año**: 2024
