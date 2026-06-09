package com.geniuscontrole.config;

import org.springframework.cache.annotation.CachingConfigurer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

/**
 * Configuración de Redis para caché y almacenamiento de sesiones.
 * <p>
 * Redis se utiliza como capa de caché para:
 * </p>
 * <ul>
 *   <li>Respuestas de consultas frecuentes a MongoDB (reduce latencia).</li>
 *   <li>Rate limiting por IP en la API (seguridad).</li>
 *   <li>Estado de tareas de scraping en curso.</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Configuration
public class RedisConfig implements CachingConfigurer {

    /**
     * Configura el RedisTemplate con serialización JSON.
     * <p>
     * Serialización: Usa JSON en lugar de Java Serialization por:
     * 1. Interoperabilidad con otros lenguajes (ej: Python scraper).
     * 2. Legibilidad de los datos en Redis CLI.
     * 3. Seguridad (evita deserialización de objetos Java arbitrarios).
     * </p>
     *
     * @param connectionFactory Factory de conexión a Redis.
     * @return RedisTemplate configurado con serialización JSON.
     */
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory connectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);

        // Keys como String
        template.setKeySerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());

        // Values como JSON (seguridad: evita Java Serialization)
        GenericJackson2JsonRedisSerializer jsonSerializer = new GenericJackson2JsonRedisSerializer();
        template.setValueSerializer(jsonSerializer);
        template.setHashValueSerializer(jsonSerializer);

        template.afterPropertiesSet();
        return template;
    }

    /**
     * Configura el CacheManager de Redis con TTL por defecto.
     *
     * @param connectionFactory Factory de conexión a Redis.
     * @return RedisCacheManager con configuración de TTL y serialización.
     */
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory) {
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
            // TTL por defecto: 5 minutos
            .entryTtl(Duration.ofMinutes(5))
            // No cachear valores null
            .disableCachingNullValues()
            // Prefijo para las keys de caché
            .prefixCacheNameWith("geniuscontrole:cache:")
            // Serialización JSON para valores
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer()
                )
            );

        return RedisCacheManager.builder(connectionFactory)
            .cacheDefaults(defaultConfig)
            // Cache específico para productos con TTL de 10 minutos
            .withCacheConfiguration("products",
                defaultConfig.entryTtl(Duration.ofMinutes(10))
            )
            // Cache para estadísticas con TTL de 2 minutos
            .withCacheConfiguration("stats",
                defaultConfig.entryTtl(Duration.ofMinutes(2))
            )
            .build();
    }
}
