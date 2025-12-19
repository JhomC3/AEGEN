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
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

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
        
        self.summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "Eres un experto en síntesis de memoria. Tu tarea es actualizar el 'Perfil Histórico' de un usuario basado en nuevos mensajes. "
                       "Mantén detalles críticos como nombres, preferencias, hechos importantes y el estado de proyectos actuales. "
                       "Sé conciso pero preciso. No borres información antigua a menos que haya sido corregida por el usuario."),
            ("user", "PERFIL ACTUAL:\n{current_summary}\n\nNUEVOS MENSAJES:\n{new_messages}\n\nActualiza el perfil integrando los nuevos mensajes:")
        ])

    def _get_local_path(self, chat_id: str) -> Path:
        return STORAGE_DIR / f"{chat_id}_memory.json"

    async def get_summary(self, chat_id: str) -> str:
        """Recupera el resumen histórico del usuario."""
        local_path = self._get_local_path(chat_id)
        if local_path.exists():
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("summary", "Sin historial previo.")
            except Exception as e:
                logger.error(f"Error leyendo memoria local para {chat_id}: {e}")
        
        return "Sin historial previo profesional."

    async def update_memory(self, chat_id: str, new_messages_text: str):
        """
        Analiza nuevos mensajes, actualiza el resumen y lo persiste.
        """
        current_summary = await self.get_summary(chat_id)
        
        try:
            # Generar nuevo resumen incremental
            chain = self.summary_prompt | self.llm
            response = await chain.ainvoke({
                "current_summary": current_summary,
                "new_messages": new_messages_text
            })
            
            new_summary = str(response.content).strip()
            
            # Persistir localmente
            local_path = self._get_local_path(chat_id)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump({"summary": new_summary, "chat_id": chat_id}, f, ensure_ascii=False)
            
            logger.info(f"Memoria de largo plazo actualizada para {chat_id}")
            
            # Sincronización opcional con Gemini File API (Shadow upload para backup)
            # Por ahora mantenemos local para velocidad, pero la estructura está lista.
            
        except Exception as e:
            logger.error(f"Error actualizando memoria para {chat_id}: {e}", exc_info=True)

# Instancia singleton
long_term_memory = LongTermMemoryManager()
