import asyncio
import gzip
import logging
import shutil
import time
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.core.dependencies import get_sqlite_store

logger = logging.getLogger(__name__)


class CloudBackupManager:
    """Gestiona copias de seguridad en Google Cloud Storage."""

    def __init__(self, bucket_name: str | None = None) -> None:
        self.bucket_name = bucket_name or settings.GCS_BACKUP_BUCKET
        self.store = get_sqlite_store()

    def _get_client(self) -> Any:
        try:
            from google.cloud import storage

            return storage.Client()
        except ImportError:
            logger.warning("google-cloud-storage not installed.")
            return None

    async def create_backup(self) -> str | None:
        """Crea un backup comprimido y lo sube a GCS."""
        if not self.bucket_name:
            logger.warning("GCS_BACKUP_BUCKET not configured.")
            return None

        db_path = Path(settings.SQLITE_DB_PATH)
        timestamp = int(time.time())
        snapshot_path = db_path.parent / f"snapshot_{timestamp}.db"
        compressed_path = db_path.parent / f"backup_{timestamp}.db.gz"

        try:
            # 1. Snapshot
            db = await self.store.get_db()
            # SQLite VACUUM INTO
            await db.execute(f"VACUUM INTO '{snapshot_path}'")  # noqa: S608
            logger.info("Snapshot created at %s", snapshot_path)

            # 2. Comprimir
            def compress_file() -> None:
                with (
                    snapshot_path.open("rb") as f_in,
                    gzip.open(compressed_path, "wb") as f_out,
                ):
                    shutil.copyfileobj(f_in, f_out)

            await asyncio.to_thread(compress_file)

            # 3. Subir
            client = self._get_client()
            if client:
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob(f"backups/{compressed_path.name}")
                blob.upload_from_filename(str(compressed_path))
                logger.info(
                    "Backup uploaded: gs://%s/backups/%s",
                    self.bucket_name,
                    compressed_path.name,
                )
                return str(compressed_path.name)

        except Exception as e:
            logger.error("Backup failed: %s", e)
        finally:
            if snapshot_path.exists():
                snapshot_path.unlink()
            if compressed_path.exists():
                compressed_path.unlink()

        return None

    async def restore_latest(self) -> bool:
        """Descarga y restaura el último backup desde GCS."""
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

            latest_blob = max(blobs, key=lambda b: b.updated)
            local_gz = Path(settings.SQLITE_DB_PATH).parent / latest_blob.name
            latest_blob.download_to_filename(str(local_gz))

            db_path = Path(settings.SQLITE_DB_PATH)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            def decompress() -> None:
                with gzip.open(local_gz, "rb") as f_in, db_path.open("wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            await asyncio.to_thread(decompress)
            local_gz.unlink()
            logger.info("Restored from %s", latest_blob.name)
            return True
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return False
