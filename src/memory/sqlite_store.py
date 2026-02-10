# src/memory/sqlite_store.py
import sys

# Monkeypatch sqlite3 con sqlean para habilitar extensiones en macOS/Linux
try:
    import sqlean

    sys.modules["sqlite3"] = sqlean
except ImportError:
    pass

import logging
from pathlib import Path
from typing import Optional

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
        self._connection: Optional[aiosqlite.Connection] = None
        logger.info(f"SQLiteStore inicializado con ruta: {db_path}")

    async def connect(self) -> aiosqlite.Connection:
        """Establece la conexión y carga las extensiones necesarias."""
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

            logger.info("Conexión a SQLite establecida y extensión vectorial cargada.")

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
    ) -> int:
        """
        Inserta una memoria en la base de datos.
        Retorna el ID de la memoria insertada.
        """
        import json
        import sqlite3

        db = await self.get_db()
        metadata_json = json.dumps(metadata or {})

        try:
            cursor = await db.execute(
                """
                INSERT INTO memories (chat_id, namespace, content, content_hash, memory_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chat_id, namespace, content, content_hash, memory_type, metadata_json),
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
