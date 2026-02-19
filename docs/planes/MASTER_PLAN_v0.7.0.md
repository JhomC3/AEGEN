# AEGEN - Plan Maestro de Implementación

Este documento detalla los pasos técnicos para la evolución de AEGEN hacia un sistema autónomo y profesional. Cada bloque representa un conjunto de capacidades que pueden solaparse en el tiempo.

## Bloque A: Saneamiento y Autonomía (Fase Actual)
**Objetivo:** Limpieza total de deuda técnica y automatización de la gestión de conocimientos.

### A.1. Saneamiento de Raíz [EJECUTADO ✅]
- Eliminar scripts legacy de Google Cloud.
- Unificar almacenamiento: Eliminar carpeta `/data`, centralizar en `/storage`.
- Refactorizar rutas de respaldo en `src/memory/backup.py` para usar subcarpetas en `/storage`.

### A.2. Vigilante de Conocimiento (Auto-Sync) [EJECUTADO ✅]
- Implementación de `KnowledgeWatcher` con estrategia de Async Polling nativo (ADR-0022).
- Sistema de detección de cambios (Create/Update/Delete) en `storage/knowledge/`.
- Integración asíncrona en el ciclo de vida `lifespan` de FastAPI en `src/main.py`.

### A.3. Flexibilidad Lingüística (Overhaul Personalidad) [EJECUTADO ✅]
- [Plan Detallado](./v0.7.0-A.3-overhaul-personalidad.md)
- Implementación de Arquitectura Soul Stack v2 y Reflejo Natural (ADR-0023).
- Adaptación dinámica al estilo del usuario mediante `StyleAnalyzer` y Eco Léxico.

## Bloque B: Expansión de Memoria y Contexto
**Objetivo:** Convertir historiales externos en conocimiento estructurado y útil.

### B.1. Herramienta de Ingesta Masiva (Bulk Ingestor)
- Crear parsers especializados en `src/tools/bulk_ingestor.py` para formatos exportados de ChatGPT, Claude y WhatsApp.
- Transformar mensajes masivos en eventos compatibles con el sistema.

### B.2. Agente de Revisión de Vida (Life Review)
- Implementar un proceso de análisis masivo que extraiga patrones de largo plazo (valores, hitos, red de apoyo).
- Población automática de las secciones correspondientes del `UserProfile` de Pydantic.

### B.3. Olvido Inteligente (Smart Decay)
- Modificar el algoritmo de Ranking RRF en `hybrid_search.py` para incluir un factor de decaimiento temporal.
- Diferenciar hechos entre "Estado" (volátil) y "Rasgo" (permanente) para aplicar diferentes políticas de expiración.

## Bloque C: Ecosistema de Acción (Habilidades / Skills)
**Objetivo:** Dotar al asistente de capacidad real de acción mediante herramientas externas.

### C.1. Skill Creator Tool (La Fábrica de Habilidades)
- Crear una infraestructura donde añadir una nueva herramienta sea solo cuestión de configuración.
- Automatizar el registro de especialistas y herramientas en el `MasterOrchestrator`.

### C.2. Integración de Herramientas de Acción
- Evaluar e integrar habilidades prioritarias como búsqueda web, gestión de agenda (Google Calendar) y análisis de archivos complejos.

### C.3. Verificador de Verdad (Anti-Alucinación)
- Implementar un paso de "Auto-Crítica" post-generación donde el agente verifique sus respuestas contra los hechos confirmados en la Bóveda de Conocimiento.

---
*Nota: Este plan es dinámico y se ajusta según la retroalimentación del usuario y la viabilidad técnica.*
