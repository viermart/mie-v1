# 🚀 Deploy a Railway - Instrucciones

## Paso 1: Instala Railway CLI (en tu máquina local)

```bash
npm install -g @railway/cli
```

## Paso 2: Ve a la carpeta mie-v1

```bash
cd mie-v1
```

## Paso 3: Inicia sesión en Railway

```bash
railway login
```

Te abrirá el navegador para autenticar.

## Paso 4: Inicializa el proyecto

```bash
railway init
```

Responde "No" si te pregunta si tienes un `railway.json` (ya existe).

## Paso 5: Configura variables de entorno

```bash
railway variables set TELEGRAM_TOKEN=8406348922:AAEewXECoJATJ-w9QoYvypkuctLg381_S1w
railway variables set TELEGRAM_CHAT_ID=1186281649
railway variables set DB_PATH=mie.db
```

## Paso 6: Deploy

```bash
railway up
```

Esto subirá el código a Railway y iniciará el servicio.

## Paso 7: Verifica que esté vivo

```bash
railway logs
```

Deberías ver logs como:
```
🚀 MIE V1 iniciando...
✅ Loops programados
❤️ Heartbeat: MIE V1 iniciado correctamente
```

---

## 📱 Verifica en Telegram

En tu chat de Telegram (@mie_bot o donde hayas configurado), deberías recibir:

**Heartbeat (primer mensaje):**
```
❤️ MIE Heartbeat
2026-04-21 10:15:23 UTC
MIE V1 iniciado correctamente
```

**Daily Report (08:00 UTC):**
```
📊 MIE DAILY REPORT
2026-04-21 08:00 UTC

📈 Market Snapshot (24h):
BTC:
  Current: $45234.50
  24h Range: $44100.00 - $45900.00
  Observations: 287
...
```

---

## 🔍 Comandos útiles

Ver logs en vivo:
```bash
railway logs -f
```

Ver variables de entorno:
```bash
railway variables
```

Detener el servicio:
```bash
railway down
```

Redeployar después de cambios:
```bash
git add .
git commit -m "Update MIE"
railway up
```

---

## ⚡ Quick Deploy (copiar-pegar)

```bash
npm install -g @railway/cli
cd mie-v1
railway login
railway init
railway variables set TELEGRAM_TOKEN=8406348922:AAEewXECoJATJ-w9QoYvypkuctLg381_S1w
railway variables set TELEGRAM_CHAT_ID=1186281649
railway variables set DB_PATH=mie.db
railway up
railway logs
```

---

## ✅ Listo!

MIE está viva en Railway 24/7 observando BTC/ETH y enviándote reportes a Telegram.

¿Preguntas? Ver: mie-v1/TESTING.md
