# Comunicación Inter-Agentes

AEGEN utiliza contratos estrictos (Pydantic) para la delegación de tareas entre el Orquestador y los especialistas.

## 1. Contratos de Delegación

### Petición de Delegación Interna
Define la tarea, el mensaje del usuario y el contexto necesario.

```python
class InternalDelegationRequest(BaseModel):
    task_type: Literal["planning", "analysis", "transcription", "document_processing"]
    user_message: str
    context: dict[str, Any]
    conversation_history: list[V2ChatMessage]
    priority: Literal["low", "medium", "high", "urgent"]
```

### Respuesta de Delegación Interna
Estandariza la salida del especialista para que el ChatAgent pueda "traducirla" al usuario.

```python
class InternalDelegationResponse(BaseModel):
    status: Literal["success", "error", "partial"]
    result: dict[str, Any]
    summary: str
    suggestions: list[str]
    error_details: Optional[str]
```

## 2. Lógica de Traducción
Cuando un especialista devuelve un `result` técnico, el sistema utiliza un paso de **Response Translation** para convertir datos estructurados en una respuesta empática y natural.

---
*Esquemas definidos en `src/core/schemas/agents.py`*
