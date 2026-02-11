# ADR-0016: Localización Inteligente V2 y Perfilamiento Proactivo

## Estado
Aceptado (Enero 2026)

## Contexto
Aunque el sistema ya tenía una localización básica (ADR-0015), presentaba limitaciones:
1. **Detección Rígida:** Se basaba solo en metadatos de Telegram, que a menudo son insuficientes (ej: `language_code="es"` sin país).
2. **Jerga Default:** Al no detectar país, el LLM usaba su sesgo default (jerga argentina) con usuarios de otros países (ej: Colombia).
3. **Falta de Matices:** No había distinción regional (Bogotá vs Medellín vs Cali), lo cual es clave para la cercanía en Colombia.
4. **Error de Routing:** El LLM devolvía a veces el nombre de la herramienta (`tool`) en lugar del especialista, causando fallos de enrutamiento.

## Decisiones

### 1. Módulo de Localización Extendido
Se crea `src/core/localization.py` con una base de datos de países, zonas horarias y regiones.
- **Mapeo de Regiones:** Se incluyen ciudades principales de Colombia (Bogotá, Medellín, Cali, etc.) con sus dialectos específicos (rolo, paisa, caleño).
- **Zonas Horarias Precisas:** Asignación automática de `America/Bogota` y otras IANA timezones.

### 2. Sistema de Perfilamiento Proactivo
Se implementa `ProfilingManager` para:
- **Detección en Diálogo:** Analizar pasivamente el texto buscando confirmación de ubicación (ej: "Estoy en Medellín").
- **Hints de Pregunta:** Si la ubicación no está confirmada, inyectar un "hint" en el System Prompt para que MAGI pregunte de forma natural durante la conversación.

### 3. Personalidad MAGI y Mimetismo (Mirroring)
Se actualiza `SystemPromptBuilder` para incluir:
- **Mirroring (~30%):** Instrucción explícita de observar el vocabulario del usuario y mimetizar jerga local suavemente para crear afinidad, sin perder la esencia MAGI.
- **Hora Local Dinámica:** Inyección de la hora exacta del usuario basada en su zona horaria configurada.

### 4. Traducción Tool -> Specialist en Router
Se modifica `RoutingAnalyzer` para resolver automáticamente nombres de herramientas a sus especialistas dueños, eliminando el bug de "Specialist no disponible".

### 5. Optimización de Sincronización
Los cambios de localización pasiva (basados en metadatos de cada mensaje) solo se guardan en Redis. Solo las confirmaciones explícitas del usuario se sincronizan con la nube (Google Cloud), reduciendo latencia y ruido.

## Consecuencias

### Positivas
- **Cercanía Extrema:** MAGI ahora puede saludar adecuadamente según la hora local y usar modismos regionales si el usuario los inicia.
- **Robustez de Routing:** Eliminación de fallos cuando el LLM selecciona una herramienta.
- **Perfil Evolutivo:** El sistema aprende del usuario de forma natural.

### Riesgos
- **Complejidad de Dialectos:** Mantener una base de datos de dialectos regionales requiere actualización constante.
- **Falsos Positivos:** La detección pasiva de ubicación en texto podría fallar si el usuario menciona una ciudad por otros motivos.
