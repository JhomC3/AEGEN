# AEGEN - Development Guide
> **Single Source of Truth para TODO desarrollo técnico**

## 🚀 Quick Start (5 minutos)

```bash
# 1. Setup completo
make install

# 2. Antes de escribir código - SIEMPRE
# Revisar checklist abajo ↓

# 3. Desarrollo
make dev          # Correr en desarrollo
make verify       # Validar antes de commit
```

---

## 📋 CHECKLIST OBLIGATORIO - Antes de Escribir Código

**Copiar y pegar en TODO PR/commit:**

```
□ Archivo < 100 líneas, funciones < 20 líneas
□ Una responsabilidad por archivo/clase
□ Dependencies inyectadas, no construidas
□ Business logic separado de infrastructure
□ Tests unitarios incluidos
□ LLM calls trackeadas con correlation_id
□ Performance targets validados (<2s routing)
□ Observabilidad metrics agregadas
```

**🚫 RED FLAGS - STOP si ves:**
- Clases con múltiples responsabilidades
- Métodos > 20 líneas
- Multiple if/else complejos
- Mixing business logic con infrastructure
- LLM calls sin tracking/observabilidad
- Hardcoded LLM imports (usar src.core.engine)
- Performance regressions sin justificación
- Missing correlation_id propagation
- **Uso de `aiofiles` o escritura en `storage/` local para datos de usuario**
- **Paths de archivos hardcodeados fuera de `/tmp`**

---

## ⚡ Reglas MUST (Forzadas automáticamente)

### Código Base
- **ruff** único formatter/linter
- **async/await** obligatorio para I/O
- **Tipado estricto** - no `Any` sin `TODO: [TICKET-ID]`
- **JSON logging** estructurado con `correlation_id`
- **No secretos hardcodeados** - usar Pydantic Settings
- **No PII en logs** - usar redactor
- **Observabilidad LLM** - trackear TODAS las llamadas LLM con métricas
- **Performance monitoring** - correlation_id end-to-end obligatorio

### Arquitectura
- **Tools sin estado** - no manejan lifecycle de archivos
- **Docstrings públicos** formato Numpy/Google + `LLM-hints`
- **Single Responsibility** máximo 7 métodos/clase
- **Clean Architecture** business logic vs infrastructure
- **LLM Tracing** - todo LLM call debe pasar por tracker central
- **Performance targets** - <2s routing, <3s delegation, <5s total response
- **Hybrid Architecture** - balance performance/funcionalidad (ADR-0009)

### Testing
- **Tests obligatorios** para nueva funcionalidad
- **Cobertura no disminuye**
- **Snapshot tests** para prompts en `prompts/`
- **Performance tests** - validar targets de latencia
- **Integration tests** - flujo completo con observabilidad

---

## 🛠️ Comandos Esenciales

```bash
# Desarrollo diario
make dev          # Docker + hot-reload
make verify       # Linting + tests + architecture
make format       # Auto-fix código

# Estado proyecto
make status       # Git + testing + métricas
make sync-docs    # Actualizar documentación

# Debugging
make logs-dev     # Ver logs desarrollo
make doctor       # Diagnóstico completo
```

---

## 🔄 Workflow de Desarrollo

### Para TODA nueva funcionalidad:

1. **Pre-código (OBLIGATORIO)**
   ```bash
   # Revisar checklist arriba ↑
   # Planificar responsabilidades
   # Definir interfaces claras
   ```

2. **Durante desarrollo**
   ```bash
   make verify      # Validar frecuentemente
   # Mantener archivos < 100 líneas
   # Tests mientras desarrollas
   ```

3. **Antes de commit**
   ```bash
   make verify      # Final validation
   git commit       # Auto-valida con hooks
   ```

### Git Strategy
```
main ← develop ← feature/branch-name
```

**Commits:**
```bash
# Formato obligatorio
feat(scope): descripción imperativa

# Opcional
[BREAKING]

• ¿Por qué?: user story o bug
• ¿Qué?: solución técnica
• ¿Cómo?: archivos clave
```

---

## 🏗️ Patterns de Arquitectura

### Diskless-First Pattern
- **Nunca** guardar datos de usuario o historiales en el sistema de archivos local.
- Utilizar `RedisMessageBuffer` para persistencia temporal inmediata.
- Confiar en la consolidación asíncrona hacia Google Cloud para almacenamiento de largo plazo.
- Los perfiles de usuario deben gestionarse exclusivamente a través de `ProfileManager` (Redis + Cloud).
- El almacenamiento local (`/tmp`) solo se permite para procesamiento efímero de archivos (ej. transcodificación de audio) que se eliminan inmediatamente después.

### Identity Structural Pattern
- **Seed desde Plataforma:** Al primer contacto, el nombre se inicializa desde la plataforma (ej: Telegram `first_name`).
- **Aprendizaje Conversacional:** El nombre detectado en la conversación (FactExtractor) tiene prioridad y sobrescribe al seed.
- **Sincronización:** La Knowledge Base actúa como fuente de hechos, el Perfil como caché para el Prompt Builder.

### Personality Management Pattern
- **Evolución obligatoria:** Toda interacción significativa debe ser analizada para actualizar el perfil de adaptación de personalidad del usuario.
- **Base inmutable:** Nunca modificar `SOUL.md` o `IDENTITY.md` mediante código; estos son el ancla de identidad.
- **Overlays modulares:** Los especialistas deben definir sus matices de personalidad mediante `SkillOverlay` sin sobrescribir la identidad base.

### Event-Driven
- `CanonicalEventV1` como lingua franca
- Eventos inmutables y serializables

### Registry Pattern
- Autodescubrimiento de especialistas
- No hard-coding de dependencies
- **IMPORTANTE:** Todo especialista debe ser una clase que herede de `SpecialistInterface` y debe ser registrado en el `specialist_registry` para ser descubierto por el sistema.

### Tool Composition
- Herramientas atómicas y componibles
- Sin estado interno

### State Graphs
- LangGraph para orquestación declarativa
- Flujos complejos como grafos

---

## 🧪 Testing Standards

### Por Tipo
- **Unit:** Lógica pura + mocks de I/O
- **Integration:** Componentes + Redis/VectorStorage (Stub)
- **E2E:** Flujo completo Telegram → respuesta
- **Snapshot:** Prompts + respuestas LLM

### Coverage Mínimo
- **Unit:** 85%
- **Integration:** 60%
- **E2E:** Casos críticos

---

## 📊 Quality Gates por Fase

### Fase 3A (Básico)
```bash
make lint && make test
```

### Fase 3B (Sistema Conversacional)
```bash
make verify  # Incluye integration tests
```

### Fase 3C (Actual)
```bash
make verify  # + architecture enforcement
```

---

## 🔧 Troubleshooting

### Performance Issues
```bash
# Verificar métricas LLM
curl localhost:8000/metrics | grep llm_call

# Ver latencia por endpoint
curl localhost:8000/system/status

# Profile memoria y CPU
make profile
```

### Linting falla
```bash
make format  # Auto-fix la mayoría
```

### Tests fallan
```bash
# Correr específico
pytest tests/unit/test_specific.py -v
```

### Architecture violations
```bash
# Ver qué falla específicamente
make verify
# Refactorizar según checklist arriba ↑
```

### Observability Issues
```bash
# Verificar correlation IDs
grep -r "correlation_id" src/

# Ver métricas LLM en vivo
watch "curl -s localhost:8000/metrics | grep -E '(llm_|performance_)'"
```

### Docker issues
```bash
make clean       # Limpiar todo
make run-dev     # Fresh start
```

---

## 🎯 Errores Comunes y Soluciones

| Error | Solución |
|-------|----------|
| File > 100 lines | Dividir responsabilidades en archivos separados |
| Function > 20 lines | Extraer submétodos privados |
| Sync I/O detected | Usar `aiohttp`, `asyncio.to_thread` (evitar `aiofiles` para datos persistentes) |
| Missing tests | Añadir tests unitarios para nueva funcionalidad |
| No docstring | Agregar docstring con formato Google + LLM-hints |

---

## 📚 Referencias Rápidas

- **PROJECT_OVERVIEW.md** - Visión y roadmap
- **Este archivo** - TODO lo técnico
- **Makefile** - Comandos disponibles
- **Código + tests** - Implementación actual

**🚨 Si algo no está aquí, buscar en PROJECT_OVERVIEW.md o preguntar al equipo.**

---

**✅ Esta es la ÚNICA fuente de verdad para desarrollo técnico en AEGEN.**
