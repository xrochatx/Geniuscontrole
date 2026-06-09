package com.geniuscontrole.controller;

import com.geniuscontrole.model.ScraperTask;
import com.geniuscontrole.model.dto.ScraperRequest;
import com.geniuscontrole.model.dto.ScraperResponse;
import com.geniuscontrole.service.ScraperService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Controlador REST del Scraper — Gestión de procesos de scraping.
 * <p>
 * Expone endpoints para iniciar y monitorear procesos de scraping.
 * La ejecución del scraper es asíncrona para no bloquear la API.
 * </p>
 *
 * <p><b>Endpoints:</b></p>
 * <ul>
 *   <li>POST /api/v1/scraper/start — Inicia un nuevo proceso de scraping.</li>
 *   <li>GET /api/v1/scraper/status/{taskId} — Consulta el estado de una tarea.</li>
 *   <li>GET /api/v1/scraper/tasks — Lista tareas recientes.</li>
 * </ul>
 *
 * <p><b>Seguridad:</b></p>
 * <ul>
 *   <li>Validación de input con Bean Validation (@Valid).</li>
 *   <li>Sanitización de parámetros en ScraperService.</li>
 *   <li>Límite de páginas (máx. 50) para prevenir abuso.</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@RestController
@RequestMapping("/api/v1/scraper")
@RequiredArgsConstructor
@Slf4j
public class ScraperController {

    private final ScraperService scraperService;

    /**
     * Inicia un nuevo proceso de scraping de forma asíncrona.
     * <p>
     * El proceso Python se ejecuta en segundo plano. La respuesta
     * incluye un taskId para consultar el estado posteriormente.
     * </p>
     *
     * @param request Solicitud de scraping con URL, modo y páginas.
     * @return ScraperResponse con el taskId de la tarea creada.
     */
    @PostMapping("/start")
    public ResponseEntity<ScraperResponse> startScraping(
            @Valid @RequestBody ScraperRequest request
    ) {
        log.info("POST /api/v1/scraper/start - URL: {}, Mode: {}, Pages: {}",
                request.getTargetUrl(), request.getMode(), request.getMaxPages());

        try {
            // Iniciar scraping asíncrono (no bloquea)
            scraperService.startScraping(request);

            // Construir respuesta con estado ACCEPTED
            ScraperResponse response = ScraperResponse.builder()
                    .status(ScraperTask.TaskStatus.PENDING)
                    .message("Proceso de scraping iniciado. Use el endpoint /status para monitorear.")
                    .targetUrl(request.getTargetUrl())
                    .build();

            // Obtener el taskId de la tarea más reciente
            List<ScraperTask> recentTasks = scraperService.getRecentTasks();
            if (!recentTasks.isEmpty()) {
                response.setTaskId(recentTasks.get(0).getId());
            }

            return ResponseEntity.status(HttpStatus.ACCEPTED).body(response);

        } catch (Exception e) {
            log.error("Error al iniciar scraping: {}", e.getMessage(), e);

            ScraperResponse errorResponse = ScraperResponse.builder()
                    .status(ScraperTask.TaskStatus.FAILED)
                    .message("Error al iniciar el scraping: " + e.getMessage())
                    .targetUrl(request.getTargetUrl())
                    .build();

            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Consulta el estado de una tarea de scraping por su ID.
     *
     * @param taskId Identificador de la tarea.
     * @return ScraperResponse con el estado actual de la tarea.
     */
    @GetMapping("/status/{taskId}")
    public ResponseEntity<ScraperResponse> getScraperStatus(@PathVariable String taskId) {
        log.info("GET /api/v1/scraper/status/{}", taskId);

        return scraperService.getTaskStatus(taskId)
                .map(task -> {
                    String message = switch (task.getStatus()) {
                        case PENDING -> "Tarea en cola, esperando ejecución.";
                        case RUNNING -> "Scraping en progreso...";
                        case COMPLETED -> "Scraping completado exitosamente.";
                        case FAILED -> "Error: " + task.getErrorMessage();
                    };

                    return ResponseEntity.ok(ScraperResponse.fromTask(task, message));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Lista las tareas de scraping más recientes.
     *
     * @return Lista de las 10 tareas más recientes con su estado.
     */
    @GetMapping("/tasks")
    public ResponseEntity<List<ScraperResponse>> getRecentTasks() {
        log.info("GET /api/v1/scraper/tasks");

        List<ScraperResponse> tasks = scraperService.getRecentTasks().stream()
                .map(task -> ScraperResponse.fromTask(task, task.getStatus().name()))
                .collect(Collectors.toList());

        return ResponseEntity.ok(tasks);
    }
}
