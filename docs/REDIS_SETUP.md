# Redis Setup para AEGEN Phase 3B

## Configuración de Redis para Memoria Conversacional

AEGEN Phase 3B utiliza Redis para almacenar la memoria conversacional de sesiones de chat, permitiendo mantener contexto entre múltiples interacciones.

## Configuración

### Variables de Entorno

```env
# Redis Session Storage
REDIS_SESSION_URL=redis://redis:6379/1
REDIS_SESSION_TTL=3600  # 1 hora timeout de sesión
```

### Configuración en `src/core/config/base.py`

```python
REDIS_SESSION_URL: str = "redis://redis:6379/1"
REDIS_SESSION_TTL: int = 3600  # 1 hour session timeout
```

## Opciones de Ejecución

### Opción 1: Docker (Recomendado)

```bash
# Iniciar Redis en background
docker run -d --name aegen-redis -p 6379:6379 redis:alpine

# Verificar que esté ejecutándose
docker ps | grep redis
```

### Opción 2: Docker Compose

Crear `docker-compose.redis.yml`:

```yaml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

```bash
# Iniciar Redis con compose
docker-compose -f docker-compose.redis.yml up -d
```

### Opción 3: Instalación Local

#### macOS
```bash
brew install redis
brew services start redis
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### Verificación
```bash
redis-cli ping
# Debe retornar: PONG
```

## Configuración para Desarrollo

### URL de Conexión

Para desarrollo local, actualizar la variable de entorno:

```env
REDIS_SESSION_URL=redis://localhost:6379/1
```

### Configuraciones de Base de Datos

Redis utiliza múltiples databases numeradas. AEGEN usa:

- **Database 0**: Cache general / otros usos
- **Database 1**: Memoria conversacional de sesiones

## Testing

### Test Manual de Conexión

```bash
# Conectar a Redis y probar
redis-cli -n 1
127.0.0.1:6379[1]> ping
PONG
127.0.0.1:6379[1]> set test "hello"
OK
127.0.0.1:6379[1]> get test
"hello"
127.0.0.1:6379[1]> del test
(integer) 1
```

### Test Automatizado

```bash
# Ejecutar test de memoria conversacional
uv run python scripts/test_redis_memory.py
```

### Inspeccionar Sesiones Activas

```bash
# Conectar a database 1 (sesiones)
redis-cli -n 1

# Listar todas las claves de sesión
KEYS session:chat:*

# Ver contenido de una sesión
GET session:chat:123456789

# Ver TTL de una sesión
TTL session:chat:123456789
```

## Monitoreo

### Comandos Útiles

```bash
# Info general de Redis
redis-cli info

# Monitor comandos en tiempo real
redis-cli monitor

# Estadísticas de memory usage
redis-cli info memory

# Número de claves en database 1
redis-cli -n 1 dbsize
```

### Logs de SessionManager

El SessionManager logea automáticamente:

- Conexiones establecidas
- Sesiones guardadas/recuperadas
- Errores de conexión
- Estadísticas de TTL

```python
# Los logs aparecen con el formato:
# SessionManager: Redis connection established
# Session saved for chat_id: 123, 5 messages, TTL: 3600s
# Session retrieved for chat_id: 123, 5 messages
```

## Troubleshooting

### Error: "No module named 'redis'"

```bash
# Reinstalar dependencias
uv sync
```

### Error: "Connection refused"

```bash
# Verificar que Redis esté ejecutándose
docker ps | grep redis
# o
brew services list | grep redis
# o
sudo systemctl status redis-server
```

### Error: "Connection timeout"

```bash
# Verificar conectividad
redis-cli ping

# Verificar puerto
netstat -tlnp | grep 6379
```

### Limpiar Todas las Sesiones

```bash
# ⚠️  CUIDADO: Elimina todas las sesiones
redis-cli -n 1 flushdb
```

## Configuración de Producción

### Persistencia

Para producción, configurar persistencia Redis:

```bash
# En redis.conf
save 900 1    # Guardar cada 15 minutos si hay 1 cambio
save 300 10   # Guardar cada 5 minutos si hay 10 cambios
save 60 10000 # Guardar cada minuto si hay 10000 cambios
```

### Memoria

Configurar límites de memoria:

```bash
# En redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU eviction cuando se alcance el límite
```

### Seguridad

```bash
# En redis.conf
requirepass your_secure_password

# En .env
REDIS_SESSION_URL=redis://:your_secure_password@redis:6379/1
```

## Estructura de Datos

### Formato de Sesión en Redis

```json
{
  "chat_id": "123456789",
  "conversation_history": [
    {"role": "user", "content": "Hola"},
    {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"}
  ],
  "last_update": "2025-01-20T15:30:00.000Z",
  "metadata": {
    "last_event_type": "audio",
    "payload_keys": ["transcript", "response"]
  }
}
```

### Clave de Redis

```
session:chat:{chat_id}
```

Ejemplo: `session:chat:123456789`
