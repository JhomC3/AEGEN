# Conexión AEGEN (GCP) ↔ Senda (PROPUESTA, no ejecutada)

Hallazgo: AEGEN corre en Docker en GCP (de ahí el 409 de polling). El
`BIENESTAR_DOMAIN_URL=http://127.0.0.1:8000` solo vale en el Mac; desde GCP
ese loopback es el propio contenedor remoto. No exponer 8000 a Internet.

## Opción recomendada: ubicación conjunta en GCP (mismo host/red privada)

Añadir servicio `senda` al `docker-compose` (o manifiesto equivalente) en el
mismo host GCP:

- Imagen propia (`apps/entrenamiento/Dockerfile`, Python 3.11 + `uv sync
  --locked` del dominio; no reutilizar la imagen de AEGEN: runtimes y
  dependencias difieren, p. ej. `plotly`).
- Sin puertos publicados; solo red interna (`magi_network`):
  AEGEN → `http://senda:8000` con `X-Sync-Token` (mismo modelo auth, sin
  cambios). `BIENESTAR_DOMAIN_URL=http://senda:8000` en el entorno de AEGEN.
- Volumen persistente para `apps/entrenamiento/data/` (SQLite + backups) +
  respaldo a GCS (o equivalente); secretos por variables de entorno del host
  (nunca en la imagen ni en git).
- Un solo escritor: el contenedor `senda`; el checkout del Mac queda solo
  lectura tras el corte.

Por qué conjunta y no túnel al Mac: sin piezas siempre-encendidas en casa,
sin NAT/firewall doméstico, latencia local al orquestador y superficie de red
mínima (cero puertos nuevos a Internet). Un túnel (Tailscale/WireGuard/Cloudflare)
mantendría los datos en casa pero exige el Mac 24/7 y otra capa que operar.

## Decisiones del dueño (bloquean el despliegue, no el diseño)

1. TLS y móvil: el móvil habla hoy a la LAN del Mac. Con Senda en GCP, la app
   debe apuntar al nuevo host (HTTPS con terminación TLS en el borde GCP) y
   recompilarse con la nueva URL (el token no cambia). Alternativa: mantener el
   escritor en el Mac y que GCP llame por túnel privado (desaconsejado arriba).
2. Gate LAN (`GYM_LAN_SYNC_ONLY=1`): en GCP los pares ya no son LAN; revisar la
   política (allow-list por ruta + token se mantiene; rate-limit y TLS del
   borde lo complementan).
3. Secretos en GCP: Secret Manager o `.env` del host (decisión operativa).
4. Despliegue: quién construye/publica la imagen y dónde viven los volúmenes.

## Autorización por recorrido (TLS no autoriza: solo cifra, integra y autentica el servidor)

Corrección explícita: TLS **no sustituye** ninguna confianza de autorización.
Lo único que aporta es confidencialidad, integridad y (con certificado válido)
autenticidad del servidor. Cada acceso se autoriza así, por capas:

### 1. AEGEN → SENDA (red privada, sin Internet)

1. Pertenencia a la red privada (`magi_network`, sin puertos publicados:
   inalcanzable desde fuera del host).
2. `X-Sync-Token` por petición (mismo secreto operativo).
3. Allow-list exacta por método+path (incluidas las 6 rutas Rumbo; test
   `test_rutas_subagente.py`).
4. Rate-limit por peer + CSRF exento solo por igualdad exacta.

### 2. Móvil → SENDA

Controles base (los de hoy, conservados): `X-Sync-Token`, allow-list exacta,
rate-limit, cuerpos acotados. Encima, una de dos opciones (decisión del dueño):

- **(A) Acceso privado (recomendado)**: Tailscale en VM + móvil; la URL
  embebida apunta al nombre tailnet; **cero superficie pública** para la API.
- **(B) 443 público + token**: acepta que el único factor de autorización sea
  el token (256 bits) + allow-list + rate-limit + TLS. Exige rotación
  documentada ante sospecha y vigilancia de abuso. No recomendado sin un
  factor más.

### 3. Navegador → SENDA (dashboard sin login: NO publicarlo confiando en CSRF)

El dashboard no tiene autenticación de usuario; CSRF solo protege contra
sitios cruzados, no autoriza lectores. Opciones:

- **(A) Privado (recomendado)**: Tailscake/SSH, sin superficie pública.
- **(B) OAuth2-Proxy con cuenta Google allowlist** delante del dashboard
  (nuevo componente solo si se exige acceso público con login).

CSRF + Origin quedan como segunda capa detrás del perímetro, nunca como
control único.

## Migración Mac → GCP (propuesta, no ejecutada)

1. Ventana sin escrituras móviles; detener escritor Mac; comprobar puerto libre.
2. Backup `.backup` WAL-seguro + SHA-256 + integridad + esquema + conteos.
3. Transferir backup + secretos al volumen `senda_data`
   (`gcloud compute scp` o equivalente; decide el dueño la vía).
4. `init_db` en destino (migraciones idempotentes); verificar conteos
   idénticos y `undo peek` coherente; justificar diferencias solo por
   migraciones previstas (no se esperan: esquema 24 en ambos).
5. Pruebas: `/healthz`, lecturas, escritura+undo controlados, subagente contra
   `http://senda:8000`, y móvil contra el nuevo host tras recompilar APK.
6. Declarar `senda` escritor canónico; Mac queda solo lectura (no se borra).
7. Rollback: si hay escrituras posteriores al backup, reconciliar vía API
   (releer y re-aplicar) antes de restaurar; nunca backup antiguo encima.
   Ensayo de recuperación en aislado como precondición (ya superado una vez
   en Mac; repetir contra el procedimiento GCP antes del corte).

## Acceso privado con Tailscale (decisión del dueño: dashboard + móvil)

- VM y móvil en la misma tailnet; acceso limitado a sus dispositivos vía ACL
  (etiqueta + propietario). **Nada público**: sin puertos publicados, sin DNS
  público, sin funnel. `compose-senda.yml` lleva el sidecar activo.
- `tailscale` como sidecar en compose (mismo `network_mode: service:senda`
  que senda): estado en volumen + `TS_AUTH_ONCE`; verificar tag `senda` y
  grants antes de desplegar. Serve vigente (sintaxis verificada):
  `tailscale serve --bg --https=443 http://127.0.0.1:8000` (el proxy solo
  admite loopback como destino; persiste tras reboot).
- URL única del dashboard: `https://senda.tail402592.ts.net/` (nombre senda
  ya aplicado por el dueño en tailnet y URL; el `--hostname=senda-gcp` del
  compose queda pendiente de alinear por el dueño en su copia local — NO por
  tar — para que un recreate no renombre el dispositivo). El proxy
  re-origina desde 127.0.0.1, así que el gate la ve como loopback (permitida;
  autorización = tailnet + ACL, CSRF segunda capa). Condición: uvicorn con
  `--no-proxy-headers` EXPLÍCITO (prohibido `--proxy-headers` en senda: con
  ese flag, uvicorn reescribe el cliente desde `X-Forwarded-For` y el gate ve
  la IP tailnet en vez del loopback — 403 real en U32).
- `http://<ip-tailnet>:8000/` directo responde **403 al dashboard por diseño**
  (peer 100.x = remoto; solo API con token). No es un error ni se corrige
  confiando en `100.64.0.0/10` o en `X-Forwarded-For` (ignorado por
  construcción; uvicorn sin `--proxy-headers`).
- Tras el proxy el navegador usa `https://` y uvicorn ve `http`: el compose
  de senda fija `GYM_BEHIND_TLS_PROXY=1` para el check de Origin (configuración,
  nunca cabecera). Token, rate-limit, CSRF de mutaciones, cero puertos y cero
  funnel intactos.
- Android: añadir el destino tailnet en la app (mismo token); recompilar APK
  debug solo si se quiere el nuevo default horneado (release intacto).

## Secretos: fuente única y rotación (sin volcar valores)

- Fuente efectiva única: ficheros `data/hc_sync_token` y `data/csrf_secret`
  (modo 600). `start_server.sh` aplica este orden: (1) variable explícita
  (`SENDA_SYNC_TOKEN`/`SENDA_CSRF_SECRET`) → persiste en fichero;
  (2) fichero existente → reutiliza; (3) generación aleatoria solo si no hay
  nada. **Ningún valor se imprime jamás** (probado: existente/env/generación,
  cero fugas en salida).
- Añadir el token de SENDA: en el host (nunca en el chat), o bien variable en
  `.env` del despliegue o escritura directa en el volumen; el arranque lo
  persiste y reutiliza.
- Rotar: detener escritor → sustituir el fichero → rearrancar → recompilar APK
  debug (token embebido en build) → actualizar `BIENESTAR_SYNC_TOKEN` de AEGEN
  → comprobar que el token viejo responde 401.
- Verificado: `.env` excluido de git con permisos `600`; `polling.py` nunca
  registra valores; imágenes sin `.env` (`.dockerignore`).

## Estado

Artefactos preparados para revisión (`apps/entrenamiento/Dockerfile`,
`ops/proxy/compose-senda.yml` con bloque proxy dormido,
`ops/proxy/Caddyfile` dormido salvo superficie pública). GCP intacto.
Destino Mac provisional validado a nivel servidor+subagente; móvil y Telegram
pendientes (cierre exige ambos contra GCP). Corte GCP solo tras inventario,
capacidad, migración y recuperación revisados.

## ACL de ejemplo para el serve de prueba (consola tailnet → Access controls)

```json
{
  "tagOwners": {"tag:senda-test": ["tu-usuario@"]},
  "grants": [
    {"src": ["tu-usuario@"], "dst": ["tag:senda-test"], "ip": ["443"]}
  ]
}
```

Solo tus dispositivos alcanzan el serve; el resto de la tailnet (y todo lo
demás) no tiene ruta. Sustituir `tu-usuario@` y aplicar antes de la prueba §6.
