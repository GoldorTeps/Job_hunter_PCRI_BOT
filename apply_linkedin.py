"""
LinkedIn Easy Apply — automatización con sesión Premium.
Usa la cookie li_at para aplicar directamente desde la cuenta del usuario.
"""
import os
import time
import random

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import SEARCHES
from tracker import track

LINKEDIN_COOKIE = os.getenv('LINKEDIN_COOKIE', '')
MAX_APPLIES_PER_RUN = int(os.getenv('MAX_APPLIES_PER_RUN', '10'))

# Selectores LinkedIn Easy Apply (pueden cambiar con updates de LinkedIn)
SEL_EASY_APPLY   = 'button.jobs-apply-button:has-text("Easy Apply"), button.jobs-apply-button:has-text("Solicitud sencilla")'
SEL_NEXT         = 'button[aria-label="Continuar a la siguiente sección"], button[aria-label="Continue to next step"]'
SEL_SUBMIT       = 'button[aria-label="Enviar solicitud"], button[aria-label="Submit application"]'
SEL_COVER_LETTER = 'textarea[id*="cover-letter"], textarea[placeholder*="carta"], textarea[placeholder*="cover"]'
SEL_DISMISS      = 'button[aria-label="Descartar"], button[aria-label="Dismiss"]'
SEL_ALREADY      = 'span:has-text("Solicitud enviada"), span:has-text("Applied")'


def _random_delay(min_s=1.2, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))


def _setup_context(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    context = browser.new_context(
        user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/122.0.0.0 Safari/537.36'
        ),
        viewport={'width': 1280, 'height': 800},
        locale='es-ES',
    )
    context.add_cookies([{
        'name':   'li_at',
        'value':  LINKEDIN_COOKIE,
        'domain': '.linkedin.com',
        'path':   '/',
    }])
    return browser, context


def _fill_cover_letter(page, text: str) -> bool:
    """Intenta rellenar el campo de carta de presentación si existe."""
    try:
        field = page.query_selector(SEL_COVER_LETTER)
        if field:
            field.click()
            field.fill(text)
            _random_delay(0.5, 1.2)
            return True
    except Exception:
        pass
    return False


def _answer_screening_questions(page, cv_text: str):
    """
    Responde preguntas de cribado comunes.
    Estrategia conservadora: sí a trabajo en España, no a relocation, etc.
    """
    try:
        # Checkboxes y radios simples
        for label_text in [
            'Sí', 'Yes', 'España', 'Autorizado', 'Tiempo completo', 'Full-time'
        ]:
            labels = page.query_selector_all(f'label:has-text("{label_text}")')
            for label in labels[:1]:
                try:
                    label.click()
                    _random_delay(0.3, 0.7)
                except Exception:
                    pass

        # Inputs numéricos de experiencia — extraemos del CV si es posible
        numeric_inputs = page.query_selector_all('input[type="text"][id*="experience"], input[type="number"]')
        for inp in numeric_inputs[:3]:
            try:
                placeholder = inp.get_attribute('placeholder') or ''
                if 'año' in placeholder.lower() or 'year' in placeholder.lower():
                    inp.fill('3')
                    _random_delay(0.2, 0.5)
            except Exception:
                pass
    except Exception as e:
        print(f'[Apply] Error en preguntas de cribado: {e}')


def _navigate_form(page, cover_letter: str, cv_text: str) -> bool:
    """
    Navega los pasos del formulario Easy Apply.
    Devuelve True si llega al submit, False si hay algún problema.
    """
    max_steps = 8
    for step in range(max_steps):
        _random_delay(1.0, 2.0)

        # Rellenar carta si aparece
        _fill_cover_letter(page, cover_letter)

        # Responder preguntas
        _answer_screening_questions(page, cv_text)

        # ¿Hay botón de submit?
        submit_btn = page.query_selector(SEL_SUBMIT)
        if submit_btn and submit_btn.is_visible():
            _random_delay(0.8, 1.5)
            submit_btn.click()
            _random_delay(1.5, 2.5)
            return True

        # ¿Hay botón de siguiente?
        next_btn = page.query_selector(SEL_NEXT)
        if next_btn and next_btn.is_visible():
            next_btn.click()
            continue

        # Sin botones reconocibles — salir
        print(f'[Apply] Paso {step+1}: sin botón siguiente ni submit.')
        break

    return False


def apply_to_job(job: dict) -> bool:
    """
    Aplica a una oferta de LinkedIn usando Easy Apply.
    Devuelve True si la candidatura se envió correctamente.
    """
    if not LINKEDIN_COOKIE:
        print('[Apply] Sin LINKEDIN_COOKIE configurada.')
        return False

    cover_letter = job.get('cover_letter', '')
    cv_text = ''
    try:
        cv_path = os.path.join(
            os.path.dirname(__file__), 'cvs', f'{job.get("cv_name", "mozo")}.txt'
        )
        with open(cv_path, encoding='utf-8') as f:
            cv_text = f.read()
    except Exception:
        pass

    try:
        with sync_playwright() as p:
            browser, context = _setup_context(p)
            page = context.new_page()

            # Abrir oferta
            page.goto(job['url'], timeout=20000)
            _random_delay(1.5, 3.0)

            # ¿Ya aplicado?
            if page.query_selector(SEL_ALREADY):
                print(f'[Apply] Ya aplicado: {job["title"]}')
                browser.close()
                return False

            # ¿Tiene Easy Apply?
            try:
                easy_btn = page.wait_for_selector(SEL_EASY_APPLY, timeout=6000)
            except PWTimeout:
                print(f'[Apply] Sin Easy Apply: {job["title"]}')
                browser.close()
                return False

            easy_btn.click()
            _random_delay(1.5, 2.5)

            # Navegar el formulario
            success = _navigate_form(page, cover_letter, cv_text)

            # Cerrar modal de confirmación si aparece
            try:
                dismiss = page.query_selector(SEL_DISMISS)
                if dismiss:
                    dismiss.click()
            except Exception:
                pass

            browser.close()

            if success:
                print(f'[Apply] ✅ Aplicado: {job["title"]} — {job["company"]}')
                track(job, estado='aplicada')
                _notify_applied(job)
            else:
                print(f'[Apply] ⚠️ Formulario no completado: {job["title"]}')

            return success

    except Exception as e:
        print(f'[Apply] Error en {job["title"]}: {e}')
        return False


def _notify_applied(job: dict):
    """Manda confirmación a Telegram cuando se aplica con éxito."""
    from notifier import _send
    _send(
        f"✅ <b>Candidatura enviada</b>\n\n"
        f"<b>{job['title']}</b>\n"
        f"🏢 {job['company']}\n"
        f"📍 {job['location']}\n"
        f"📄 {job.get('cv_name', '')}\n"
        f"🔗 <a href='{job['url']}'>Ver en LinkedIn</a>"
    )


def run_auto_apply(jobs: list) -> int:
    """
    Recorre la lista de jobs e intenta aplicar a los de LinkedIn con Easy Apply.
    Respeta el límite MAX_APPLIES_PER_RUN.
    Devuelve el número de candidaturas enviadas.
    """
    if not LINKEDIN_COOKIE:
        print('[Apply] LINKEDIN_COOKIE no configurada — auto-apply desactivado.')
        return 0

    applied = 0
    for job in jobs:
        if applied >= MAX_APPLIES_PER_RUN:
            print(f'[Apply] Límite de {MAX_APPLIES_PER_RUN} candidaturas alcanzado.')
            break

        if job.get('source') != 'LinkedIn':
            continue
        if not job.get('cv_name'):
            continue

        success = apply_to_job(job)
        if success:
            applied += 1
            _random_delay(8, 15)   # pausa larga entre aplicaciones

    print(f'[Apply] Sesión completada: {applied} candidaturas enviadas.')
    return applied
