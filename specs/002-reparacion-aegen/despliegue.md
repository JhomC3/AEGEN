# Reparación 002: procedimiento adaptado a la VM

2026-10-21. Preparado localmente, **no ejecutado en GCP**. Sustituye el
procedimiento anterior. El encargo autoriza preparar la entrega; no autoriza
commit, push, construcción remota ni interrupción del bot.

Actualización 2026-10-27: commit y push autorizados por el dueño, en
`codex/consolidacion-aegen-senda`. No hay autorización de despliegue ni merge.
GitHub es el medio preferido para transferir el código publicado. En GCP se
debe obtener la rama en un directorio separado, sin ejecutar pull, checkout o
limpieza sobre el checkout operativo modificado. El tar de §3–§4 se conserva
como alternativa de transferencia ya preparada, no como requisito de GitHub.

## 1. Inventario recibido del dueño

- VM: /home/jjhonn_1020/AEGEN, develop,
  11487668e1a8435cdc6f99b84dbfef2db211fe50.
- Árbol modificado: routing/config/polling y archivos de SENDA; .env.save,
  .tmp/, apps/, ops/, skill bienestar y su test sin seguimiento.
- En ejecución: magi_app_prod (referencia 481c61cc1b9e), magi_polling
  (aegen-polling), magi_redis y magi_tailscale, saludables según Docker.
  SENDA no aparece entre los contenedores en ejecución.
- docker-compose 2.29.1; RAM disponible 416 MiB, swap usada 511 MiB;
  disco libre 6,8 GiB.

Es evidencia aportada, no inspección directa del agente ni prueba funcional
del bot. Los scripts vuelven a comprobar las condiciones al ejecutarse.

## 2. Estrategia y límites

No se usa Git para desplegar: nada de checkout, pull, reset, stash, limpieza
ni cambio de rama. No es necesario publicar cambios para probarlos.

La entrega contiene solo los **13 archivos fuente reparados** y auxiliares de
operación. Cada imagen nueva deriva del ID exacto de su imagen anterior y
superpone esos archivos. Hereda dependencias y resto del código; no instala
paquetes. El Dockerfile no tiene instrucciones RUN y el build usa red desactivada.

Antes, una sonda compara todos los archivos src/ de la base 1148766 con cada
imagen real y exige que los tres módulos nuevos no existieran. Si difieren,
aborta mostrando rutas, sin reinicios; se revisará la diferencia real.

- .env se reutiliza, sin copiarlo ni editarlo; exige modo 640, UID 1000,
  GID 10001, coherentes con la reparación anterior de permisos. Si difiere, aborta.
- storage/ no se monta durante preparación. Al activar se respalda con app y
  polling detenidos. El rollback normal conserva los datos actuales.
- Redis, Tailscale, SENDA y sus volúmenes no se recrean. Se comprueban ID,
  imagen y hora de arranque de Redis/Tailscale antes y después.
- Nunca se ejecutan down, prune, borrados de volúmenes ni otro polling.
- No hay nuevos recursos GCP ni descargas de imágenes. No se afirma coste cero
  del consumo del servidor existente.

## 3. Archivo para subir desde el Mac

Archivo visible dentro del proyecto:

/Users/jhomc/Proyectos/AEGEN/entrega-reparacion-aegen/aegen-reparacion-002.tar

SHA-256:

ab46d8a9d4b44dd7cf17c2e3bf662c4e66662cf0c870b627dada953ca3b62f9f

Usar **Upload file** de la ventana SSH de GCP. Debe quedar en
/home/jjhonn_1020/aegen-reparacion-002.tar. No subir .env, tokens, DB ni el
paquete anterior de SENDA.

## 4. Preparar en la VM — requiere autorización de construcción

Pegar el bloque completo en **SSH de GCP**, solo tras autorizar esta fase.
No arranca, detiene ni recrea servicios. Ejecuta dos contenedores efímeros de
sonda con red desactivada, entrypoint Python y raíz de solo lectura; no
inician AEGEN ni polling.

~~~bash
bash <<'SH'
set -Eeuo pipefail
umask 077
cd "$HOME"
echo 'ab46d8a9d4b44dd7cf17c2e3bf662c4e66662cf0c870b627dada953ca3b62f9f  aegen-reparacion-002.tar' | sha256sum -c
mkdir -p "$HOME/AEGEN/.tmp"
entrega=$(mktemp -d "$HOME/AEGEN/.tmp/repair002-XXXXXXXX")
tar -xf "$HOME/aegen-reparacion-002.tar" -C "$entrega"
echo "ENTREGA=$entrega"
bash "$entrega/operacion/preparar.sh"
SH
~~~

El script registra el respaldo en esa misma carpeta e imprime los comandos
exactos de activación y rollback: no se sustituyen fechas ni se busca el último.

Comprueba espacio antes de exportar imágenes o construir: dos veces la suma del
tamaño de ambas imágenes, dos veces storage y 1 GiB de margen. Es una cota
conservadora; si no cabe, aborta. No libera espacio por su cuenta. El consumo
real del build solo se podrá comprobar en la VM.

El respaldo contiene IDs y export de imágenes, manifiesto SHA-256, Compose,
estado Git y diff de archivos seguidos, huella/permisos de .env e identidad de
contenedores ajenos. Los archivos sin seguimiento permanecen en su lugar;
no se copian ni borran. No es un respaldo externo de la VM.

Esperado: **PREPARADO. Ningún servicio reiniciado.**
Si falla, conservar la carpeta y compartir el error; no activar. Un intento
incompleto no se sobrescribe; otra ejecución crea una carpeta nueva tras revisar
la causa. No hay activación automática.

## 5. Activación — autorización separada

Preparar imprime la línea completa bash .../operacion/activar.sh con su ruta
real. Ejecutarla solo al autorizar la interrupción del bot; no hay ruta ficticia
que sustituir.

Secuencia:
1. Verifica manifiestos, configuración, permisos, imágenes y espacio restante.
2. Detiene primero polling y después app. El bot queda temporalmente sin servicio.
3. Respalda storage/ con ambos detenidos, incluidos WAL/SHM, y valida el archivo.
4. Recrea solo app con --no-deps --no-build --pull never y el ID nuevo.
5. Espera salud Docker con límite de 180 s. Después recrea solo polling y
   comprueba los IDs nuevos. No hay dos pollers simultáneos.
6. Comprueba que Redis/Tailscale no se reiniciaron y que .env no cambió.

Si falla tras detener servicios, imprime el rollback correspondiente a esa
entrega. No reactiva automáticamente polling con app en estado desconocido.
ACTIVADO no demuestra validación funcional ni reparación completa.

## 6. Rollback exacto, sin reconstrucción ni Git

Preparar imprime la línea bash .../operacion/rollback.sh con ruta real.
El script usa su propia carpeta; no depende de variables de otra sesión.

Verifica el manifiesto, carga las imágenes exportadas, detiene polling/app y
recrea ambos con sus IDs anteriores. Verifica identidad y salud, conservando
checkout, .env, almacenamiento actual, Redis y Tailscale. Compose debe seguir
idéntico al registrado; si cambió, aborta en vez de sobrescribirlo.

La salud Docker del rollback no demuestra que el problema previo del proveedor
esté resuelto: restaura las imágenes anteriores.

**No restaura storage automáticamente.** Ante corrupción: detener escritores,
conservar estado posterior y decidir qué reconciliar. La copia previa existe
con SHA; restaurarla sin evaluar escrituras posteriores perdería memoria nueva.

## 7. Validación real después de activar

En SSH de GCP:

~~~bash
bash <<'SH'
set -Eeuo pipefail
cd "$HOME/AEGEN"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
curl -fsS --max-time 60 http://localhost:8000/system/llm-health
echo
curl -fsS --max-time 10 http://localhost:8000/system/health
echo
SH
~~~

La comprobación profunda llama al proveedor y puede consumir su cuota habitual.
Esperado: LLM healthy y salud posterior ok. Ante fallo, recoger el error actual,
sin atribuirlo automáticamente a Google ni afirmar que Groq funciona.

Con el único polling existente, el dueño prueba en Telegram:
1. «Responde únicamente RECIBIDO»: debe llegar una respuesta utilizable.
2. Dos mensajes dentro de la ventana de ráfaga: «Estoy probando una ráfaga» y
   «Responde únicamente RAFAGA». Comprobar una respuesta del lote consolidado.
   Enviar después otro mensaje mientras se procesa una respuesta: debe atenderse
   después. Contrastar con logs, no solo con el texto del modelo.
3. Solicitud explícita de herramienta CBT con contenido ficticio, sin datos
   personales reales. Comprobar ejecución y respuesta en logs. Si routing elige
   chat, el caso sigue pendiente; no se declara aprobado.

Recoger logs inmediatamente, sin filtros que oculten el primer fallo:

~~~bash
docker logs --since 5m --tail 160 magi_app_prod
docker logs --since 5m --tail 80 magi_polling
~~~

Revisar antes de compartir: pueden contener chat ID, mensajes privados o errores
del proveedor. No publicar secretos. No se ejecutan escrituras en SENDA.
La prueba de ráfaga real no es prueba exhaustiva de concurrencia.

## 8. Evidencia local y límites

Base de pruebas: archivo Git de 1148766 más exactamente los 13 archivos fuente y
los siete archivos de tests de reparación, sin cambios de SENDA.
Resultado: **34 passed**, incluido webhook, con mocks/FakeRedis.
Log: .tmp/repair002-revision/pruebas-final.log.

Sintaxis shell, auxiliares Python y estructura del tar comprobados. No hay Docker
en este Mac: build, Compose, recursos, sonda de imágenes, recreación, rollback y
Telegram reales siguen pendientes en la VM. No se presentan como ensayados.

Riesgos del bot que esta entrega no elimina:
- Latido dependiente del event loop: bloqueo superior al TTL puede permitir
  solapamiento. Perder token detiene renovación, no el trabajo en curso.
- Espera acotada reprogramada: propietario colgado puede provocar reintentos.
- Recuperación exige Redis con claves vivas: 3600 s tras apagado ordenado,
  60 s normales tras SIGKILL. Lote consumido por flush_all sin replay.
- Fallback FTS5 local no demuestra que el proveedor conversacional funcione.

## 9. Cierre

Preparación → autorización de ventana → activación → validación real.
Solo si proveedor, conversación, ráfaga y herramienta pasan se declara validado
el recorrido reparado. Integrar SENDA sigue siendo otro trabajo. No hay commits,
push ni cambios de infraestructura autorizados.
