package com.geniuscontrole.repository;

import com.geniuscontrole.model.Product;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * Repositorio de productos — Spring Data MongoDB.
 * <p>
 * Proporciona operaciones CRUD y consultas derivadas para la
 * colección 'products' de MongoDB. Incluye búsqueda por texto
 * completo (full-text search) usando @TextIndexed.
 * </p>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Repository
public interface ProductRepository extends MongoRepository<Product, String> {

    /**
     * Busca un producto por su SKU único.
     *
     * @param sku SKU del producto.
     * @return Optional con el producto si existe.
     */
    Optional<Product> findBySku(String sku);

    /**
     * Verifica si existe un producto con el SKU dado.
     *
     * @param sku SKU a verificar.
     * @return true si existe.
     */
    boolean existsBySku(String sku);

    /**
     * Busca productos por nombre (búsqueda parcial, case-insensitive).
     * Usa regex de MongoDB para búsqueda flexible.
     *
     * @param name Patrón de búsqueda.
     * @param pageable Configuración de paginación.
     * @return Page de productos que coinciden.
     */
    @Query("{ 'name': { $regex: ?0, $options: 'i' } }")
    Page<Product> findByNameContainingIgnoreCase(String name, Pageable pageable);

    /**
     * Busca productos por categoría con paginación.
     *
     * @param category Categoría del producto.
     * @param pageable Configuración de paginación.
     * @return Page de productos de la categoría.
     */
    Page<Product> findByCategory(String category, Pageable pageable);

    /**
     * Busca productos dentro de un rango de precios.
     *
     * @param minPrice Precio mínimo (inclusivo).
     * @param maxPrice Precio máximo (inclusivo).
     * @param pageable Configuración de paginación.
     * @return Page de productos en el rango de precio.
     */
    Page<Product> findByPriceBetween(Double minPrice, Double maxPrice, Pageable pageable);

    /**
     * Busca productos en stock.
     *
     * @param pageable Configuración de paginación.
     * @return Page de productos disponibles.
     */
    Page<Product> findByInStockTrue(Pageable pageable);

    /**
     * Obtiene todas las categorías distintas.
     *
     * @return Lista de categorías únicas.
     */
    @Query(value = "{}", fields = "{ 'category' : 1 }")
    List<Product> findDistinctCategories();

    /**
     * Cuenta productos por categoría.
     *
     * @param category Categoría.
     * @return Número de productos en la categoría.
     */
    long countByCategory(String category);
}
