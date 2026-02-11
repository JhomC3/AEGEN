from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class Message:
    """Estructura de mensaje en cola."""

    id: str
    user_id: str
    content: str
    timestamp: datetime
    metadata: dict[str, Any] | None = None
    target_agent: str | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        content: str,
        target_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Message":
        """Crea nuevo mensaje con ID único."""
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            target_agent=target_agent,
        )
