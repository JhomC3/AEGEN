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

- [ ] **1.1 Purga de Hardcodes y Voseo:** Modificar `SOUL.md` y el prompt builder para prohibir el voseo (a menos que se explicite) y eliminar reglas rígidas de "Tough Love" en `tcc_overlay.md`.
- [ ] **1.2 Few-Shot Dinámico:** Implementar un sistema de anclas de estilo donde el prompt inyecta 2-3 ejemplos de "interacciones perfectas" (`gold_standards.yaml`) para guiar al modelo por imitación en lugar de por prohibición.
- [ ] **1.3 Refactorización del Router y Prompts Base:** Ajustar el `enhanced_router.py` y los prompts de TCC para forzar "Escucha Activa Multi-turno", limitando al agente a una pregunta máxima por mensaje para evitar el "Q&A" aislado.

## Bloque 2: Motor de Propósito e Hilos Conductores (State Management)
**Objetivo:** Dotar al sistema de memoria estructurada orientada a objetivos, no solo a retención de datos pasivos.
**Justificación:** Para ser un "Soporte de Vida", el sistema debe saber qué estás intentando lograr (ej. entrenar, dormir mejor) y registrar tus avances para hilar conversaciones futuras.

- [ ] **2.1 Schema de Hitos y Metas (ADR-0026):** Modificar `schema.sql` para introducir tablas de `user_goals` y `user_milestones`.
- [ ] **2.2 Extractor de Hitos en Background:** Crear un worker o nodo en LangGraph que analice las conversaciones terminadas y extraiga eventos estructurados (Ej: `[Acción: Gimnasio] [Estado: Hecho] [Emoción: Apatía]`).
- [ ] **2.3 Inyección de Hitos en Contexto:** Que el `prompt_builder.py` cargue los hitos recientes no resueltos para que MAGI tenga "temas pendientes" de los que hablar y establecer el hilo conductor.

## Bloque 3: Proactividad y Cronógrafos (Romper el Reactivismo)
**Objetivo:** Permitir que AEGEN inicie conversaciones.
**Justificación:** Un asistente real te pregunta "¿cómo te fue?" horas después del evento.
- [ ] **3.1 Bandeja de Salida Diferida (ADR-0027):** Creación de un sistema de cola (`outbox_messages`) en SQLite donde un agente puede programar un mensaje para el futuro (`send_at`).
- [ ] **3.2 Integración de Polling Proactivo:** Modificar el webhook/polling de Telegram (`src/api/adapters/telegram_adapter.py`) para que evalúe periódicamente y despache los mensajes pendientes de la bandeja de salida.

## Bloque 4: Reingeniería del Experto RAG (Separación de Preocupaciones)
**Objetivo:** Mejorar el uso del Knowledge Base (TCC, Finanzas, etc.) sin que el agente suene como si estuviera leyendo un libro.
**Justificación:** El conocimiento experto debe dictar la *estrategia*, no el *diálogo exacto*.
- [ ] **4.1 Agente Estratega (Invisible):** Un nodo de LangGraph que consulta el RAG y define un "Plan de Intervención Interno" (ej. "Técnica a usar: Reestructuración cognitiva suave enfocada en el esfuerzo").
- [ ] **4.2 Agente Interfaz (MAGI):** MAGI recibe el "Plan de Intervención" en su prompt y se encarga puramente de traducirlo a una charla humana, empática y natural, ejecutando la estrategia sutilmente sobre varios mensajes.

---

## Notas y Riesgos
- **Riesgo Arquitectónico:** La proactividad (Bloque 3) requiere cuidado extremo para no generar bucles infinitos de auto-mensajes ni enviar spam al usuario. Requiere un *debounce* estricto y límites de frecuencia.
- **Riesgo de Personalidad:** La transición de reglas negativas a ejemplos (Few-shot) requiere encontrar los "Gold Standards" correctos para cada tipo de interacción.
