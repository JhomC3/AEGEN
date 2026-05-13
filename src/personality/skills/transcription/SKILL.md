---
name: "Transcription Agent"
id: "transcription_agent"
version: "1.0.0"
capabilities: ["audio"]
requirements:
  tools: ["transcription_tool"]
  memory_access: "none"
  priority: 5
  update_history: false
  chain_to: "chat_specialist"
---

## Instructions
Transcribe audio recibido usando Groq Whisper API.
Devuelve la transcripción al agente de chat para continuar la conversación.
