# ADR 0022: Implementación de Knowledge Watcher mediante Async Polling

* **Estado:** Aceptado
* **Decisores:** Jhonn Muñoz C., AI Assistant (Opencode)
* **Fecha:** 2026-02-11
* **Contexto:** Evolución v0.7.0 (Saneamiento y Autonomía)

## Contexto y Problema

El sistema AEGEN necesita la capacidad de **Auto-Sync**: detectar automáticamente cambios (creación, modificación, eliminación) en los archivos de conocimiento base (`storage/knowledge/`) sin necesidad de reiniciar el servidor.

La solución estándar en Python es la librería `watchdog`, que utiliza APIs del sistema operativo (`inotify`, `FSEvents`) para notificaciones en tiempo real. Sin embargo, AEGEN opera bajo restricciones estrictas:

1.  **Filosofía Async-First:** Todo I/O debe ser asíncrono nativo (`asyncio`). `watchdog` utiliza hilos (threads) bloqueantes que requieren puentes complejos hacia el event loop.
2.  **Compatibilidad Docker:** En entornos contenerizados con volúmenes montados (como en desarrollo), los eventos de sistema de archivos (`inotify`) a menudo no se propagan correctamente desde el host al contenedor, requiriendo un fallback a polling de todos modos.
3.  **Minimización de Dependencias:** Se busca reducir la superficie de dependencias externas para facilitar el mantenimiento a largo plazo.

## Decisión

Se decide implementar un mecanismo de **Async Polling Nativo** (`KnowledgeWatcher`) en lugar de utilizar la librería `watchdog`.

### Detalles de Implementación:
1.  **Loop Asíncrono:** Una tarea de fondo (`asyncio.create_task`) que se ejecuta en el `lifespan` de la aplicación.
2.  **Intervalo de Sondeo:** Escaneo del directorio cada 30 segundos (configurable).
3.  **Detección de Cambios:** Comparación de snapshots en memoria (nombre de archivo + `mtime`).
4.  **Gestión de Estado:**
    *   **Nuevo:** Ingesta inmediata.
    *   **Modificado:** Eliminación de fragmentos previos (soft-delete) + Re-ingesta.
    *   **Eliminado:** Eliminación de fragmentos previos (soft-delete).

## Consecuencias

### Positivas
*   **Simplicidad:** Se elimina una dependencia externa y la complejidad de gestionar hilos.
*   **Robustez:** Funciona garantizadamente en cualquier entorno (Local, Docker, Kubernetes) sin problemas de propagación de eventos de sistema de archivos.
*   **Cumplimiento de Estándares:** Adherencia 100% a la arquitectura `async` del proyecto.
*   **Control:** Mayor facilidad para implementar *debouncing* natural (el intervalo de polling actúa como buffer).

### Negativas
*   **Latencia:** Los cambios no son instantáneos; existe un retraso máximo igual al intervalo de sondeo (30s).
*   **Costo Computacional:** El escaneo periódico consume ciclos de CPU, aunque despreciable para la cantidad actual de archivos (<100).

## Notas Adicionales
Si el volumen de archivos crece a escalas masivas (>10,000), esta decisión deberá revisarse en favor de un sistema de eventos híbrido.
