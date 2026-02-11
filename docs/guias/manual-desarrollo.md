# Manual de Desarrollo AEGEN

Este documento explica **cómo operar** en el entorno de desarrollo de AEGEN. Para conocer las leyes técnicas obligatorias, consulta primero **[RULES.MD](../../RULES.MD)**.

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

## 📋 Flujo de Trabajo Obligatorio

Antes de escribir una sola línea de código, debes seguir este proceso:

1.  **Planificación:** Crea un plan detallado en `docs/planes/YYYY-MM-DD-nombre.md` y obtén aprobación.
2.  **Desarrollo:** Mantén los archivos bajo las 100 líneas y funciones bajo las 20 líneas (ver `RULES.MD`).
3.  **Verificación Continua:** Ejecuta `make verify` frecuentemente.
4.  **Formateado:** Usa `make format` antes de cada commit.

## 🛠️ Comandos Esenciales

| Comando | Función |
| :--- | :--- |
| `make dev` | Docker + Hot-reload para desarrollo rápido. |
| `make verify` | CI completa: Ruff, MyPy, Bandit y Pytest. |
| `make format` | Corrección automática de estilo y orden de imports. |
| `make status` | Estado del proyecto, arquitectura y sincronización. |
| `make sync-docs` | Actualiza el estado operativo en `PROJECT_OVERVIEW.md`. |

## 🧪 Estándares de Pruebas (Testing)

AEGEN exige una **cobertura mínima del 85%**.
- **Unitarias:** Lógica pura con mocks de entrada/salida.
- **Integración:** Flujos entre componentes con Redis/SQLite reales.
- **E2E:** Flujo completo desde Telegram hasta la respuesta final.

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
4. Añade el detalle técnico en `docs/arquitectura/agentes/especialistas.md`.

---
*El incumplimiento de las normas en `RULES.MD` detendrá el pipeline de despliegue.*
