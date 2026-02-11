# src/memory/sqlite_store.py
import asyncio
import sys

# Monkeypatch sqlite3 con sqlean para habilitar extensiones en macOS/Linux
try:
    import sqlean

    sys.modules["sqlite3"] = sqlean
except ImportError:
    pass

import logging
from pathlib import Path

import aiofiles
import aiosqlite
import sqlite_vec

logger = logging.getLogger(__name__)


class SQLiteStore:
    """
    Gestor de persistencia local basado en SQLite con soporte vectorial.
    Utiliza aiosqlite para operaciones asíncronas y sqlite-vec para búsqueda semántica.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()
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

    async def disconnect(self):
        """Cierra la conexión de forma segura."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Conexión a SQLite cerrada.")

    async def init_db(self, schema_path: str):
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
        """
        Inserta una memoria con metadatos de provenance.
        Retorna el ID de la memoria insertada.
        """
        import json
        import sqlite3

        db = await self.get_db()
        metadata_json = json.dumps(metadata or {})

        try:
            cursor = await db.execute(
                """
                INSERT INTO memories
                    (chat_id, namespace, content, content_hash, memory_type,
                     metadata, source_type, confidence, sensitivity, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    namespace,
                    content,
                    content_hash,
                    memory_type,
                    metadata_json,
                    source_type,
                    confidence,
                    sensitivity,
                    evidence,
                ),
            )
            memory_id = cursor.lastrowid
            await db.commit()
            return memory_id if memory_id is not None else -1
        except sqlite3.IntegrityError:
            # Probablemente duplicado por hash
            logger.debug(f"Memory with hash {content_hash} already exists.")
            async with db.execute(
                "SELECT id FROM memories WHERE content_hash = ?", (content_hash,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else -1
        except Exception as e:
            logger.error(f"Error inserting memory: {e}")
            await db.rollback()
            raise

    async def insert_vector(self, memory_id: int, embedding: list[float]) -> int:
        """
        Inserta un vector y lo vincula con una memoria.
        """
        import struct

        db = await self.get_db()
        vector_blob = struct.pack(f"{len(embedding)}f", *embedding)

        try:
            # 1. Insertar en tabla vectorial
            cursor = await db.execute(
                "INSERT INTO memory_vectors(embedding) VALUES (?)", (vector_blob,)
            )
            vector_id = cursor.lastrowid

            # 2. Vincular en tabla de mapeo
            await db.execute(
                "INSERT INTO vector_memory_map (vector_id, memory_id) VALUES (?, ?)",
                (vector_id, memory_id),
            )
            await db.commit()
            return vector_id if vector_id is not None else -1
        except Exception as e:
            logger.error(f"Error inserting vector: {e}")
            await db.rollback()
            raise

    async def hash_exists(self, content_hash: str) -> bool:
        """Verifica si un hash de contenido ya existe en la DB."""
        db = await self.get_db()
        async with db.execute(
            "SELECT 1 FROM memories WHERE content_hash = ?", (content_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

    async def soft_delete_memories(self, memory_ids: list[int]) -> int:
        """Marks memories as inactive (soft delete). Returns count updated."""
        if not memory_ids:
            return 0
        db = await self.get_db()
        placeholders = ",".join(["?"] * len(memory_ids))
        try:
            cursor = await db.execute(
                f"UPDATE memories SET is_active = 0 WHERE id IN ({placeholders})",  # nosec B608
                memory_ids,
            )
            await db.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error in soft_delete_memories: {e}")
            await db.rollback()
            return 0

    async def get_memory_stats(self, chat_id: str) -> dict:
        """Returns memory statistics for a user."""
        db = await self.get_db()
        stats: dict = {"total": 0, "by_type": {}, "by_sensitivity": {}}
        try:
            async with db.execute(
                "SELECT memory_type, sensitivity, COUNT(*) as cnt "
                "FROM memories WHERE chat_id = ? AND is_active = 1 "
                "GROUP BY memory_type, sensitivity",
                (chat_id,),
            ) as cursor:
                for row in await cursor.fetchall():
                    mtype, sens, cnt = row[0], row[1] or "low", row[2]
                    stats["by_type"][mtype] = stats["by_type"].get(mtype, 0) + cnt
                    stats["by_sensitivity"][sens] = (
                        stats["by_sensitivity"].get(sens, 0) + cnt
                    )
                    stats["total"] += cnt
        except Exception as e:
            logger.error(f"Error in get_memory_stats: {e}")
        return stats

    async def save_profile(self, chat_id: str, profile_data: dict) -> None:
        """Guarda un perfil de usuario en la DB."""
        import json

        db = await self.get_db()
        payload = json.dumps(profile_data, ensure_ascii=False)

        try:
            await db.execute(
                """
                INSERT INTO profiles (chat_id, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(chat_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, payload),
            )
            await db.commit()
        except Exception as e:
            logger.error(f"Error saving profile to SQLite: {e}")
            await db.rollback()
            raise

    async def load_profile(self, chat_id: str) -> dict | None:
        """Carga un perfil de usuario de la DB."""
        import json

        db = await self.get_db()
        try:
            async with db.execute(
                "SELECT data FROM profiles WHERE chat_id = ?", (chat_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row["data"])
                return None
        except Exception as e:
            logger.error(f"Error loading profile from SQLite: {e}")
            return None
