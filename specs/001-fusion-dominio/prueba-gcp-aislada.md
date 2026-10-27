# Prueba aislada en GCP — proyecto exclusivo `senda-test` (sin datos vivos)

Directorio `~/senda-test`, `docker-compose -p senda-test` explícito en todo,
nombres y volúmenes exclusivos, red `aegen_magi_network` solo adjuntada como
externa (nada de AEGEN se modifica; sin segundo polling: esta prueba no usa
Telegram). Revisar cada salida antes de continuar.

```bash
C=~/senda-test/docker-compose.yml; P=senda-test
```

## 0. Costes: sin recursos facturables nuevos (consumos menores aparte)

- Nada nuevo con coste: sin IPs estáticas, sin balanceadores, sin Cloud SQL,
  sin buckets, sin DNS gestionado. Los contenedores de prueba se destruyen al
  final (paso 10) y no queda nada en ejecución.
- Consumos menores que sí existen: descarga puntual de imágenes (`python:3.11-
  slim`, `tailscale:stable`, cientos de MB, una vez) y disco temporal para
  imágenes + volúmenes de prueba (se liberan en la limpieza). Tráfico tailnet
  de las pruebas. Todo dentro del free tier con tus 11 GB libres; compruébalo
  en el paso 1 antes de seguir.

## 1. Paquete verificado + directorio separado (600 desde el inicio)

```bash
mkdir -p ~/senda-test && cd ~/senda-test
echo "d8931ae577803c59753bfe6dc305f13da7d8aa47f72183cc2b31565e1400ec96  senda-prod.tar" | sha256sum -c
tar -xf senda-prod.tar
mkdir -p app && cp -R apps/entrenamiento/. app/ && rm -rf apps
cp ops/senda-test/docker-compose.yml ./docker-compose.yml
ls app/app.py app/Dockerfile docker-compose.yml
(umask 077; printf 'SENDA_SYNC_TOKEN=%s\n' "$(openssl rand -hex 32)" > .env)
(umask 077; printf 'SENDA_CSRF_SECRET=%s\n' "$(openssl rand -hex 48)" >> .env)
(umask 077; printf 'SENDA_RATE_LIMIT=30\n' >> .env)
```

`TS_AUTHKEY` (efímera + tag `senda-test`, de tu consola tailnet) directo en el
host, nunca en el chat:

```bash
cd ~/senda-test
read -s TS_AUTHKEY && (umask 077; printf 'TS_AUTHKEY=%s\n' "$TS_AUTHKEY" >> .env) && unset TS_AUTHKEY
ls -l .env   # debe mostrar -rw-------
```

## 2. Capacidad previa (lectura) + validación sin secretos

```bash
free -m | head -n 2; df -h / | tail -n 1
ls -l /dev/net/tun 2>/dev/null || echo "SIN TUN: revisar userspace antes de seguir"
docker-compose -f $C -p $P config --quiet && echo "compose válido"
```

`config --quiet` no imprime nada (ni secretos): solo el código de salida.

## 3. Arranque (solo senda-test; app/polling/redis intactos)

```bash
cd ~/senda-test
docker-compose -f $C -p $P up -d --build
docker-compose -f $C -p $P ps
```

## 4. Salud interna desde Docker (sin suponer red del host)

```bash
docker exec senda_test_domain python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/healthz',timeout=5).status)"
docker exec senda_test_tailscale tailscale status
docker exec senda_test_tailscale tailscale serve status
```

## 5. HTTPS por nombre completo desde tu dispositivo con Tailscale

Nombre estable del nodo (solo lectura, sin secretos):

```bash
docker exec senda_test_tailscale tailscale status --json | python3 -c "import json,sys;print(json.load(sys.stdin)['Self']['DNSName'])"
```

Desde tu **móvil con Tailscale activado** (la shell de la VM no está en la
tailnet salvo que instales el cliente; no asumir conectividad del host),
abre `https://<nombre>:443/` → debe mostrar el dashboard. **Sin `-k`**:
el certificado es válido y el móvil lo verifica normalmente.

## 6. API por HTTPS con nombre (token desde el fichero, sin mostrarlo)

Desde el mismo dispositivo autorizado (ejemplos con `curl`; en el móvil
vale su navegador/cliente con la cabecera):

```bash
B="https://<nombre>"
T=$(grep ^SENDA_SYNC_TOKEN ~/senda-test/.env | cut -d= -f2-)
H=(-H "X-Sync-Token: $T" -H 'Content-Type: application/json')
curl "$B/api/v1/ejercicios" "${H[@]}" | head -c 120; echo
curl -X POST "$B/api/v1/ejercicio" "${H[@]}" -d '{"ejercicio":"PressT","grupo_muscular":"Pectoral"}' | head -c 100; echo
curl -X POST "$B/api/v1/sesion" "${H[@]}" -d '{"fecha":"2001-01-02","sets":[{"ejercicio":"PressT","kg":10,"reps":5,"rir":1}]}' | head -c 100; echo
curl "$B/api/v1/sesion?fecha=2001-01-02" "${H[@]}" | head -c 100; echo
curl -X POST "$B/api/v1/undo" "${H[@]}" -d '{}' | head -c 100; echo
curl "$B/api/v1/sesion?fecha=2001-01-02" "${H[@]}" | head -c 100; echo
curl -X POST "$B/api/v1/alimento" "${H[@]}" -d '{"nombre":"AvenaT","categoria":"Cereal","kcal":100}' | head -c 100; echo
curl -X POST "$B/api/v1/diario" "${H[@]}" -d '{"fecha":"2001-01-02","entradas":[{"alimento":"AvenaT","cantidad_g":10}]}' | head -c 100; echo
curl "$B/api/v1/rumbo/dia?fecha=2001-01-02" "${H[@]}" | head -c 100; echo
curl -X POST "$B/api/v1/rumbo/dia" "${H[@]}" -d '{"fecha":"2001-01-02","t1":7,"t2":7,"t3":7}' | head -c 100; echo
curl "$B/api/v1/rumbo/preguntas" "${H[@]}" | head -c 100; echo
curl -X POST "$B/api/v1/respiracion/sesion" "${H[@]}" -d '{"client_session_id":"11111111-1111-1111-1111-111111111111","start_epoch_ms":1789282800000,"end_epoch_ms":1789282920000,"time_zone_offset_minutes":0,"patron":{"inhale_s":4.0,"hold_in_s":0.0,"exhale_s":6.0,"hold_out_s":0.0}}' | head -c 100; echo
curl "$B/api/v1/sugerencia?fecha=2001-01-02" "${H[@]}" | head -c 100; echo
curl "$B/api/v1/sesion?fecha=2001-01-02" -H 'X-Sync-Token: erroneo' | head -c 80; echo
```

Días `2001-01-0x`: datos de prueba identificables. La última línea debe
rechazar (401) sin mostrar nada útil.

## 7. Persistencia con registro testigo (reinicio Y recreación)

```bash
cd ~/senda-test
T=$(grep ^SENDA_SYNC_TOKEN .env | cut -d= -f2-)
B="https://<nombre>"
curl -X POST "$B/api/v1/rumbo/dia" -H "X-Sync-Token: $T" -H 'Content-Type: application/json' -d '{"fecha":"2001-01-03","t1":8,"t2":8,"t3":8}' | head -c 100; echo
docker-compose -f $C -p $P restart senda-test && sleep 15
curl "$B/api/v1/rumbo/dia?fecha=2001-01-03" -H "X-Sync-Token: $T" | head -c 150; echo
docker-compose -f $C -p $P up -d --force-recreate senda-test && sleep 10
docker exec senda_test_tailscale tailscale serve status   # puede faltar: esperado
docker-compose -f $C -p $P up -d --force-recreate tailscale-test && sleep 10
docker exec senda_test_tailscale tailscale serve status   # serve de vuelta
curl "$B/api/v1/rumbo/dia?fecha=2001-01-03" -H "X-Sync-Token: $T" | head -c 150; echo
```

El registro testigo (`2001-01-03`, 8/8/8) debe seguir **después del reinicio
y después de la recreación**. Orden obligatorio por el netns compartido.

## 8. Denegación tailnet no autorizada

Con la ACL del serve limitada a tus dispositivos: desde un dispositivo de tu
tailnet FUERA de la ACL, `https://<nombre>/` debe fallar. Sin segundo
dispositivo, registrar pendiente explícito (fuera de la tailnet no hay ruta
ni DNS en ningún caso).

## 9. Consumo real

```bash
docker stats --no-stream senda_test_domain senda_test_tailscale
free -m | head -n 2; df -h / | tail -n 1
```

## 10. Limpieza (SOLO recursos senda-test)

```bash
cd ~/senda-test
docker-compose -f $C -p $P stop senda-test tailscale-test
docker-compose -f $C -p $P rm -f senda-test tailscale-test
docker volume rm senda-test_senda_test_data senda-test_tailscale_test_state
cd ~ && rm -rf ~/senda-test
docker volume ls | grep -i senda || echo "sin restos senda-test"
# AEGEN, Redis, storage, .env y .env.save intactos: no se tocaron.
```
