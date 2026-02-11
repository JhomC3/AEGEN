# src/memory/backup.py
"""
Cloud backup and restore manager for SQLite memory.

Provides functionality to snapshot, compress, and sync the local database
with Google Cloud Storage.
"""

import asyncio
import gzip
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

from src.core.config import settings
from src.memory.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class CloudBackupManager:
    """
    Gestiona el respaldo y recuperación de la base de datos en GCS.
    """

    def __init__(self, store: SQLiteStore | None = None):
        self.store = store or SQLiteStore(settings.SQLITE_DB_PATH)
        self.bucket_name = settings.GCS_BACKUP_BUCKET
        self._client = None

    def _get_client(self):
        """Inicializa el cliente de GCS."""
        if self._client:
            return self._client

        try:
            if settings.GCS_CREDENTIALS_JSON:
                import json

                creds_dict = json.loads(
                    settings.GCS_CREDENTIALS_JSON.get_secret_value()
                )
                credentials = service_account.Credentials.from_service_account_info(
                    creds_dict
                )
                self._client = storage.Client(credentials=credentials)
            else:
                # Usa GOOGLE_APPLICATION_CREDENTIALS env var por defecto
                self._client = storage.Client()
            return self._client
        except Exception as e:
            logger.error(f"Error initializing GCS client: {e}")
            return None

    async def create_backup(self) -> str | None:
        """
        Crea un snapshot de la DB, lo comprime y lo sube a GCS.
        """
        if not self.bucket_name:
            logger.warning("GCS_BACKUP_BUCKET not configured. Skipping backup.")
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        snapshot_path = Path(f"data/snapshot_{timestamp}.db")
        compressed_path = Path(f"data/backup_{timestamp}.db.gz")

        try:
            # 1. Crear snapshot seguro (VACUUM INTO)
            db = await self.store.get_db()
            await db.execute(f"VACUUM INTO '{snapshot_path}'")
            logger.info(f"Snapshot created at {snapshot_path}")

            # 2. Comprimir
            def compress_file():
                with open(snapshot_path, "rb") as f_in:
                    with gzip.open(compressed_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

            await asyncio.to_thread(compress_file)
            logger.info(f"Backup compressed to {compressed_path}")

            # 3. Subir a GCS
            client = self._get_client()
            if client:
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob(f"backups/{compressed_path.name}")
                blob.upload_from_filename(str(compressed_path))
                logger.info(
                    f"Backup uploaded to GCS: gs://{self.bucket_name}/backups/{compressed_path.name}"
                )
                return str(compressed_path.name)

        except Exception as e:
            logger.error(f"Error during backup process: {e}", exc_info=True)
            return None
        finally:
            # Limpiar archivos temporales locales
            if snapshot_path.exists():
                os.remove(snapshot_path)
            if compressed_path.exists():
                os.remove(compressed_path)

        return None

    async def restore_latest(self) -> bool:
        """
        Busca el backup más reciente en GCS y lo restaura localmente.
        """
        if not self.bucket_name:
            return False

        client = self._get_client()
        if not client:
            return False

        try:
            bucket = client.bucket(self.bucket_name)
            blobs = list(client.list_blobs(bucket, prefix="backups/"))

            if not blobs:
                logger.info("No backups found in GCS.")
                return False

            # Ordenar por nombre (que incluye fecha ISO) para obtener el último
            latest_blob = sorted(blobs, key=lambda x: x.name, reverse=True)[0]

            local_gz = Path(f"data/{os.path.basename(latest_blob.name)}")
            db_path = Path(settings.SQLITE_DB_PATH)

            # Asegurar que el directorio data existe
            db_path.parent.mkdir(exist_ok=True)

            print(f"📥 Descargando backup desde GCS: {latest_blob.name}...")
            latest_blob.download_to_filename(str(local_gz))

            # Descomprimir directamente al destino
            print(f"📂 Restaurando base de datos a {db_path}...")

            def decompress_file():
                with gzip.open(local_gz, "rb") as f_in:
                    with open(db_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

            await asyncio.to_thread(decompress_file)

            # Limpiar temporal
            os.remove(local_gz)
            logger.info("Database restored successfully from GCS.")
            return True

        except Exception as e:
            logger.error(f"Error during restore process: {e}", exc_info=True)
            return False
