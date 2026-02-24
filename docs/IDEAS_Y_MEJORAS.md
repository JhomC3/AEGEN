# Notas de Mejora y Futuras Funcionalidades

Este archivo sirve como repositorio de ideas, feedback de usuario y ajustes de comportamiento deseados para futuras iteraciones de AEGEN/MAGI.

## 🧠 Personalidad y Comportamiento

### 1. Naturalidad en el Cierre (Anti-Robot)
- **Problema:** MAGI tiende a terminar casi todos sus mensajes con una pregunta reflexiva o de seguimiento. Esto se siente forzado y artificial ("muy de IA").
- **Mejora Deseada:**
    - Eliminar la obligatoriedad de preguntar al final.
    - Permitir cierres declarativos, silencios cómodos o simplemente acompañar sin demandar una respuesta inmediata.
    - Se siente más como un "compañero real" si no está constantemente interrogando.

## 📝 Gestión de Tareas y Estado

### 2. Verificación Explícita de Actividades (Task Tracking)
- **Problema:** El sistema a veces asume o infiere que una tarea sugerida ya se realizó, o sugiere nuevas actividades sin validar el estado de las anteriores.
- **Mejora Deseada:**
    - **No inferir completitud:** Si se sugiere "hacer respiraciones", el sistema debe mantener esa tarea como "pendiente" hasta que el usuario confirme explícitamente que la hizo.
    - **Bloqueo Secuencial:** Antes de sugerir una nueva actividad terapéutica o práctica, preguntar o verificar si se completó la anterior.
    - **Ejemplo:** "Antes de pasar a lo siguiente, ¿pudiste hacer los 2 minutos de respiración que hablamos?"

---
### 3. Agentes Especialistas de Análisis (Deep Analytics)
- **Concepto:** Crear agentes que no chatean, sino que analizan la base de datos de hitos en profundidad.
- **Ejemplo:** Un "Fitness Analytics Agent" que pueda graficar mentalmente el progreso de peso/repeticiones y sugerir ajustes en la carga de entrenamiento de forma científica.

### 4. Memoria Selectiva (Olvido Inteligente)
- **Concepto:** A medida que AEGEN recopila años de datos, no todo es relevante. Implementar un ranking de relevancia temporal para que MAGI no mencione cosas triviales de hace 3 años a menos que sean hitos fundacionales.
*
