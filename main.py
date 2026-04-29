import time
import threading
import traceback
from datetime import datetime

import requests
import schedule

from config import CHECK_INTERVAL_MIN, DIGEST_HOUR, ACTIVE_HOUR_START, ACTIVE_HOUR_END, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from database import init_db, is_seen, mark_seen, stats
from scraper import run_all_searches
from notifier import (
    send_startup, send_job_alert_with_buttons, send_manual_followup,
    send_apply_result, send_daily_digest, send_error, answer_callback,
)
from ai_assistant import enrich_job
from tracker import (
    init_tracker, track, update_status, today_jobs,
    STATUS_PENDING, STATUS_APPROVED_AUTO, STATUS_APPROVED_MANUAL,
    STATUS_DISCARDED, STATUS_FAILED,
)
from apply_linkedin import apply_to_job

# Ofertas notificadas en esta sesión (job_id → job dict completo)
_pending_jobs: dict = {}


def _is_active_hour() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    if now.hour < ACTIVE_HOUR_START:
        return False
    if now.hour > ACTIVE_HOUR_END:
        return False
    if now.hour == ACTIVE_HOUR_END and now.minute > 30:
        return False
    return True


def _now():
    return datetime.now().strftime('%H:%M:%S')


# ── Lógica de callbacks ──────────────────────────────────────────────────────

def _handle_callback(cb: dict):
    data    = cb.get('data', '')
    cb_id   = cb['id']

    if data.startswith('apply_'):
        job_id = data[len('apply_'):]
        job = _pending_jobs.get(job_id)
        if not job:
            answer_callback(cb_id, '⚠️ Oferta no disponible (bot reiniciado). Usa el enlace.')
            return

        if job.get('source') == 'LinkedIn':
            answer_callback(cb_id, '⚡ Aplicando en LinkedIn...')
            success, reason = apply_to_job(job)
            if success:
                update_status(job_id, STATUS_APPROVED_AUTO)
                send_apply_result(job, True)
            else:
                update_status(job_id, STATUS_FAILED)
                send_apply_result(job, False, reason)
            _pending_jobs.pop(job_id, None)
        else:
            answer_callback(cb_id, '🔗 Abre el enlace y aplica manualmente.')
            send_manual_followup(job)
            # El status sigue siendo pending hasta que el usuario confirme

    elif data.startswith('discard_'):
        job_id = data[len('discard_'):]
        answer_callback(cb_id, '❌ Oferta descartada.')
        update_status(job_id, STATUS_DISCARDED)
        _pending_jobs.pop(job_id, None)

    elif data.startswith('done_'):
        job_id = data[len('done_'):]
        answer_callback(cb_id, '✅ Registrada como aplicada manualmente.')
        update_status(job_id, STATUS_APPROVED_MANUAL)
        _pending_jobs.pop(job_id, None)


def _poll_callbacks():
    """Hilo secundario: escucha callback queries de Telegram mediante long-polling."""
    api = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'
    offset = 0

    while True:
        try:
            r = requests.post(
                f'{api}/getUpdates',
                json={'offset': offset, 'timeout': 30, 'allowed_updates': ['callback_query']},
                timeout=35,
            )
            if not r.ok:
                time.sleep(5)
                continue

            for update in r.json().get('result', []):
                offset = update['update_id'] + 1
                if 'callback_query' in update:
                    try:
                        _handle_callback(update['callback_query'])
                    except Exception as e:
                        print(f'[Callbacks] Error procesando callback: {e}')

        except Exception as e:
            print(f'[Callbacks] Error en poll: {e}')
            time.sleep(5)


# ── Loop principal ───────────────────────────────────────────────────────────

def check_jobs():
    print(f'[{_now()}] Buscando...')
    try:
        jobs     = run_all_searches()
        new_jobs = []

        for job in jobs:
            if not is_seen(job['id']):
                enriched = enrich_job(job)
                mark_seen(job)
                if enriched is None:
                    continue
                track(enriched, status=STATUS_PENDING)
                _pending_jobs[enriched['id']] = enriched
                if _is_active_hour():
                    send_job_alert_with_buttons(enriched)
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
        jobs = today_jobs()
        send_daily_digest(
            auto_applied=[j for j in jobs if j['status'] == STATUS_APPROVED_AUTO],
            manual      =[j for j in jobs if j['status'] == STATUS_APPROVED_MANUAL],
            discarded   =[j for j in jobs if j['status'] == STATUS_DISCARDED],
            pending     =[j for j in jobs if j['status'] == STATUS_PENDING],
            failed      =[j for j in jobs if j['status'] == STATUS_FAILED],
            db_stats    =stats(),
        )
    except Exception as e:
        err = traceback.format_exc()
        print(f'[ERROR digest] {err}')
        send_error(str(e))


if __name__ == '__main__':
    print('🚀 Job Hunter arrancando...')
    init_db()
    init_tracker()
    send_startup()

    # Hilo de escucha de callbacks (botones Telegram)
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        t = threading.Thread(target=_poll_callbacks, daemon=True, name='callbacks')
        t.start()
        print('✅ Hilo de callbacks activo.')

    # Primera búsqueda inmediata
    check_jobs()

    schedule.every(CHECK_INTERVAL_MIN).minutes.do(check_jobs)
    schedule.every().day.at(f'{DIGEST_HOUR:02d}:00').do(daily_digest)

    print(f'✅ Buscando cada {CHECK_INTERVAL_MIN} min · Resumen a las {DIGEST_HOUR}:00 h')

    while True:
        schedule.run_pending()
        time.sleep(60)
