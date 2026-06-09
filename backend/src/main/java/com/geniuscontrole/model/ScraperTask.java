package com.geniuscontrole.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.io.Serializable;
import java.time.Instant;

/**
 * Entidad ScraperTask — Documento MongoDB para rastrear
 * el estado de las tareas de scraping.
 * <p>
 * Cada vez que la API inicia un proceso de scraping, se crea
 * un registro ScraperTask para monitorear su progreso.
 * </p>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "scraper_tasks")
public class ScraperTask implements Serializable {

    private static final long serialVersionUID = 1L;

    /** Identificador único de la tarea. */
    @Id
    private String id;

    /** URL objetivo del scraping. */
    private String targetUrl;

    /** Modo de scraping: 'static' o 'dynamic'. */
    private String mode;

    /** Número máximo de páginas a recorrer. */
    private Integer maxPages;

    /**
     * Estado de la tarea.
     * Valores posibles: PENDING, RUNNING, COMPLETED, FAILED.
     */
    private TaskStatus status;

    /** Timestamp de inicio de la tarea. */
    private Instant startedAt;

    /** Timestamp de finalización de la tarea. */
    private Instant completedAt;

    /** Número de productos encontrados. */
    private Integer productsFound;

    /** Mensaje de error (si aplica). */
    private String errorMessage;

    /** Salida estándar del proceso Python (para debug). */
    private String processOutput;

    /** Duración del proceso en segundos. */
    private Double durationSeconds;

    /**
     * Enumeración de estados posibles para una tarea de scraping.
     */
    public enum TaskStatus {
        /** Tarea creada, esperando ejecución. */
        PENDING,
        /** Tarea en ejecución. */
        RUNNING,
        /** Tarea completada exitosamente. */
        COMPLETED,
        /** Tarea fallida con error. */
        FAILED
    }
}
