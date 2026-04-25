# Job Hunter — Setup

## 1. Crear el bot de Telegram (2 min)

1. Abre Telegram → busca **@BotFather**
2. Escribe `/newbot` → ponle un nombre (ej: `Mi Job Hunter`)
3. Copia el **token** que te da (parece: `123456789:ABCdef...`)
4. Abre este enlace en el navegador para obtener tu chat_id:
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
   (primero envía cualquier mensaje a tu bot)
5. En el JSON busca `"id"` dentro de `"chat"` — ese es tu **CHAT_ID**

---

## 2. Subir a Railway

1. Sube esta carpeta a un repositorio de GitHub
2. En Railway → **New Project** → **Deploy from GitHub repo**
3. Selecciona el repo

---

## 3. Variables de entorno en Railway

En tu proyecto de Railway → **Variables** → añade estas:

| Variable | Valor |
|---|---|
| `TELEGRAM_TOKEN` | El token de @BotFather |
| `TELEGRAM_CHAT_ID` | Tu chat ID numérico |
| `CHECK_INTERVAL_MINUTES` | `30` (cada cuánto busca) |
| `DIGEST_HOUR` | `8` (hora del resumen diario) |

---

## 4. Añadir base de datos (Railway PostgreSQL)

En Railway → tu proyecto → **+ New** → **Database** → **PostgreSQL**

Railway inyecta `DATABASE_URL` automáticamente. No hace falta configurar nada más.

---

## 5. Arrancar

Railway arranca el worker automáticamente con el `Procfile`.  
En 2 minutos recibirás el mensaje de inicio en Telegram. ✅

---

## Ajustar búsquedas

Edita `config.py`:
- `SEARCHES` → añade/quita keywords por categoría
- `BLACKLIST` → palabras que descartan una oferta
- `RADIUS_KM` → radio de búsqueda (defecto: 20 km)
- `LOCATION` → ciudad base (defecto: Torremolinos)
