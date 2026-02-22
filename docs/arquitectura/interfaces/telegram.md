# Interfaz de Telegram

Telegram es la puerta de entrada principal para los usuarios de AEGEN. Este módulo gestiona la comunicación con la API de Bot de Telegram y la transformación de mensajes.

## 1. Gestión de Eventos

El sistema utiliza un **Webhook** para recibir actualizaciones en tiempo real. Cada mensaje se transforma en un `CanonicalEventV1` antes de ser enviado al orquestador.

### Tipos de Mensajes Soportados
- **Texto**: Procesamiento directo de lenguaje natural.
- **Voz/Audio**: Descarga automática y delegación al `TranscriptionAgent`.
- **Comandos**: Interceptación de comandos de sistema (`/privacidad`, `/olvidar`).

## 2. Herramientas de Respuesta

El sistema utiliza herramientas estandarizadas (`tools`) para enviar respuestas de vuelta al usuario:
- **reply_to_telegram_chat**: Envía un mensaje de texto. Utiliza el campo estándar `text` para el contenido del mensaje, asegurando compatibilidad con los esquemas de validación internos y la API de Telegram.

## 3. Seguridad y Robustez

- **Validación de Token**: Solo se aceptan peticiones con el token de bot configurado.
- **Reintentos**: El sistema de polling (sondeo) utiliza retroceso exponencial (backoff) para reconectar en caso de fallos de red.
- **Limpieza de Archivos**: Los archivos descargados temporalmente se eliminan tras su procesamiento.

---
*Ver implementación en `src/tools/telegram_interface.py` y `src/api/routers/webhooks.py`*
