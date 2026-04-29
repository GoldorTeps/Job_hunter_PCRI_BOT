"""
Tracking de candidaturas.
Guarda en PostgreSQL (Railway) y en candidaturas.csv (local).
Columnas: fecha, empresa, puesto, portal, categoria, cv_usado, estado, url, job_id
"""
import csv
import os
from datetime import datetime
from database import _connection, _ph, _use_postgres

CSV_PATH = os.path.join(os.path.dirname(__file__), 'candidaturas.csv')

COLUMNS = ['fecha', 'empresa', 'puesto', 'portal', 'categoria', 'cv_usado', 'estado', 'url', 'job_id']

STATUS_PENDING         = 'pending'
STATUS_APPROVED_AUTO   = 'approved_auto'
STATUS_APPROVED_MANUAL = 'approved_manual'
STATUS_DISCARDED       = 'discarded'
STATUS_FAILED          = 'failed'


def init_tracker():
    """Crea la tabla candidaturas si no existe y migra columnas nuevas."""
    with _connection() as conn:
        conn.cursor().execute('''
            CREATE TABLE IF NOT EXISTS candidaturas (
                id        SERIAL PRIMARY KEY,
                fecha     TEXT,
                empresa   TEXT,
                puesto    TEXT,
                portal    TEXT,
                categoria TEXT,
                cv_usado  TEXT,
                estado    TEXT DEFAULT 'pending',
                url       TEXT,
                job_id    TEXT
            )
        ''')

    # Migración: añadir job_id si la tabla ya existía sin él
    try:
        with _connection() as conn:
            if _use_postgres():
                conn.cursor().execute(
                    'ALTER TABLE candidaturas ADD COLUMN IF NOT EXISTS job_id TEXT'
                )
            else:
                conn.cursor().execute(
                    'ALTER TABLE candidaturas ADD COLUMN job_id TEXT'
                )
    except Exception:
        pass  # Columna ya existe

    _ensure_csv_header()


def _ensure_csv_header():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()


def track(job: dict, status: str = STATUS_PENDING):
    """Registra una candidatura en DB y en CSV."""
    row = {
        'fecha':     datetime.now().strftime('%Y-%m-%d %H:%M'),
        'empresa':   job.get('company', ''),
        'puesto':    job.get('title', ''),
        'portal':    job.get('source', ''),
        'categoria': job.get('category', ''),
        'cv_usado':  job.get('cv_name', ''),
        'estado':    status,
        'url':       job.get('url', ''),
        'job_id':    job.get('id', ''),
    }

    try:
        ph = _ph()
        with _connection() as conn:
            conn.cursor().execute(
                f'''INSERT INTO candidaturas
                    (fecha, empresa, puesto, portal, categoria, cv_usado, estado, url, job_id)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})''',
                tuple(row.values())
            )
    except Exception as e:
        print(f'[Tracker] Error DB: {e}')

    try:
        _ensure_csv_header()
        with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writerow(row)
    except Exception as e:
        print(f'[Tracker] Error CSV: {e}')

    print(f'[Tracker] ✔ {row["puesto"]} — {row["empresa"]} ({status})')


def update_status(job_id: str, status: str):
    """Actualiza el estado de una candidatura por job_id."""
    if not job_id:
        return
    try:
        ph = _ph()
        with _connection() as conn:
            conn.cursor().execute(
                f'UPDATE candidaturas SET estado = {ph} WHERE job_id = {ph}',
                (status, job_id)
            )
        print(f'[Tracker] Estado → {status} para job_id={job_id}')
    except Exception as e:
        print(f'[Tracker] Error update_status: {e}')


def today_jobs() -> list:
    """Devuelve todas las candidaturas registradas hoy."""
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        ph = _ph()
        with _connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f'''SELECT empresa, puesto, portal, categoria, cv_usado, estado, url, job_id
                    FROM candidaturas WHERE fecha LIKE {ph}''',
                (f'{today}%',)
            )
            rows = cur.fetchall()
        cols = ['empresa', 'puesto', 'portal', 'categoria', 'cv_usado', 'status', 'url', 'job_id']
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        print(f'[Tracker] Error today_jobs: {e}')
        return []
