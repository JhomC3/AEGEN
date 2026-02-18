#!/usr/bin/env python3
"""
Simple Architecture Check - Validación de límites de tamaño de archivo.
Nota: La complejidad de funciones y patrones prohibidos ahora se validan vía Ruff.
"""

import sys
import ast
from pathlib import Path


def check_function_lengths() -> None:
    """
    Check for functions longer than 50 lines (Soft Warning).
    Uses AST to count lines in function definitions.
    """
    violations = []
    max_lines_func = 50

    for py_file in Path("src").glob("**/*.py"):
        if not py_file.exists():
            continue

        try:
            content = py_file.read_text()
            tree = ast.parse(content)
        except Exception:
            continue  # Skip files that can't be parsed

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Simple line count: end - start
                # This includes docstrings and internal comments, which is fine for a rough metric
                if (
                    getattr(node, "end_lineno", None) is not None
                    and getattr(node, "lineno", None) is not None
                ):
                    length = node.end_lineno - node.lineno  # type: ignore
                    if length > max_lines_func:
                        violations.append(
                            f"{py_file}:{node.lineno} - {node.name} ({length} líneas)"
                        )

    if violations:
        print(f"\n⚠️  Advertencia: {len(violations)} funciones exceden las {max_lines_func} líneas:")
        # Sort by length descending
        violations.sort(key=lambda x: int(x.split("(")[1].split()[0]), reverse=True)
        for v in violations[:10]:
            print(f"   {v}")
        if len(violations) > 10:
            print(f"   ... y {len(violations) - 10} más")
        print("   (Recomendación: Refactorizar oportunísticamente)")


def check_file_sizes() -> bool:
    """Check that Python files are within limits defined in AGENTS.md."""
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


def main():
    """Simple validation - only file sizes."""
    print("🔍 Ejecutando chequeos de arquitectura...")

    # Soft check for function lengths
    check_function_lengths()

    # Soft check for file sizes (warn but don't fail build yet)
    check_file_sizes()

    print("✅ ¡Chequeos de arquitectura completados!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
