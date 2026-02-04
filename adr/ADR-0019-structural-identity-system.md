# ADR-0019: Structural Identity System

## Contexto y Problema
MAGI presentaba "amnesia de identidad" en dos niveles:
1. No aprovechaba el nombre proporcionado por la plataforma (Telegram `first_name`) en el primer contacto.
2. No sincronizaba los nombres aprendidos durante la conversación (extraídos por `FactExtractor`) con el perfil persistente del usuario, lo que obligaba a MAGI a preguntar el nombre repetidamente o a usar el default "Usuario".

## Decisión
Implementar un **Sistema de Identidad Estructural** con tres capas de verdad:
1. **Seed de Plataforma (Nivel 1)**: Captura inicial del nombre desde el webhook para evitar el anonimato total. Solo se aplica si el nombre actual es el default.
2. **Aprendizaje Conversacional (Nivel 2)**: El `FactExtractor` busca activamente el nombre del usuario en el texto.
3. **Sincronización de Perfil (Nivel 3)**: Un flujo unidireccional `Knowledge Base (KB) -> Profile`. Los hechos confirmados en la KB sobre la identidad sobrescriben el caché del perfil.

## Consecuencias
- **Positivas**: MAGI se siente más inteligente y personal. Se elimina el hardcode de IDs de administrador.
- **Neutrales**: Mayor carga en el `ConsolidationWorker` (una operación extra de Redis por consolidación).
- **Negativas**: Ninguna identificada.

## Estado
Aceptado e Implementado (v0.2.2)
