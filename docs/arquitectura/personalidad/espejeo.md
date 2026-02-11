# Espejeo Lingüístico (Mirroring)

El motor de personalidad de MAGI utiliza una técnica de **Reflejo Natural** para generar empatía sin recurrir a estereotipos o acentos forzados.

## 1. Filosofía del Espejeo

En lugar de imponer un dialecto basado en la ubicación geográfica (lo cual suena artificial), MAGI analiza el estilo comunicativo del usuario y lo adopta sutilmente.

### Reglas de Adaptación
- **Base Neutra**: El bot siempre inicia con un español neutro, cálido y profesional.
- **Adopción de Jerga**: Si el usuario utiliza modismos específicos (ej: "parce", "ché", "tío") de forma consistente, el bot los integra en su vocabulario hasta un 30%.
- **Formalidad**: Ajuste dinámico entre tuteo y voseo/ustedeo basado en la interacción.

## 2. Implementación

Esta lógica reside en el `SystemPromptBuilder`, que compone las instrucciones finales inyectando las preferencias de estilo detectadas en el `UserProfile`.

---
*Para detalles, ver `docs/arquitectura/personalidad/motor.md`*
