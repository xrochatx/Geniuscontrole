package com.geniuscontrole.service;

import com.geniuscontrole.model.Product;
import com.geniuscontrole.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Servicio de productos — Lógica de negocio para consultas.
 * <p>
 * Proporciona acceso a los productos almacenados en MongoDB con:
 * </p>
 * <ul>
 *   <li>Caché Redis para respuestas frecuentes (@Cacheable).</li>
 *   <li>Paginación y filtrado flexible.</li>
 *   <li>Estadísticas generales del catálogo.</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ProductService {

    private final ProductRepository productRepository;

    /**
     * Obtiene todos los productos con paginación.
     *
     * @param page Número de página (0-indexed).
     * @param size Tamaño de página.
     * @param sortBy Campo para ordenar.
     * @param direction Dirección de ordenamiento (asc/desc).
     * @return Página de productos.
     */
    @Cacheable(value = "products", key = "'all-' + #page + '-' + #size + '-' + #sortBy + '-' + #direction")
    public Page<Product> getAllProducts(int page, int size, String sortBy, String direction) {
        log.debug("Consultando productos: page={}, size={}, sortBy={}, dir={}", page, size, sortBy, direction);

        Sort sort = direction.equalsIgnoreCase("desc")
                ? Sort.by(sortBy).descending()
                : Sort.by(sortBy).ascending();

        Pageable pageable = PageRequest.of(page, size, sort);
        return productRepository.findAll(pageable);
    }

    /**
     * Busca un producto por su SKU.
     *
     * @param sku SKU del producto.
     * @return Optional con el producto.
     */
    @Cacheable(value = "products", key = "'sku-' + #sku")
    public Optional<Product> getProductBySku(String sku) {
        log.debug("Buscando producto por SKU: {}", sku);
        return productRepository.findBySku(sku);
    }

    /**
     * Busca productos por nombre (búsqueda parcial, case-insensitive).
     *
     * @param query Texto de búsqueda.
     * @param page Número de página.
     * @param size Tamaño de página.
     * @return Página de productos que coinciden.
     */
    @Cacheable(value = "products", key = "'search-' + #query + '-' + #page + '-' + #size")
    public Page<Product> searchProducts(String query, int page, int size) {
        log.debug("Buscando productos con query: '{}'", query);
        // Escapar caracteres especiales de regex para seguridad
        String escapedQuery = query.replaceAll("[.*+?^${}()|\\[\\]\\\\]", "\\\\$0");
        Pageable pageable = PageRequest.of(page, size);
        return productRepository.findByNameContainingIgnoreCase(escapedQuery, pageable);
    }

    /**
     * Busca productos por categoría con paginación.
     *
     * @param category Categoría del producto.
     * @param page Número de página.
     * @param size Tamaño de página.
     * @return Página de productos de la categoría.
     */
    @Cacheable(value = "products", key = "'cat-' + #category + '-' + #page + '-' + #size")
    public Page<Product> getProductsByCategory(String category, int page, int size) {
        log.debug("Consultando productos de categoría: {}", category);
        Pageable pageable = PageRequest.of(page, size);
        return productRepository.findByCategory(category, pageable);
    }

    /**
     * Busca productos dentro de un rango de precios.
     *
     * @param minPrice Precio mínimo.
     * @param maxPrice Precio máximo.
     * @param page Número de página.
     * @param size Tamaño de página.
     * @return Página de productos en el rango.
     */
    @Cacheable(value = "products", key = "'price-' + #minPrice + '-' + #maxPrice + '-' + #page + '-' + #size")
    public Page<Product> getProductsByPriceRange(Double minPrice, Double maxPrice, int page, int size) {
        log.debug("Consultando productos en rango de precio: [{}, {}]", minPrice, maxPrice);
        Pageable pageable = PageRequest.of(page, size);
        return productRepository.findByPriceBetween(minPrice, maxPrice, pageable);
    }

    /**
     * Obtiene estadísticas generales del catálogo de productos.
     * Cacheado en Redis con TTL de 2 minutos.
     *
     * @return Mapa con estadísticas del catálogo.
     */
    @Cacheable(value = "stats", key = "'product-stats'")
    public Map<String, Object> getProductStats() {
        log.debug("Generando estadísticas del catálogo de productos.");

        Map<String, Object> stats = new HashMap<>();
        List<Product> allProducts = productRepository.findAll();

        stats.put("totalProducts", allProducts.size());

        if (!allProducts.isEmpty()) {
            // Estadísticas de precios
            double avgPrice = allProducts.stream()
                    .filter(p -> p.getPrice() != null)
                    .mapToDouble(Product::getPrice)
                    .average()
                    .orElse(0.0);

            double maxPrice = allProducts.stream()
                    .filter(p -> p.getPrice() != null)
                    .mapToDouble(Product::getPrice)
                    .max()
                    .orElse(0.0);

            double minPrice = allProducts.stream()
                    .filter(p -> p.getPrice() != null)
                    .mapToDouble(Product::getPrice)
                    .min()
                    .orElse(0.0);

            stats.put("averagePrice", Math.round(avgPrice * 100.0) / 100.0);
            stats.put("maxPrice", maxPrice);
            stats.put("minPrice", minPrice);

            // Productos en stock
            long inStockCount = allProducts.stream()
                    .filter(p -> Boolean.TRUE.equals(p.getInStock()))
                    .count();
            stats.put("inStockCount", inStockCount);
            stats.put("outOfStockCount", allProducts.size() - inStockCount);

            // Categorías
            Map<String, Long> categories = allProducts.stream()
                    .filter(p -> p.getCategory() != null)
                    .collect(Collectors.groupingBy(Product::getCategory, Collectors.counting()));
            stats.put("categories", categories);
            stats.put("totalCategories", categories.size());

            // Rating promedio
            double avgRating = allProducts.stream()
                    .filter(p -> p.getRating() != null && p.getRating() > 0)
                    .mapToInt(Product::getRating)
                    .average()
                    .orElse(0.0);
            stats.put("averageRating", Math.round(avgRating * 100.0) / 100.0);
        }

        return stats;
    }
}
