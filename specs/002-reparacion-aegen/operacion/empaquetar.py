"""Genera entrega sin secretos y copia de pruebas sobre la base de la VM.

Ejecutar desde AEGEN con su entorno virtual: uv run --no-sync python ...
"""

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path.cwd()
BASE = "11487668e1a8435cdc6f99b84dbfef2db211fe50"
OP = ROOT / "specs/002-reparacion-aegen/operacion"
OUT = ROOT / ".tmp/repair002-entrega-final"
SOURCE = [
    "src/api/services/event_processor.py",
    "src/api/services/debounce_manager.py",
    "src/api/services/processing_lock.py",
    "src/api/services/lock_wait.py",
    "src/api/services/startup_recovery.py",
    "src/api/routers/status.py",
    "src/agents/specialists/skill_based_specialist.py",
    "src/agents/orchestrator/master_orchestrator.py",
    "src/personality/skills/chat/tools.py",
    "src/memory/embeddings.py",
    "src/memory/hybrid_search.py",
    "src/core/ingestion_buffer.py",
    "src/main.py",
]
TESTS = [
    "tests/unit/api/test_event_response.py",
    "tests/unit/api/test_debounce_lock.py",
    "tests/unit/api/test_health_llm.py",
    "tests/unit/memory/test_embedding_degradation.py",
    "tests/unit/orchestrator/test_skill_error_state.py",
    "tests/unit/personality/test_chat_tool_errors.py",
    "tests/integration/test_telegram_webhook.py",
]
OUT.mkdir(parents=True, exist_ok=True)
stage = OUT / "paquete"
baseline = OUT / "base-vm"
stage.mkdir()
baseline.mkdir()
git = shutil.which("git")
assert git is not None
# Ejecutable resuelto y argumentos constantes; no se interpreta ningún shell.
archive = subprocess.check_output([git, "archive", BASE])  # noqa: S603
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    source.extractall(baseline, filter="data")
expected: dict[str, str | None] = {}
# Verificar código y dependencias de cada imagen antes de superponer archivos.
for path in sorted((baseline / "src").rglob("*")):
    if path.is_file():
        name = path.relative_to(baseline).as_posix()
        expected[name] = hashlib.sha256(path.read_bytes()).hexdigest()
for name in SOURCE:
    expected.setdefault(name, None)
    target = stage / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
    shutil.copyfile(ROOT / name, baseline / name)
for name in TESTS:
    (baseline / name).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, baseline / name)
for name in ("requirements.lock", "pyproject.toml"):
    # Las dependencias de la imagen se heredan, sin instalarlas ni sustituirlas.
    assert (baseline / name).is_file()
(stage / "base.json").write_text(json.dumps(expected, indent=2) + "\n")
(stage / "Dockerfile").write_text(
    "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nUSER root\n"
    "COPY --chown=10001:10001 src/ /app/src/\nUSER 10001:10001\n"
)
(stage / ".dockerignore").write_text("**\n!Dockerfile\n!src/\n!src/**\n")
(stage / "operacion").mkdir()
for name in (
    "common.sh",
    "preparar.sh",
    "activar.sh",
    "rollback.sh",
    "verificar_base.py",
):
    shutil.copyfile(OP / name, stage / "operacion" / name)
members = sorted(path for path in stage.rglob("*") if path.is_file())
(stage / "manifest.sha256").write_text(
    "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        f"{path.relative_to(stage).as_posix()}\n"
        for path in members
    )
)
bundle = OUT / "aegen-reparacion-002.tar"
with tarfile.open(bundle, "w", format=tarfile.USTAR_FORMAT) as output:
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            output.add(
                path, arcname=path.relative_to(stage).as_posix(), recursive=False
            )
sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
(OUT / "SHA256.txt").write_text(f"{sha}  {bundle.name}\n")
sys.stdout.write(f"PAQUETE={bundle}\nSHA256={sha}\nBASE_PRUEBAS={baseline}\n")
