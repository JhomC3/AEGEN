# AEGEN - Product Requirements Document
> Version: 0.1.0; Estado: Prescriptivo; Owner: Product/Tech

## 1. Visión
Entregar respuestas precisas y rápidas a los usuarios a través de una plataforma de agentes federados, comenzando con transcripción y consulta de documentos.

## 2. Flujos y KPIs (Fase 2)
- **Transcripción:** p95 latencia < 2s; Word Error Rate (WER) no debe degradarse respecto a la línea base en `audio_samples/`.
- **Flujo de Inventario Conversacional:** p95 latencia < 3s por turno; Tasa de Éxito de Tarea (subir archivo, luego añadir 3 items por audio/texto) >= 95%.

## 3. Requisitos No Funcionales (NFRs)
- **Timeouts:** Timeout global por request de 30s.
- **Límites:** Tamaño máximo de archivo de audio de 25MB.
- **Costo:** Monitoreo del costo por 1k requests por flujo.

## 4. Fuera de Alcance (Fase 2)
- Memoria conversacional a largo plazo.
- Múltiples fuentes de datos para RAG.
