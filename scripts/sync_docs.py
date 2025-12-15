#!/usr/bin/env python3
"""
Script para sincronizar automáticamente el estado real del proyecto
con la documentación en PROJECT_OVERVIEW.md.

Parte de la estrategia de "Gobernanza Automática" del proyecto AEGEN.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd: str) -> str:
    """Ejecuta un comando y retorna la salida limpia."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando '{cmd}': {e}")
        return ""


def get_git_status() -> dict[str, str]:
    """Extrae información actual del repositorio git."""
    branch = run_command("git rev-parse --abbrev-ref HEAD")

    # Archivos modificados (sin incluir nuevos archivos)
    modified_files = run_command("git diff --name-only HEAD")
    unstaged_files = run_command("git diff --name-only")

    # Combinar y limpiar lista de cambios pendientes
    all_changes = set()
    if modified_files:
        all_changes.update(modified_files.split("\n"))
    if unstaged_files:
        all_changes.update(unstaged_files.split("\n"))

    # Filtrar archivos vacíos y limitar a los más relevantes
    relevant_changes = [f for f in all_changes if f and not f.startswith(".git")]
    changes_str = str(relevant_changes[:5])  # Máximo 5 archivos para legibilidad

    return {"branch": branch, "changes": changes_str}


# FUNCIONES ELIMINADAS: La detección automática de progreso es frágil
# y crea acoplamiento entre documentación y detalles de implementación.
# El progreso se actualizará manualmente en PROJECT_OVERVIEW.md


def update_project_overview():
    """
    Actualiza PROJECT_OVERVIEW.md SOLO con datos objetivos y verificables.

    ACTUALIZA:
    - Git branch actual
    - Archivos con cambios pendientes
    - Timestamp de sincronización

    NO ACTUALIZA (manual):
    - Progreso de fase
    - Próximo hito
    - Funcionalidades activas
    """
    overview_path = Path("PROJECT_OVERVIEW.md")

    if not overview_path.exists():
        print("Error: PROJECT_OVERVIEW.md no encontrado")
        return False

    # Obtener SOLO datos objetivos
    git_info = get_git_status()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Leer contenido actual
    content = overview_path.read_text()

    # Actualizar SOLO las líneas específicas que son objetivas
    content = re.sub(
        r'Branch_Trabajo: ".*?"', f'Branch_Trabajo: "{git_info["branch"]}"', content
    )
    content = re.sub(
        r"Cambios_Pendientes: \[.*?\]",
        f"Cambios_Pendientes: {git_info['changes']}",
        content,
    )
    content = re.sub(
        r'Última_Sincronización: ".*?"',
        f'Última_Sincronización: "{timestamp}"',
        content,
    )

    # Escribir archivo actualizado
    overview_path.write_text(content)
    print(f"✅ Datos objetivos actualizados - {timestamp}")
    print(f"   Branch: {git_info['branch']}")
    print(f"   Cambios: {len(git_info['changes'])} archivos")
    print("⚠️  Progreso de fase: Actualizar manualmente en PROJECT_OVERVIEW.md")

    return True


def main():
    """Función principal del script."""
    print("🔄 Sincronizando documentación con estado real...")

    # Verificar que estamos en el directorio correcto
    if not Path("src").exists() or not Path("PROJECT_OVERVIEW.md").exists():
        print("Error: Ejecutar desde el directorio raíz del proyecto AEGEN")
        sys.exit(1)

    success = update_project_overview()

    if success:
        print("✅ Sincronización completada")
    else:
        print("❌ Error en la sincronización")
        sys.exit(1)


if __name__ == "__main__":
    main()
