# Manual de Gestión de Conocimiento (Auto-Sync)

Este manual describe cómo alimentar el cerebro de **AEGEN** con nuevos documentos, guías terapéuticas y material de referencia sin necesidad de conocimientos de programación ni reinicios del sistema.

## 1. Concepto de "Auto-Sync"
AEGEN cuenta con un **Vigilante de Conocimiento** (`KnowledgeWatcher`) que monitorea constantemente una carpeta específica.
Cualquier archivo válido que coloques allí será:
1.  **Detectado** automáticamente en menos de 30 segundos.
2.  **Leído y procesado** (extracción de texto).
3.  **Indexado** en la memoria vectorial para ser usado en futuras conversaciones.

---

## 2. Tipos de Archivos Soportados

| Formato | Extensión | Recomendación |
| :--- | :--- | :--- |
| **PDF** | `.pdf` | Ideal para libros, papers y guías formateadas. **Debe tener texto seleccionable** (no escaneos de imagen). |
| **Markdown** | `.md` | El mejor formato para notas técnicas o estructuradas. |
| **Texto Plano** | `.txt` | Para notas rápidas o transcripciones simples. |

> ⚠️ **Nota:** Los archivos de imagen, Word (.docx) o Excel (.xlsx) **NO** son procesados actualmente y serán ignorados por el sistema.

---

## 3. Cómo Subir Documentos (Paso a Paso)

El sistema se ejecuta en una Máquina Virtual (VM) de Google Cloud. Debes colocar los archivos en la carpeta `~/AEGEN/storage/knowledge/` de esa VM.

### Método A: Desde la Consola Web de Google Cloud (Fácil)
Ideal para subir 1 o 2 archivos rápidamente sin configurar nada en tu PC.

1.  Ve a [Google Cloud Console > Compute Engine](https://console.cloud.google.com/compute/instances).
2.  Ubica tu instancia (ej. `aegen-vm`) y haz clic en el botón **SSH**. Se abrirá una terminal en tu navegador.
3.  En la esquina superior derecha de esa terminal, haz clic en el botón de **"Subir archivo"** (Upload file).
4.  Selecciona el PDF desde tu computadora. El archivo se subirá a tu carpeta de usuario (ej. `/home/tu_usuario/`).
5.  **Mueve el archivo a la carpeta de conocimiento** ejecutando este comando en la terminal SSH:

    ```bash
    # Reemplaza 'mi_documento.pdf' por el nombre real de tu archivo
    mv mi_documento.pdf ~/AEGEN/storage/knowledge/
    ```

### Método B: Usando línea de comandos (Avanzado)
Si tienes `gcloud` instalado en tu computadora, puedes subir archivos directamente:

```bash
# Sintaxis: gcloud compute scp [ARCHIVO_LOCAL] [USUARIO]@[INSTANCIA]:[RUTA_DESTINO]
gcloud compute scp "C:\Documentos\Guia_TCC.pdf" usuario@aegen-vm:~/AEGEN/storage/knowledge/ --zone us-central1-a
```

---

## 4. Ciclo de Vida de los Documentos

El sistema es inteligente y reacciona a tus acciones sobre los archivos:

### ➤ Añadir conocimiento
Simplemente **copia** el archivo a la carpeta.
*   **Resultado:** AEGEN lee el archivo y lo aprende.

### ➤ Actualizar conocimiento
Si modificas un archivo (ej. corriges un error en un `.md`) y lo **sobreescribes** en la carpeta:
*   **Resultado:** AEGEN detecta el cambio, **borra** lo que sabía de la versión anterior y **re-aprende** la nueva versión inmediatamente.

### ➤ Eliminar conocimiento
Si **borras** un archivo de la carpeta:
*   **Resultado:** AEGEN **elimina** todas las memorias asociadas a ese documento para evitar dar información obsoleta.

```bash
# Ejemplo: Borrar un documento desde la terminal SSH
rm ~/AEGEN/storage/knowledge/documento_obsoleto.pdf
```

---

## 5. Verificación (¿Cómo sé si funcionó?)

Puedes ver en tiempo real qué está haciendo el cerebro de AEGEN consultando los "logs" (registros) del sistema.

Desde la terminal SSH de tu VM:

```bash
# Ver los logs del sistema filtrando por el vigilante
cd ~/AEGEN
docker-compose logs -f app | grep "KnowledgeWatcher"
```

**Deberías ver mensajes como estos:**
> `INFO:     Detectado archivo nuevo: Guia_Ansiedad.pdf`
> `INFO:     Procesando conocimiento global: Guia_Ansiedad.pdf`
> `INFO:     ✅ Ingeridos 45 fragmentos nuevos de Guia_Ansiedad.pdf`

Si ves el ✅, ¡el conocimiento ya está disponible para el Agente!

---

## 6. Buenas Prácticas para Documentos

Para que AEGEN entienda mejor tus documentos:

1.  **Nombres Claros:** Usa nombres de archivo descriptivos.
    *   ✅ `Protocolo_TCC_Depresion.pdf`
    *   ❌ `doc_v2_final.pdf`
2.  **Texto Limpio:** En PDFs, asegúrate de que el texto sea legible y no esté torcido o manchado (si es escaneado, usa un OCR antes).
3.  **Estructura:** Si usas Markdown (`.md`), usa títulos (`#`, `##`) para separar secciones. Esto ayuda al sistema a dividir la información en "trozos" coherentes.
