import time
import traceback
from collections import defaultdict

import schedule

from datetime import datetime
from config import CHECK_INTERVAL_MIN, DIGEST_HOUR, ACTIVE_HOUR_START, ACTIVE_HOUR_END
from database import init_db, is_seen, mark_seen, stats
from scraper import run_all_searches
from notifier import send_startup, send_job_alert, send_daily_digest, send_error
from ai_assistant import enrich_job
from tracker import init_tracker, track


def _is_active_hour() -> bool:
    now = datetime.now()
    # Lunes a viernes, 09:00 – 17:30
    if now.weekday() >= 5:
        return False
    if now.hour < ACTIVE_HOUR_START:
        return False
    if now.hour > ACTIVE_HOUR_END:
        return False
    if now.hour == ACTIVE_HOUR_END and now.minute > 30:
        return False
    return True


def check_jobs():
    if not _is_active_hour():
        print(f'[{_now()}] Fuera de horario, saltando.')
        return
    print(f'[{_now()}] Buscando...')
    try:
        jobs    = run_all_searches()
        new_jobs = []

        for job in jobs:
            if not is_seen(job['id']):
                enriched = enrich_job(job)
                mark_seen(job)                    # siempre marcar para no reprocesar
                if enriched is None:              # categoría sin CV → descartar
                    continue
                send_job_alert(enriched)
                track(enriched)                   # registrar candidatura notificada
                new_jobs.append(enriched)
                time.sleep(0.8)

        print(f'[{_now()}] {len(new_jobs)} nuevas / {len(jobs)} encontradas')
    except Exception as e:
        err = traceback.format_exc()
        print(f'[ERROR] {err}')
        send_error(str(e))


def daily_digest():
    print(f'[{_now()}] Enviando resumen diario...')
    try:
        jobs     = run_all_searches()
        new_jobs = [j for j in jobs if not is_seen(j['id'])]

        by_cat = defaultdict(list)
        for job in new_jobs:
            by_cat[job['category']].append(job)
            mark_seen(job)

        send_daily_digest(dict(by_cat), stats())
    except Exception as e:
        err = traceback.format_exc()
        print(f'[ERROR digest] {err}')
        send_error(str(e))


def _now():
    return datetime.now().strftime('%H:%M:%S')


if __name__ == '__main__':
    print('🚀 Job Hunter arrancando...')
    init_db()
    init_tracker()
    send_startup()

    # Primera búsqueda inmediata
    check_jobs()

    # Programar búsquedas periódicas
    schedule.every(CHECK_INTERVAL_MIN).minutes.do(check_jobs)
    schedule.every().day.at(f'{DIGEST_HOUR:02d}:00').do(daily_digest)

    print(f'✅ Buscando cada {CHECK_INTERVAL_MIN} min · Resumen a las {DIGEST_HOUR}:00 h')

    while True:
        schedule.run_pending()
        time.sleep(60)
