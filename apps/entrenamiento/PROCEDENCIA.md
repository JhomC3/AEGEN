# Procedencia — apps/entrenamiento

Copia de trabajo del dominio de bienestar y dirección personal, tomada de
`entrenamiento@fa72df0` (`dev`, 2026-10-04), reconciliada con `4fe5970`,
`e9ee8ab` (aire vertical H06+H09) y `0e4203f` (lotes 047/048), para la fusión
SDD 001. Las adiciones posteriores de seguridad, atomicidad, API y rendimiento
del destino se documentan en esa spec. No representa el estado actual del
checkout hermano ni incorpora automáticamente sus cambios posteriores.
Incluye: `app.py`, `src/`, `templates/`, `static/`, `scripts/`, `tests/`,
`docs/`, `pyproject.toml`, `uv.lock`, `README.md`, `sdd-lock.json`.
Incluye también el código fuente Android; su SDK y compilaciones se excluyen.
Excluye: `.venv/`, `.tmp/` (y sus worktrees), `data/` (DB, backups, tokens,
secretos), SDK/build Android, `__pycache__/`,
`*.pyc`, `.agents/`, conversación ajena sin seguimiento.
El nombre de producto aprobado es **SENDA**; las rutas técnicas e identificadores
persistentes de Entrenamiento se conservan por compatibilidad.
