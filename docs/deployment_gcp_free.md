# ☁️ Guía de Despliegue: Google Cloud Platform (Free Tier)

Esta guía detalla cómo desplegar AEGEN en una instancia **e2-micro** de Google Cloud Platform (GCP) aprovechando la capa gratuita ("Always Free").

## ⚠️ Requisitos Previos Críticos
Para que este despliegue funcione en una máquina con solo **1GB de RAM**, es necesario realizar una optimización clave:
1.  **Sustituir Whisper Local por Gemini API:** El modelo de transcripción local `faster-whisper` consume demasiada memoria. Debemos usar la capacidad multimodal de Gemini 1.5 Flash para procesar audio.

## 🛠️ Pasos de Despliegue

### 1. Crear la Instancia (VM)
1.  Ir a [Google Cloud Console > Compute Engine](https://console.cloud.google.com/compute/instances).
2.  **Crear Instancia**:
    *   **Nombre:** `aegen-bot`
    *   **Región:** `us-central1`, `us-west1` o `us-east1` (Son las regiones elegibles para Free Tier).
    *   **Zona:** Cualquiera en esa región (ej. `us-central1-a`).
    *   **Serie:** `E2`
    *   **Tipo de máquina:** `e2-micro` (2 vCPU, 1 GB de memoria).
    *   **Disco de arranque:** Cambiar a **Standard persistent disk** (HDD), tamaño **30 GB** (El máximo gratuito). OS: **Debian GNU/Linux 12 (bookworm)**.
    *   **Firewall:** Marcar "Permitir tráfico HTTP" y "Permitir tráfico HTTPS".
3.  Click en **Crear**.

### 2. Configuración del Sistema (SSH)
Conéctate por SSH a la instancia (botón "SSH" en la consola) y ejecuta:

```bash
# 1. Actualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Docker y Git
sudo apt install -y docker.io docker-compose git

# 3. Habilitar Docker para tu usuario
sudo usermod -aG docker $USER
# (Cierra la ventana SSH y vuelve a entrar para aplicar cambios)

# 4. 🚨 CRÍTICO: Configurar Swap (Memoria Virtual)
# Sin esto, el proceso de build o ejecución fallará por falta de RAM.
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Despliegue del Código
```bash
# 1. Clonar repositorio
git clone https://github.com/JhomC3/aegen.git
cd aegen

# 2. Configurar variables de entorno
cp .env.example .env
nano .env
# -> Pega tus claves API reales (Gemini, Telegram, etc.)
# -> Asegúrate de poner APP_ENV=production

# 3. Iniciar servicios
docker-compose up -d --build
```

### 4. Exponer al Mundo (Webhook)
La instancia tiene una IP externa efímera (cambia si reinicias) o estática (si la reservas).
1.  En la consola de GCP, ve a **Red de VPC > Direcciones IP**.
2.  Reserva la IP externa de tu instancia para que sea estática.
3.  Configura el firewall para permitir el puerto 8000 (FastAPI):
    *   **Red de VPC > Firewall > Crear regla**.
    *   Nombre: `allow-8000`
    *   Rangos de IP de origen: `0.0.0.0/0`
    *   Protocolos y puertos: `tcp:8000`
4.  Actualiza el webhook de Telegram:
    ```bash
    curl -F "url=http://<TU_IP_EXTERNA>:8000/api/v1/webhooks/telegram" https://api.telegram.org/bot<TU_TOKEN>/setWebhook
    ```

## 📉 Optimización de Costos
*   **Compute Engine:** Gratis (e2-micro, 30GB disco).
*   **Network:** Gratis (hasta 1GB tráfico egress a todo el mundo, excluyendo China/Australia).
*   **Gemini API:** Gratis (Free Tier con límites de rate, suficiente para uso personal).
*   **Redis:** Usamos contenedor local (gratis, consume RAM de la VM).
*   **ChromaDB:** Usamos contenedor local (gratis, consume disco de la VM).

¡Tu bot AEGEN ahora vive en la nube gratis! 🚀
