# Manual de Desarrollo AEGEN

Este documento explica **cómo operar** en el entorno de desarrollo de AEGEN. Para conocer los estándares técnicos obligatorios, consulta primero **[AGENTS.md](../../AGENTS.md)**.

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
2.  **Desarrollo:** Mantén los archivos bajo los límites de LOC definidos en `AGENTS.md` (150 objetivo, 200 máximo para lógica).
3.  **Verificación Continua:** Ejecuta `make verify` frecuentemente.
4.  **Formateado:** Usa `make format` antes de cada commit.

## 🛠️ Comandos Esenciales

| Comando | Función |
| :--- | :--- |
| `make dev` | Docker + Hot-reload para desarrollo rápido. |
| `make verify` | CI completa: Ruff, MyPy, Bandit y Pytest. |
| `make format` | Corrección automática de estilo y orden de imports. |
| `make status` | Estado del proyecto, arquitectura y sincronización. |
| `make sync-docs` | Sincroniza documentación con el estado del proyecto. |

## 🧪 Estándares de Pruebas (Testing)

AEGEN exige una **cobertura mínima del 50%** (objetivo progresivo: 85%).
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

## 🏗️ Flujo para Nuevos Skills (Habilidades/Agentes)

AEGEN usa un sistema modular basado en directorios (ADR-0026):
1. Crea una carpeta en `src/personality/skills/<id_del_skill>/`.
2. Escribe el manifiesto `SKILL.md` con el frontmatter YAML (metadatos) y cuerpo Markdown (instrucciones).
3. (Opcional) Implementa el tool en `tools.py` exportando `SKILL_TOOL`.
4. El `SkillLoader` registrará automáticamente el agente al iniciar la app.
5. Registra los patrones de ruteo en `src/agents/orchestrator/routing/intent_patterns_data.py`.

---
*El incumplimiento de los estándares en `AGENTS.md` detendrá el pipeline de despliegue.*
