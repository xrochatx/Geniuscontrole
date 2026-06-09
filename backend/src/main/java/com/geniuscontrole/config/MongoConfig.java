package com.geniuscontrole.config;

import com.mongodb.client.MongoClient;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.mongodb.config.EnableMongoAuditing;
import org.springframework.data.mongodb.repository.config.EnableMongoRepositories;

/**
 * Configuración de MongoDB para el almacenamiento de productos.
 * <p>
 * Características de seguridad:
 * </p>
 * <ul>
 *   <li>Autenticación mediante URI con credenciales (application.yml).</li>
 *   <li>Auditoría automática de timestamps (createdAt, updatedAt).</li>
 *   <li>Creación automática de índices.</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Configuration
@EnableMongoRepositories(basePackages = "com.geniuscontrole.repository")
@EnableMongoAuditing
public class MongoConfig {
    // La configuración de conexión se realiza en application.yml.
    // Spring Boot Data MongoDB auto-configura el MongoClient.
    // @EnableMongoAuditing habilita @CreatedDate y @LastModifiedDate.
}
