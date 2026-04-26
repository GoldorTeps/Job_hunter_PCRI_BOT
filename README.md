# 🤖 Precari_bot

**El bot que te ayuda a buscar trabajo precario.**

Busca ofertas de empleo de baja cualificación en Indeed, InfoJobs, Turijobs y LinkedIn, selecciona el CV adecuado, genera una carta de presentación personalizada con IA y aplica automáticamente en LinkedIn — todo mientras tú estás currando.

---

## ¿Qué hace?

- Rastrea ofertas cada 30 minutos en **Indeed, InfoJobs, Turijobs y LinkedIn**
- Filtra por zona (Torremolinos + 20 km) y descarta chollos MLM y comisionistas
- Elige el CV correcto según la categoría del puesto (almacén, hostelería, reparto, telemarketing)
- Genera una **carta de presentación** con GPT-4o-mini, sin inventarse datos
- Te avisa por **Telegram** con la oferta, el CV y la carta lista
- Aplica automáticamente en **LinkedIn Easy Apply** con tu sesión Premium
- Registra todas las candidaturas en base de datos
- Envía un **resumen diario a las 9:00 h**
- Corre **24/7** en Railway — las notificaciones solo llegan en horario laboral

---

## Categorías cubiertas

| Emoji | Categoría | CV usado |
|-------|-----------|----------|
| 📦 | Almacén / Logística | CV Mozo |
| 🍽️ | Hostelería | CV Mozo |
| 🛵 | Reparto | CV Mozo |
| 📞 | Telemarketing | CV Telemarketing |

---

## Stack

- **Python 3.11**
- **Playwright** — automatización LinkedIn Easy Apply
- **OpenAI gpt-4o-mini** — selección de CV y cartas de presentación
- **PostgreSQL** (Railway) + SQLite local como fallback
- **Telegram Bot API** — notificaciones
- **feedparser / BeautifulSoup** — scraping Indeed, InfoJobs, Turijobs
- **schedule** — tareas periódicas
- **Railway** — despliegue como worker 24/7

---

## Variables de entorno

```env
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
OPENAI_API_KEY=
DATABASE_URL=           # Railway lo inyecta automáticamente con PostgreSQL
LINKEDIN_COOKIE=        # Cookie li_at de tu sesión LinkedIn Premium
MAX_APPLIES_PER_RUN=10  # Máximo de candidaturas por ciclo (opcional)
CHECK_INTERVAL_MINUTES=30
ACTIVE_HOUR_START=9
ACTIVE_HOUR_END=17
DIGEST_HOUR=9
```

---

## Instalación local

```bash
git clone https://github.com/GoldorTeps/Job_hunter_PCRI_BOT.git
cd Job_hunter_PCRI_BOT

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env   # rellena tus variables
python main.py
```

---

## Despliegue en Railway

1. Conecta el repositorio en [railway.app](https://railway.app)
2. Añade un plugin **PostgreSQL**
3. Configura las variables de entorno del apartado anterior
4. Railway usará el `Procfile` automáticamente:
   ```
   worker: playwright install chromium --with-deps && python main.py
   ```

---

## ¿Cómo consigo la cookie li_at?

1. Abre LinkedIn en Firefox o Chrome con tu sesión iniciada
2. F12 → **Almacenamiento** (Firefox) o **Application** (Chrome) → Cookies → `linkedin.com`
3. Copia el valor de la cookie **`li_at`**
4. Pégalo en Railway como variable `LINKEDIN_COOKIE`

> La cookie caduca si cierras sesión o LinkedIn la invalida. Si el auto-apply deja de funcionar, renuévala.

---

## Estructura del proyecto

```
├── main.py              # Orquestador principal y scheduler
├── config.py            # Variables y configuración de búsquedas
├── scraper.py           # Indeed, InfoJobs, Turijobs
├── scraper_linkedin.py  # LinkedIn (endpoint público)
├── ai_assistant.py      # Selección de CV y cartas con OpenAI
├── apply_linkedin.py    # Auto-apply LinkedIn Easy Apply (Playwright)
├── notifier.py          # Telegram
├── tracker.py           # Registro de candidaturas en BD
├── database.py          # Abstracción PostgreSQL / SQLite
├── cvs/                 # CVs en .txt (excluidos del repo)
│   ├── mozo.txt
│   ├── telemarketing.txt
│   └── admin.txt
└── Procfile
```

---

## Limitaciones conocidas

- LinkedIn Easy Apply solo funciona con formularios estándar; los pasos muy personalizados pueden fallar
- Los selectores de LinkedIn pueden romperse con actualizaciones de la plataforma
- La cookie `li_at` necesita renovación manual si caduca
- InfoJobs y Turijobs pueden cambiar su HTML sin previo aviso

---

## Licencia

MIT — úsalo, fórkalo, mejóralo. Si te ayuda a salir de un trabajo de mierda, misión cumplida.
