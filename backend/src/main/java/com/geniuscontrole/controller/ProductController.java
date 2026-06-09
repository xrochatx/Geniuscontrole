package com.geniuscontrole.controller;

import com.geniuscontrole.model.Product;
import com.geniuscontrole.service.ProductService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Controlador REST de Productos — API de consulta del catálogo.
 * <p>
 * Expone endpoints para consultar los productos extraídos por el scraper
 * y almacenados en MongoDB. Las respuestas son cacheadas en Redis.
 * </p>
 *
 * <p><b>Endpoints:</b></p>
 * <ul>
 *   <li>GET /api/v1/products — Lista todos los productos (paginado).</li>
 *   <li>GET /api/v1/products/{sku} — Detalle de un producto por SKU.</li>
 *   <li>GET /api/v1/products/search — Búsqueda por nombre.</li>
 *   <li>GET /api/v1/products/category/{category} — Filtrado por categoría.</li>
 *   <li>GET /api/v1/products/price-range — Filtrado por rango de precio.</li>
 *   <li>GET /api/v1/products/stats — Estadísticas del catálogo.</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@RestController
@RequestMapping("/api/v1/products")
@RequiredArgsConstructor
@Slf4j
public class ProductController {

    private final ProductService productService;

    /**
     * Lista todos los productos con paginación y ordenamiento.
     *
     * @param page Número de página (default: 0).
     * @param size Tamaño de página (default: 20, max: 100).
     * @param sortBy Campo para ordenar (default: "name").
     * @param direction Dirección de ordenamiento (default: "asc").
     * @return Página de productos con headers de paginación.
     */
    @GetMapping
    public ResponseEntity<Page<Product>> getAllProducts(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "name") String sortBy,
            @RequestParam(defaultValue = "asc") String direction
    ) {
        log.info("GET /api/v1/products - page={}, size={}, sortBy={}, dir={}",
                page, size, sortBy, direction);

        // Limitar tamaño de página para seguridad (prevenir abuso)
        size = Math.min(size, 100);

        Page<Product> products = productService.getAllProducts(page, size, sortBy, direction);

        // Headers de paginación personalizados
        HttpHeaders headers = new HttpHeaders();
        headers.add("X-Total-Count", String.valueOf(products.getTotalElements()));
        headers.add("X-Page-Number", String.valueOf(products.getNumber()));
        headers.add("X-Page-Size", String.valueOf(products.getSize()));
        headers.add("X-Total-Pages", String.valueOf(products.getTotalPages()));

        return ResponseEntity.ok().headers(headers).body(products);
    }

    /**
     * Obtiene un producto por su SKU único.
     *
     * @param sku SKU del producto.
     * @return Producto encontrado o 404 Not Found.
     */
    @GetMapping("/{sku}")
    public ResponseEntity<Product> getProductBySku(@PathVariable String sku) {
        log.info("GET /api/v1/products/{}", sku);

        return productService.getProductBySku(sku)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Busca productos por nombre (búsqueda parcial, case-insensitive).
     *
     * @param q Texto de búsqueda.
     * @param page Número de página.
     * @param size Tamaño de página.
     * @return Página de productos que coinciden con la búsqueda.
     */
    @GetMapping("/search")
    public ResponseEntity<Page<Product>> searchProducts(
            @RequestParam String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        log.info("GET /api/v1/products/search?q={}", q);

        if (q == null || q.trim().isEmpty()) {
            return ResponseEntity.badRequest().build();
        }

        size = Math.min(size, 100);
        Page<Product> products = productService.searchProducts(q.trim(), page, size);
        return ResponseEntity.ok(products);
    }

    /**
     * Filtra productos por categoría.
     *
     * @param category Nombre de la categoría.
     * @param page Número de página.
     * @param size Tamaño de página.
     * @return Página de productos de la categoría.
     */
    @GetMapping("/category/{category}")
    public ResponseEntity<Page<Product>> getProductsByCategory(
            @PathVariable String category,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        log.info("GET /api/v1/products/category/{}", category);

        size = Math.min(size, 100);
        Page<Product> products = productService.getProductsByCategory(category, page, size);
        return ResponseEntity.ok(products);
    }

    /**
     * Filtra productos por rango de precio.
     *
     * @param minPrice Precio mínimo (inclusivo).
     * @param maxPrice Precio máximo (inclusivo).
     * @param page Número de página.
     * @param size Tamaño de página.
     * @return Página de productos en el rango de precio.
     */
    @GetMapping("/price-range")
    public ResponseEntity<Page<Product>> getProductsByPriceRange(
            @RequestParam Double minPrice,
            @RequestParam Double maxPrice,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        log.info("GET /api/v1/products/price-range?min={}&max={}", minPrice, maxPrice);

        if (minPrice < 0 || maxPrice < 0 || minPrice > maxPrice) {
            return ResponseEntity.badRequest().build();
        }

        size = Math.min(size, 100);
        Page<Product> products = productService.getProductsByPriceRange(minPrice, maxPrice, page, size);
        return ResponseEntity.ok(products);
    }

    /**
     * Obtiene estadísticas generales del catálogo de productos.
     *
     * @return Mapa con estadísticas: total, precios promedio/min/max,
     *         categorías, stock, rating promedio.
     */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getProductStats() {
        log.info("GET /api/v1/products/stats");

        Map<String, Object> stats = productService.getProductStats();
        return ResponseEntity.ok(stats);
    }
}
