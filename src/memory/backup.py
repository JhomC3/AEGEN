# src/memory/backup.py
"""
Cloud backup and restore manager for SQLite memory.

Provides functionality to snapshot, compress, and sync the local database
with Google Cloud Storage.
"""

import asyncio
import gzip
import logging
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

    def __init__(self, store: SQLiteStore | None = None) -> None:
        self.store = store or SQLiteStore(settings.SQLITE_DB_PATH)
        self.bucket_name = settings.GCS_BACKUP_BUCKET
        self._client = None

    def _get_client(self) -> storage.Client | None:
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

        # Asegurar que el directorio de backups existe
        backup_dir = Path(settings.SQLITE_BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        snapshot_path = backup_dir / f"snapshot_{timestamp}.db"
        compressed_path = backup_dir / f"backup_{timestamp}.db.gz"

        try:
            # 1. Crear snapshot seguro (VACUUM INTO)
            db = await self.store.get_db()
            # SQLite VACUUM INTO doesn't support parameterized queries for the filename
            # The path is constructed from a timestamp and controlled directory, so it is safe.
            await db.execute(f"VACUUM INTO '{snapshot_path}'")  # noqa: S608
            logger.info(f"Snapshot created at {snapshot_path}")

            # 2. Comprimir
            def compress_file():
                with snapshot_path.open("rb") as f_in:
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
                snapshot_path.unlink()
            if compressed_path.exists():
                compressed_path.unlink()

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

            backup_dir = Path(settings.SQLITE_BACKUP_DIR)
            backup_dir.mkdir(parents=True, exist_ok=True)

            local_gz = backup_dir / Path(latest_blob.name).name
            db_path = Path(settings.SQLITE_DB_PATH)

            logger.info(f"📥 Descargando backup desde GCS: {latest_blob.name}...")
            latest_blob.download_to_filename(str(local_gz))

            # Descomprimir directamente al destino
            logger.info(f"📂 Restaurando base de datos a {db_path}...")

            def decompress_file():
                # Explicitly open in binary mode
                with gzip.open(local_gz, "rb") as f_in:
                    with db_path.open("wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

            await asyncio.to_thread(decompress_file)

            # Limpiar temporal
            if local_gz.exists():
                local_gz.unlink()
            logger.info("Database restored successfully from GCS.")
            return True

        except Exception as e:
            logger.error(f"Error during restore process: {e}", exc_info=True)
            return False
