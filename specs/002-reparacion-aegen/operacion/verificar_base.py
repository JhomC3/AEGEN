"""Sonda sin red: compara los archivos de la imagen con la base probada."""

import hashlib
import json
import sys
from pathlib import Path

root = Path("/app")
manifest = json.loads(Path("/repair/base.json").read_text())
different = []
for name, expected in manifest.items():
    path = root / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if actual != expected:
        different.append(name)
if different:
    # Solo rutas del código: no imprimir contenido ni variables de entorno.
    raise SystemExit("BASE DIFERENTE en " + sys.argv[1] + ": " + ", ".join(different))
sys.stdout.write("BASE COMPATIBLE: " + sys.argv[1] + "\n")
