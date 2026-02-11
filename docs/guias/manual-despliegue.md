# Manual de Despliegue en GCP (Free Tier)

Guía oficial para el despliegue de **AEGEN** en instancias **e2-micro** de Google Cloud Platform, optimizada para operar con 1GB de RAM.

## 1. Preparación de la Infraestructura

### Configuración de la Instancia VM
1. **Región:** `us-east1`, `us-west1` o `us-central1`.
2. **Máquina:** `e2-micro` (2 vCPU, 1 GB RAM).
3. **Disco:** 30 GB (Debian 11 Bullseye recomendado).
4. **Firewall:** Permitir tráfico HTTP/HTTPS.

### Configuración del Sistema (SSH) - ¡CRÍTICO!
Es obligatorio crear un espacio de intercambio (Swap) para evitar que el proceso de construcción de Docker muera por falta de memoria.

```bash
# Crear Swap de 2GB
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Despliegue con Docker

### Instalación y Clonación
```bash
sudo apt-get install -y docker.io git
git clone https://github.com/JhomC3/AEGEN.git
cd AEGEN
cp .env.example .env # Configurar GOOGLE_API_KEY y TELEGRAM_TOKEN
```

### Arranque del Contenedor
```bash
# Construir y levantar
docker-compose up -d --build

# Verificar logs
docker-compose logs -f app
```

## 3. Servicio de Polling (Telegram)

Dado que no usamos HTTPS público, ejecutamos un servicio de sondeo (polling) en el host.

### Configuración de Systemd
Crea el archivo `/etc/systemd/system/aegen-polling.service`:

```ini
[Unit]
Description=AEGEN Telegram Polling Service
After=docker.service

[Service]
Type=simple
User=TU_USUARIO
WorkingDirectory=/home/TU_USUARIO/AEGEN
EnvironmentFile=/home/TU_USUARIO/AEGEN/.env
ExecStart=/usr/bin/python3 src/tools/polling.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 4. Mantenimiento y Sincronización

AEGEN incluye scripts automatizados para gestionar la salud de los datos desde el contenedor:

```bash
# Saneamiento de Base de Datos (Provenance)
docker exec -it magi_app_prod python -m scripts.migrate_provenance

# Sincronización de Conocimiento (PDFs)
docker exec -it magi_app_prod python -m scripts.sync_knowledge

# Limpieza de archivos físicos legacy
docker exec -it magi_app_prod python scripts/archive_legacy.py
```

## 5. Gestión de Backups

La base de datos SQLite se respalda automáticamente en Google Cloud Storage (si está configurado).
- **Snapshot:** Se crea mediante el comando `VACUUM INTO`.
- **Gzip:** Se comprime para reducir costos de almacenamiento.
- **Retención:** Se recomienda configurar una política de ciclo de vida en GCS de 7 días.

---
*Para resolución de problemas, consulta los logs con `docker-compose logs -f app`.*
