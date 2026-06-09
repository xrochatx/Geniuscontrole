# ============================================================================
# GeniusControle - Módulo de Persistencia MongoDB
# Módulo: storage.py
# Descripción: Capa de acceso a datos para almacenar y consultar productos
#              extraídos en MongoDB. Incluye hash de integridad SHA-256
#              para cada registro y operaciones upsert por SKU.
# ============================================================================

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

from config import ScraperConfig
from logger_config import setup_logger

logger = setup_logger("storage")


class MongoStorage:
    """
    Capa de persistencia segura en MongoDB.
    
    Medidas de seguridad implementadas:
    1. Conexión autenticada a MongoDB.
    2. Hash SHA-256 de integridad para cada producto almacenado.
    3. Upsert por SKU para evitar duplicados.
    4. Índices automáticos para optimizar consultas.
    5. Validación de datos antes de la inserción.
    """

    def __init__(self):
        """
        Inicializa la conexión a MongoDB con autenticación.
        
        Raises:
            ConnectionFailure: Si no se puede conectar a MongoDB.
        """
        self._client: Optional[MongoClient] = None
        self._db = None
        self._collection = None

    def connect(self) -> bool:
        """
        Establece conexión autenticada a MongoDB y configura índices.
        
        Returns:
            True si la conexión fue exitosa.
            
        Seguridad: La conexión usa URI con credenciales desde config.
        """
        try:
            mongo_uri = ScraperConfig.get_mongo_uri()
            logger.info("Conectando a MongoDB...")

            self._client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                # Seguridad: limitar tamaño del pool de conexiones
                maxPoolSize=10,
                minPoolSize=1
            )

            # Verificar conexión con ping
            self._client.admin.command("ping")

            self._db = self._client[ScraperConfig.MONGO_DATABASE]
            self._collection = self._db[ScraperConfig.MONGO_COLLECTION]

            # Crear índices para optimizar consultas
            self._create_indexes()

            logger.info(
                "Conexión a MongoDB establecida. DB: %s, Collection: %s",
                ScraperConfig.MONGO_DATABASE, ScraperConfig.MONGO_COLLECTION
            )
            return True

        except ConnectionFailure as e:
            logger.error("Error de conexión a MongoDB: %s", str(e))
            raise
        except OperationFailure as e:
            logger.error("Error de autenticación en MongoDB: %s", str(e))
            raise

    def _create_indexes(self) -> None:
        """
        Crea índices en MongoDB para optimizar las consultas frecuentes.
        
        Índices:
        - sku (único): Para búsquedas y upserts por SKU.
        - name (texto): Para búsquedas full-text por nombre.
        - category: Para filtrado por categoría.
        - scraped_at: Para ordenamiento cronológico.
        """
        try:
            self._collection.create_index(
                [("sku", ASCENDING)],
                unique=True,
                name="idx_sku_unique"
            )
            self._collection.create_index(
                [("name", "text")],
                name="idx_name_text"
            )
            self._collection.create_index(
                [("category", ASCENDING)],
                name="idx_category"
            )
            self._collection.create_index(
                [("scraped_at", ASCENDING)],
                name="idx_scraped_at"
            )
            logger.debug("Índices de MongoDB creados/verificados correctamente.")
        except OperationFailure as e:
            logger.warning("Error al crear índices (pueden existir): %s", str(e))

    @staticmethod
    def _compute_integrity_hash(product_data: dict) -> str:
        """
        Calcula el hash SHA-256 de integridad para un producto.
        
        El hash se genera a partir de los campos clave del producto,
        permitiendo detectar manipulaciones en los datos almacenados.
        
        Args:
            product_data: Diccionario con los datos del producto.
        
        Returns:
            Hash SHA-256 como string hexadecimal.
        """
        # Campos clave para el hash (excluir metadatos mutables)
        hash_fields = {
            "sku": product_data.get("sku", ""),
            "name": product_data.get("name", ""),
            "price": str(product_data.get("price", "")),
            "url": product_data.get("url", ""),
        }
        # Serializar de forma determinista
        hash_string = json.dumps(hash_fields, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()

    def save_product(self, product_data: dict) -> bool:
        """
        Almacena un producto en MongoDB con upsert por SKU.
        
        Si el producto ya existe (mismo SKU), se actualiza.
        Si no existe, se inserta como nuevo documento.
        
        Args:
            product_data: Diccionario con los datos del producto.
                Campos esperados: sku, name, price, url, image_url, category.
        
        Returns:
            True si la operación fue exitosa.
            
        Seguridad: Agrega hash de integridad y timestamp automáticamente.
        """
        if not self._validate_product(product_data):
            return False

        try:
            # Agregar metadatos de seguridad
            product_data["integrity_hash"] = self._compute_integrity_hash(product_data)
            product_data["scraped_at"] = datetime.now(timezone.utc)
            product_data["updated_at"] = datetime.now(timezone.utc)

            # Upsert: insertar o actualizar por SKU
            result = self._collection.update_one(
                {"sku": product_data["sku"]},
                {"$set": product_data, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
                upsert=True
            )

            if result.upserted_id:
                logger.debug("Producto insertado: %s", product_data.get("name", "N/A"))
            else:
                logger.debug("Producto actualizado: %s", product_data.get("name", "N/A"))

            return True

        except Exception as e:
            logger.error(
                "Error al guardar producto '%s': %s",
                product_data.get("sku", "UNKNOWN"), str(e)
            )
            return False

    def save_products_bulk(self, products: list[dict]) -> dict:
        """
        Almacena múltiples productos en lote.
        
        Args:
            products: Lista de diccionarios de productos.
        
        Returns:
            Diccionario con estadísticas: inserted, updated, errors.
        """
        stats = {"inserted": 0, "updated": 0, "errors": 0}

        for product in products:
            if self.save_product(product):
                stats["inserted"] += 1
            else:
                stats["errors"] += 1

        logger.info(
            "Almacenamiento en lote completado: %d insertados/actualizados, %d errores",
            stats["inserted"], stats["errors"]
        )
        return stats

    @staticmethod
    def _validate_product(product_data: dict) -> bool:
        """
        Valida que un producto tenga los campos mínimos requeridos.
        
        Args:
            product_data: Diccionario con los datos del producto.
        
        Returns:
            True si el producto es válido.
        """
        required_fields = ["sku", "name", "price", "url"]

        for field in required_fields:
            if field not in product_data or not product_data[field]:
                logger.warning(
                    "Producto inválido: campo requerido '%s' faltante o vacío.",
                    field
                )
                return False

        # Validar que el precio sea numérico
        try:
            float(product_data["price"])
        except (ValueError, TypeError):
            logger.warning(
                "Producto inválido: precio no numérico '%s'.",
                product_data.get("price")
            )
            return False

        return True

    def get_product_count(self) -> int:
        """Retorna el número total de productos almacenados."""
        return self._collection.count_documents({})

    def get_stats(self) -> dict:
        """
        Retorna estadísticas del almacenamiento.
        
        Returns:
            Diccionario con métricas de la base de datos.
        """
        try:
            count = self.get_product_count()
            return {
                "database": ScraperConfig.MONGO_DATABASE,
                "collection": ScraperConfig.MONGO_COLLECTION,
                "total_products": count,
                "connection_status": "CONNECTED"
            }
        except Exception:
            return {"connection_status": "DISCONNECTED"}

    def close(self) -> None:
        """Cierra la conexión a MongoDB de forma segura."""
        if self._client:
            self._client.close()
            logger.info("Conexión a MongoDB cerrada.")
