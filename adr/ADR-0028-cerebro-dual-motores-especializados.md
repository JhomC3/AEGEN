# ADR-0028 - Arquitectura de Cerebro Dual y Especialización de Motores LLM

- **Fecha:** 2026-02-22
- **Estado:** Propuesto

## Contexto

Actualmente, AEGEN utiliza una única instancia de LLM (el singleton `llm` en `src/core/engine.py`) para todas las tareas: desde chatear empáticamente con el usuario hasta extraer hitos estructurados en JSON. 
Esta arquitectura presenta dos problemas críticos:
1. **Contaminación de Contexto:** Al enviar las instrucciones de personalidad ("Soul Stack") en cada mensaje, los modelos de extracción (como Kimi K2) se confunden y devuelven texto conversacional en lugar de esquemas JSON válidos, rompiendo la persistencia de memoria.
2. **Latencia Inestable:** Los timeouts actuales son demasiado largos (60s), lo que bloquea al usuario si el proveedor de IA tiene un fallo momentáneo.

## Decisión

Implementaremos el patrón de **Cerebro Dual (Dual Brain)**, separando la inferencia en dos motores especializados:

1. **llm_chat (Motor Conversacional):**
   - **Modelo:** Kimi K2 (vía Groq).
   - **Timeout:** 10 segundos.
   - **Propósito:** Responder al usuario final inyectando el "Soul Stack" completo.
   - **Resiliencia:** Fallback automático a Gemini 2.5 Flash.

2. **llm_core (Motor Estructural):**
   - **Modelo:** `gpt-oss-120b` (vía Groq).
   - **Timeout:** 15 segundos.
   - **Formato:** `response_format: {"type": "json_object"}`.
   - **Propósito:** Tareas puramente técnicas (Milestone Extraction, Reflection Node, Life Reviewer).
   - **Aislamiento:** Este motor **NO** recibirá instrucciones de personalidad ni Gold Standards conversacionales.

## Consecuencias

### Positivas
- **Estabilidad de Datos:** Al usar un modelo de 120B para JSON y eliminar el ruido de la personalidad, los errores de formato se reducirán en un 99%.
- **UX más rápida:** Los timeouts de 10s garantizan que el usuario siempre reciba una respuesta rápida (ya sea de Groq o de Gemini).
- **Separación de Preocupaciones:** Permite evolucionar la personalidad de MAGI sin romper los procesos de fondo del sistema.

### Negativas / Riesgos
- **Consumo de Cuota:** Duplicamos el número de llamadas a Groq (una para chatear, otra para extraer hitos). Se requiere monitoreo de límites de RPM/TPM.
- **Complejidad en Engine:** El archivo `src/core/engine.py` se vuelve un poco más complejo al gestionar múltiples instancias y fallbacks.
