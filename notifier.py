import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

API = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

CV_LABELS = {
    'mozo':          '📄 CV Mozo / Almacén',
    'camarero':      '📄 CV Camarero / Hostelería',
    'conductor':     '📄 CV Conductor / Reparto',
    'telemarketing': '📄 CV Telemarketing',
    'admin':         '📄 CV Auxiliar Admin',
}


def _post(text: str, parse_mode: str = 'HTML', reply_markup=None) -> dict:
    """Llama a sendMessage y devuelve el JSON completo de respuesta."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f'[Telegram] Sin config — {text[:80]}')
        return {}
    payload = {
        'chat_id':                  TELEGRAM_CHAT_ID,
        'text':                     text,
        'parse_mode':               parse_mode,
        'disable_web_page_preview': True,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(f'{API}/sendMessage', json=payload, timeout=10)
        return r.json() if r.ok else {}
    except Exception as e:
        print(f'[Telegram] Error: {e}')
        return {}


def _send(text: str, parse_mode: str = 'HTML') -> bool:
    return bool(_post(text, parse_mode).get('ok'))


def answer_callback(callback_id: str, text: str = ''):
    """Responde a un callback query para quitar el spinner del botón."""
    try:
        requests.post(
            f'{API}/answerCallbackQuery',
            json={'callback_query_id': callback_id, 'text': text},
            timeout=5,
        )
    except Exception:
        pass


def send_startup():
    _send(
        '🤖 <b>Precari_bot activo</b> — Torremolinos + 20 km\n\n'
        '📦 Almacén  🍽️ Hostelería  🛵 Reparto  📞 Telemarketing\n\n'
        '🔍 Busco cada 30 min en Indeed, Turijobs, Trabajos.com, SAE y LinkedIn.\n'
        '⚡ Auto-apply activado en LinkedIn Easy Apply.\n'
        '📊 Resumen diario a las 9:00. ¡Que salga pronto! 💪'
    )


def send_job_alert_with_buttons(job: dict) -> int | None:
    """Envía alerta de oferta con botones inline Aplicar/Descartar. Devuelve message_id."""
    is_linkedin = job.get('source') == 'LinkedIn'
    summary = f"\n<i>{job['summary'][:180]}…</i>" if job.get('summary') else ''
    cv_line = f"\n{CV_LABELS.get(job['cv_name'], job['cv_name'])}" if job.get('cv_name') else ''

    if is_linkedin:
        header = '⚡ <b>LinkedIn — Auto-apply listo</b>'
        apply_label = '✅ Aplicar (bot lo hace)'
    else:
        header = f"{job['category']} — Nueva oferta"
        apply_label = '✅ Aplicar'

    text = (
        f"{header}\n\n"
        f"<b>{job['title']}</b>\n"
        f"🏢 {job['company']}\n"
        f"📍 {job['location']}  ·  {job['source']}"
        f"{cv_line}"
        f"{summary}\n\n"
        f"🔗 <a href='{job['url']}'>Ver oferta</a>"
    )
    keyboard = {'inline_keyboard': [[
        {'text': apply_label,    'callback_data': f'apply_{job["id"]}'},
        {'text': '❌ Descartar', 'callback_data': f'discard_{job["id"]}'},
    ]]}

    resp = _post(text, reply_markup=keyboard)
    return resp.get('result', {}).get('message_id')


def send_manual_followup(job: dict):
    """Envía mensaje de seguimiento para confirmar aplicación manual."""
    text = (
        f"🔗 <b>Aplica manualmente</b>\n\n"
        f"<b>{job['title']}</b> — {job['company']}\n"
        f"<a href='{job['url']}'>Abrir oferta</a>\n\n"
        f"Cuando lo hayas enviado, pulsa el botón:"
    )
    keyboard = {'inline_keyboard': [[
        {'text': '✅ Ya lo hice', 'callback_data': f'done_{job["id"]}'},
    ]]}
    _post(text, reply_markup=keyboard)


def send_apply_result(job: dict, success: bool, reason: str = ''):
    """Notifica el resultado del auto-apply de LinkedIn."""
    cv = CV_LABELS.get(job.get('cv_name', ''), job.get('cv_name', ''))
    if success:
        _send(
            f"✅ <b>Candidatura enviada</b>\n\n"
            f"<b>{job['title']}</b>\n"
            f"🏢 {job['company']}\n"
            f"📍 {job['location']}\n"
            f"{cv}\n"
            f"🔗 <a href='{job['url']}'>Ver en LinkedIn</a>"
        )
    else:
        _send(
            f"❌ <b>Auto-apply fallido</b>\n\n"
            f"<b>{job['title']}</b> — {job['company']}\n"
            f"Motivo: {reason or 'Error desconocido'}"
        )


def send_daily_digest(
    auto_applied: list,
    manual: list,
    discarded: list,
    pending: list,
    failed: list,
    db_stats: dict,
):
    total = len(auto_applied) + len(manual) + len(discarded) + len(pending) + len(failed)

    if total == 0:
        _send('📭 <b>Resumen diario</b>\n\nSin actividad hoy. Seguiré buscando. 👀')
        return

    lines = ['🌅 <b>Resumen diario</b>\n']

    if auto_applied:
        lines.append(f'⚡ <b>Auto-apply LinkedIn:</b> {len(auto_applied)}')
        for j in auto_applied:
            lines.append(f"  • {j['puesto']} — {j['empresa']}")

    if manual:
        lines.append(f'✅ <b>Aplicadas manualmente:</b> {len(manual)}')
        for j in manual:
            lines.append(f"  • {j['puesto']} — {j['empresa']} ({j['portal']})")

    if discarded:
        lines.append(f'❌ <b>Descartadas:</b> {len(discarded)}')
        for j in discarded:
            lines.append(f"  • {j['puesto']} — {j['empresa']}")

    if pending:
        lines.append(f'⏳ <b>Pendientes sin respuesta:</b> {len(pending)}')
        for j in pending:
            lines.append(f"  • {j['puesto']} — {j['empresa']} ({j['portal']})")

    if failed:
        lines.append(f'⚠️ <b>Auto-apply fallido:</b> {len(failed)}')
        for j in failed:
            lines.append(f"  • {j['puesto']} — {j['empresa']}")

    lines.append(f'\n📊 Total acumulado: {db_stats["total"]} ofertas procesadas')
    _send('\n'.join(lines))


def send_error(msg: str):
    _send(f'⚠️ <b>Error en Job Hunter</b>\n\n<code>{msg[:300]}</code>')
