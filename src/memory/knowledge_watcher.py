# src/memory/knowledge_watcher.py
import asyncio
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path

from src.memory.global_knowledge_loader import GlobalKnowledgeLoader

logger = logging.getLogger(__name__)


class KnowledgeWatcher:
    """
    Vigilante de archivos de conocimiento base (Auto-Sync).
    Detecta archivos nuevos, modificados o eliminados en storage/knowledge/
    usando una estrategia de Async Polling.
    Tambien observa cambios en skills para hot-reload.
    """

    def __init__(
        self, loader: GlobalKnowledgeLoader, interval: int | float = 30
    ) -> None:
        self.loader = loader
        self.interval = interval
        self.knowledge_path = loader.knowledge_path
        self._file_snapshots: dict[str, float] = {}
        self._skill_snapshots: dict[str, float] = {}
        self._watch_task: asyncio.Task | None = None
        self._is_running = False
        self._skill_dirs = [
            Path("storage/skills"),
            Path("src/personality/skills"),
        ]
        self._on_skill_change: Callable | None = None

    def set_skill_change_callback(self, callback: Callable) -> None:
        """Registra un callback para cuando un skill cambia."""
        self._on_skill_change = callback

    async def start(self) -> None:
        """Inicia el loop de vigilancia en segundo plano."""
        if self._is_running:
            logger.warning("KnowledgeWatcher ya está en ejecución.")
            return

        if not self.knowledge_path.exists():
            logger.warning(
                f"Directorio de conocimiento no encontrado: "
                f"{self.knowledge_path}. No se puede iniciar el vigilante."
            )
            return

        # Snapshot inicial
        self._update_snapshots()

        self._is_running = True
        self._watch_task = asyncio.create_task(self._poll_loop())
        logger.info(
            f"KnowledgeWatcher iniciado. Monitoreando {self.knowledge_path} "
            f"cada {self.interval}s"
        )

    async def stop(self) -> None:
        """Detiene el loop de vigilancia."""
        self._is_running = False
        if self._watch_task:
            self._watch_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._watch_task
            self._watch_task = None
        logger.info("KnowledgeWatcher detenido.")

    def _get_current_files(self) -> dict[str, tuple[Path, float]]:
        """Escanea el directorio y retorna los archivos válidos con su mtime."""
        files: dict[str, tuple[Path, float]] = {}
        if not self.knowledge_path.exists():
            return files

        for file_path in self.knowledge_path.glob("*"):
            if file_path.is_dir() or file_path.name.startswith("."):
                continue

            should_process, _ = self.loader._should_process_file(file_path)
            if should_process:
                try:
                    files[file_path.name] = (file_path, file_path.stat().st_mtime)
                except FileNotFoundError:
                    continue

        return files

    def _update_snapshots(self) -> None:
        """Actualiza el estado interno sin disparar ingestas."""
        current = self._get_current_files()
        self._file_snapshots = {name: mtime for name, (_, mtime) in current.items()}

    async def _poll_loop(self) -> None:
        """Loop infinito de escaneo periodico."""
        while self._is_running:
            try:
                await asyncio.sleep(self.interval)
                await self._check_for_changes()
                await self._check_skill_changes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error en loop de KnowledgeWatcher: %s", e)

    def _get_skill_files(self) -> dict[str, float]:
        """Escanea directorios de skills y retorna SKILL.md con su mtime."""
        files: dict[str, float] = {}
        for base_dir in self._skill_dirs:
            if not base_dir.exists():
                continue
            for skill_dir in base_dir.iterdir():
                if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
                    continue
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    try:
                        key = f"{base_dir.name}/{skill_dir.name}/SKILL.md"
                        files[key] = skill_md.stat().st_mtime
                    except FileNotFoundError:
                        continue
        return files

    async def _check_skill_changes(self) -> None:
        """Detecta cambios en SKILL.md y dispara hot-reload."""
        if not self._on_skill_change:
            return

        current = self._get_skill_files()
        current_names = set(current.keys())
        previous_names = set(self._skill_snapshots.keys())

        changed = set()
        for name in current_names & previous_names:
            if current[name] > self._skill_snapshots[name]:
                changed.add(name)

        for name in changed:
            logger.info("Detectado skill modificado: %s", name)
            if self._on_skill_change is not None:
                try:
                    await self._on_skill_change(name)
                except Exception as e:
                    logger.error("Error en callback de skill change: %s", e)

        self._skill_snapshots = current

    async def _check_for_changes(self) -> None:
        """Detecta y procesa cambios en los archivos."""
        current_files = self._get_current_files()
        current_names = set(current_files.keys())
        previous_names = set(self._file_snapshots.keys())

        # 1. Archivos nuevos
        added = current_names - previous_names
        for name in added:
            path, mtime = current_files[name]
            logger.info(f"Detectado archivo nuevo: {name}")
            await self.loader.ingest_file(path)
            self._file_snapshots[name] = mtime

        # 2. Archivos eliminados
        removed = previous_names - current_names
        for name in removed:
            logger.info(f"Detectado archivo eliminado: {name}")
            await self.loader.manager.delete_file_knowledge(name, namespace="global")
            del self._file_snapshots[name]

        # 3. Archivos modificados
        common = current_names & previous_names
        for name in common:
            path, mtime = current_files[name]
            if mtime > self._file_snapshots[name]:
                logger.info(f"Detectado archivo modificado: {name}")
                # Re-ingesta: Borrar suave y volver a procesar
                await self.loader.manager.delete_file_knowledge(
                    name, namespace="global"
                )
                await self.loader.ingest_file(path)
                self._file_snapshots[name] = mtime
