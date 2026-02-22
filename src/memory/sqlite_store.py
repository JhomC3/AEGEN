# src/memory/sqlite_store.py
import asyncio
import logging
import sys
from pathlib import Path

# Monkeypatch sqlite3 con sqlean para habilitar extensiones en macOS/Linux
try:
    import sqlean

    sys.modules["sqlite3"] = sqlean
except ImportError:
    pass

import aiofiles
import aiosqlite
import sqlite_vec

from src.memory.repositories.memory_repo import MemoryRepository
from src.memory.repositories.profile_repo import ProfileRepository
from src.memory.repositories.state_repo import StateRepository

logger = logging.getLogger(__name__)


class SQLiteStore:
    """
    Gestor de persistencia local basado en SQLite con soporte vectorial.
    Utiliza aiosqlite para operaciones asíncronas y sqlite-vec para búsqueda semántica.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

        # Repositorios
        self._memory_repo = MemoryRepository(self)
        self._profile_repo = ProfileRepository(self)
        self.state_repo = StateRepository(self)

        logger.info(f"SQLiteStore inicializado con ruta: {db_path}")

    async def connect(self) -> aiosqlite.Connection:
        """Establece la conexión y carga las extensiones necesarias."""
        async with self._lock:
            if self._connection is None:
                # Asegurar que el directorio existe
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

                # Conectar
                self._connection = await aiosqlite.connect(self.db_path)

                # Cargar extensión sqlite-vec usando la ruta de la librería
                await self._connection.enable_load_extension(True)
                await self._connection.load_extension(sqlite_vec.loadable_path())

                # Configurar row_factory para obtener diccionarios
                self._connection.row_factory = aiosqlite.Row

                logger.info(
                    "Conexión a SQLite establecida y extensión vectorial cargada."
                )

        return self._connection

    async def disconnect(self) -> None:
        """Cierra la conexión de forma segura."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Conexión a SQLite cerrada.")

    async def init_db(self, schema_path: str) -> None:
        """Inicializa la base de datos ejecutando el script SQL de esquema."""
        db = await self.connect()

        if not Path(schema_path).exists():
            raise FileNotFoundError(f"Archivo de esquema no encontrado: {schema_path}")

        # Usar aiofiles para lectura asíncrona del archivo
        async with aiofiles.open(schema_path) as f:
            schema_sql = await f.read()

        try:
            # Ejecutar script de inicialización
            await db.executescript(schema_sql)
            await db.commit()
            logger.info("Base de datos inicializada con el esquema proporcionado.")
        except Exception as e:
            logger.error(f"Error inicializando la base de datos: {e}")
            await db.rollback()
            raise

    async def get_db(self) -> aiosqlite.Connection:
        """Retorna la conexión activa, conectando si es necesario."""
        return await self.connect()

    # === Delegación a MemoryRepository ===

    async def insert_memory(
        self,
        chat_id: str,
        content: str,
        content_hash: str,
        memory_type: str,
        namespace: str = "user",
        metadata: dict | None = None,
        source_type: str = "explicit",
        confidence: float = 1.0,
        sensitivity: str = "low",
        evidence: str | None = None,
    ) -> int:
        return await self._memory_repo.insert_memory(
            chat_id,
            content,
            content_hash,
            memory_type,
            namespace,
            metadata,
            source_type,
            confidence,
            sensitivity,
            evidence,
        )

    async def insert_vector(self, memory_id: int, embedding: list[float]) -> int:
        return await self._memory_repo.insert_vector(memory_id, embedding)

    async def hash_exists(self, content_hash: str) -> bool:
        return await self._memory_repo.hash_exists(content_hash)

    async def soft_delete_memories(self, memory_ids: list[int]) -> int:
        return await self._memory_repo.soft_delete_memories(memory_ids)

    async def delete_memories_by_filename(
        self, filename: str, namespace: str = "global"
    ) -> int:
        return await self._memory_repo.delete_memories_by_filename(filename, namespace)

    async def get_memory_stats(self, chat_id: str) -> dict:
        return await self._memory_repo.get_memory_stats(chat_id)

    # === Delegación a ProfileRepository ===

    async def save_profile(self, chat_id: str, profile_data: dict) -> None:
        await self._profile_repo.save_profile(chat_id, profile_data)

    async def load_profile(self, chat_id: str) -> dict | None:
        return await self._profile_repo.load_profile(chat_id)

    async def list_all_chat_ids(self) -> list[str]:
        return await self._profile_repo.list_all_chat_ids()
