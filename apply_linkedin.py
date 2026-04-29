"""
LinkedIn Easy Apply — automatización con sesión Premium.
Usa la cookie li_at para aplicar directamente desde la cuenta del usuario.
"""
import os
import time
import random

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import SEARCHES

LINKEDIN_COOKIE     = os.getenv('LINKEDIN_COOKIE', '')
MAX_APPLIES_PER_RUN = int(os.getenv('MAX_APPLIES_PER_RUN', '10'))

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
    try:
        for label_text in ['Sí', 'Yes', 'España', 'Autorizado', 'Tiempo completo', 'Full-time']:
            labels = page.query_selector_all(f'label:has-text("{label_text}")')
            for label in labels[:1]:
                try:
                    label.click()
                    _random_delay(0.3, 0.7)
                except Exception:
                    pass

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
    max_steps = 8
    for step in range(max_steps):
        _random_delay(1.0, 2.0)
        _fill_cover_letter(page, cover_letter)
        _answer_screening_questions(page, cv_text)

        submit_btn = page.query_selector(SEL_SUBMIT)
        if submit_btn and submit_btn.is_visible():
            _random_delay(0.8, 1.5)
            submit_btn.click()
            _random_delay(1.5, 2.5)
            return True

        next_btn = page.query_selector(SEL_NEXT)
        if next_btn and next_btn.is_visible():
            next_btn.click()
            continue

        print(f'[Apply] Paso {step+1}: sin botón siguiente ni submit.')
        break

    return False


def apply_to_job(job: dict) -> tuple[bool, str]:
    """
    Aplica a una oferta de LinkedIn usando Easy Apply.
    Devuelve (success: bool, reason: str).
    """
    if not LINKEDIN_COOKIE:
        return False, 'LINKEDIN_COOKIE no configurada'

    cover_letter = job.get('cover_letter', '')
    cv_text = ''
    try:
        from ai_assistant import CV_TEXTS
        cv_text = CV_TEXTS.get(job.get('cv_name', 'mozo'), '')
    except Exception:
        pass

    try:
        with sync_playwright() as p:
            browser, context = _setup_context(p)
            page = context.new_page()

            page.goto(job['url'], timeout=20000)
            _random_delay(1.5, 3.0)

            if page.query_selector(SEL_ALREADY):
                browser.close()
                return False, 'Ya aplicado anteriormente'

            try:
                easy_btn = page.wait_for_selector(SEL_EASY_APPLY, timeout=6000)
            except PWTimeout:
                browser.close()
                return False, 'Easy Apply no disponible en esta oferta'

            easy_btn.click()
            _random_delay(1.5, 2.5)

            success = _navigate_form(page, cover_letter, cv_text)

            try:
                dismiss = page.query_selector(SEL_DISMISS)
                if dismiss:
                    dismiss.click()
            except Exception:
                pass

            browser.close()

            if success:
                print(f'[Apply] ✅ Aplicado: {job["title"]} — {job["company"]}')
                return True, ''
            else:
                print(f'[Apply] ⚠️ Formulario no completado: {job["title"]}')
                return False, 'Formulario no completado'

    except Exception as e:
        print(f'[Apply] Error en {job["title"]}: {e}')
        return False, str(e)


def run_auto_apply(jobs: list) -> list[dict]:
    """
    Recorre la lista de jobs e intenta aplicar a los de LinkedIn con Easy Apply.
    Devuelve lista de dicts: {'job': job_dict, 'applied': bool, 'reason': str}
    """
    if not LINKEDIN_COOKIE:
        print('[Apply] LINKEDIN_COOKIE no configurada — auto-apply desactivado.')
        return []

    results = []
    applied_count = 0

    for job in jobs:
        if applied_count >= MAX_APPLIES_PER_RUN:
            print(f'[Apply] Límite de {MAX_APPLIES_PER_RUN} candidaturas alcanzado.')
            break

        if job.get('source') != 'LinkedIn':
            continue
        if not job.get('cv_name'):
            continue

        success, reason = apply_to_job(job)
        results.append({'job': job, 'applied': success, 'reason': reason})

        if success:
            applied_count += 1
            _random_delay(8, 15)

    print(f'[Apply] Sesión completada: {applied_count} candidaturas enviadas.')
    return results
