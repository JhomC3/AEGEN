# src/tools/skills_cli.py
"""
CLI de Skills — Gestion de skills desde terminal.

Comandos: aegen skills install, aegen skills list, aegen skills create.
"""

# ruff: noqa: T201  # CLI tool intentionally uses print()
import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SKILLS_DIR = Path("src/personality/skills")
USER_SKILLS_DIR = Path("storage/skills/user")


def list_skills(verbose: bool = False) -> None:
    """Lista todos los skills disponibles."""
    skills = []
    for base in [SKILLS_DIR, USER_SKILLS_DIR]:
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name.startswith((".", "_")):
                continue
            skill_md = d / "SKILL.md"
            if not skill_md.exists():
                continue

            from src.personality.skill_parser import parse_skill_md

            content = skill_md.read_text(encoding="utf-8")
            parsed = parse_skill_md(content)
            skills.append({
                "id": parsed.manifest.id,
                "name": parsed.manifest.name,
                "version": parsed.manifest.version,
                "source": "user" if "storage" in str(d) else "bundled",
                "capabilities": parsed.manifest.capabilities,
                "path": str(d),
            })

    if not skills:
        print("No hay skills instalados.")
        return

    print(f"\n{'ID':<25} {'Name':<30} {'Version':<10} {'Source':<10}")
    print("-" * 75)
    for s in skills:
        print(f"{s['id']:<25} {s['name']:<30} {s['version']:<10} " f"{s['source']:<10}")
        if verbose and s.get("capabilities"):
            print(f"  Capabilities: {', '.join(s['capabilities'])}")
    print(f"\nTotal: {len(skills)} skills\n")


def create_skill(skill_id: str, name: str) -> None:
    """Crea un nuevo skill template."""
    target_dir = USER_SKILLS_DIR / skill_id
    if target_dir.exists():
        print(f"Error: Skill '{skill_id}' ya existe en {target_dir}")
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(UTC).isoformat()
    content = f"""---
name: "{name}"
id: "{skill_id}"
version: "1.0.0"
status: "draft"
generated_by: "skills_cli"
generated_at: "{generated_at}"
capabilities: []
requires:
  env: []
  python_packages: []
  bins: []
priority: 5
---

## Propósito
[Describe el proposito de este skill]

## Instructions
[Instrucciones especificas del skill]

## Anti-Patterns
[Lo que este skill NO debe hacer]

## Reglas Lingüisticas del Skill
[Estilo de comunicacion especifico]
"""

    skill_md = target_dir / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")
    print(f"Skill '{skill_id}' creado en {skill_md}")
    print("Edita el archivo para personalizarlo.")


def install_skill(skill_path: str) -> None:
    """Instala un skill desde un archivo SKILL.md."""
    source = Path(skill_path)
    if not source.exists():
        print(f"Error: Archivo no encontrado: {source}")
        sys.exit(1)

    from src.personality.skill_parser import parse_skill_md

    content = source.read_text(encoding="utf-8")
    parsed = parse_skill_md(content)

    target_dir = USER_SKILLS_DIR / parsed.manifest.id
    target_dir.mkdir(parents=True, exist_ok=True)

    target_md = target_dir / "SKILL.md"
    target_md.write_text(content, encoding="utf-8")
    print(f"Skill '{parsed.manifest.id}' instalado en {target_md}")


def status_skill(skill_id: str) -> None:
    """Muestra el estado de un skill especifico."""
    for base in [SKILLS_DIR, USER_SKILLS_DIR]:
        skill_md = base / skill_id / "SKILL.md"
        if not skill_md.exists():
            continue

        from src.personality.skill_parser import parse_skill_md

        content = skill_md.read_text(encoding="utf-8")
        parsed = parse_skill_md(content)

        print(f"\nSkill: {parsed.manifest.name}")
        print(f"ID: {parsed.manifest.id}")
        print(f"Version: {parsed.manifest.version}")
        print(f"Source: {'user' if 'storage' in str(skill_md) else 'bundled'}")
        print(f"Path: {skill_md}")

        if parsed.manifest.capabilities:
            print(f"Capabilities: {', '.join(parsed.manifest.capabilities)}")

        if parsed.instructions:
            print(f"\nInstructions:\n{parsed.instructions[:200]}...")

        return

    print(f"Skill '{skill_id}' no encontrado.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGEN Skills CLI")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="Lista skills")
    list_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Mostrar detalles"
    )

    create_parser = subparsers.add_parser("create", help="Crea un skill")
    create_parser.add_argument("id", help="ID del skill")
    create_parser.add_argument("name", help="Nombre del skill")

    install_parser = subparsers.add_parser("install", help="Instala un skill")
    install_parser.add_argument("path", help="Ruta al SKILL.md")

    status_parser = subparsers.add_parser("status", help="Estado de un skill")
    status_parser.add_argument("id", help="ID del skill")

    args = parser.parse_args()

    if args.command == "list":
        list_skills(verbose=getattr(args, "verbose", False))
    elif args.command == "create":
        create_skill(args.id, args.name)
    elif args.command == "install":
        install_skill(args.path)
    elif args.command == "status":
        status_skill(args.id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
