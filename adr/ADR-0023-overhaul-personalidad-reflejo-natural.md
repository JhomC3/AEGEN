# ADR-0023: Overhaul de Personalidad y Reflejo Natural

> **Estado:** Aceptado
> **Fecha:** 11 de Febrero, 2026
> **Autor:** AEGEN/MAGI
> **Implementa:** Plan A.3 (v0.7.0)

## Contexto

El sistema de personalidad de MAGI dependía de reglas rígidas y una instrucción de "Mirroring (~30%)" vaga en el prompt. Esto causaba dos problemas principales:
1.  **Falsos Acentos:** Al pedirle al LLM que "observara el vocabulario", a veces asumía dialectos incorrectos (ej. hablar como argentino a un mexicano solo por usar palabras comunes).
2.  **Inconsistencia:** La personalidad variaba demasiado entre sesiones y especialistas (Chat vs TCC).

La investigación de **OpenClaw (Soul Stack)** sugiere una arquitectura por capas donde la identidad base es inmutable, pero la presentación es adaptable.

## Decisión

Adoptamos el principio de **"Dialecto Confirmado vs. Estilo Detectado"**:

1.  **Neutralidad Cálida y Eco Léxico (Default):**
    *   Si no hay preferencia explícita, MAGI usa un **Español Latinoamericano Estándar** (neutro pero cercano, no robótico).
    *   **Eco Léxico:** MAGI adopta el vocabulario específico del usuario (sustantivos/verbos) para generar sintonía sin fingir acentos.

2.  **Preferencia Explícita:**
    *   El usuario puede definir un `preferred_dialect`.
    *   La ubicación (`country_code`) sirve para *sugerir* pero no imponer.
    *   MAGI nunca infiere el dialecto; lo obedece si está configurado.

3.  **Estilo Detectado (Reflejo Natural):**
    *   MAGI analizará mediante heurísticas en Python (`StyleAnalyzer`) señales de estilo: formalidad, brevedad, uso de emojis.
    *   Esto permite adaptarse a *cómo* habla el usuario (serio/jocoso) sin arriesgarse a fingir un acento falso.

4.  **Simplificación de Arquitectura (Post-Auditoría):**
    *   Se descarta inicialmente el `PersonaSynthesizer` (LLM Razonador) para reducir latencia y costos, optando por un ensamblaje modular determinista de alta calidad.

5.  **Arquitectura Soul Stack (5 Capas):**
    *   **Capa 1 (Identity):** Inmutable. MAGI como amigo cercano y apoyo honesto.
    *   **Capa 2 (Soul):** Inmutable. Valores éticos, "Eco Léxico" y compromiso de utilidad.
    *   **Capa 3 (Mirror):** Dinámica. Inyecta preferencias explícitas y estilo detectado por Python.
    *   **Capa 4 (Skill):** Dinámica. Reglas del rol activo (Chat, TCC con Firmeza Benevolente).
    *   **Capa 5 (Runtime):** Contexto temporal, memoria episódica y RAG.

## Consecuencias

### Positivas
*   Elimina la vergüenza ajena de los "acentos falsos" de la IA.
*   Mayor coherencia en todos los especialistas.
*   Adaptación natural al nivel de formalidad del usuario.
*   **Baja Latencia:** El ensamblaje en Python es instantáneo comparado con una síntesis vía LLM.

### Negativas
*   Requiere que el usuario confirme su preferencia para tener la experiencia "localizada" completa.
*   El prompt resultante es una concatenación de bloques; requiere una redacción muy cuidadosa en los archivos Markdown para evitar redundancias.

## Estado de Implementación
Finalizado el 12 de Febrero, 2026.
