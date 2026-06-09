package com.geniuscontrole.service;

import com.geniuscontrole.model.ScraperTask;
import com.geniuscontrole.model.dto.ScraperRequest;
import com.geniuscontrole.repository.ScraperTaskRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * Servicio de Scraping — Ejecuta el proceso Python como subproceso.
 * <p>
 * Responsabilidades:
 * </p>
 * <ul>
 *   <li>Crear y gestionar tareas de scraping en MongoDB.</li>
 *   <li>Ejecutar el script Python main.py como proceso externo.</li>
 *   <li>Capturar stdout/stderr del proceso para monitoreo.</li>
 *   <li>Actualizar el estado de la tarea según el resultado.</li>
 *   <li>Invalidar caché de productos tras un scraping exitoso.</li>
 * </ul>
 *
 * <p><b>Seguridad:</b></p>
 * <ul>
 *   <li>Sanitización de parámetros antes de pasar al proceso.</li>
 *   <li>Timeout configurable para evitar procesos colgados.</li>
 *   <li>Ejecución asíncrona (@Async) para no bloquear la API.</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ScraperService {

    private final ScraperTaskRepository taskRepository;

    /** Ejecutable de Python (configurable: python, python3, etc.) */
    @Value("${scraper.python.executable:python}")
    private String pythonExecutable;

    /** Ruta al script main.py del scraper. */
    @Value("${scraper.python.script-path:../scraper/main.py}")
    private String scriptPath;

    /** Timeout máximo para el proceso de scraping (segundos). */
    @Value("${scraper.python.timeout-seconds:300}")
    private int timeoutSeconds;

    /** Directorio de trabajo para el proceso Python. */
    @Value("${scraper.python.working-directory:../scraper}")
    private String workingDirectory;

    /**
     * Inicia un nuevo proceso de scraping de forma asíncrona.
     * <p>
     * Flujo:
     * 1. Crear registro ScraperTask con estado PENDING.
     * 2. Construir comando con parámetros sanitizados.
     * 3. Ejecutar proceso Python con ProcessBuilder.
     * 4. Capturar salida y actualizar estado.
     * 5. Invalidar caché de productos si fue exitoso.
     * </p>
     *
     * @param request Solicitud de scraping validada.
     * @return CompletableFuture con la tarea creada.
     */
    @Async
    @CacheEvict(value = {"products", "stats"}, allEntries = true)
    public CompletableFuture<ScraperTask> startScraping(ScraperRequest request) {
        log.info("Iniciando nuevo proceso de scraping. URL: {}, Modo: {}, Páginas: {}",
                request.getTargetUrl(), request.getMode(), request.getMaxPages());

        // Crear tarea en estado PENDING
        ScraperTask task = ScraperTask.builder()
                .targetUrl(request.getTargetUrl())
                .mode(request.getMode())
                .maxPages(request.getMaxPages())
                .status(ScraperTask.TaskStatus.PENDING)
                .startedAt(Instant.now())
                .build();

        task = taskRepository.save(task);
        log.info("Tarea de scraping creada con ID: {}", task.getId());

        try {
            // Actualizar estado a RUNNING
            task.setStatus(ScraperTask.TaskStatus.RUNNING);
            taskRepository.save(task);

            // Construir y ejecutar el proceso Python
            String output = executeScraperProcess(request);

            // Proceso completado exitosamente
            task.setStatus(ScraperTask.TaskStatus.COMPLETED);
            task.setProcessOutput(truncateOutput(output));
            task.setCompletedAt(Instant.now());
            task.setDurationSeconds(
                Duration.between(task.getStartedAt(), task.getCompletedAt()).toMillis() / 1000.0
            );

            // Intentar extraer el conteo de productos del output JSON
            task.setProductsFound(extractProductCount(output));

            log.info("Scraping completado exitosamente. Tarea: {}, Productos: {}",
                    task.getId(), task.getProductsFound());

        } catch (Exception e) {
            log.error("Error durante el scraping. Tarea: {}, Error: {}",
                    task.getId(), e.getMessage(), e);
            task.setStatus(ScraperTask.TaskStatus.FAILED);
            task.setErrorMessage(e.getMessage());
            task.setCompletedAt(Instant.now());
            task.setDurationSeconds(
                Duration.between(task.getStartedAt(), task.getCompletedAt()).toMillis() / 1000.0
            );
        }

        taskRepository.save(task);
        return CompletableFuture.completedFuture(task);
    }

    /**
     * Ejecuta el script Python main.py como proceso externo.
     * <p>
     * Seguridad:
     * - Los parámetros son sanitizados antes de la ejecución.
     * - Se configura un timeout para evitar procesos colgados.
     * - Se captura tanto stdout como stderr.
     * </p>
     *
     * @param request Solicitud de scraping con parámetros validados.
     * @return Salida estándar del proceso Python.
     * @throws Exception Si el proceso falla o excede el timeout.
     */
    private String executeScraperProcess(ScraperRequest request) throws Exception {
        // Sanitizar parámetros para prevenir inyección de comandos
        String sanitizedUrl = sanitizeParameter(request.getTargetUrl());
        String sanitizedMode = sanitizeParameter(request.getMode());
        int maxPages = Math.min(Math.max(request.getMaxPages(), 1), 50);

        // Construir el comando
        ProcessBuilder pb = new ProcessBuilder(
                pythonExecutable,
                scriptPath,
                "--url", sanitizedUrl,
                "--mode", sanitizedMode,
                "--pages", String.valueOf(maxPages),
                "--output-format", "json"
        );

        // Configurar directorio de trabajo
        File workDir = new File(workingDirectory);
        if (workDir.exists()) {
            pb.directory(workDir);
        }

        // Redirigir stderr a stdout para captura unificada
        pb.redirectErrorStream(true);

        // Configurar variables de entorno para el proceso Python
        pb.environment().put("PYTHONUNBUFFERED", "1");

        log.info("Ejecutando: {} {} --url {} --mode {} --pages {}",
                pythonExecutable, scriptPath, sanitizedUrl, sanitizedMode, maxPages);

        // Iniciar el proceso
        Process process = pb.start();

        // Capturar salida del proceso
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
                log.debug("[SCRAPER] {}", line);
            }
        }

        // Esperar a que termine con timeout
        boolean finished = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);

        if (!finished) {
            process.destroyForcibly();
            throw new RuntimeException(
                "El proceso de scraping excedió el timeout de " + timeoutSeconds + " segundos."
            );
        }

        int exitCode = process.exitValue();
        if (exitCode != 0 && exitCode != 130) {  // 130 = SIGINT (interrupción)
            throw new RuntimeException(
                "El proceso de scraping terminó con código de error: " + exitCode +
                ". Output: " + truncateOutput(output.toString())
            );
        }

        return output.toString();
    }

    /**
     * Sanitiza un parámetro para prevenir inyección de comandos.
     * <p>
     * Elimina caracteres potencialmente peligrosos que podrían
     * ser interpretados por el shell del sistema operativo.
     * </p>
     *
     * @param param Parámetro a sanitizar.
     * @return Parámetro sanitizado.
     */
    private String sanitizeParameter(String param) {
        if (param == null) return "";
        // Eliminar caracteres de shell que podrían causar inyección
        return param.replaceAll("[;&|`$(){}\\[\\]!#]", "")
                     .trim();
    }

    /**
     * Extrae el conteo de productos del output JSON del scraper.
     *
     * @param output Salida del proceso Python.
     * @return Número de productos extraídos, o 0 si no se puede parsear.
     */
    private Integer extractProductCount(String output) {
        try {
            // Buscar "products_extracted" en el JSON de output
            if (output.contains("\"products_extracted\"")) {
                int idx = output.indexOf("\"products_extracted\"");
                String sub = output.substring(idx);
                // Extraer el número después de ":"
                String numStr = sub.replaceAll(".*\"products_extracted\"\\s*:\\s*(\\d+).*", "$1");
                return Integer.parseInt(numStr.trim().split("[^0-9]")[0]);
            }
        } catch (Exception e) {
            log.warn("No se pudo extraer conteo de productos del output.");
        }
        return 0;
    }

    /**
     * Trunca la salida del proceso para almacenamiento seguro.
     * Evita almacenar outputs excesivamente largos en MongoDB.
     *
     * @param output Salida completa del proceso.
     * @return Salida truncada (máx. 5000 caracteres).
     */
    private String truncateOutput(String output) {
        if (output == null) return "";
        if (output.length() > 5000) {
            return output.substring(0, 5000) + "\n... [TRUNCATED]";
        }
        return output;
    }

    /**
     * Obtiene el estado de una tarea de scraping por su ID.
     *
     * @param taskId ID de la tarea.
     * @return Optional con la tarea si existe.
     */
    public Optional<ScraperTask> getTaskStatus(String taskId) {
        return taskRepository.findById(taskId);
    }

    /**
     * Obtiene las tareas de scraping más recientes.
     *
     * @return Lista de las 10 tareas más recientes.
     */
    public List<ScraperTask> getRecentTasks() {
        return taskRepository.findTop10ByOrderByStartedAtDesc();
    }
}
