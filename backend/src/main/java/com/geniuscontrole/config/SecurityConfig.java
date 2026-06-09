package com.geniuscontrole.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

/**
 * Configuración de seguridad HTTP del API Gateway.
 * <p>
 * Implementa las siguientes medidas de ciberseguridad:
 * </p>
 * <ul>
 *   <li>CORS restrictivo: Solo permite orígenes específicos.</li>
 *   <li>Headers HTTP de seguridad: HSTS, CSP, X-Frame-Options, X-Content-Type-Options.</li>
 *   <li>Sesión stateless: No almacena estado de sesión en servidor (API REST).</li>
 *   <li>CSRF deshabilitado: No aplica para APIs REST stateless.</li>
 *   <li>API abierta para la demo: Sin autenticación (configurable para producción).</li>
 * </ul>
 *
 * @author Juan Rochat
 * @version 1.0.0
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /**
     * Configura la cadena de filtros de seguridad HTTP.
     *
     * @param http Builder de configuración de seguridad.
     * @return SecurityFilterChain configurado.
     * @throws Exception Si hay error en la configuración.
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // --- CORS: Configuración restrictiva ---
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))

            // --- CSRF: Deshabilitado para API REST stateless ---
            // Justificación: Las APIs REST no usan cookies de sesión,
            // por lo que CSRF no aplica. La protección se realiza
            // mediante tokens en headers de autorización.
            .csrf(AbstractHttpConfigurer::disable)

            // --- Sesión: Modo stateless (no almacena estado) ---
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            )

            // --- Autorización: Rutas públicas para la demo ---
            .authorizeHttpRequests(auth -> auth
                // Endpoints de la API pública (demo)
                .requestMatchers("/api/v1/**").permitAll()
                // Actuator health check público
                .requestMatchers("/actuator/health").permitAll()
                // Todo lo demás requiere autenticación
                .anyRequest().authenticated()
            )

            // --- Headers HTTP de Seguridad ---
            .headers(headers -> headers
                // X-Frame-Options: Previene clickjacking
                .frameOptions(frame -> frame.deny())
                // X-Content-Type-Options: Previene MIME sniffing
                .contentTypeOptions(Customizer.withDefaults())
                // Strict-Transport-Security (HSTS): Fuerza HTTPS
                .httpStrictTransportSecurity(hsts -> hsts
                    .includeSubDomains(true)
                    .maxAgeInSeconds(31536000)  // 1 año
                )
                // Content-Security-Policy: Restringe fuentes de contenido
                .contentSecurityPolicy(csp ->
                    csp.policyDirectives(
                        "default-src 'self'; " +
                        "script-src 'self'; " +
                        "style-src 'self' 'unsafe-inline'; " +
                        "img-src 'self' data:; " +
                        "font-src 'self'; " +
                        "frame-ancestors 'none'"
                    )
                )
                // Referrer-Policy: No enviar referrer a terceros
                .referrerPolicy(referrer ->
                    referrer.policy(ReferrerPolicyHeaderWriter.ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN)
                )
                // Permissions-Policy: Deshabilitar APIs de dispositivo innecesarias
                .permissionsPolicy(permissions ->
                    permissions.policy("camera=(), microphone=(), geolocation=()")
                )
            );

        return http.build();
    }

    /**
     * Configuración CORS (Cross-Origin Resource Sharing).
     * <p>
     * Seguridad: Restringe los orígenes que pueden hacer peticiones
     * a la API. En desarrollo se permite localhost; en producción
     * debe configurarse con dominios específicos.
     * </p>
     *
     * @return CorsConfigurationSource con las reglas CORS.
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();

        // Orígenes permitidos (desarrollo local + Postman)
        config.setAllowedOrigins(List.of(
            "http://localhost:3000",    // Frontend dev
            "http://localhost:8080",    // Self
            "http://localhost:5173"     // Vite dev server
        ));

        // Métodos HTTP permitidos
        config.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));

        // Headers permitidos
        config.setAllowedHeaders(Arrays.asList(
            "Authorization", "Content-Type", "X-Requested-With",
            "Accept", "Origin", "Cache-Control"
        ));

        // Headers expuestos al cliente
        config.setExposedHeaders(Arrays.asList(
            "X-Total-Count", "X-Page-Number", "X-Page-Size"
        ));

        config.setAllowCredentials(true);
        config.setMaxAge(3600L);  // Cache CORS preflight por 1 hora

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
