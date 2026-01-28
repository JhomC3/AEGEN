# ADR-0013: Arquitectura de Personalidad Adaptativa y Evolutiva (MAGI)

## Estado
Propuesto

## Contexto
MAGI es el agente conversacional principal de AEGEN. Se requiere que MAGI tenga una personalidad distintiva (inspirada en Clawdbot: casual, directa, con opiniones) pero que también sea capaz de adaptarse a cada usuario y evolucionar con el tiempo. Además, cuando MAGI activa un especialista (ej: TCC), debe adoptar un "overlay" de personalidad que modifique su tono sin perder su esencia base.

## Decisión
Se implementa una arquitectura de personalidad en 4 capas:

1.  **Capa Base (Inmutable):** Definida en archivos Markdown (`src/personality/base/`). Incluye el `SOUL.md` (ética y valores) e `IDENTITY.md` (quién es MAGI).
2.  **Capa de Adaptación (Por Usuario):** Almacenada en el perfil de Redis/Cloud del usuario (`personality_adaptation`). Incluye parámetros como `preferred_style`, `humor_tolerance` y `formality_level`.
3.  **Capa de Skill Overlay (Modular):** Modificadores específicos por especialista (`src/personality/skills/`). Permiten añadir instrucciones y tonos (ej: "Tough Love" para TCC) sobre la base de MAGI.
4.  **Capa Runtime:** Contexto dinámico como fecha, hora, canal y memoria episódica.

El `SystemPromptBuilder` es el encargado de componer estas capas en un único system prompt coherente para cada interacción.

## Consecuencias
- **Positivas:**
    - Experiencia de usuario personalizada y evolutiva.
    - Personalidad consistente a través de diferentes especialistas.
    - Facilidad para añadir nuevos especialistas con sus propios matices de personalidad.
- **Negativas:**
    - Mayor consumo de tokens debido a prompts más estructurados y detallados.
    - Mayor complejidad en la gestión del estado del perfil del usuario.

## Implementación Técnica
- **PersonalityManager:** Singleton para cargar y cachear archivos de personalidad.
- **SystemPromptBuilder:** Servicio para la composición dinámica de prompts.
- **ConsolidationManager:** Ahora incluye un paso de análisis de personalidad para aprender de las interacciones y actualizar el perfil del usuario.
- **Hybrid Activation:** Soporte para detección automática de intenciones y comandos explícitos (/tcc, /chat).
