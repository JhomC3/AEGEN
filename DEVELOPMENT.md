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
```

**🚫 RED FLAGS - STOP si ves:**
- Clases con múltiples responsabilidades
- Métodos > 20 líneas  
- Multiple if/else complejos
- Mixing business logic con infrastructure

---

## ⚡ Reglas MUST (Forzadas automáticamente)

### Código Base
- **ruff** único formatter/linter
- **async/await** obligatorio para I/O
- **Tipado estricto** - no `Any` sin `TODO: [TICKET-ID]`
- **JSON logging** estructurado con `correlation_id`
- **No secretos hardcodeados** - usar Pydantic Settings
- **No PII en logs** - usar redactor

### Arquitectura
- **Tools sin estado** - no manejan lifecycle de archivos
- **Docstrings públicos** formato Numpy/Google + `LLM-hints` 
- **Single Responsibility** máximo 7 métodos/clase
- **Clean Architecture** business logic vs infrastructure

### Testing
- **Tests obligatorios** para nueva funcionalidad
- **Cobertura no disminuye**
- **Snapshot tests** para prompts en `prompts/`

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

• WHY: user story o bug  
• WHAT: solución técnica
• HOW: archivos clave
```

---

## 🏗️ Patterns de Arquitectura

### Event-Driven
- `CanonicalEventV1` como lingua franca
- Eventos inmutables y serializables

### Registry Pattern  
- Autodescubrimiento de especialistas
- No hard-coding de dependencies

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
- **Integration:** Componentes + Redis/ChromaDB  
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

### Fase 3B (Actual) 
```bash
make verify  # Incluye integration tests
```

### Fase 3C (Próximo)
```bash
make verify  # + architecture enforcement
```

---

## 🔧 Troubleshooting

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
| Sync I/O detected | Usar `aiohttp`, `aiofiles`, `asyncio.to_thread` |
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