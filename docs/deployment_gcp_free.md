# Guía de Despliegue en GCP Free Tier (Always Free)

Esta guía detalla los pasos para desplegar **AEGEN** en una instancia **e2-micro** de Google Cloud Platform, manteniéndose dentro de la capa gratuita ("Always Free") y optimizando el sistema para operar con solo 1GB de RAM.

## Prerrequisitos

1.  Cuenta de Google Cloud Platform activa con facturación habilitada (necesario aunque sea gratuito).
2.  Proyecto creado en GCP.
3.  `GOOGLE_API_KEY` válida para Gemini API.

---

## 1. Creación de la Instancia VM

1.  Ve a **Compute Engine** > **Instancias de VM**.
2.  Haz clic en **Crear Instancia**.
3.  **Configuración Crítica (Free Tier):**
    *   **Región:** `us-east1`, `us-west1` o `us-central1` (Solo estas son elegibles para Always Free).
    *   **Zona:** Cualquiera dentro de la región (ej. `us-central1-a`).
    *   **Serie:** `E2`.
    *   **Tipo de máquina:** `e2-micro` (2 vCPU, 1 GB de memoria).
    *   **Disco de arranque:**
        *   Cambiar a **Debian GNU/Linux 11 (bullseye)** (Recomendado por estabilidad y bajo consumo).
        *   Tipo de disco: **Disco persistente estándar**.
        *   Tamaño: **30 GB** (El máximo permitido en Free Tier).
    *   **Firewall:** Marcar "Permitir tráfico HTTP" y "Permitir tráfico HTTPS".

4.  Haz clic en **Crear**.

---

## 2. Configuración del Sistema (SSH)

Conéctate a la instancia mediante SSH (botón "SSH" en la consola de GCP) y ejecuta los siguientes comandos.

### 2.1. Crear Espacio de Intercambio (Swap) - ¡CRÍTICO!
La e2-micro tiene solo 1GB de RAM. Sin swap, el build de Docker fallará por falta de memoria.

```bash
# Crear archivo de swap de 2GB
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Hacer permanente
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Ajustar "swappiness" para usar disco solo cuando sea necesario
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

### 2.2. Instalar Docker y Git

```bash
sudo apt-get update
sudo apt-get install -y docker.io git
# Iniciar Docker y habilitar arranque automático
sudo systemctl start docker
sudo systemctl enable docker
# Dar permisos al usuario actual (evita usar sudo para docker)
sudo usermod -aG docker $USER
# (Necesitas cerrar sesión y volver a entrar para que aplique el grupo docker, o usar 'newgrp docker')
newgrp docker
```

---

## 3. Despliegue de AEGEN

### 3.1. Clonar el repositorio

```bash
git clone https://github.com/JhomC3/AEGEN.git
cd AEGEN
```

### 3.2. Configurar Variables de Entorno

Crea el archivo `.env` con tu clave de API:

```bash
nano .env
```

Pega el siguiente contenido (ajusta con tu clave real):

```env
GOOGLE_API_KEY=tu_clave_api_aqui
PORT=8000
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Guarda con `Ctrl+O`, `Enter`, y sal con `Ctrl+X`.

### 3.3. Compilar y Levantar Contenedores

```bash
# Compilar imagen (puede tardar unos minutos en e2-micro)
docker compose build --no-cache

# Levantar servicio en segundo plano
docker compose up -d
```

### 3.4. Verificación

```bash
# Ver logs
docker compose logs -f

# Verificar uso de recursos
docker stats
```

Deberías ver que el contenedor `app` consume menos de 500MB de RAM.

---

## 4. Conectar con Telegram (Modo Polling)

Dado que no tenemos HTTPS en la IP pública (necesario para Webhooks), usaremos un script de "Polling" que viene incluido. Este script descarga los mensajes de Telegram y se los pasa a tu bot localmente.

### 4.1. Instalar Requests (si no está en la imagen base)
Entra al contenedor para ver si podemos correrlo ahí, o mejor, instálalo en la VM host:

```bash
sudo apt-get install python3-requests
```

### 4.2. Crear y Ejecutar el Servicio de Polling

1.  Crea un archivo de servicio para que corra siempre:
    ```bash
    sudo nano /etc/systemd/system/aegen-polling.service
    ```

2.  Pega esto (asegúrate de poner tu Token real):
    ```ini
    [Unit]
    Description=AEGEN Telegram Polling Service
    After=docker.service

    [Service]
    Type=simple
    User=jjhonn_1020
    # Asegúrate de que la ruta sea correcta a donde clonaste el repo
    WorkingDirectory=/home/jjhonn_1020/AEGEN
    Environment="TELEGRAM_BOT_TOKEN=PON_TU_TOKEN_AQUI"
    ExecStart=/usr/bin/python3 src/tools/polling.py
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
    *(Nota: Reemplaza `User` y `WorkingDirectory` con tu usuario real si es diferente).*

3.  Inicia el servicio:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start aegen-polling
    sudo systemctl enable aegen-polling
    ```

4.  Verifica que esté corriendo:
    ```bash
    sudo systemctl status aegen-polling
    ```

