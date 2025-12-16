# src/memory/vector_memory_manager.py
from enum import Enum


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    PREFERENCE = "preference"
    DOCUMENT = "document"


class VectorMemoryManager:
    def __init__(self):
        pass

    async def retrieve_context(
        self, user_id: str, query: str, context_type: MemoryType, limit: int
    ):
        return []

    async def store_context(
        self, user_id: str, content: str, context_type: MemoryType, metadata: dict
    ):
        return True
