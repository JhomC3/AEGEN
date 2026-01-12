
import asyncio
import json
import logging
import re
from pathlib import Path

import aiofiles

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Rutas - Ajustadas para ser relativas al root del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "memory"

# Patrones de "Trauma Técnico" a eliminar
BAD_PATTERNS = [
    r"error.*api",
    r"api.*error",
    r"lo siento",
    r"disculpa",
    r"fecha.*incorrecta",
    r"no.*puedo.*procesar",
    r"mis disculpas",
    r"soy una ia",
    r"modelo de lenguaje",
    r"technical issue",
    r"rate limit",
    r"quota exceeded",
    r"429",
    r"501",
    r"500",
]

async def sanitize_file(file_path: Path):
    """Limpia un archivo específico de patrones tóxicos."""
    try:
        logger.info(f"Escaneando: {file_path.name}")
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Archivo corrupto o no JSON: {file_path.name}. Omitiendo.")
            return

        is_dirty = False
        
        # Estrategia para summaries (diccionarios)
        if isinstance(data, dict):
            if "summary" in data:
                original_summary = data["summary"]
                cleaned_summary = original_summary
                
                # Reemplazo agresivo en el texto del resumen
                for pattern in BAD_PATTERNS:
                    if re.search(pattern, cleaned_summary, re.IGNORECASE):
                        logger.info(f"⚠️ Detectado patrón tóxico '{pattern}' en {file_path.name}")
                        cleaned_summary = re.sub(pattern, "[...]", cleaned_summary, flags=re.IGNORECASE)
                        is_dirty = True
                
                # Si detectamos mucha basura, reseteamos a un estado estoico limpio
                if is_dirty or "error" in cleaned_summary.lower():
                     logger.warning(f"☢️ Resumen altamente contaminado en {file_path.name}. RESETEANDO.")
                     data["summary"] = "El usuario busca disciplina y control emocional en su trading. Estilo directo y estoico preferido."
                     is_dirty = True
                else:
                    data["summary"] = cleaned_summary

            # Limpiar buffer (lista de mensajes) si existe
            if "buffer" in data and isinstance(data["buffer"], list):
                new_buffer = []
                for msg in data["buffer"]:
                    msg_content = msg.get("content", "")
                    if any(re.search(p, msg_content, re.IGNORECASE) for p in BAD_PATTERNS):
                        logger.info(f"🗑️ Eliminando mensaje tóxico del buffer en {file_path.name}")
                        is_dirty = True
                        continue # Saltamos este mensaje
                    new_buffer.append(msg)
                data["buffer"] = new_buffer
        
        if is_dirty:
            # Escribir limpio
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))
            logger.info(f"✅ Archivo SANEADO guardado: {file_path.name}")
        else:
            logger.info(f"✨ Archivo limpio: {file_path.name}")

    except Exception as e:
        logger.error(f"Error procesando {file_path}: {e}")

async def main():
    logger.info(f"Verificando directorio de almacenamiento: {STORAGE_DIR}")
    if not STORAGE_DIR.exists():
        logger.error(f"Directorio no encontrado: {STORAGE_DIR}")
        return

    tasks = []
    for file_path in STORAGE_DIR.glob("*.json"):
        if "profile" in file_path.name:
            continue
        tasks.append(sanitize_file(file_path))
    
    if tasks:
        await asyncio.gather(*tasks)
        logger.info("🏁 Lobotomía completada.")
    else:
        logger.info("No se encontraron archivos de memoria para escanear.")

if __name__ == "__main__":
    asyncio.run(main())
