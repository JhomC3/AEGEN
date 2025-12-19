# src/memory/long_term_memory.py
import logging
import os
import json
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import settings
from src.core.engine import llm

logger = logging.getLogger(__name__)

# Configuración del directorio de almacenamiento local
STORAGE_DIR = Path("storage/memory")

class LongTermMemoryManager:
    """
    Gestiona la memoria episódica de largo plazo mediante resúmenes incrementales
    y persistencia en Gemini File API.
    """

    def __init__(self):
        # Configurar SDK nativo por si se usa File API directamente
        api_key_str = settings.GOOGLE_API_KEY.get_secret_value() if settings.GOOGLE_API_KEY else ""
        genai.configure(api_key=api_key_str)
        
        # Reutilizamos el LLM global configurado en el sistema
        self.llm = llm
        
        # Asegurar que el directorio de almacenamiento existe
        try:
            STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directorio de memoria verificado: {STORAGE_DIR}")
        except PermissionError:
            logger.error(f"FATAL: Sin permisos para crear '{STORAGE_DIR}'.")
        except Exception as e:
            logger.error(f"Error inesperado creando '{STORAGE_DIR}': {e}")
        
        self.summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "Eres un experto en síntesis de memoria. Tu tarea es actualizar el 'Perfil Histórico' de un usuario basado en nuevos mensajes. "
                       "Mantén detalles críticos como nombres, preferencias, hechos importantes y el estado de proyectos actuales. "
                       "Sé conciso pero preciso. No borres información antigua a menos que haya sido corregida por el usuario."),
            ("user", "PERFIL ACTUAL:\n{current_summary}\n\nNUEVOS MENSAJES:\n{new_messages}\n\nActualiza el perfil integrando los nuevos mensajes:")
        ])

    def _get_buffer_path(self, chat_id: str) -> Path:
        return STORAGE_DIR / f"{chat_id}_buffer.json"

    async def get_summary(self, chat_id: str) -> dict[str, str]:
        """Recupera el resumen histórico y los mensajes en el búfer."""
        local_path = self._get_local_path(chat_id)
        buffer_path = self._get_buffer_path(chat_id)
        
        summary = "Sin historial previo profesional."
        raw_buffer = []

        if local_path.exists():
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    summary = data.get("summary", summary)
            except Exception as e:
                logger.error(f"Error leyendo memoria local para {chat_id}: {e}")

        if buffer_path.exists():
            try:
                with open(buffer_path, "r", encoding="utf-8") as f:
                    raw_buffer = json.load(f)
            except Exception as e:
                logger.error(f"Error leyendo búfer para {chat_id}: {e}")
        
        return {"summary": summary, "buffer": raw_buffer}

    async def store_raw_message(self, chat_id: str, role: str, content: str):
        """Guarda un mensaje en el búfer persistente inmediatamente."""
        buffer_path = self._get_buffer_path(chat_id)
        raw_buffer = []
        
        if buffer_path.exists():
            try:
                with open(buffer_path, "r", encoding="utf-8") as f:
                    raw_buffer = json.load(f)
            except Exception:
                pass
        
        raw_buffer.append({"role": role, "content": content})
        
        # Limitar el búfer a los últimos 20 mensajes antes de forzar resumen
        if len(raw_buffer) > 20:
            raw_buffer = raw_buffer[-20:]

        with open(buffer_path, "w", encoding="utf-8") as f:
            json.dump(raw_buffer, f, ensure_ascii=False)

    async def update_memory(self, chat_id: str):
        """
        Analiza el búfer de mensajes, actualiza el resumen y limpia el búfer.
        """
        data = await self.get_summary(chat_id)
        current_summary = data["summary"]
        raw_buffer = data["buffer"]
        
        if not raw_buffer:
            return

        # Convertir búfer a texto para el resumen
        new_messages_text = "\n".join([f"{m['role']}: {m['content']}" for m in raw_buffer])
        
        try:
            # Generar nuevo resumen incremental
            chain = self.summary_prompt | self.llm
            response = await chain.ainvoke({
                "current_summary": current_summary,
                "new_messages": new_messages_text
            })
            
            new_summary = str(response.content).strip()
            
            # Persistir resumen localmente
            local_path = self._get_local_path(chat_id)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump({"summary": new_summary, "chat_id": chat_id}, f, ensure_ascii=False)
            
            # Limpiar el búfer ya que ha sido consolidado en el resumen
            buffer_path = self._get_buffer_path(chat_id)
            if buffer_path.exists():
                buffer_path.unlink()
                
            logger.info(f"Memoria de largo plazo consolidada para {chat_id}")
            
        except Exception as e:
            logger.error(f"Error consolidando memoria para {chat_id}: {e}", exc_info=True)

# Instancia singleton
long_term_memory = LongTermMemoryManager()
