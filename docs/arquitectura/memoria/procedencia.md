# Procedencia de Datos (Provenance)

El sistema de procedencia garantiza que AEGEN sepa de dónde viene cada fragmento de información almacenado en su memoria, permitiendo un comportamiento fundamentado y seguro.

## 1. Clasificación de Origen (`source_type`)

Cada memoria se etiqueta con uno de los siguientes tipos:

- **`explicit`**: Información proporcionada directamente por el usuario (ej: "Me llamo Juan"). Máxima confianza.
- **`observed`**: Datos detectados por el sistema (ej: frecuencia de uso, zona horaria). Confianza verificable.
- **`inferred`**: Hipótesis generadas por la IA (ej: "Posible patrón de pensamiento todo-o-nada"). Requiere confirmación.

## 2. Confianza y Evidencia

Para las memorias de tipo `inferred`, el sistema almacena:
- **Confianza**: Un valor decimal (0.0 - 1.0) que indica la seguridad del LLM en su deducción.
- **Evidencia**: La cita textual del usuario que justifica la inferencia.

## 3. Seguridad Clínica

Las memorias con sensibilidad **Alta** (temas de salud mental o trauma) nunca se tratan como hechos definitivos si son `inferred`, activando bucles de confirmación en la conversación.

---
*Esquemas definidos en `src/core/schemas/common.py`*
