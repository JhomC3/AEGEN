from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class GenericMessage:
    """
    Un objeto de datos (DTO) para representar un mensaje de forma agnóstica
    a la plataforma de origen (Telegram, Slack, etc.).
    """

    user_info: Dict[str, Any]
    message_type: str  # "text", "image", "audio", etc.
    content: Any  # Puede ser texto, o un objeto de archivo para otros tipos
    file_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
