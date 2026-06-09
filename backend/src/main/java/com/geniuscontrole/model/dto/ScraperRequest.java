package com.geniuscontrole.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.validator.constraints.URL;

/**
 * DTO de solicitud para iniciar un proceso de scraping.
 * <p>
 * Seguridad: Todos los campos son validados con Bean Validation
 * para prevenir inyección de comandos y URLs maliciosas.
 * </p>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScraperRequest {

    /**
     * URL objetivo del sitio e-commerce.
     * Validación: Debe ser una URL válida con protocolo HTTP/HTTPS.
     */
    @NotBlank(message = "La URL objetivo es obligatoria")
    @URL(message = "La URL debe tener un formato válido (http/https)")
    private String targetUrl;

    /**
     * Modo de scraping.
     * Valores aceptados: 'static' (BeautifulSoup) o 'dynamic' (Selenium).
     */
    @NotBlank(message = "El modo de scraping es obligatorio")
    @Pattern(regexp = "^(static|dynamic)$", message = "El modo debe ser 'static' o 'dynamic'")
    private String mode;

    /**
     * Número máximo de páginas a recorrer.
     * Límite: entre 1 y 50 páginas (seguridad contra abuso).
     */
    @Min(value = 1, message = "Debe recorrer al menos 1 página")
    @Max(value = 50, message = "Máximo 50 páginas por ejecución (seguridad)")
    @Builder.Default
    private Integer maxPages = 5;
}
