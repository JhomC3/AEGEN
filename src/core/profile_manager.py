
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

logger = logging.getLogger(__name__)

# Rutas - Relativas al root del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "memory"
PROFILE_PATH = STORAGE_DIR / "user_profile.json"

class UserProfileManager:
    """
    Gestiona el perfil evolutivo del usuario en formato JSON.
    Arquitectura 'Alma Evolutiva' v0.3.1.
    """

    def __init__(self):
        self.profile: Dict[str, Any] = self._get_default_profile()
        self._ensure_storage()

    def _ensure_storage(self):
        """Asegura que el directorio de almacenamiento existe."""
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_default_profile(self) -> Dict[str, Any]:
        """Retorna la estructura base de un perfil nuevo."""
        return {
            "identity": {
                "name": "Usuario",
                "style": "Stoic Trench",
                "preferred_language": "es"
            },
            "metrics": {
                "emotional_volatility": 0.5,
                "discipline_score": 0.5,
                "total_sessions": 0
            },
            "evolution": {
                "phase": "Inicio",
                "level": 1,
                "milestones_count": 0
            },
            "active_tags": ["bienvenida"],
            "timeline": [
                {
                    "date": datetime.now().isoformat(),
                    "event": "Creación del perfil evolutivo",
                    "type": "system"
                }
            ],
            "metadata": {
                "version": "0.3.1",
                "last_updated": datetime.now().isoformat()
            }
        }

    async def load_profile(self) -> Dict[str, Any]:
        """Carga el perfil desde el disco."""
        if not PROFILE_PATH.exists():
            logger.info("Perfil no encontrado. Creando uno por defecto.")
            await self.save_profile()
            return self.profile

        try:
            async with aiofiles.open(PROFILE_PATH, "r", encoding="utf-8") as f:
                content = await f.read()
                self.profile = json.loads(content)
                logger.debug("Perfil cargado exitosamente.")
                return self.profile
        except Exception as e:
            logger.error(f"Error cargando perfil: {e}")
            return self.profile

    async def save_profile(self):
        """Guarda el perfil actual en el disco."""
        try:
            self.profile["metadata"]["last_updated"] = datetime.now().isoformat()
            async with aiofiles.open(PROFILE_PATH, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.profile, indent=2, ensure_ascii=False))
            logger.info(f"Perfil evolutivo persistido en {PROFILE_PATH}")
        except Exception as e:
            logger.error(f"Error guardando perfil: {e}")

    async def add_milestone(self, event: str, event_type: str = "milestone", metadata: Optional[Dict] = None):
        """Añade un hito a la línea de tiempo."""
        milestone = {
            "date": datetime.now().isoformat(),
            "event": event,
            "type": event_type
        }
        if metadata:
            milestone["metadata"] = metadata
            
        self.profile["timeline"].append(milestone)
        self.profile["evolution"]["milestones_count"] += 1
        
        # Limitar timeline si crece mucho (mantener últimos 50 eventos)
        if len(self.profile["timeline"]) > 50:
            self.profile["timeline"] = self.profile["timeline"][-50:]
            
        await self.save_profile()

    async def update_metrics(self, volatility: Optional[float] = None, discipline: Optional[float] = None):
        """Actualiza métricas de usuario."""
        if volatility is not None:
            # Suavizado de métrica (moving average simple)
            current = self.profile["metrics"]["emotional_volatility"]
            self.profile["metrics"]["emotional_volatility"] = (current * 0.7) + (volatility * 0.3)
            
        if discipline is not None:
            current = self.profile["metrics"]["discipline_score"]
            self.profile["metrics"]["discipline_score"] = (current * 0.7) + (discipline * 0.3)
            
        await self.save_profile()

    async def add_tag(self, tag: str):
        """Añade un tag de interés/bibliografía if not exists."""
        if tag not in self.profile["active_tags"]:
            self.profile["active_tags"].append(tag)
            await self.save_profile()

    async def remove_tag(self, tag: str):
        """Remueve un tag si el usuario ya no lo requiere."""
        if tag in self.profile["active_tags"]:
            self.profile["active_tags"].remove(tag)
            await self.save_profile()

    def get_active_tags(self) -> List[str]:
        """Retorna tags actuales para Smart RAG."""
        return self.profile.get("active_tags", [])

    def get_style(self) -> str:
        """Retorna el estilo de comunicación preferido."""
        return self.profile.get("identity", {}).get("style", "Stoic Trench")

# Instancia singleton
user_profile_manager = UserProfileManager()
