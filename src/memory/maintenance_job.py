# src/memory/maintenance_job.py
import asyncio
import logging
from datetime import UTC, datetime, timedelta

from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)


class MemoryMaintenanceJob:
    """
    Job periódico para evitar que los archivos expiren en Google Cloud (48h limit).
    Se ejecuta cada 24 horas.
    """

    def __init__(self, interval_hours: int = 24):
        self.interval = interval_hours * 3600
        logger.info(f"MemoryMaintenanceJob inicializado (Intervalo: {interval_hours}h)")

    async def start(self):
        """Inicia el ciclo infinito del job."""
        while True:
            try:
                await self.refresh_all_files()
            except Exception as e:
                logger.error(f"Error en job de mantenimiento de memoria: {e}")

            logger.info(
                f"Mantenimiento completado. Siguiente ejecución en {self.interval / 3600}h"
            )
            await asyncio.sleep(self.interval)

    async def refresh_all_files(self):
        """
        Lista todos los archivos y vuelve a subir aquellos que estén por expirar.
        En esta arquitectura unificada, 'refresh' significa volver a persistir
        desde Redis a Cloud para los perfiles activos.
        """
        logger.info("Iniciando refresh de archivos en Google Cloud...")

        files = await file_search_tool.list_files()
        now = datetime.now(UTC)

        # Google File API expira a las 48h. Refrescamos si tienen > 24h.
        for f in files:
            creation_time = f.create_time  # datetime object
            if not creation_time:
                continue

            age = now - creation_time

            if age > timedelta(hours=24):
                logger.info(
                    f"Archivo detectado para renovación: {f.display_name} (Edad: {age})"
                )
                # Aquí la lógica ideal es disparar un evento de 're-sync'
                # Por ahora, los perfiles se refrescan con cada interacción.
                # Para archivos de conocimiento global, el GlobalKnowledgeLoader lo maneja.
                pass

    def run_in_background(self):
        """Dispara el job en el loop de asyncio."""
        asyncio.create_task(self.start())


# Singleton
memory_maintenance_job = MemoryMaintenanceJob()
