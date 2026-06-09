package com.geniuscontrole.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.index.TextIndexed;
import org.springframework.data.mongodb.core.mapping.Document;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.io.Serializable;
import java.time.Instant;

/**
 * Entidad Product — Documento MongoDB para productos extraídos.
 * <p>
 * Representa un producto de e-commerce almacenado en la colección
 * 'products' de MongoDB. Incluye hash de integridad SHA-256
 * para detectar manipulaciones en los datos.
 * </p>
 *
 * <p><b>Campos de seguridad:</b></p>
 * <ul>
 *   <li>integrityHash: SHA-256 calculado sobre campos clave.</li>
 *   <li>scrapedAt: Timestamp de extracción para auditoría.</li>
 *   <li>sourceUrl: URL origen para trazabilidad.</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "products")
public class Product implements Serializable {

    private static final long serialVersionUID = 1L;

    /** Identificador único generado por MongoDB. */
    @Id
    private String id;

    /** SKU (Stock Keeping Unit) — Identificador único del producto. */
    @NotBlank(message = "El SKU es obligatorio")
    @Indexed(unique = true)
    private String sku;

    /** Nombre del producto. */
    @NotBlank(message = "El nombre es obligatorio")
    @TextIndexed
    private String name;

    /** Precio del producto. */
    @NotNull(message = "El precio es obligatorio")
    @Min(value = 0, message = "El precio no puede ser negativo")
    private Double price;

    /** URL de la página de detalle del producto. */
    @NotBlank(message = "La URL es obligatoria")
    private String url;

    /** URL de la imagen del producto. */
    private String imageUrl;

    /** Categoría del producto. */
    @Indexed
    private String category;

    /** Indica si el producto está en stock. */
    private Boolean inStock;

    /** Rating del producto (1-5). */
    private Integer rating;

    /** URL de la página fuente (PLP) desde donde se extrajo. */
    private String sourceUrl;

    /**
     * Hash SHA-256 de integridad.
     * Calculado sobre: sku + name + price + url.
     * Permite detectar manipulaciones en los datos almacenados.
     */
    private String integrityHash;

    /** Timestamp de cuando fue extraído por el scraper. */
    @Indexed
    private Instant scrapedAt;

    /** Timestamp de creación del registro (auditoría). */
    @CreatedDate
    private Instant createdAt;

    /** Timestamp de última modificación (auditoría). */
    @LastModifiedDate
    private Instant updatedAt;
}
