#!/usr/bin/env python3
# scripts/sync_knowledge.py
"""
Script oficial de sincronización de conocimiento global.

Inicializa los recursos globales, ejecuta el cargador de conocimiento
aplicando los filtros de seguridad, y cierra las conexiones limpiamente.

Uso: python -m scripts.sync_knowledge
"""

import asyncio
import logging
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.dependencies import initialize_global_resources, shutdown_global_resources
from src.memory.global_knowledge_loader import global_knowledge_loader

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sync_knowledge")


async def main():
    logger.info("=== Iniciando Sincronización de Conocimiento Global ===")

    # 1. Inicializar base de datos y recursos
    try:
        await initialize_global_resources()
        logger.info("Recursos globales inicializados.")
    except Exception as e:
        logger.error(f"Error fatal inicializando recursos: {e}")
        return

    # 2. Ejecutar sincronización
    try:
        await global_knowledge_loader.sync_knowledge()
    except Exception as e:
        logger.error(f"Error durante la sincronización: {e}")
    finally:
        # 3. Cerrar conexiones
        await shutdown_global_resources()
        logger.info("Conexiones cerradas.")

    logger.info("=== Proceso de sincronización completado ===")


if __name__ == "__main__":
    asyncio.run(main())
