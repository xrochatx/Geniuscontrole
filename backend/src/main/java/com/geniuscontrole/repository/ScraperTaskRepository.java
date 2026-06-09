package com.geniuscontrole.repository;

import com.geniuscontrole.model.ScraperTask;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repositorio de tareas de scraping — Spring Data MongoDB.
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Repository
public interface ScraperTaskRepository extends MongoRepository<ScraperTask, String> {

    /**
     * Busca tareas por estado.
     *
     * @param status Estado de la tarea.
     * @return Lista de tareas con el estado dado.
     */
    List<ScraperTask> findByStatus(ScraperTask.TaskStatus status);

    /**
     * Busca las últimas N tareas ordenadas por fecha de inicio descendente.
     *
     * @return Lista de tareas recientes.
     */
    List<ScraperTask> findTop10ByOrderByStartedAtDesc();
}
