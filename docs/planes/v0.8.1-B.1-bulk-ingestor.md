# Plan B.1: Herramienta de Ingesta Masiva (Bulk Ingestor)

> **Fecha:** 12 de Febrero, 2026
> **Fase:** Bloque B.1 del Plan Maestro `v0.7.0-saneamiento-y-evolucion.md`
> **Estado:** Propuesto

---

## 1. Diagnóstico y Necesidad

AEGEN es más potente cuanta más memoria tiene del usuario. Actualmente, la memoria se construye mensaje a mensaje. Permitir la ingesta de historiales previos de otras IAs (ChatGPT, Claude) o apps de mensajería (WhatsApp) acelerará drásticamente la personalización de MAGI.

### Formatos Soportados Inicialmente
- **ChatGPT:** Exportación JSON (`conversations.json`).
- **Claude:** Exportación JSON (`conversations.json`).
- **WhatsApp:** Exportación TXT (Chat export).

---

## 2. Arquitectura Propuesta

Se creará un servicio centralizado de ingesta que delegue el parseo a clases especializadas por formato.

```
src/tools/bulk_ingestor/
├── __init__.py
├── base_parser.py       # Interfaz Abstracta
├── chatgpt_parser.py    # Lógica para OpenAI
├── claude_parser.py     # Lógica para Anthropic
└── whatsapp_parser.py   # Lógica para WhatsApp
```

El flujo será:
1. **Identificación:** Detectar el formato del archivo.
2. **Parseo:** Extraer mensajes (Human/Assistant) y timestamps.
3. **Normalización:** Convertir a `GenericMessageEvent` o directamente a llamadas al `IngestionPipeline`.
4. **Procesamiento:** Inyectar en la memoria persistente (`SQLiteStore`) con metadatos de procedencia (`source_type='observed'`, `metadata={'source': 'chatgpt_import'}`).

---

## 3. Pasos de Implementación

### Paso 1: Definir la Estructura de Datos y BaseParser
Crear la interfaz que define cómo debe comportarse un parser.

### Paso 2: Implementar ChatGPT Parser
Lógica para navegar el JSON de OpenAI, extrayendo hilos conversacionales coherentes.

### Paso 3: Implementar Claude Parser
Lógica similar para el formato de Anthropic.

### Paso 4: Implementar WhatsApp Parser
Parser de texto plano con soporte para formatos de fecha variables (según región del export).

### Paso 5: Integración con IngestionPipeline
Asegurar que los mensajes masivos no saturen el sistema (batch processing) y que se use la memoria de procedencia correctamente.

### Paso 6: CLI de Ingesta
Crear un script `scripts/bulk_import.py` para ejecución manual por parte del usuario/admin.

---

## 4. Consideraciones de Seguridad y Privacidad
- El proceso debe ser local.
- No se suben archivos a la nube antes de ser procesados (a menos que se use un canal seguro).
- Se debe validar el `chat_id` para evitar contaminación de perfiles.

---

## 5. Archivos Afectados
- `src/tools/bulk_ingestor/` (Nueva carpeta)
- `scripts/bulk_import.py` (Nuevo script)
- `src/memory/ingestion_pipeline.py` (Posibles ajustes para batching)
