# src/personality/skill_curator.py
"""
Curador automatico de skills.

Worker semanal que gestiona el ciclo de vida de skills:
- >30 dias sin uso → marcar como stale
- >90 dias sin uso → archivar (.archive/)
"""

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

STALE_DAYS = 30
ARCHIVE_DAYS = 90
SKILLS_DIR = Path("src/personality/skills")
ARCHIVE_DIR = SKILLS_DIR / ".archive"
USER_SKILLS_DIR = Path("storage/skills/user")


async def _get_skill_last_used(
    skill_id: str, redis_conn: aioredis.Redis | None = None
) -> datetime | None:
    """Obtiene el ultimo uso de un skill desde Redis."""
    if redis_conn is None:
        from src.core.dependencies import redis_connection

        redis_conn = redis_connection

    if redis_conn is None:
        return None

    try:
        val = await redis_conn.hget("skill:last_used", skill_id)
        if val:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            return datetime.fromisoformat(val)
    except Exception as e:
        logger.warning("[CURATOR] Error leyendo ultimo uso de %s: %s", skill_id, e)
    return None


async def _archive_skill(skill_dir: Path, dry_run: bool = False) -> bool:
    """Mueve un skill al directorio de archivo."""
    archive_dir = skill_dir.parent / ".archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / skill_dir.name

    if dry_run:
        logger.info("[CURATOR] DRY-RUN: Archivar %s → %s", skill_dir, target)
        return True

    try:
        shutil.move(str(skill_dir), str(target))
        logger.info("[CURATOR] Skill archivado: %s → %s", skill_dir, target)
        return True
    except Exception as e:
        logger.error("[CURATOR] Error archivando %s: %s", skill_dir, e)
        return False


def _discover_skills() -> list[Path]:
    """Descubre todos los directorios de skills."""
    skills = []
    for base in [SKILLS_DIR, USER_SKILLS_DIR]:
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir() and not d.name.startswith((".", "_")):
                if (d / "SKILL.md").exists():
                    skills.append(d)
    return skills


async def run_skill_curator(
    dry_run: bool = False,
    redis_conn: object | None = None,
) -> dict:
    """
    Ejecuta el curador de skills.

    Args:
        dry_run: Si True, solo reporta sin mover archivos.
        redis_conn: Conexion Redis para leer metricas de uso.

    Returns:
        Reporte: {"stale": [...], "archived": [...], "active": [...]}
    """
    report: dict[str, list[str]] = {
        "stale": [],
        "archived": [],
        "active": [],
    }

    skills = _discover_skills()
    now = datetime.now(UTC)

    for skill_dir in skills:
        skill_id = skill_dir.name
        last_used = await _get_skill_last_used(skill_id, redis_conn)

        if last_used is None:
            report["active"].append(skill_id)
            continue

        days_inactive = (now - last_used).days

        if days_inactive > ARCHIVE_DAYS:
            if not dry_run:
                success = await _archive_skill(skill_dir)
                if success:
                    report["archived"].append(skill_id)
            else:
                report["archived"].append(skill_id)
        elif days_inactive > STALE_DAYS:
            report["stale"].append(skill_id)
        else:
            report["active"].append(skill_id)

    logger.info(
        "[CURATOR] Reporte: active=%d, stale=%d, archived=%d (dry_run=%s)",
        len(report["active"]),
        len(report["stale"]),
        len(report["archived"]),
        dry_run,
    )
    return report
