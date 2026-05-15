# PLAN: Inteligencia Asimétrica y Alertas de LLM (ADR-0027)

> **Instrucciones para Agentes:**
> - Para **crear** o modificar este plan: Usar la skill `writing-plans`.
> - Para **ejecutar** este plan: Usar la skill `executing-plans` para proceder tarea por tarea con verificaciones intermedias.

- **Estado:** En Ejecución
- **Fecha:** 2026-05-13
- **Razón de Creación:** Refactorización Arquitectónica y Mejora de UX/Observabilidad.
- **ADR Relacionado:** `adr/ADR-0027-inteligencia-asimetrica.md`
- **Objetivo General:** Implementar una asignación de modelos LLM por especialidad (Groq para ruteo/velocidad, Minimax para razonamiento) y un sistema de alertas proactivas para administradores cuando un proveedor falla.

---

## Resumen Ejecutivo

Actualmente, AEGEN usa un único modelo monolítico (anteriormente Kimi K2 en Groq, que ha sido retirado) para todas las tareas. Esto causa problemas: si usamos un modelo pesado para ruteo, el bot es lento; si usamos uno ligero para terapia, pierde calidad. Además, cuando un modelo es retirado silenciosamente por el proveedor, nos enteramos muy tarde.

Este plan descentraliza el motor LLM (Groq para UX rápida, Minimax para análisis profundo, Gemini para RAG) e introduce un sistema de notificaciones de fallback que envía alertas directamente al Telegram del administrador.

---

## Análisis de Impacto

### Dependencias afectadas
- `src/core/config/base.py`: Nuevos modelos y variable `ADMIN_CHAT_ID`.
- `src/core/engine.py`: Refactorización de `_initialize_llm` a getters específicos.
- `src/core/observability/llm_wrapper.py`: Capacidad de inyectar el bus de eventos en el handler para emitir alertas.

### Cobertura de tests existente
- Se deberá actualizar `test_engine.py` (si existe) y mantener compatibilidad con Mypy en `src/`.

### Verificación del pipeline
- Confirmar que el `EnhancedRouter` usa el LLM rápido.
- Confirmar que `tcc_specialist` y `psicotrading_specialist` usan el LLM analítico.
- Confirmar que se recibe una alerta en Telegram simulando un fallo de OpenRouter.

---

## Fase 1: Configuración y Modelos Base

### Objetivo
Ajustar las variables de entorno y constantes para reflejar el mercado de Mayo 2026.

### Tareas
- [ ] Modificar `BaseAppSettings` en `src/core/config/base.py`.
- [ ] Actualizar `.env.example`.

## Fase 2: Refactor del Motor LLM (Engine)

### Objetivo
Desacoplar el singleton monolítico en fábricas de cadenas de modelos asimétricas.

### Tareas
- [ ] Modificar `src/core/engine.py` para exponer `get_fast_llm()` y `get_analytical_llm()`.
- [ ] Implementar envoltorio de captura de excepciones en la cadena de Fallback que publique en el bus.
- [ ] Actualizar `src/core/observability/llm_wrapper.py` para soportar la emisión de alertas al fallar un intento.

## Fase 3: Integración en Orquestadores y Skills

### Objetivo
Que cada agente consuma el LLM adecuado.

### Tareas
- [ ] Modificar `SpecialistCache` para usar `get_fast_llm()` en el ruteo.
- [ ] Modificar los tools de skills (`chat`, `tcc`, `psicotrading`) para instanciar su LLM específico.

## Fase 4: Alertas Admin (Out-of-band)

### Objetivo
Crear el suscriptor que envía notificaciones críticas.

### Tareas
- [ ] Crear `src/api/services/admin_notificator.py`.
- [ ] Integrar en `lifespan` (`src/main.py`).
