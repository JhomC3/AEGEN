# Manual de Gestión de Conocimiento de AEGEN

Este manual describe cómo alimentar a AEGEN con documentos, guías terapéuticas
y material de referencia usando el nuevo sistema de gestión de conocimiento.

## 1. Arquitectura del Sistema

AEGEN cuenta con un sistema profesional de gestión de conocimiento que incluye:

| Componente | Función |
|---|---|
| `KnowledgeManager` | Orquestador principal: valida, registra e ingiere archivos |
| `KnowledgeTracker` | Tabla `knowledge_files` en SQLite con trazabilidad completa |
| `KnowledgeIngestor` | Extrae texto y lo ingiere con `SemanticChunker` (Gemini Flash) o `RecursiveChunker` |
| `KnowledgeWatcher` | Vigilante opcional que detecta cambios en `storage/knowledge/` |

Cada archivo queda registrado con su hash SHA-256, estado, chunker usado y
cantidad de chunks generados. Esto permite saber exactamente qué está en el
sistema y cuándo se ingirió.

## 2. Tipos de Archivos Soportados

| Formato | Extensión | Recomendación |
|---|---|---|
| **PDF** | `.pdf` | Ideal para libros y guías. Debe tener texto seleccionable (no escaneos). |
| **Markdown** | `.md` | Mejor formato para notas estructuradas. |
| **Texto Plano** | `.txt` | Para notas rápidas o transcripciones. |

## 3. Cómo Subir Documentos

### Método A: Consola Web de Google Cloud (Recomendado)

1. Ve a [Google Cloud Console](https://console.cloud.google.com/compute/instances).
2. Ubica tu VM (`instance-20251218-164804`) y haz clic en **SSH** > **Abrir en ventana del navegador**.
3. En la esquina superior derecha de la terminal, haz clic en el ícono de **Subir archivo**.
4. Selecciona el PDF desde tu computadora. Se subirá a tu home (`~`).
5. Mueve el archivo a la carpeta de conocimiento:

```bash
mv ~/*.pdf ~/AEGEN/storage/knowledge/
```

### Método B: Línea de comandos (Avanzado)

```bash
gcloud compute scp "mi-documento.pdf" \
  jjhonn_1020@instance-20251218-164804:~/AEGEN/storage/knowledge/ \
  --zone us-central1-a
```

### Método C: Desde Google Drive

Si tienes los PDFs en Google Drive, desde la VM:

```bash
pip install gdown
gdown "https://drive.google.com/uc?id=FILE_ID" -O ~/AEGEN/storage/knowledge/libro.pdf
```

El FILE_ID se obtiene del link de compartir de Google Drive:
`https://drive.google.com/file/d/FILE_ID/view`

## 4. Comandos de Gestión

Después de subir los archivos, usar los siguientes comandos desde la VM:

```bash
cd ~/AEGEN

# Ver estado de todos los archivos registrados
make knowledge-status

# Sincronizar archivos nuevos en storage/knowledge/
make knowledge-sync

# Añadir un archivo específico
make knowledge-add FILE=ruta/al/archivo.pdf

# Eliminar un archivo y sus chunks
make knowledge-delete FILE=archivo.pdf

# Re-ingestiar todo (cambiar de chunker recursive → semantic)
make knowledge-reingest CHUNKER=semantic
```

### Interpretación del Estado

| Estado | Significado |
|---|---|
| `pending` | Archivo registrado, pendiente de ingestión |
| `ingesting` | Ingestión en progreso |
| `done` | Ingestión exitosa |
| `failed` | Error durante la ingestión (ver `error_message`) |

### Ver Logs en Tiempo Real

```bash
docker-compose logs -f app | grep "KNOWLEDGE\|INGESTION\|CHUNKER"
```

## 5. Chunkers Disponibles

| Chunker | Ventajas | Desventajas |
|---|---|---|
| `semantic` | Jerarquía L3→L4, dominio clasificado, ruido purificado | Usa Gemini (costo de API), más lento |
| `recursive` | Rápido, no usa API externa | Chunks planos por tamaño, puede cortar ideas |

**Recomendación:** Usar `semantic` para documentos importantes (libros, guías
clínicas). Usar `recursive` para notas rápidas o documentos de referencia.

## 6. Verificación Mensual de Integridad

Cada mes, verificar que los backups y snapshots están funcionando:

```bash
# 1. Verificar que los snapshots del disco existen
#    Ir a GCP Console → Compute Engine → Snapshots
#    Debe mostrarse un snapshot reciente (< 24h)

# 2. Verificar que el backup en GCS existe
gsutil ls gs://aegen-backups-jjhonn/backups/

# 3. Verificar el estado del sistema de conocimiento
make knowledge-status
```

## 7. Limpieza de Archivos Obsoletos

Periódicamente, eliminar archivos legacy que ya no se usan:

```bash
cd ~/AEGEN

# Eliminar archivos de BD obsoletos (si existen)
rm -f storage/memory.db storage/memory.sqlite

# Eliminar backups locales antiguos (GCS ya los tiene)
rm -f storage/backups/*.db
```

## 8. Respaldo y Recuperación

### Backup Automático

El sistema respalda automáticamente la base de datos a GCS después de cada
sesión de conversación (`session_logger.py`).

**Bucket:** `gs://aegen-backups-jjhonn`
**Retención:** 30 días (lifecycle rule automática)
**Snapshot del disco:** Diario con retención de 14 días

### Recuperación desde Backup

Si la VM se destruye o la base de datos se corrompe, el sistema restaura
automáticamente desde el último backup en GCS al arrancar (`dependencies.py:37`).
No se requiere intervención manual.
