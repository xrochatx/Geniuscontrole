package com.geniuscontrole.model.dto;

import com.geniuscontrole.model.ScraperTask;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * DTO de respuesta para operaciones del scraper.
 * <p>
 * Contiene información sobre el estado de la tarea de scraping,
 * incluyendo su ID para consultas posteriores de estado.
 * </p>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScraperResponse {

    /** Identificador de la tarea para consultas de estado. */
    private String taskId;

    /** Estado actual de la tarea. */
    private ScraperTask.TaskStatus status;

    /** Mensaje descriptivo del estado. */
    private String message;

    /** URL objetivo del scraping. */
    private String targetUrl;

    /** Número de productos encontrados (cuando completa). */
    private Integer productsFound;

    /** Timestamp de inicio. */
    private Instant startedAt;

    /** Timestamp de finalización. */
    private Instant completedAt;

    /** Duración del proceso en segundos. */
    private Double durationSeconds;

    /**
     * Factory method para crear una respuesta desde una entidad ScraperTask.
     *
     * @param task Entidad ScraperTask.
     * @param message Mensaje descriptivo.
     * @return ScraperResponse mapeado desde la entidad.
     */
    public static ScraperResponse fromTask(ScraperTask task, String message) {
        return ScraperResponse.builder()
                .taskId(task.getId())
                .status(task.getStatus())
                .message(message)
                .targetUrl(task.getTargetUrl())
                .productsFound(task.getProductsFound())
                .startedAt(task.getStartedAt())
                .completedAt(task.getCompletedAt())
                .durationSeconds(task.getDurationSeconds())
                .build();
    }
}
