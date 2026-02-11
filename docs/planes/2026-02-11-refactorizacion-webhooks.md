# Plan de Refactorización: Saneamiento del Punto de Entrada (Webhooks)

> **Para Claude:** REQUERIMIENTO: Usar la habilidad `executing-plans` para implementar este plan tarea por tarea.

**Objetivo:** Reducir `src/api/routers/webhooks.py` de 402 líneas a menos de 100 líneas, aplicando el Principio de Responsabilidad Única (SRP) y la regla 100/20 de AEGEN.

**Impacto:** Mejora la mantenibilidad, facilita las pruebas unitarias del flujo de Telegram y estabiliza el punto de entrada de la aplicación.

---

## Fase 1: Extracción de Lógica de Procesamiento
Actualmente, `webhooks.py` contiene lógica de procesamiento de eventos, validación de firmas y gestión de tareas asíncronas.

### Tarea 1.1: Crear el Procesador de Eventos
**Archivo:** `src/api/routers/webhooks_logic.py`
- Mover la función `process_event_task` y sus dependencias internas.
- Asegurar que cada submétodo tenga menos de 20 líneas.

### Tarea 1.2: Crear el Gestor de Búfer
**Archivo:** `src/api/routers/webhooks_buffer.py`
- Mover la función `process_buffered_events` y la lógica de consolidación temporal.

---

## Fase 2: Saneamiento del Router Principal
Reducir `src/api/routers/webhooks.py` a su mínima expresión: definición de rutas y delegación inmediata.

### Tarea 2.1: Refactor de la Ruta POST
- Simplificar el endpoint `/telegram`.
- Mover la lógica de validación de `TelegramUpdate` a un validador especializado en `src/core/schemas/telegram.py` o un módulo nuevo.

---

## Fase 3: Verificación y Pruebas
1. Ejecutar `make verify`.
2. Ejecutar tests de integración: `pytest tests/integration/test_telegram_webhook.py`.

---
*Este plan sigue la máxima de "Planificación Primero" de AEGEN.*
