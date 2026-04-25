import os

TELEGRAM_TOKEN   = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
DATABASE_URL     = os.getenv('DATABASE_URL', '')

CHECK_INTERVAL_MIN = int(os.getenv('CHECK_INTERVAL_MINUTES', '30'))
ACTIVE_HOUR_START  = int(os.getenv('ACTIVE_HOUR_START', '9'))    # 09:00
ACTIVE_HOUR_END    = int(os.getenv('ACTIVE_HOUR_END',   '17'))   # 17:30
DIGEST_HOUR        = int(os.getenv('DIGEST_HOUR', '9'))           # resumen al arrancar el día

LOCATION   = 'Torremolinos'
RADIUS_KM  = 20
PROVINCE   = '29'  # Málaga (InfoJobs)

SEARCHES = [
    {
        'category': '📦 Almacén',
        'indeed':   ['mozo almacen', 'operario almacen', 'carretillero', 'picking logistica'],
        'infojobs': ['mozo almacen', 'almacen'],
        'turijobs': [],
    },
    {
        'category': '🍽️ Hostelería',
        'indeed':   ['camarero', 'cocinero', 'ayudante cocina', 'recepcionista hotel'],
        'infojobs': ['camarero', 'hosteleria'],
        'turijobs': ['camarero', 'cocinero', 'recepcionista'],
    },
    {
        'category': '🛵 Reparto',
        'indeed':   ['repartidor', 'conductor reparto', 'mensajero delivery'],
        'infojobs': ['repartidor', 'reparto'],
        'turijobs': [],
    },
    {
        'category': '📞 Telemarketing',
        'indeed':   ['teleoperador', 'call center', 'atencion telefonica'],
        'infojobs': ['teleoperador', 'telemarketing'],
        'turijobs': [],
    },
]

BLACKLIST = [
    'multinivel', 'mlm', 'sin sueldo fijo', 'solo comisiones',
    'inversión inicial', 'autónomo obligatorio', 'autonomo obligatorio',
    'amway', 'herbalife', 'ingresos extra desde casa', 'trabaja desde casa sin experiencia',
    'franquicia', 'distribuidor independiente',
]
