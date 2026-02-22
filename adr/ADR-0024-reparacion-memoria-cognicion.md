# ADR-0024: Reparación de Memoria y Cognición (Post-Mortem v0.7.2)

- **Fecha:** 2026-02-12
- **Estado:** Aceptado

## Contexto

El informe forense `v0.7.2-analisis-forense-alucinaciones.md` documentó un fallo
en cascada con 4 vectores de ataque: (A) JSON corrupto en SQLite causando amnesia
total del perfil, (B) hechos inferidos por el LLM almacenados como datos confirmados
causando alucinaciones persistentes, (C) el Router cambiando de especialista
terapéutico a genérico durante una crisis, y (D) saturación de API por tareas de
fondo retrasando la autocorrección.

## Decisión

1. **Resiliencia JSON**: Añadir sanitización (`ast.literal_eval` fallback +
   regex de comillas) y validación Pydantic en `ProfileRepository.load_profile()`
   y `KnowledgeBaseManager.load_knowledge()`. Nunca retornar `None` sin intentar
   reparación.

2. **Solo Hechos Explícitos**: Modificar el prompt de `FactExtractor` para
   prohibir la clasificación `inferred`. Solo se almacenan datos que el usuario
   dijo literalmente (`explicit`). Añadir filtro de `confidence >= 0.8` antes
   de guardar.

3. **Sesión Terapéutica Sticky**: Introducir el concepto de `active_therapeutic_session`
   en el Router. Cuando CBT está activo y el usuario expresa frustración/queja,
   se mantiene en CBT con acción `handle_resistance` en vez de redirigir a Chat.

4. **Regulación de Tareas de Fondo**: Añadir un semáforo
   (`asyncio.Semaphore(1)`) en la extracción incremental para limitar
   la concurrencia a una sola tarea, descartando invocaciones redundantes
   y evitando saturación de cuota API.

## Consecuencias

### Positivas
- Eliminación de amnesia por errores de formato JSON.
- Eliminación de alucinaciones persistentes por hechos inferidos.
- Continuidad terapéutica durante sesiones CBT.
- Estabilidad de API bajo carga.

### Negativas
- Pérdida de hechos que antes se inferían (el sistema "aprende" más lento).
- Mayor rigidez en el routing (el usuario debe usar `/chat` para cambiar explícitamente).
