# Enrutamiento Inteligente (EnhancedRouter)

El sistema de enrutamiento es el corazón de la inteligencia de AEGEN, encargado de dirigir cada mensaje del usuario al especialista más adecuado.

## 1. Arquitectura de Decisión

El enrutamiento no es lineal, sino que utiliza un **RoutingAnalyzer** basado en LLM (Modelo de Lenguaje) con las siguientes características:

### Factores de Decisión
- **Intención (Intent)**: Análisis semántico de lo que el usuario busca.
- **Vulnerabilidad**: Detección de estados emocionales que requieren intervención de TCC.
- **Afinidad (Stickiness)**: Preferencia por mantener el especialista actual para dar coherencia al hilo.
- **Contexto**: Uso de los últimos 5 mensajes para entender respuestas cortas o ambiguas.

## 2. Estrategias de Enrutamiento

- **EventRouter**: Para eventos no textuales (audio, archivos).
- **EnhancedRouter**: Para mensajes de texto complejos usando *Function Calling* (Llamada a Funciones).
- **ChainingRouter**: Para definir secuencias lógicas entre agentes.

---
*Decisiones registradas en `adr/ADR-0009-migracion-rendimiento-enrutamiento.md`*
