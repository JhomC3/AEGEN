# Inventario GCP en solo lectura (el dueño ejecuta en la VM y revisa antes)

Nada se instala ni se modifica. Este guion **excluye** tokens, contraseñas,
contenido de `.env` (solo nombres de claves) y variables de entorno de los
contenedores (ningún `inspect` completo ni `exec … env`).

```bash
echo "== contenedores (nombres, imagen, estado, puertos) =="
docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
echo "== red interna (nombre e IP por contenedor, sin secretos) =="
docker network inspect magi_network --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{end}}'
echo "== volúmenes y uso =="
docker volume ls; docker system df
echo "== puertos publicados =="
ss -ltn
echo "== firewall local =="
sudo iptables -L -n 2>/dev/null | head -n 20
echo "== disco/memoria/swap =="
df -h / | tail -n 1; free -m | head -n 2; swapon -s 2>/dev/null | head -n 3
echo "== TUN para Tailscale (userspace si falta) =="
ls -l /dev/net/tun 2>/dev/null || echo "sin /dev/net/tun (usar userspace)"
echo "== claves presentes en .env (NOMBRES, sin valores) =="
grep -o '^[A-Za-z_]*=' ~/AEGEN/.env | sort | tr '\n' ' '; echo
echo "== backups =="
du -sh ~/AEGEN/storage 2>/dev/null
```

## Consultas que NO pueden hacerse desde la VM (consola GCP / gcloud)

Separadas para obtenerlas aparte (todas de lectura):

- `gcloud compute firewall-rules list` (reglas efectivas de la VPC).
- `gcloud compute addresses list` (IP externa estática o efímera).
- `gcloud dns managed-zones list` + `record-sets list` (solo si hay DNS propio;
  con Tailscale no se necesita DNS público).
- Buckets y ciclo de vida: `gsutil ls` + `gsutil lifecycle get gs://BUCKET`
  (nombre del bucket lo indica el dueño).
- SO y serie de la VM: `gcloud compute instances describe INSTANCIA --format='yaml(machineType,disks,metadata)'`.
