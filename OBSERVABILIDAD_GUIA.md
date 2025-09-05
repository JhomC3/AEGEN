# 🚀 Guía Super Fácil: Cómo Ver las Métricas de AEGEN

*Una guía tan simple que hasta un niño de 7 años puede hacerlo* 👶

---

## 🎯 ¿Qué vamos a hacer?

Vamos a **espiar** a nuestro robot inteligente (AEGEN) para ver:
- ¿Cuántas veces habla con la IA? 🤖💬
- ¿Qué tan rápido lo hace? ⚡
- ¿Cuánto dinero gastamos? 💰
- ¿Está funcionando bien? ✅

---

## 🔧 PASO 1: Encender Nuestro Robot

**¿Qué hacer?**
Abre tu **terminal** (la pantalla negra donde escribes comandos) y escribe:

```bash
python -m src.main
```

**¿Qué verás?**
Un montón de texto que termina con algo como:
```
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: FastAPI application 'AEGEN' configured and ready.
```

**🎉 ¡Perfecto! Tu robot ya está despierto!**

---

## 🔍 PASO 2: Ver Si Todo Está Bien

**¿Qué hacer?**
En otra ventana de terminal (sin cerrar la primera), escribe:

```bash
curl http://localhost:8000/system/llm/health
```

**¿Qué verás?**
```json
{
  "status": "healthy",
  "metrics_collector": "operational",
  "timestamp": "2025-09-05T12:00:00Z"
}
```

**✅ Si ves "healthy" = ¡Todo funciona perfecto!**
**❌ Si ves "unhealthy" = Algo está mal, pide ayuda**

---

## 📊 PASO 3: Ver el Estado del Robot

**¿Qué hacer?**
Escribe este comando mágico:

```bash
curl http://localhost:8000/system/llm/status
```

**¿Qué verás?**
```json
{
  "correlation_id": "abc12345",
  "active_calls": {"google:gemini-pro": 0.0},
  "total_calls_today": 0,
  "average_latency_ms": 0.0,
  "total_cost_today": 0.0,
  "status": "operational"
}
```

**🤓 ¿Qué significa cada cosa?**
- `active_calls`: ¿Cuántas conversaciones está teniendo ahora?
- `total_calls_today`: ¿Cuántas veces habló con la IA hoy?
- `average_latency_ms`: ¿Qué tan rápido responde? (menos = mejor)
- `total_cost_today`: ¿Cuánto dinero gastamos hoy?
- `status`: ¿Está funcionando bien?

---

## 🎮 PASO 4: ¡Hacer que el Robot Trabaje!

**¿Por qué?**
Ahora mismo el robot no ha hecho nada, así que no hay métricas. ¡Vamos a darle trabajo!

**¿Qué hacer?**
Simula un mensaje de Telegram que SÍ activa el sistema completo con observabilidad:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456,
    "message": {
      "message_id": 1,
      "from": {
        "id": 999999999,
        "is_bot": false,
        "first_name": "TestUser",
        "username": "testuser"
      },
      "chat": {
        "id": 999999999,
        "first_name": "TestUser",
        "username": "testuser",
        "type": "private"
      },
      "date": 1699999999,
      "text": "Hola! Explica qué son los microservicios en 2 oraciones."
    }
  }'
```

**¿Qué verás?**
```json
{"task_id":"abc123-def456","message":"Telegram event accepted for processing."}
```

El sistema procesará tu mensaje usando el flujo completo con observabilidad.

---

## 🔬 PASO 5: Ver las Métricas Completas

**¿Qué hacer?**
Ahora que el robot trabajó, veamos sus métricas:

```bash
curl http://localhost:8000/system/llm/metrics/summary
```

**¿Qué verás?**
```json
{
  "total_calls": 1,
  "total_tokens": 89,
  "average_latency_seconds": 3.2,
  "total_cost_usd": 0.0000891,
  "active_calls_count": 0
}
```

**🤓 ¿Qué significa?**
- `total_calls`: ¡El robot habló 1 vez!
- `total_tokens`: Usó 89 "palabritas" para hablar (input + output)
- `average_latency_seconds`: Tardó 3.2 segundos en responder
- `total_cost_usd`: Nos costó $0.0000891 (¡menos de una décima de centavo!)
- `active_calls_count`: No está hablando ahora

---

## 🌟 PASO 6: Ver TODAS las Métricas (Modo Experto)

**¿Qué hacer?**
Para ver TODO lo que el robot está midiendo:

```bash
curl http://localhost:8000/metrics
```

**¿Qué verás?**
¡Un montón de números! Busca las líneas que empiecen con `aegen_llm`:

```
aegen_llm_calls_total{provider="google",model="gemini-pro",status="success"} 1.0
aegen_llm_tokens_total{provider="google",model="gemini-pro",type="input"} 25.0
aegen_llm_tokens_total{provider="google",model="gemini-pro",type="output"} 20.0
```

---

## 👀 PASO 7: Espiar en Tiempo Real

**¿Qué hacer?**
Para ver cómo cambian las métricas mientras el robot trabaja:

```bash
watch -n 2 'curl -s http://localhost:8000/system/llm/status | jq'
```

**¿Qué verás?**
La pantalla se actualizará cada 2 segundos mostrando las métricas nuevas.

**Para salir:** Presiona `Ctrl + C`

---

## 🎪 PASO 8: Hacer que el Robot Trabaje Mucho

**¿Qué hacer?**
Vamos a darle más trabajo para ver cómo cambian los números:

```bash
# Trabajo 1
curl -X POST http://localhost:8000/api/v1/analysis/ingest \
  -H "Content-Type: application/json" \
  -d '{"data": "Analiza: Bitcoin transaction 1"}'

# Trabajo 2
curl -X POST http://localhost:8000/api/v1/analysis/ingest \
  -H "Content-Type: application/json" \
  -d '{"data": "Analiza: Ethereum smart contract"}'

# Trabajo 3
curl -X POST http://localhost:8000/api/v1/analysis/ingest \
  -H "Content-Type: application/json" \
  -d '{"data": "Analiza: DeFi protocol data"}'
```

**Ahora mira las métricas otra vez:**
```bash
curl http://localhost:8000/system/llm/status
```

**¡Los números habrán cambiado!** 📈

---

## 🏆 PASO 9: Comandos de Emergencia

**Si algo sale mal:**

**🆘 Ver si el robot sigue vivo:**
```bash
curl http://localhost:8000/system/llm/health
```

**🔍 Ver todos los endpoints disponibles:**
```bash
curl http://localhost:8000/docs
```
*(Abre tu navegador y ve a http://localhost:8000/docs)*

**🛑 Parar el robot:**
En la terminal donde está corriendo, presiona `Ctrl + C`

---

## 📱 PASO 10: Comandos Súper Fáciles

**Copia y pega estos comandos uno por uno:**

```bash
# 1. Ver estado general
curl http://localhost:8000/system/llm/status

# 2. Ver resumen de métricas
curl http://localhost:8000/system/llm/metrics/summary

# 3. Comprobar salud
curl http://localhost:8000/system/llm/health

# 4. Dar trabajo al robot
curl -X POST http://localhost:8000/api/v1/analysis/ingest -H "Content-Type: application/json" -d '{"data": "test"}'

# 5. Ver métricas completas
curl http://localhost:8000/metrics | grep aegen_llm
```

---

## 🎨 Trucos Geniales

**💡 Hacer que sea más bonito:**
Si tienes `jq` instalado, puedes hacer que los números se vean mejor:
```bash
curl -s http://localhost:8000/system/llm/status | jq
```

**💡 Guardar las métricas:**
```bash
curl -s http://localhost:8000/system/llm/status > mis_metricas.json
```

**💡 Ver solo lo importante:**
```bash
curl -s http://localhost:8000/metrics | grep aegen_llm_calls_total
```

---

## 🚨 ¿Problemas Comunes?

**❌ "Connection refused"**
→ El robot no está encendido. Ve al PASO 1.

**❌ "command not found: curl"**
→ En Windows usa: `Invoke-WebRequest http://localhost:8000/system/llm/status`

**❌ Números todos en 0**
→ El robot no ha trabajado. Ve al PASO 4.

**❌ "unhealthy" en el health check**
→ Algo está roto. Reinicia el robot (PASO 1).

---

## 🎉 ¡Felicidades!

¡Ya sabes espiar a tu robot inteligente! 🕵️‍♀️

Ahora puedes:
- ✅ Ver si está funcionando bien
- ✅ Saber cuánto dinero gasta
- ✅ Ver qué tan rápido trabaja
- ✅ Contar cuántas veces usa la IA
- ✅ Detectar problemas antes que se vuelvan grandes

**¡Eres oficialmente un Inspector de Robots!** 🏅

---

*📝 Nota: Esta guía asume que tienes AEGEN corriendo en tu computadora local en el puerto 8000. Si usas otro puerto o servidor, cambia `localhost:8000` por la dirección correcta.*