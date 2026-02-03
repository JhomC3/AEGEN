# src/memory/cloud_gateway.py
import json
import logging
import re
from datetime import datetime
from typing import Any

import yaml

from src.tools.google_file_search import file_search_tool

logger = logging.getLogger(__name__)


class CloudMemoryGateway:
    """
    Gateway centralizado para la persistencia de memoria en Google Cloud.
    Implementa el patrón de Memoria Unificada (Markdown + YAML Frontmatter).
    """

    def __init__(self):
        logger.info("CloudMemoryGateway inicializado")

    def serialize_to_markdown(
        self, data: dict[str, Any], metadata: dict[str, Any]
    ) -> str:
        """
        Convierte un diccionario de datos en un archivo Markdown con Frontmatter YAML.
        """
        frontmatter = yaml.dump(metadata, sort_keys=False, allow_unicode=True)

        # Generar cuerpo legible para RAG
        body = self._generate_readable_body(metadata.get("type", "unknown"), data)

        return f"---\n{frontmatter}---\n\n{body}"

    def deserialize_from_markdown(
        self, content: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Extrae el Frontmatter YAML y el cuerpo de un archivo Markdown.
        """
        try:
            # Buscar bloques entre ---
            match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not match:
                return {}, {}

            yaml_content = match.group(1)
            metadata = yaml.safe_load(yaml_content)

            # El cuerpo es todo lo que sigue al segundo ---
            body_start = match.end()
            body = content[body_start:].strip()

            return metadata, {"body": body}
        except Exception as e:
            logger.error(f"Error deserializando memoria: {e}")
            return {}, {}

    async def upload_memory(
        self, chat_id: str, filename: str, data: dict[str, Any], mem_type: str
    ):
        """
        Sincroniza un objeto de datos con Google Cloud.
        """
        metadata = {
            "chat_id": chat_id,
            "type": mem_type,
            "last_updated": datetime.now().isoformat(),
            "version": "1.2.0",
            "data": data,  # Guardamos los datos puros en el YAML para recuperación determinística
        }

        content = self.serialize_to_markdown(data, metadata)

        # Siempre usamos .md y text/plain
        cloud_filename = f"{filename}.md" if not filename.endswith(".md") else filename

        try:
            await file_search_tool.upload_from_string(
                content=content,
                filename=cloud_filename,
                chat_id=chat_id,
                mime_type="text/plain",
            )
            logger.info(f"Memoria '{mem_type}' subida a cloud para {chat_id}")
        except Exception as e:
            logger.error(f"Error subiendo memoria a cloud: {e}")

    async def download_memory(
        self, chat_id: str, filename: str
    ) -> dict[str, Any] | None:
        """
        Recupera y deserializa memoria desde Google Cloud.
        Como la File API no permite descarga directa, usamos una consulta RAG específica
        pidiendo el contenido RAW del bloque YAML.
        """
        cloud_filename = f"{filename}.md" if not filename.endswith(".md") else filename

        query = f"Extrae el contenido completo del bloque entre '---' del archivo {cloud_filename}. Quiero el YAML puro."

        try:
            # Forzamos una consulta que devuelva el contenido textual
            raw_content = await file_search_tool.query_files(query, chat_id)

            if not raw_content or "No encontrado" in raw_content:
                return None

            # Intentar parsear el YAML recuperado
            # A veces el LLM añade ```yaml ... ```, lo limpiamos
            clean_yaml = re.sub(r"```yaml|```", "", raw_content).strip()

            # Si el RAG falló en dar el YAML exacto, intentamos una búsqueda por campos
            if not clean_yaml.startswith("chat_id"):
                logger.warning(
                    "RAG no devolvió YAML puro, intentando recuperación semántica asistida"
                )
                return await self._semantic_recovery(chat_id, filename)

            metadata = yaml.safe_load(clean_yaml)
            return metadata.get("data")

        except Exception as e:
            logger.error(f"Error descargando memoria de cloud para {chat_id}: {e}")
            return None

    async def _semantic_recovery(
        self, chat_id: str, filename: str
    ) -> dict[str, Any] | None:
        """Fallback semántico si el YAML no se pudo recuperar exacto."""
        from src.core.engine import llm

        query = f"Dame todos los datos técnicos del archivo {filename} en formato JSON."
        raw_text = await file_search_tool.query_files(query, chat_id)

        if not raw_text:
            return None

        prompt = (
            "Convierte esta información de memoria en un objeto JSON válido. "
            f"La información pertenece al archivo {filename}.\n\n"
            f"DATOS:\n{raw_text}\n\n"
            "RESPONDE SOLO EL JSON:"
        )

        try:
            resp = await llm.ainvoke(prompt)
            match = re.search(r"(\{[\s\S]*\})", str(resp.content))
            if match:
                return json.loads(match.group(1))
        except Exception:
            return None
        return None

    def _generate_readable_body(self, mem_type: str, data: dict[str, Any]) -> str:
        """Genera un cuerpo Markdown legible para que RAG funcione mejor."""
        if mem_type == "user_profile":
            identity = data.get("identity", {})
            return f"# Perfil de {identity.get('name', 'Usuario')}\n- Estilo: {identity.get('style')}\n- Metas: {data.get('values_and_goals', {}).get('short_term_goals')}"

        if mem_type == "knowledge_base":
            facts = data.get("entities", [])
            return f"# Bóveda de Conocimiento\n- Hechos: {', '.join([str(f) for f in facts])}"

        return f"Datos de tipo {mem_type}: {json.dumps(data, ensure_ascii=False)}"


# Singleton
cloud_gateway = CloudMemoryGateway()
