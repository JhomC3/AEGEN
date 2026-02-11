# Manual de Desarrollo AEGEN

Este documento es la **Única Fuente de Verdad** para el desarrollo técnico del proyecto. Define el flujo de trabajo diario y los estándares que garantizan la calidad del sistema.

## 🚀 Inicio Rápido (Quick Start)

Para configurar tu entorno en menos de 5 minutos:

```bash
# 1. Instalar dependencias con uv
make install

# 2. Configurar entorno
cp .env.example .env  # Y editar con tus llaves

# 3. Desarrollo activo
make dev          # Inicia contenedores con recarga en caliente (hot-reload)
make verify       # Ejecuta la suite de validación completa (lint + test + arch)
```

## 📋 Lista de Verificación (Checklist) Obligatoria

Antes de realizar cualquier commit o enviar un cambio, verifica:

- [ ] **Límites:** Archivo < 100 líneas, Funciones < 20 líneas.
- [ ] **Responsabilidad:** Una sola responsabilidad por archivo/clase (SRP).
- [ ] **Asincronía:** Todo I/O de red o disco es `async`.
- [ ] **Tipado:** Tipado estricto en todas las funciones; evitar `Any`.
- [ ] **Observabilidad:** Llamadas a LLM rastreadas con `correlation_id`.
- [ ] **Tests:** Incluye pruebas unitarias para la nueva lógica.

## 🛠️ Comandos Esenciales

| Comando | Función |
| :--- | :--- |
| `make dev` | Docker + Hot-reload para desarrollo rápido. |
| `make verify` | CI completa: Ruff, MyPy, Bandit y Pytest. |
| `make format` | Corrección automática de estilo y orden de imports. |
| `make status` | Estado del proyecto, arquitectura y sincronización. |
| `make sync-docs` | Actualiza el estado operativo en `PROJECT_OVERVIEW.md`. |

## 🧪 Estándares de Pruebas (Testing)

- **Unitarias:** Lógica pura con mocks de entrada/salida.
- **Integración:** Flujos entre componentes con Redis/SQLite reales.
- **E2E:** Flujo completo desde Telegram hasta la respuesta final.
- **Cobertura Mínima:** 85% para lógica unitaria.

## 🔍 Inspección de Sesiones con Redis

AEGEN usa Redis (Database 1) para la memoria activa. Úsalo para depurar:

```bash
# Conectar a la base de datos de sesiones
redis-cli -n 1

# Listar sesiones activas
KEYS session:chat:*

# Ver contenido de una sesión (JSON)
GET session:chat:123456789

# Ver mensajes pendientes en el búfer
LRANGE chat:buffer:123456789 0 -1
```

## 🏗️ Flujo para Nuevos Especialistas

Para añadir una nueva habilidad al bot:
1. Define la interfaz en `src.core.interfaces`.
2. Implementa la lógica en `src.agents.specialists`.
3. Registra el agente en el `MasterOrchestrator`.
4. Añade un documento de detalle en `docs/arquitectura/agentes/`.

---
*Cualquier violación de estos estándares será detectada automáticamente por `make verify`.*
