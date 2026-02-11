# Procesamiento de Voz (FasterWhisper)

AEGEN utiliza una implementación optimizada de **FasterWhisper** para la transcripción de audio con baja latencia y alta precisión.

## 1. Configuración de Calidad

Para maximizar la precisión en contextos psicológicos, se aplican los siguientes parámetros:

- **Modelo:** `small` (Balance óptimo entre velocidad y precisión).
- **Precisión de Cálculo:** `float32` (Evita pérdida de calidad por cuantización).
- **Idioma Forzado:** `es` (Español) para prevenir detecciones erróneas.
- **Filtro VAD (Voice Activity Detection):** Activo para ignorar ruidos de fondo.
- **Duración Mínima de Silencio:** 700ms (Optimizado para el habla natural).

## 2. Implementación Técnica

```python
# Referencia de lógica en src/tools/speech_processing.py
segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    language="es",
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 700},
    compute_type="float32"
)
```

---
*Para detalles de integración con Telegram, ver `src/tools/telegram_interface.py`*
