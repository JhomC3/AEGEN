#!/usr/bin/env python3
"""
Simple Architecture Check - Validación básica y rápida.
Reemplaza el enforce_architecture.py complejo por checks esenciales.
"""

import subprocess
import sys
from pathlib import Path


def check_file_sizes() -> bool:
    """Check that Python files are within limits defined in RULES.MD."""
    violations = []
    max_lines_logic = 200
    max_lines_definition = 300

    definition_paths = [
        "src/core/schemas",
        "src/core/config",
        "src/core/routing_models.py",
    ]

    for py_file in Path("src").glob("**/*.py"):
        if not py_file.exists():
            continue

        lines = len(py_file.read_text().splitlines())

        # Determine limit based on path
        is_definition = any(str(py_file).startswith(p) for p in definition_paths)
        limit = max_lines_definition if is_definition else max_lines_logic

        if lines > limit:
            type_str = "definición" if is_definition else "lógica"
            violations.append(
                f"{py_file}: {lines} líneas (máximo sugerido para {type_str}: {limit})"
            )

    if violations:
        print("⚠️ Posibles violaciones de tamaño de archivo:")
        for v in violations[:10]:  # Mostrar máximo 10
            print(f"   {v}")
        if len(violations) > 10:
            print(f"   ... y {len(violations) - 10} más")
        return False

    return True


def check_basic_patterns() -> bool:  # noqa: C901
    """Check basic patterns in changed files."""
    try:
        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        changed_files = [
            f
            for f in result.stdout.strip().split("\n")
            if f
            and f.endswith(".py")
            and not f.startswith("scripts/")
            and not f.startswith("tests/")
        ]

        if not changed_files:
            return True

        violations = []

        for file_path in changed_files:
            if not Path(file_path).exists():
                continue

            # Skip legacy or specific exception files
            if "global_knowledge_loader.py" in file_path or "polling.py" in file_path:
                continue

            content = Path(file_path).read_text()

            # Check for sync I/O patterns
            if "import requests" in content:
                violations.append(f"{file_path}: Usar aiohttp en lugar de requests")

            if "open(" in content and "async" not in content:
                violations.append(
                    f"{file_path}: Usar aiofiles para I/O de archivos (solo efímero)"
                )

            if '"storage/' in content or "'storage/" in content:
                violations.append(
                    f"{file_path}: Usar Redis/Cloud en lugar de 'storage/' para datos persistentes"
                )

        if violations:
            print("❌ Violaciones de patrones:")
            for v in violations:
                print(f"   {v}")
            return False

        return True

    except subprocess.CalledProcessError:
        # Git command failed, skip check
        return True


def main():
    """Simple validation - file sizes + basic patterns."""
    print("🔍 Ejecutando chequeos de arquitectura simples...")

    all_passed = True

    # Check file sizes
    if not check_file_sizes():
        all_passed = False
        print("\n📏 Solución: Dividir archivos grandes en módulos más pequeños")

    # Check basic patterns
    if not check_basic_patterns():
        all_passed = False
        print("\n🔄 Solución: Usar patrones asíncronos (ver docs/guias/desarrollo.md)")

    if all_passed:
        print("✅ ¡Chequeos de arquitectura pasados!")
        return True
    else:
        print("\n❌ Se encontraron problemas de arquitectura")
        print("📚 Revisa docs/guias/desarrollo.md para las guías")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
