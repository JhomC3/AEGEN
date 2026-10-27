#!/bin/bash
# Rollback de la preparación SENDA — restaura ÚNICAMENTE lo modificado.
# Sin `git clean`, sin borrar volúmenes, sin marcadores: requiere el
# directorio de respaldo creado por prepare-senda.sh (~/.aegen-respaldo-<ts> ).
# Uso: ./ops/proxy/rollback-senda.sh ~/.aegen-respaldo-<ts>
# No toca contenedores en ejecución, datos, storage, Redis ni trabajos ajenos.
set -euo pipefail

[ $# -eq 1 ] || { echo "Uso: $0 ~/.aegen-respaldo-<ts>"; exit 1; }
BK="$1"
cd ~/AEGEN
[ -f "$BK/.env" ] || { echo "ERROR: respaldo incompleto en $BK"; exit 1; }
[ -f "$BK/anadidos.txt" ] || { echo "ERROR: manifiesto ausente en $BK"; exit 1; }

echo "== restaura .env =="
cp "$BK/.env" .env
chmod 600 .env

echo "== revierte ficheros seguidos (solo los 8 modificados) =="
git checkout -- \
  src/agents/orchestrator/routing/intent_parser.py \
  src/agents/orchestrator/routing/intent_patterns_data.py \
  src/agents/orchestrator/routing/specialist_mapper.py \
  src/core/config/base.py \
  src/core/routing_models.py \
  src/tools/polling.py \
  .env.example \
  .gitignore

echo "== retira rutas añadidas (lista exacta del manifiesto) =="
while IFS= read -r p; do
  [ -e "$p" ] || [ -L "$p" ] || continue
  rm -rf "$p"
  echo "retirado: $p"
done < "$BK/anadidos.txt"
# Limpia directorios que queden vacíos (solo si están vacíos; lo ajeno queda).
for d in apps/entrenamiento apps ops/senda-test ops/proxy ops src/personality/skills/bienestar src/personality/skills src/personality tests/unit/personality; do
  rmdir "$d" 2>/dev/null || true
done

echo "== estado (imágenes y volúmenes intactos a propósito) =="
git status --short | head -n 10
echo "ROLLBACK OK. Las imágenes construidas quedan inertes sin contenedores."
