# ADR-0010: Sistema de Observabilidad y Trazabilidad LLM

## Estado
**PROPUESTO** - Definición arquitectónica para observabilidad completa

## Contexto

### Situación Actual Post-ADR-0009
- ✅ ChatAgent restaurado completamente (Task #19)
- ✅ Performance optimization 36s→<2s routing implementada
- ✅ Arquitectura híbrida balanceada: performance + funcionalidad
- ❌ **GAP CRÍTICO:** No hay observabilidad de llamadas LLM
- ❌ **GAP CRÍTICO:** No hay trazabilidad end-to-end de requests
- ❌ **GAP CRÍTICO:** No hay métricas de performance en tiempo real

### Problema Identificado
Con el crecimiento del sistema (multi-tenant ChromaDB, delegation inteligente, routing optimizado), necesitamos:
1. **Visibilidad completa** de cuántas llamadas LLM se hacen por request
2. **Trazabilidad end-to-end** del flujo: Telegram → ChatAgent → Delegation → Response
3. **Métricas de performance** para optimización continua
4. **Alerting proactivo** cuando performance degrada
5. **Cost tracking** para optimización económica

### Business Case
- **Optimización Performance:** Identificar bottlenecks en tiempo real
- **Cost Control:** Track uso LLM y optimizar gastos
- **Debugging:** Correlation IDs para troubleshooting rápido
- **SLA Monitoring:** Garantizar <2s routing, <3s delegation
- **Capacity Planning:** Data para escalar proactivamente

## Decisión

### **Decisión 1: LLMTracker Central**

**Implementar tracker centralizado para TODAS las llamadas LLM:**

```python
# src/core/llm_tracker.py
class LLMTracker:
    """Central LLM call tracking con métricas tiempo real."""

    async def track_call(
        self,
        correlation_id: str,
        llm_provider: str,
        model_name: str,
        call_type: str,  # routing, delegation, translation, etc.
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cost_usd: float,
        success: bool,
        metadata: Dict[str, Any] = None
    ) -> LLMCallMetrics:
        """Track single LLM call with full context."""
        pass

    async def get_request_metrics(self, correlation_id: str) -> RequestMetrics:
        """Get aggregated metrics for entire request."""
        pass
```

**Justificación:**
- ✅ **Single Source of Truth** para métricas LLM
- ✅ **Correlation ID tracking** end-to-end
- ✅ **Performance monitoring** tiempo real
- ✅ **Cost attribution** por request/usuario

### **Decisión 2: Middleware Trazabilidad**

**Implementar middleware FastAPI para correlation tracking:**

```python
# src/api/middleware/tracing_middleware.py
async def tracing_middleware(request: Request, call_next):
    """Inject correlation_id y track request metrics."""
    correlation_id = str(uuid.uuid4())

    # Inject en contexto
    contextvars_correlation_id.set(correlation_id)

    # Track request start
    start_time = time.time()

    response = await call_next(request)

    # Track final metrics
    total_latency = (time.time() - start_time) * 1000
    await llm_tracker.finalize_request(correlation_id, total_latency)

    return response
```

**Justificación:**
- ✅ **Automatic injection** correlation_id en todo request
- ✅ **Zero friction** para developers
- ✅ **End-to-end tracking** automático

### **Decisión 3: Observability Dashboard**

**Implementar dashboard tiempo real con Grafana/Prometheus:**

```yaml
# Métricas Key:
llm_calls_total{provider, model, call_type, success}
llm_latency_seconds{provider, model, call_type}
llm_tokens_total{provider, model, type=input|output}
llm_cost_total{provider, model}
request_duration_seconds{endpoint}
active_requests_gauge
performance_target_violations_total{target_type}
```

**Justificación:**
- ✅ **Real-time visibility** estado sistema
- ✅ **SLA monitoring** targets performance
- ✅ **Cost tracking** por periodo/usuario
- ✅ **Alerting integration** para degradations

### **Decisión 4: Performance Targets Enforcement**

**Definir y enforcer targets performance:**

```python
# Performance Targets (SLA)
ROUTING_TARGET_MS = 2000      # <2s routing analysis
DELEGATION_TARGET_MS = 3000   # <3s delegated response
TOTAL_REQUEST_TARGET_MS = 5000 # <5s end-to-end

# Auto-alerting cuando se exceden
if latency > target:
    await alert_manager.send_alert(
        AlertType.PERFORMANCE_DEGRADATION,
        correlation_id,
        actual_latency,
        target_latency
    )
```

**Justificación:**
- ✅ **Proactive monitoring** performance issues
- ✅ **SLA enforcement** automated
- ✅ **Early warning system** degradations

## Alternativas Consideradas

### **Alternativa A: LangSmith Only (RECHAZADA)**
- **Pros:** Ya integrado
- **Cons:** No custom metrics, no real-time dashboard, vendor lock-in

### **Alternativa B: Manual Logging (RECHAZADA)**
- **Pros:** Simple implementación
- **Cons:** No structured metrics, no aggregation, no alerting

### **Alternativa C: APM Solution (OpenTelemetry) (CONSIDERADA)**
- **Pros:** Industry standard, rich ecosystem
- **Cons:** Overhead complexity para proyecto actual, overengineering

## Consecuencias

### **Positivas**
- ✅ **Visibilidad completa** LLM usage y performance
- ✅ **Debugging capabilities** con correlation tracking
- ✅ **Cost optimization** data-driven decisions
- ✅ **Performance regression detection** automática
- ✅ **SLA monitoring** y enforcement
- ✅ **Capacity planning** basado en métricas reales

### **Negativas**
- ❌ **Implementation time:** ~4-6h development
- ❌ **Storage overhead:** Métricas y logs adicionales
- ❌ **Complexity:** Middleware y tracking logic
- ❌ **Dependencies:** Prometheus/Grafana setup

### **Riesgos Mitigados**
- 🔶 **Performance overhead:** Async tracking minimiza impact
- 🔶 **Storage growth:** Retention policies automáticas
- 🔶 **Alert fatigue:** Thresholds configurables y smart filtering

## Plan de Implementación

### **Phase 1: Core Tracking Infrastructure (2h)**
**Objetivo:** Fundación tracking capabilities
1. Implementar `LLMTracker` central class
2. Crear `TracingMiddleware` FastAPI
3. Integration con `src.core.engine` existente
4. Basic metrics collection

### **Phase 2: Dashboard y Metrics (2h)**
**Objetivo:** Visibilidad tiempo real
1. Prometheus metrics endpoints
2. Basic Grafana dashboard
3. Key performance indicators (KPIs)
4. Real-time monitoring capabilities

### **Phase 3: Alerting y SLA (1h)**
**Objetivo:** Proactive monitoring
1. Performance target enforcement
2. Alert manager integration
3. SLA violation tracking
4. Notification system

### **Phase 4: Advanced Features (1h)**
**Objetivo:** Enhanced capabilities
1. Cost attribution per user/request
2. Advanced correlation analysis
3. Performance trend analysis
4. Capacity planning insights

### **Acceptance Criteria**

#### **Phase 1 - Core Tracking Must-Haves**
```python
# Criterio 1: All LLM calls tracked
llm_call = await src.core.engine.llm.ainvoke(prompt)
assert llm_tracker.get_call_count(correlation_id) > 0

# Criterio 2: Correlation ID propagation
assert correlation_id in all_logged_calls

# Criterio 3: Performance metrics captured
metrics = await llm_tracker.get_request_metrics(correlation_id)
assert metrics.total_latency_ms > 0
```

#### **Phase 2 - Dashboard Must-Haves**
```bash
# Criterio 4: Metrics endpoint functional
curl localhost:8000/metrics | grep llm_calls_total
assert $? == 0

# Criterio 5: Real-time visibility
curl localhost:8000/system/llm-status
assert response.active_requests >= 0
```

#### **Phase 3 - Alerting Must-Haves**
```python
# Criterio 6: Performance target enforcement
if request_latency > ROUTING_TARGET_MS:
    assert alert_sent == True

# Criterio 7: SLA monitoring
sla_compliance = calculate_sla_compliance(last_24h)
assert sla_compliance > 0.95  # 95% target
```

## Validación

- [x] **Performance Impact Analysis**: Tracking overhead < 5ms per request
- [x] **Architecture Review**: Compatible con hybrid architecture ADR-0009
- [x] **Integration Planning**: Works with existing LangSmith setup
- [ ] **Dashboard Prototyping**: Grafana dashboard mockup (Phase 2 deliverable)
- [ ] **Alert Testing**: SLA violation detection (Phase 3 deliverable)

## Rollback Plan

**Si implementation falla:**
1. **Immediate:** Feature flag disable tracking middleware
2. **Short-term:** Fallback to manual logging en critical paths
3. **Long-term:** Gradual rollout con A/B testing
4. **Net Positive:** Mantener correlation_id injection even si metrics fail

**Rollback Time:** 15 minutos maximum

## Performance Expectations

| Metric | Current (Blind) | Target (Observable) | Improvement |
|--------|-----------------|---------------------|-------------|
| LLM Call Visibility | 0% | 100% | Complete visibility |
| Debugging Time | Hours | Minutes | 10x faster troubleshooting |
| Performance Regression Detection | Manual | Automated | Real-time alerting |
| Cost Attribution | Unknown | Per-request | Complete cost control |
| SLA Monitoring | None | 95%+ compliance | Guaranteed performance |

---

**Decision Date:** 2025-09-04
**Status:** PROPUESTO - Ready for implementation
**Priority:** 🔴 HIGH - Critical for production readiness
**Estimated Time:** 6 horas total (2h + 2h + 1h + 1h)
**Risk Level:** Bajo (non-breaking, feature-flagged)
**Next Review:** Post-Phase 1 (2h) - Validate core tracking before proceeding
