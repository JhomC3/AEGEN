# ADR-0011: Message Bundling System - Intelligent Message Grouping

## Estado
**REVERTIDO** - La implementación fue retirada el 2026-01-22 para simplificar el flujo asíncrono y rediseñar la integración con Redis. Se mantiene el ADR como registro de decisión pero no está presente en el código actual.

## Contexto

### Problema Crítico Identificado
- **Sistema Asíncrono:** FastAPI + BackgroundTasks procesa cada mensaje independientemente
- **Resultado:** Mensajes consecutivos ("Hola", "¿Cómo estás?", "Me puedes ayudar") → respuestas desordenadas
- **Ineficiencia:** 3 mensajes = 3 llamadas LLM + 3 consultas Redis + 3 consultas ChromaDB
- **UX Degradada:** Sistema se siente fragmentado, no conversacional natural

### Situación Actual (Post Task #20)
✅ **Sistema Observabilidad:** LangSmith + Prometheus operacional
✅ **Performance:** ~2.3s response time estable
✅ **Infraestructura:** MessageQueueManager + Redis + BackgroundTasks disponibles
✅ **Correlation IDs:** Trazabilidad end-to-end implementada

### Oportunidad de Optimización
**Concepto:** Sistema de agrupación inteligente con pausa dinámica:
- **Input:** ["Hola", "¿Cómo estás?", "Me puedes ayudar"]
- **Output:** "Hola, estoy bien, ¿tú cómo estás? Claro que te puedo ayudar, dime con qué."
- **Beneficio:** 3 mensajes → 1 respuesta coherente, reduciendo 66% llamadas LLM/DB

## Decisión

### **Decisión 1: Message Bundling con Debounce Pattern**

**Implementar sistema "Message Bundling" server-side:**

```python
# Configuración MVP Conservador
DEBOUNCE_TIMEOUT = 1.5      # Segundos - balance UX/eficiencia
MAX_BATCH_SIZE = 3          # Límite para evitar respuestas excesivamente largas
MAX_BATCH_AGE = 5          # Segundos máximos batch lifetime absoluto
BURST_KEYWORDS = ["urgente", "emergencia", "ayuda"]  # Bypass inmediato
```

**Arquitectura Técnica:**
1. **Redis Buffer:** `user:{user_id}:message_buffer` con TTL automático
2. **Timer Management:** Background task cancellable con `asyncio.create_task()`
3. **FIFO Garantizado:** Extend existing `MessageQueueManager`
4. **Prompt Engineering:** LLM-specific prompt para sintetizar respuestas coherentes
5. **Fallback Robusto:** Individual message processing si batch fails

### **Decisión 2: Implementación por Fases**

**FASE 1 - MVP Pragmático (2-3 semanas):**
- Fixed-delay debounce (1.5s timeout)
- Redis-based message buffering
- Basic error handling con fallback individual
- Métricas performance + user experience

**FASE 2 - Optimización Inteligente (4-6 semanas):**
- Dynamic timeout basado en user behavior patterns
- Semantic grouping con NLP light
- Context awareness para conversation flow
- A/B testing para optimización timeout

### **Decisión 3: Estado Distribuido en Redis**

**Redis como Single Source of Truth para buffering:**

```python
# Redis Keys Structure
user:{user_id}:message_buffer    # Lista mensajes pendientes
user:{user_id}:bundle_timer      # Timestamp próximo procesamiento
user:{user_id}:bundle_metadata   # Metadata agrupación (correlation_ids, etc.)

# TTL Configuration
BUFFER_TTL = 10                  # Segundos máximos en buffer
TIMER_TTL = 8                    # Segundos máximos timer activo
```

**Justificación:**
- ✅ **Horizontal Scalability:** Funciona con múltiples instancias FastAPI
- ✅ **Persistence:** Sobrevive restart de aplicación
- ✅ **Consistency:** Single source of truth para state distribudo
- ✅ **Integration:** Leverages existing Redis infrastructure

## Alternativas Consideradas

### **Alternativa A: Client-Side Batching (RECHAZADA)**
- Usuario agrupa mensajes antes de enviar
- **Problema:** UX complejo, no funciona para todos los clients (Telegram), pérdida mensajes

### **Alternativa B: Strict FIFO Only (RECHAZADA)**
- Solo resolver orden, no agrupar mensajes
- **Problema:** Pierde beneficio eficiencia + UX coherencia, no reduce llamadas LLM/DB

### **Alternativa C: In-Memory Buffering (RECHAZADA)**
- Mantener buffer en memoria aplicación
- **Problema:** No escala horizontalmente, pérdida state en restart, complex synchronization

## Consecuencias

### **Positivas**
- ✅ **UX Mejorada:** Respuestas coherentes y ordenadas vs fragmentadas
- ✅ **Eficiencia Operacional:** 40%+ reducción llamadas LLM/DB (target)
- ✅ **Cost Optimization:** Menos API calls = menor costo operacional
- ✅ **Scalability:** Sistema maneja más usuarios concurrentes con mismos recursos
- ✅ **Conversational Flow:** Sistema se siente más natural e inteligente
- ✅ **Backward Compatible:** Zero breaking changes para specialists existentes

### **Negativas**
- ❌ **Latencia Percibida:** 1.5s delay puede sentirse lento vs respuesta inmediata
- ❌ **Implementation Complexity:** New layer en messaging pipeline
- ❌ **State Management:** Redis dependency crítica para buffering
- ❌ **Error Surface:** Más failure points (timer, buffer, batch processing)

### **Riesgos Mitigados**
- 🔶 **False Positives:** Limit batch size + bypass keywords + user feedback
- 🔶 **Batch Failures:** Individual message fallback + retry mechanism
- 🔶 **Resource Overhead:** Redis cleanup automático + monitoring
- 🔶 **User Confusion:** Typing indicators + progress feedback

## Plan de Implementación

### **Fase 1: MVP Foundation (2-3 semanas)**
**Objetivo:** Sistema básico message bundling funcional

**Semana 1:**
1. **Extend MessageQueueManager** con Redis buffer temporal
2. **Implement debounce timer** con `asyncio` cancellable tasks
3. **Create Redis buffer operations:** enqueue, dequeue, cleanup
4. **Basic timer cancellation** cuando nuevos mensajes llegan

**Semana 2:**
1. **Create batch processor** que handle múltiples mensajes → single response
2. **Implement prompt engineering** para respuestas coherentes de batch
3. **Basic error handling** con individual message fallback
4. **Integration con existing webhook flow**

**Semana 3:**
1. **Load testing** con concurrent users + burst scenarios
2. **Performance benchmarking** vs sistema actual
3. **Error case validation** (Redis unavailable, LLM errors, timeout issues)
4. **Initial user experience validation**

### **Fase 2: Optimización y Tuning (4-6 semanas)**
**Objetivo:** Sistema optimizado con intelligence + metrics

**Semanas 4-5:**
1. **Dynamic timeout** basado en user behavior patterns
2. **Semantic grouping** con NLP light para detectar messages relacionados
3. **Context preservation** mejorado entre batch messages
4. **Advanced error handling** con dead letter queue

**Semana 6:**
1. **A/B testing** timeout optimal per user segment
2. **Performance optimization** basado en real usage data
3. **User experience survey** y qualitative feedback
4. **Documentation completa** + runbooks operational

### **Acceptance Criteria**

#### **Fase 1 - MVP Must-Haves**
```bash
# Criterio 1: Message bundling funcional
user_sends_burst = ["Hola", "¿Cómo estás?", "Me puedes ayudar"]
response = await system.process_burst(user_sends_burst)
assert len(response.messages) == 1  # Single coherent response
assert "Hola" in response.content and "estoy bien" in response.content

# Criterio 2: Performance target
batch_processing_time = measure_batch_processing()
assert batch_processing_time < 2.0  # Includes 1.5s delay + processing

# Criterio 3: Error handling robusto
simulate_redis_failure()
response = await system.process_message("test message")
assert response.success == True  # Falls back to individual processing

# Criterio 4: Resource efficiency
llm_calls_before = count_llm_calls()
process_message_burst(3_messages)
llm_calls_after = count_llm_calls()
assert (llm_calls_after - llm_calls_before) == 1  # Single LLM call for batch
```

#### **Fase 2 - Optimization Should-Haves**
```bash
# Criterio 5: Intelligent timeout
short_burst = ["Hola", "¿Cómo estás?"]  # Should use shorter timeout
long_message = ["Explícame la teoría de cuerdas"]  # Should bypass bundling
assert get_timeout(short_burst) < get_timeout(long_message)

# Criterio 6: Context preservation
conversation_batch = ["Recuerdas mi nombre?", "Era John", "¿Lo recuerdas?"]
response = await process_batch(conversation_batch)
assert "John" in response.content  # Context preserved across batch
```

## Validación

### **Consensus AI Results (COMPLETADO)**
- [x] **Gemini 2.5 Pro (FOR - 9/10):** Altamente favorable, patrón debouncing probado
- [x] **Gemini 2.5 Flash (NEUTRAL - 8/10):** Factible con benefits significativos, warns sobre complexity
- [x] **Technical Feasibility:** Confirmado - leverages existing infrastructure
- [x] **Architecture Alignment:** Perfectamente alineado con filosofía AEGEN evolutiva

### **Métricas de Éxito Definidas**
- [ ] **LLM Call Reduction:** Target >40% menos API calls (Fase 1 deliverable)
- [ ] **User Experience:** Survey satisfaction antes/después (Fase 1 deliverable)
- [ ] **Response Time P95:** Mantener <3s total incluido delay (Fase 1 deliverable)
- [ ] **Error Rate:** <5% batch processing failures (Fase 1 deliverable)

### **Risk Assessment**
- [ ] **Performance Impact:** <10% degradation baseline durante load testing
- [ ] **Resource Usage:** Memory/CPU overhead monitoring + alerting
- [ ] **User Adoption:** Beta testing con subset usuarios + feedback collection
- [ ] **Rollback Plan:** Feature flag + immediate fallback a processing individual

## Rollback Plan

**Si implementación falla o métricas no se cumplen:**

1. **Immediate (5 min):** Feature flag disable Message Bundling
2. **Short-term (30 min):** Revert webhook processing a individual messages
3. **Long-term (1 week):** Analyze failure data + re-approach con lessons learned
4. **Net Positive:** Keep infrastructure improvements (Redis optimizations, monitoring)

**Rollback Triggers:**
- Error rate >10% during processing
- User complaints >5% beta group
- Performance degradation >20% baseline
- Redis resource exhaustion

## Performance Expectations

| Metric | Current (Individual) | Target (Bundled) | Improvement |
|--------|---------------------|------------------|-------------|
| LLM API Calls | 3 calls/3 messages | 1 call/3 messages | 66% reduction |
| Total Response Time | ~2.3s immediate | ~3.8s (1.5s + 2.3s) | User experience trade-off |
| Message Ordering | Out-of-order possible | Guaranteed FIFO | 100% improvement |
| Resource Usage | High concurrent load | Reduced by bundling | 40%+ improvement |
| User Experience | Fragmented responses | Coherent conversations | Qualitative improvement |

---

**Decision Date**: 2025-01-08
**Status**: ACEPTADO - Consenso AI favorable, implementación Fase 1 autorizada
**Priority**: 🔴 HIGH - Soluciona problema crítico UX + optimización significativa
**Dependencies**: Task #20 (Observabilidad LLM - COMPLETADO)
**Next Review**: End of Fase 1 (3 semanas) - Validar MVP antes Fase 2
**Task ID**: #23 en master task list
