import os
from openai import OpenAI

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))
    return _client


# ── Cargar CVs ─────────────────────────────────────────────────────────────
def _load_cv(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), 'cvs', f'{name}.txt')
    try:
        with open(path, encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return f'CV de {name} no disponible.'


CV_TEXTS = {
    'mozo':          _load_cv('mozo'),
    'admin':         _load_cv('admin'),
    'telemarketing': _load_cv('telemarketing'),
}

# Qué CV usar según la categoría del job
CATEGORY_CV = {
    '📦 Almacén':      'mozo',
    '🍽️ Hostelería':  'mozo',
    '🛵 Reparto':      'mozo',
    '📞 Telemarketing':'telemarketing',
}


def select_cv(job: dict) -> str | None:
    """Devuelve el nombre del CV o None si la categoría no está mapeada (→ descartar)."""
    return CATEGORY_CV.get(job.get('category', ''))   # None si no existe


def generate_cover_letter(job: dict, cv_name: str) -> str:
    """Genera una carta de presentación con guardarraíles estrictos contra invención."""
    if not os.getenv('OPENAI_API_KEY', ''):
        return ''

    cv_text = CV_TEXTS.get(cv_name, '')
    summary = job.get('summary') or 'No disponible'

    prompt = f"""Eres un asistente que escribe cartas de presentación en español.
Escribe una carta MUY BREVE (3-4 oraciones) para la oferta indicada.

REGLAS ESTRICTAS — incumplirlas invalida la respuesta:
1. USA SOLO la información que aparece en el CV del candidato.
2. NO inventes experiencia, habilidades, títulos ni datos que no estén en el CV.
3. NO añadas logros, cifras ni resultados que el CV no mencione.
4. Si el CV no tiene información relevante para el puesto, limítate a indicar disponibilidad inmediata e interés en el puesto.
5. Sin florituras, sin frases hechas, sin firma ni fecha.

=== CV DEL CANDIDATO (fuente única de verdad) ===
{cv_text[:1500]}

=== OFERTA ===
Puesto: {job['title']}
Empresa: {job['company']}
Descripción: {summary}

Responde ÚNICAMENTE con el cuerpo de la carta."""

    try:
        response = _get_client().chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=220,
            temperature=0.4,   # más bajo = menos inventiva
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f'[AI] Error generando carta: {e}')
        return ''


def enrich_job(job: dict) -> dict | None:
    """
    Enriquece el job con cv_name y cover_letter.
    Devuelve None si la categoría no tiene CV mapeado → señal de descartar.
    """
    cv_name = select_cv(job)
    if cv_name is None:
        print(f'[AI] Descartado (sin CV para categoría "{job.get("category")}"): {job["title"]}')
        return None

    job['cv_name']      = cv_name
    job['cover_letter'] = generate_cover_letter(job, cv_name)
    return job
