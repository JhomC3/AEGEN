# PLAN MAESTRO: AEGEN - De Chatbot a Sistema de Soporte Vital (Life Support System)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.

- **Estado:** En Ejecución (Pivote Estratégico)
- **Fecha:** 2026-02-21
- **Razón de Creación:** Cambio de paradigma. El sistema actual es reactivo (Q&A aislado) y está sobre-restringido por hardcodeos en los prompts (ej. TCC agresiva). Se requiere evolucionar hacia una arquitectura proactiva, basada en metas a largo plazo e interacciones fluidas (Soporte Vital).
- **Objetivo General:** Transformar AEGEN en un motor asíncrono y proactivo de gestión de vida, capaz de rastrear hitos, iniciar conversaciones con propósito y aplicar estrategias de conocimiento experto sin romper la naturalidad de la interacción.

---

## Resumen Ejecutivo

El plan anterior priorizaba la ingesta masiva de memoria (WhatsApp, ChatGPT) sobre un motor conversacional rígido. Este pivote invierte la prioridad: primero construiremos un "Motor de Propósito y Seguimiento" que permita a MAGI tener *hilos conductores* a lo largo de los días, semanas y meses.
AEGEN dejará de ser un chatbot que responde preguntas para convertirse en un sistema que extrae hitos (milestones), planifica seguimientos proactivos (cronógrafos) y separa la "Estrategia" clínica/técnica de la "Interfaz" conversacional, eliminando las reglas negativas rígidas (alignment tax) a favor de In-Context Learning (Few-shot prompting).

---

## Bloque 1: Calibración de Personalidad e In-Context Learning (Core UX)
**Objetivo:** Eliminar el comportamiento robótico, los acentos erróneos (voseo no deseado) y los interrogatorios clínicos forzados.
**Justificación:** Si la salida de texto falla, la UX colapsa. El agente no debe actuar como un manual de psiquiatría, sino como un compañero inteligente.

- [x] **1.1 Purga de Hardcodes y Voseo**: Modificar `SOUL.md` y el prompt builder para prohibir el voseo y regionalismos accidentales. (Finalizado ✅ 2026-02-21)
- [x] **1.2 Few-Shot Dinámico**: Implementación de `gold_standards.yaml`. (Finalizado ✅ 2026-02-21)
- [x] **1.3 Refactorización del Router y Prompts Base**: Pacing de 1 pregunta máx. (Finalizado ✅ 2026-02-21)

## Bloque 2: Motor de Propósito e Hilos Conductores (State Management)
**Objetivo:** Dotar al sistema de memoria estructurada orientada a objetivos, no solo a retención de datos pasivos.
**Justificación:** Para ser un "Soporte de Vida", el sistema debe saber qué estás intentando lograr (ej. entrenar, dormir mejor) y registrar tus avances para hilar conversaciones futuras.

- [x] **2.1 Schema de Hitos y Metas (ADR-0026)**: Modificar `schema.sql`. (Finalizado ✅ 2026-02-21)
- [x] **2.2 Extractor de Hitos en Background**: `MilestoneExtractor`. (Finalizado ✅ 2026-02-21)
- [x] **2.3 Inyección de Hitos en Contexto**: MAGI ve sus hitos pendientes. (Finalizado ✅ 2026-02-21)

## Bloque 3: Proactividad y Cronógrafos (Romper el Reactivismo)
**Objetivo:** Permitir que AEGEN inicie conversaciones o retome temas pendientes de forma natural.
**Justificación:** Un asistente real te pregunta "¿cómo te fue?" horas después del evento, o aprovecha una nueva charla para ponerse al día.
- [x] **3.1 Bandeja de Salida Diferida (ADR-0027)**: Sistema de cola en SQLite. (Finalizado ✅ 2026-02-21)
- [x] **3.2 Integración de Polling Proactivo**: Worker en lifespan de FastAPI. (Finalizado ✅ 2026-02-21)
- [x] **3.3 Inyección Suave de Intención (Soft Intent Injection)**: MAGI recibe recados pendientes si el usuario habla primero. (Finalizado ✅ 2026-02-21)

## Bloque 4: Reingeniería del Experto RAG (Separación de Preocupaciones)
**Objetivo:** Mejorar el uso del Knowledge Base (TCC, Finanzas, etc.) sin que el agente suene como si estuviera leyendo un libro.
**Justificación:** El conocimiento experto debe dictar la *estrategia*, no el *diálogo exacto*.
- [x] **4.1 Agente Estratega (Dual Brain - ADR-0028)**: Separación de `llm_chat` y `llm_core` (120B). (Finalizado ✅ 2026-02-22)
- [x] **4.2 Agente Interfaz (MAGI)**: MAGI traduce la estrategia a charla humana natural. (Finalizado ✅ 2026-02-22)

## Bloque 5: Análisis Longitudinal y Life Review Agent
**Objetivo:** Detectar progreso real a lo largo del tiempo (ej. mejora en métricas de gimnasio o cambio positivo en estado de ánimo).
**Justificación:** La memoria de hitos aislados no sirve sin un motor que calcule la tendencia. Un "Soporte Vital" debe felicitarte por tus avances semanales o alertarte de recaídas.
- [x] **5.1 Life Review Worker**: Script asíncrono para recuperación de hitos. (Finalizado ✅ 2026-02-22)
- [x] **5.2 Prompt de Análisis de Tendencia**: LLM chain que compara registros. (Finalizado ✅ 2026-02-22)
- [x] **5.3 Agendamiento Proactivo de Progreso**: MAGI felicita o retoma temas de avance. (Finalizado ✅ 2026-02-22)

## Bloque 6: Refinamiento de Fluidez Cognitiva (Late Context Injection)
**Objetivo:** Erradicar definitivamente el "Role Clash" y las respuestas terapéuticas robóticas causadas por el desvanecimiento del prompt maestro en historiales largos.
**Justificación:** Cuando el historial de conversación es extenso, el modelo "olvida" su tono base (amigable/pragmático) y recae en su comportamiento por defecto de asistente de IA genérico, generando disculpas excesivas o clichés psicológicos.
- [x] **6.1 Reingeniería del TCC Overlay (Anti-Robótico)**: Restricciones negativas ejecutables. (Finalizado ✅ 2026-02-23)
- [x] **6.2 Relajación del Router Terapéutico**: `CONFUSION` y `RESISTANCE` intents. (Finalizado ✅ 2026-02-23)
- [x] **6.3 Late Context Injection (El Martillazo)**: Inyección de `SystemMessage` tras el historial. (Finalizado ✅ 2026-02-23)

---

## Notas y Riesgos
- **Riesgo Arquitectónico:** La proactividad (Bloque 3) requiere cuidado extremo para no generar bucles infinitos de auto-mensajes ni enviar spam al usuario. Requiere un *debounce* estricto y límites de frecuencia.
- **Riesgo de Personalidad:** La transición de reglas negativas a ejemplos (Few-shot) requiere encontrar los "Gold Standards" correctos para cada tipo de interacción.
