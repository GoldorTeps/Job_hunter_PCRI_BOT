"""
Tracking mínimo de candidaturas.
Guarda en PostgreSQL (Railway) y en candidaturas.csv (local).
Columnas: fecha, empresa, puesto, portal, categoria, cv_usado, estado, url
"""
import csv
import os
from datetime import datetime
from database import _connection, _ph, _use_postgres

CSV_PATH = os.path.join(os.path.dirname(__file__), 'candidaturas.csv')

COLUMNS = ['fecha', 'empresa', 'puesto', 'portal', 'categoria', 'cv_usado', 'estado', 'url']


def init_tracker():
    """Crea la tabla candidaturas si no existe."""
    with _connection() as conn:
        conn.cursor().execute('''
            CREATE TABLE IF NOT EXISTS candidaturas (
                id       SERIAL PRIMARY KEY,
                fecha    TEXT,
                empresa  TEXT,
                puesto   TEXT,
                portal   TEXT,
                categoria TEXT,
                cv_usado TEXT,
                estado   TEXT DEFAULT \'notificada\',
                url      TEXT
            )
        ''')
    _ensure_csv_header()


def _ensure_csv_header():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()


def track(job: dict, estado: str = 'notificada'):
    """Registra una candidatura en DB y en CSV."""
    row = {
        'fecha':     datetime.now().strftime('%Y-%m-%d %H:%M'),
        'empresa':   job.get('company', ''),
        'puesto':    job.get('title', ''),
        'portal':    job.get('source', ''),
        'categoria': job.get('category', ''),
        'cv_usado':  job.get('cv_name', ''),
        'estado':    estado,
        'url':       job.get('url', ''),
    }

    # ── PostgreSQL ──────────────────────────────────────────────────────────
    try:
        ph = _ph()
        with _connection() as conn:
            conn.cursor().execute(
                f'''INSERT INTO candidaturas
                    (fecha, empresa, puesto, portal, categoria, cv_usado, estado, url)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})''',
                tuple(row.values())
            )
    except Exception as e:
        print(f'[Tracker] Error DB: {e}')

    # ── CSV local ───────────────────────────────────────────────────────────
    try:
        _ensure_csv_header()
        with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writerow(row)
    except Exception as e:
        print(f'[Tracker] Error CSV: {e}')

    print(f'[Tracker] ✔ {row["puesto"]} — {row["empresa"]} ({row["estado"]})')
