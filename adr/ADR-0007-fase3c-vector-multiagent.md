# ADR-0007: Fase 3C - Vector DB Multi-Tenant + Agentes Modulares

## Estado
**ACEPTADO** - Validado por consensus AI (3 modelos), implementar con approach por fases

## Contexto

### Situación Actual (Fase 3B Completada)
- ✅ Sistema conversacional funcional con ChatAgent → MasterOrchestrator → Specialists
- ✅ Memoria Redis para sesiones conversacionales (TTL 1h)
- ⚠️ VectorMemoryManager como Interface/Stub (Pendiente implementación real ChromaDB)
- ✅ LangSmith observabilidad operacional

### Problema a Resolver
El branch `feature/phase3c-vector-multiagent` indica la dirección estratégica, pero la implementación actual de ChromaDB es insuficiente para escalar:

1. **No Multi-Tenancy**: Todos los usuarios comparten collection "telegram_data"
2. **Privacidad Comprometida**: Usuario A puede acceder datos de Usuario B
3. **Agentes Rígidos**: Especialistas actuales son específicos, no modulares
4. **Memoria Limitada**: Solo Redis sesión, no contexto vectorial persistente

### Objetivo Fase 3C
Implementar base vectorial multi-tenant con agentes modulares que se compongan dinámicamente según caso de uso.

## Decisión

### **Decisión 1: Multi-Tenant Vector Database (MODIFICADA - Approach Incremental)**

**FASE 1 - Adoptamos ChromaDB con metadata filtering (Semanas 1-3):**

```python
# Estructura collections simplificada
COLLECTIONS = {
    "user_{user_id}": "Toda data del usuario",
    "shared_knowledge": "Knowledge base compartida"
}

# Metadata filtering para data types
metadata = {
    "user_id": "123",
    "data_type": "conversation|document|preference",
    "session_id": "conv_456",
    "timestamp": "2025-08-25T10:00:00Z"
}
```

**FASE 2 - Evolution a collections granulares SI performance lo requiere (Semanas 7-8):**
```python
# Solo si testing demuestra necesidad
"user_123_conversations"     # Si > 10k items per user
"user_123_documents"         # Si documentos requieren embeddings diferentes
```

**Justificación Revisada:**
- ✅ **Start Simple**: Metadata filtering reduce operational overhead inicial
- ✅ **Privacidad Garantizada**: Collection per user mantiene isolation
- ✅ **Performance Validation**: Scale granular solo con data real
- ✅ **Migration Path**: Clear evolution path si collection sprawl needed

### **Decisión 2: Agentes Modulares Componibles (MODIFICADA - Build Incremental)**

**FASE 1 - Interface Foundation (Semanas 1-3):**
```python
# Base interface robusta y extensible
class BaseModularAgent(Protocol):
    async def execute(self, input_data: Any, context: AgentContext) -> AgentResult
    def get_capabilities(self) -> List[str]
    def can_handle(self, task_type: str) -> bool
    # CRÍTICO: Interface debe ser estable desde el inicio
```

**FASE 2 - Core Agents (Semanas 4-6):**
```python
# Implementar SOLO 2 agentes bien diseñados primero
FileHandlerAgent      # Subida/validación/parsing archivos
NLPParserAgent       # Procesamiento lenguaje natural

# NO implementar aún:
# DataProcessorAgent, MemoryManagerAgent (Fase 3)
```

**FASE 3 - Composition Engine (Semanas 7-8):**
```python
# Solo después de validar agents individuales
class SimpleComposer:
    def compose_for_task(self, task_type: str) -> List[BaseModularAgent]
    # Start configuration-driven, evolve hacia dynamic orchestration
```

**Justificación Revisada:**
- ✅ **Interface First**: BaseModularAgent estable previene refactoring
- ✅ **Prove Value**: 2 agents funcionando > 4 agents half-working
- ✅ **Composition Later**: Solo compose cuando individual agents validated
- ✅ **Avoid Over-Engineering**: Build complexity cuando se necesite, no before

### **Decisión 3: Hybrid Memory Architecture**

**Mantenemos Redis + añadimos Vector Memory:**

```python
# Redis: Memoria sesión corto plazo (1h TTL)
SessionMemory = {
    "conversation_state": {...},
    "active_agents": [...],
    "current_workflow": {...}
}

# ChromaDB: Memoria contexto largo plazo (persistente)
VectorMemory = {
    "conversation_embeddings": [...],
    "document_embeddings": [...], 
    "user_preferences": {...}
}
```

**Justificación:**
- ✅ **Best of Both**: Redis rápido para sesión, Vector para contexto semántico
- ✅ **Performance**: No overload ChromaDB con datos temporales
- ✅ **Consistency**: Redis proven, Vector DB complemento

### **Decisión 4: Agent Composition Engine (MODIFICADA - Simple First)**

**FASE 1-2 - Sequential Execution Simple (Semanas 1-6):**
```python
# NO AgentComposer complejo aún - solo sequential execution
async def execute_file_workflow(file_data, user_id):
    context = AgentContext(user_id=user_id, ...)
    
    # Simple sequential execution
    parsed_file = await FileHandlerAgent().execute(file_data, context)
    analysis = await NLPParserAgent().execute(parsed_file, context)
    return analysis
```

**FASE 3 - Simple Composer (Semanas 7-8):**
```python
class SimpleComposer:
    """Configuration-driven composition, no dynamic orchestration yet."""
    
    WORKFLOWS = {
        "file_analysis": [FileHandlerAgent, NLPParserAgent],
        "chat": [NLPParserAgent],  # Start simple
        # Add more as needed, don't over-engineer
    }
    
    def compose_for_task(self, task_type: str) -> List[BaseModularAgent]
    async def execute_workflow(self, agents: List[BaseModularAgent], input_data, context)
```

**Justificación Revisada:**
- ✅ **Start Without Composition**: Sequential execution validates agents independently
- ✅ **Configuration-Driven**: Simple workflows before dynamic orchestration  
- ✅ **Prove Need**: Only add composition complexity when simple approach insufficient
- ✅ **Incremental Complexity**: Build orchestration features when actual use cases require them

## Alternativas Consideradas

### **Alternativa A: Single Agent Approach (RECHAZADA)**
- Crear InventoryAgent monolítico específico
- **Problema**: No escalable, difícil de testear, no reutilizable

### **Alternativa B: PostgreSQL + pgvector (RECHAZADA)**  
- Cambiar ChromaDB por PostgreSQL con extensión vector
- **Problema**: Introduce nueva dependencia, ChromaDB ya funciona

### **Alternativa C: All-in-Redis (RECHAZADA)**
- Usar Redis para vector search con RediSearch
- **Problema**: Redis no optimizado para embeddings, overhead

## Consecuencias

### **Positivas**
- ✅ **Privacidad**: Usuarios no pueden acceder datos de otros
- ✅ **Escalabilidad**: Collections independientes escalan linealmente  
- ✅ **Modularity**: Agentes reutilizables para múltiples casos de uso
- ✅ **Performance**: Búsquedas vectoriales en datasets user-specific menores
- ✅ **Testing**: Componentes modulares más fáciles de testear

### **Negativas**  
- ❌ **Complejidad**: Más componentes para mantener
- ❌ **Resource Usage**: Más collections = más memoria ChromaDB
- ❌ **Migration**: Existing data en collection única debe migrarse

### **Riesgos**
- 🔶 **ChromaDB Limitations**: Límites en número de collections simultáneas
- 🔶 **Agent Coordination**: Complejidad en manejo de errores entre agentes
- 🔶 **Context Consistency**: Mantener consistencia entre Redis y Vector Memory

## Plan de Implementación (REVISADO - Approach Incremental)

### **Fase 1: Multi-Tenant Foundation + Interface Design (Semanas 1-3)**
**Objetivo**: Privacidad garantizada + interface estable
1. Extender `ChromaManager` con collections per-user + metadata filtering
2. Implementar `BaseModularAgent` interface (CRÍTICO: debe ser estable)
3. `VectorMemoryManager` básico per-user
4. Migration script para data existente
5. Tests unitarios exhaustivos para foundation

### **Fase 2: Core Agents Implementation (Semanas 4-6)**  
**Objetivo**: 2 agentes funcionando perfectamente, no 4 half-working
1. Implementar `FileHandlerAgent` completo con validación + parsing
2. Implementar `NLPParserAgent` con intent recognition básico
3. Sequential execution workflows (NO composition engine yet)
4. Integration tests FileHandler → NLP pipeline
5. Performance testing collection per-user

### **Fase 3: Simple Composition + Memory Integration (Semanas 7-8)**
**Objetivo**: Composition solo si agents individuales proven
1. `SimpleComposer` configuration-driven (NO dynamic orchestration)
2. Hybrid memory Redis + ChromaDB integration
3. Context retrieval optimization
4. E2E testing workflows completos
5. **Decision Point**: ¿Collections granulares needed based on performance data?

### **Acceptance Criteria (REVISADO - Phased Validation)**

#### **Fase 1 - Foundation Must-Haves**
```bash
# Criterio 1: Multi-tenancy garantizado
user_123_data = vector_db.query(user_id="123", query="buscar conversaciones")
assert user_456_data not in user_123_data  # Isolation garantizado

# Criterio 2: Interface estable
agent = FileHandlerAgent()
result = await agent.execute(test_data, context)
assert isinstance(result, AgentResult)  # Interface consistent

# Criterio 3: Performance baseline
search_time = await vector_memory.search_user_context("123", "query")
assert search_time < 200_ms  # Relaxed initial target
```

#### **Fase 2 - Core Agents Must-Haves**
```bash
# Criterio 4: Individual agents funcionando
file_result = await FileHandlerAgent().execute(file_data, context)
assert file_result.success == True
nlp_result = await NLPParserAgent().execute(file_result.data, context) 
assert nlp_result.intent is not None

# Criterio 5: Sequential workflow
result = await execute_file_workflow(file_data, user_id="123")
assert result contains expected analysis
```

#### **Fase 3 - Composition Should-Haves**
```bash
# Criterio 6: Simple composition (only if Phase 2 successful)
workflow = composer.compose_for_task("file_analysis") 
assert FileHandlerAgent in workflow
assert NLPParserAgent in workflow

# Criterio 7: Memory integration
context = await memory_manager.get_user_context("123", "recent files")
assert len(context) > 0  # Context retrieval working
```

## Validación

- [x] **Technical Review**: Consensus con múltiples modelos AI (COMPLETADO)
  - gemini-2.5-pro (critical): Over-engineering concerns, start simpler
  - gemini-2.0-flash-lite (neutral): Feasible but high complexity, phased approach
  - gemini-2.5-flash (optimistic): Strong architecture, careful implementation needed
- [x] **Architecture Review**: Consistency con patterns existentes AEGEN (COMPLETADO)
- [ ] **Performance Review**: Load testing con múltiples usuarios (Fase 1 deliverable)
- [ ] **Security Review**: Validation de user isolation (Fase 1 deliverable)

## Consensus AI Results

### **Key Agreements (All 3 models)**
- ✅ Technically feasible with ChromaDB + Redis + modular agents
- ✅ Significant user value from multi-tenancy + agent composition
- ✅ Aligns with industry best practices for scalable AI systems
- ✅ Hybrid memory (Redis + ChromaDB) is proven pattern

### **Key Concerns & Mitigations Adopted**
- ⚠️ **ChromaDB Collection Sprawl** → Start with metadata filtering, evolve if needed
- ⚠️ **Over-Engineering Agent Composition** → Build incrementally, prove value first
- ⚠️ **Implementation Complexity** → Phased approach with validation gates
- ⚠️ **Premature Optimization** → Address real problems with real performance data

### **Confidence Scores**
- Critical perspective: Concerns about complexity, recommends simplicity
- Neutral perspective: 7/10 - Feasible but requires careful execution
- Optimistic perspective: 8/10 - Strong architecture with proper implementation

---

**Decision Date**: 2026-01-22 (Revisado)
**Status**: ACEPTADO - En progreso (Fase 1: Foundation)
**Revisors**: Tech Lead, AI Consensus Models (gemini-2.5-pro, gemini-2.0-flash-lite, gemini-2.5-flash)  
**Next Review**: End of Fase 1 (Week 3) - Validate foundation before proceeding