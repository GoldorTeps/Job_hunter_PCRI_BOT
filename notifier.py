import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

API = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

def _send(text: str, parse_mode: str = 'HTML'):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f'[Telegram] Sin config — {text[:80]}')
        return False
    try:
        r = requests.post(
            f'{API}/sendMessage',
            json={
                'chat_id':                  TELEGRAM_CHAT_ID,
                'text':                     text,
                'parse_mode':               parse_mode,
                'disable_web_page_preview': True,
            },
            timeout=10,
        )
        return r.ok
    except Exception as e:
        print(f'[Telegram] Error: {e}')
        return False


def send_startup():
    _send(
        '🤖 <b>Precari_bot activo</b> — Torremolinos + 20 km\n\n'
        '📦 Almacén  🍽️ Hostelería  🛵 Reparto  📞 Telemarketing\n\n'
        '🔍 Busco cada 30 min en Indeed, InfoJobs, Turijobs y LinkedIn.\n'
        '⚡ Auto-apply activado en LinkedIn Easy Apply.\n'
        '📊 Resumen diario a las 9:00. ¡Que salga pronto! 💪'
    )


CV_LABELS = {
    'mozo':          '📄 CV Mozo / Almacén',
    'telemarketing': '📄 CV Telemarketing',
    'admin':         '📄 CV Auxiliar Admin',
}

def send_job_alert(job: dict):
    summary = f"\n<i>{job['summary'][:180]}…</i>" if job.get('summary') else ''

    cv_line = ''
    if job.get('cv_name'):
        cv_line = f"\n{CV_LABELS.get(job['cv_name'], job['cv_name'])}"

    letter_block = ''
    if job.get('cover_letter'):
        letter_block = f"\n\n✍️ <b>Carta sugerida:</b>\n<i>{job['cover_letter']}</i>"

    _send(
        f"{job['category']} — Nueva oferta\n\n"
        f"<b>{job['title']}</b>\n"
        f"🏢 {job['company']}\n"
        f"📍 {job['location']}  ·  {job['source']}"
        f"{cv_line}"
        f"{summary}"
        f"{letter_block}\n\n"
        f"🔗 <a href='{job['url']}'>Ver oferta</a>"
    )


def send_daily_digest(jobs_by_category: dict, db_stats: dict):
    total_new = sum(len(v) for v in jobs_by_category.values())

    if total_new == 0:
        _send(
            '📭 <b>Resumen diario</b>\n\n'
            'Sin ofertas nuevas hoy. Seguiré buscando. 👀'
        )
        return

    lines = [f'🌅 <b>Resumen diario — {total_new} ofertas nuevas</b>\n']

    for cat, jobs in jobs_by_category.items():
        if not jobs:
            continue
        lines.append(f'\n{cat}  <b>({len(jobs)})</b>')
        for job in jobs[:4]:
            url, title, company = job['url'], job['title'], job['company']
            lines.append(f"  • <a href='{url}'>{title}</a> — {company}")
        if len(jobs) > 4:
            lines.append(f'  <i>…y {len(jobs) - 4} más</i>')

    lines.append(f'\n📊 Total acumulado: {db_stats["total"]} ofertas procesadas')
    _send('\n'.join(lines))


def send_error(msg: str):
    _send(f'⚠️ <b>Error en Job Hunter</b>\n\n<code>{msg[:300]}</code>')
