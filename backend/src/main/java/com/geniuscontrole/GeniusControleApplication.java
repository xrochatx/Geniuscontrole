package com.geniuscontrole;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * GeniusControle - Aplicación principal del Backend.
 * <p>
 * API Gateway REST para el sistema de Web Scraping seguro.
 * Proporciona endpoints para iniciar procesos de scraping y
 * consultar productos extraídos almacenados en MongoDB.
 * </p>
 * 
 * <p><b>Funcionalidades habilitadas:</b></p>
 * <ul>
 *   <li>@EnableCaching: Caché Redis para respuestas de consultas frecuentes.</li>
 *   <li>@EnableAsync: Ejecución asíncrona del proceso de scraping Python.</li>
 * </ul>
 * 
 * @author Juan Rochat
 * @version 1.0.0
 * @since 2024
 */
@SpringBootApplication
@EnableCaching
@EnableAsync
public class GeniusControleApplication {

    public static void main(String[] args) {
        SpringApplication.run(GeniusControleApplication.class, args);
    }
}
