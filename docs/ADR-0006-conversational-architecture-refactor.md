# ADR-0006: Refactorización de Arquitectura Conversacional

**Fecha:** 2025-01-21 → 2025-08-22
**Estado:** ✅ COMPLETADO - Implementación Exitosa
**Decisores:** Equipo AEGEN + Validación Expert (Gemini)

## Contexto y Problema

### Problema Identificado
Durante las pruebas de Phase 3B, se detectó un problema crítico de UX:

**Usuario pregunta:** "¿Estás? ¿Quién eres?"
**Respuesta actual:** "Soy tu agente de planificación y coordinación dentro del sistema AEGEN Deep Agents..."

### Análisis del Problema
1. **Exposición de Agentes Internos:** El usuario interactúa directamente con `PlannerAgent`, un componente técnico interno
2. **Experiencia No Conversacional:** Las respuestas son técnicas y frías, no naturales
3. **Arquitectura Rota desde UX:** El `ChatAgent` está desactivado, el `PlannerAgent` maneja eventos "text"
4. **Inconsistencia de Personalidad:** No hay una "voz" coherente del sistema

### Arquitectura Problemática Actual
```
Usuario → Telegram → Webhook → MasterOrchestrator → PlannerAgent → Usuario
                                                        ↑
                                                   Respuesta técnica
```

## Decisión Arquitectónica

### Solución: Delegación Jerárquica a través del Orchestrator

Implementar una arquitectura donde el `ChatAgent` sea **siempre** el punto de entrada para interacciones de texto del usuario, con capacidad de delegar tareas internas a especialistas.

### Nueva Arquitectura
```
Usuario → ChatAgent (SIEMPRE) → [Decide: ¿conversar o delegar?]
                               ↓
                    Si delega → MasterOrchestrator → PlannerAgent
                               ↓
                    Resultado ← PlannerAgent (JSON/estructurado)
                               ↓
                ChatAgent ← [Traduce a lenguaje natural]
                               ↓
                Usuario ← Respuesta conversacional natural
```

### Principios de Diseño
1. **Single Point of Entry:** `ChatAgent` es el único agente registrado para `event_type='text'`
2. **Conversational Layer:** Siempre respuesta natural, nunca técnica
3. **Internal Delegation:** Delega a especialistas pero traduce sus respuestas
4. **Separation of Concerns:** `PlannerAgent` para lógica, `ChatAgent` para UX

## Implementación

### Cambios Requeridos

#### 1. Registro de Especialistas
```python
# ANTES
ChatAgent: desactivado (comentado)
PlannerAgent: ["planning", "coordination", "text"]

# DESPUÉS
ChatAgent: ["text"] # ← Único agente para texto del usuario
PlannerAgent: ["internal_planning_request"] # ← Solo para delegación interna
```

#### 2. Flujo ChatAgent
```python
class ChatAgent:
    async def _chat_node(self, state: GraphStateV2):
        user_message = state["event"].content

        # Analizar intención
        if self._is_conversational(user_message):
            # Respuesta directa
            return await self._direct_response(user_message, state)
        else:
            # Delegar a especialista
            return await self._delegate_to_specialist(user_message, state)
```

#### 3. Protocolo de Delegación
```python
# ChatAgent delega creando evento interno
internal_event = CanonicalEventV1(
    event_type="internal_planning_request",
    content=user_message,
    # ... otros campos
)

# MasterOrchestrator enruta a PlannerAgent
result = await master_orchestrator.process_internal_event(internal_event)

# ChatAgent traduce resultado a lenguaje natural
natural_response = await self._translate_to_natural_language(result)
```

### Tipos de Evento

#### Eventos de Usuario (Públicos)
- `text` → `ChatAgent` (único punto de entrada)
- `audio` → `WhisperAgent`
- `document` → `DocumentAgent`

#### Eventos Internos (Privados)
- `internal_planning_request` → `PlannerAgent`
- `internal_analysis_request` → `AnalysisAgent` (futuro)
- `internal_code_request` → `CodeAgent` (futuro)

### Manejo de conversation_history

```python
# ✅ Se guarda en historial (visible al usuario)
Usuario: "Hola, ¿cómo estás?"
ChatAgent: "¡Hola! Estoy bien, gracias por preguntar..."

# ❌ NO se guarda en historial (comunicación interna)
ChatAgent → PlannerAgent: {"task": "schedule_meeting", "details": "..."}
PlannerAgent → ChatAgent: {"status": "success", "meeting_id": "123"}

# ✅ Se guarda en historial (respuesta final al usuario)
ChatAgent: "He agendado tu reunión para mañana a las 10 AM"
```

## Ventajas

### UX/Conversacional
- **Experiencia Natural:** Usuario siempre habla con la misma "personalidad"
- **Contextualidad:** Mantiene memoria conversacional coherente
- **Respuestas Amigables:** Nunca expone terminología técnica

### Arquitectural
- **Separation of Concerns:** `ChatAgent` = UX, `PlannerAgent` = Lógica
- **Encapsulamiento:** Agentes internos completamente ocultos
- **Escalabilidad:** Fácil agregar nuevos especialistas sin cambiar UX
- **Mantenibilidad:** Cambios internos no afectan experiencia de usuario

### Técnico
- **Reutiliza MasterOrchestrator:** No duplica lógica de enrutamiento
- **Protocolo Estándar:** Comunicación inter-agente bien definida
- **Error Handling:** ChatAgent maneja errores técnicos para el usuario

## Consideraciones

### Latencia
- **Mínima:** Solo un paso adicional de traducción
- **Cacheable:** Respuestas conversacionales simples no requieren delegación

### Complejidad
- **Justificada:** La complejidad adicional mejora drásticamente la UX
- **Localizada:** Toda la lógica de delegación está en ChatAgent

### Testing
- **Unit Tests:** Cada agente se puede probar independientemente
- **Integration Tests:** Flujo completo Usuario → ChatAgent → Especialista → Usuario
- **UX Tests:** Verificar que respuestas sean siempre conversacionales

## Implementación por Fases

### Fase 1: Base Architecture ✅
- [x] Reactivar `ChatAgent` para `event_type='text'`
- [x] Cambiar `PlannerAgent` a `event_type='internal_planning_request'`
- [x] Implementar lógica básica de delegación

### Fase 2: Enhanced Delegation 🔄
- [ ] Implementar clasificador de intenciones robusto
- [ ] Protocolo de comunicación inter-agente estándar
- [ ] Error handling conversacional

### Fase 3: Advanced Features 📋
- [ ] Context-aware delegation (memoria conversacional para decidir delegación)
- [ ] Multi-turn delegation (planes complejos que requieren múltiples turnos)
- [ ] Personality customization

## Métricas de Éxito

### UX Metrics
- [ ] **Response Tone Test:** 100% de respuestas son conversacionales
- [ ] **User Confusion Reduction:** Eliminar respuestas técnicas como "agente de planificación"
- [ ] **Conversation Flow:** Memoria conversacional coherente entre turnos

### Technical Metrics
- [ ] **Delegation Accuracy:** ChatAgent delega correctamente tareas complejas
- [ ] **Response Time:** < 3s para respuestas directas, < 10s para delegadas
- [ ] **Error Handling:** Errores técnicos traducidos a mensajes amigables

## Alternativas Consideradas

### Alternativa 1: Agente Monolítico + Herramientas
- **Rechazada:** Viola principio de especialistas autónomos
- **Razón:** Perdemos modularidad y estado de agentes especializados

### Alternativa 2: Router de Intenciones
- **Rechazada:** No garantiza respuestas conversacionales
- **Razón:** PlannerAgent seguiría respondiendo directamente al usuario

### Alternativa 3: Wrapper del MasterOrchestrator
- **Rechazada:** Ineficiente para conversaciones simples
- **Razón:** Latencia innecesaria para "Hola, ¿cómo estás?"

## Referencias
- [ADR-0004: MasterRouter Architecture](./ADR-0004-master-router-architecture.md)
- [ADR-0005: Phase 3B Conversational Memory](./ADR-0005-phase3b-conversational-memory.md)
- [Análisis con Gemini 2.5 Pro sobre Delegación Jerárquica](../logs/architecture-analysis-2025-01-21.md)

---

**Estado:** Este ADR está actualmente en implementación. La decisión fue tomada tras identificar problemas críticos de UX en Phase 3B y análisis profundo con expertos externos.
