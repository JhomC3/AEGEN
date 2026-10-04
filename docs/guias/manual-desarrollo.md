# Manual de Desarrollo AEGEN

Este documento explica **cómo operar** en el entorno de desarrollo de AEGEN. Proceso común: **[SDD_BOOTSTRAP](../../../sdd-kit/SDD_BOOTSTRAP.md)** (única autoridad). Principios locales: **[constitution](../constitution.md)**. Entrada SDD: **[README](../sdd/README.md)**. Estándares técnicos obligatorios: **[AGENTS.md](../../AGENTS.md)**.

## 🚀 Inicio Rápido (Quick Start)

Para configurar tu entorno en menos de 5 minutos:

```bash
# 1. Instalar dependencias con uv
make install

# 2. Configurar entorno
cp .env.example .env  # Y editar con tus llaves

# 3. Desarrollo activo
make dev          # Inicia contenedores con recarga en caliente (hot-reload)
make dev-check    # Chequeo rápido de arquitectura (ver limitaciones de verify abajo)
```

## 📋 Flujo de Trabajo (proceso común + controles locales)

Proceso común en `../../../sdd-kit/SDD_BOOTSTRAP.md` §1.2, §8–§9
(niveles, autorización por alcance, validación veraz). Controles locales:

1.  **Planificación:** nivel según el método común; para estructural, plan en
    `docs/planes/YYYY-MM-DD-nombre.md` (plantilla propia deprecada, ver
    `../planes/plantilla-plan.md`).
2.  **Desarrollo:** Mantén los archivos bajo los límites de LOC definidos en `AGENTS.md` (150 objetivo, 200 máximo para lógica).
3.  **Verificación:** comprobaciones directas con salida comprobada (ver tabla abajo).
    `make verify` es una ayuda con limitaciones conocidas, no evidencia suficiente.
4.  **Formateado:** Usa `make format` antes de cada commit.

## 🛠️ Comandos Esenciales

| Comando | Función |
| :--- | :--- |
| `make dev` | Docker + Hot-reload para desarrollo rápido. |
| `make verify` | Ayuda con limitaciones (ver abajo); no es garantía por sí sola. |
| `make format` | Corrección automática de estilo y orden de imports. |
| `make status` | Estado del proyecto, arquitectura y sincronización. |
| `make sync-docs` | Sincroniza documentación con el estado del proyecto. |

## ✅ Validación local (controles reales)

| Cambio | Comprobación directa |
|---|---|
| `.py` | `uv run python -m ruff check .`, `uv run python -m mypy src tests`, `uv run python -m pytest tests/`, `uv run python scripts/simple_check.py` (mostrar salida) |
| Schemas/interfaces | Anterior + test de integración del subsistema afectado |
| Solo docs | Lectura, enlaces afectados y diff |

Limitaciones conocidas (sin corregir scripts en esta tarea): `Makefile:lint`
ignora el error de mypy, `Makefile:test` convierte el fallo de pytest en mensaje
y excluye `tests/unit/test_cbt_safety.py` y `tests/unit/test_profile_manager.py`;
`pyproject.toml` lleva `--no-cov`, sin mínimo vigente. Por eso no se declara
éxito por el mensaje final de `verify`.

## 🧪 Cobertura (declaración histórica)

Cobertura histórica 50 % con objetivo 85 %, sin gate vigente confirmado en
`pyproject.toml` (`--no-cov`). No se introduce otro umbral aquí.

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
