"""
LinkedIn Jobs — endpoint público sin login.
Sin riesgo de bloqueo ni cuenta necesaria.
"""
import time
import hashlib

import requests
from bs4 import BeautifulSoup

from config import BLACKLIST, SEARCHES

BASE_URL = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'es-ES,es;q=0.9',
}

# Keywords específicas para LinkedIn por categoría
LINKEDIN_KEYWORDS = {
    '📦 Almacén':      ['mozo almacen', 'operario logistica', 'mozo almacén'],
    '🍽️ Hostelería':  ['camarero', 'ayudante cocina', 'recepcionista hotel'],
    '🛵 Reparto':      ['repartidor', 'conductor reparto'],
    '📞 Telemarketing':['teleoperador', 'agente call center', 'telemarketing'],
}

LOCATION = 'Torremolinos, Andalucía, España'


def _job_id(url: str) -> str:
    return 'li_' + hashlib.md5(url.encode()).hexdigest()[:18]


def _is_blacklisted(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BLACKLIST)


def _fetch_page(keyword: str, start: int = 0) -> list:
    """Llama al endpoint público y devuelve los jobs crudos en HTML."""
    params = {
        'keywords':  keyword,
        'location':  LOCATION,
        'f_TPR':     'r86400',   # últimas 24 horas
        'position':  1,
        'pageNum':   0,
        'start':     start,
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f'[LinkedIn] Error fetch "{keyword}": {e}')
        return ''


def _parse_jobs(html: str, category: str) -> list:
    """Parsea el HTML de la respuesta y extrae los jobs."""
    jobs = []
    soup = BeautifulSoup(html, 'html.parser')

    for card in soup.select('li')[:15]:
        title_el   = card.select_one('h3.base-search-card__title')
        company_el = card.select_one('h4.base-search-card__subtitle')
        loc_el     = card.select_one('span.job-search-card__location')
        link_el    = card.select_one('a.base-card__full-link, a[href*="/jobs/view/"]')

        if not title_el or not link_el:
            continue

        title   = title_el.get_text(strip=True)
        company = company_el.get_text(strip=True) if company_el else 'Empresa'
        loc     = loc_el.get_text(strip=True) if loc_el else LOCATION
        url     = link_el.get('href', '').split('?')[0]  # limpiar tracking params

        if not title or not url:
            continue
        if _is_blacklisted(title):
            continue

        jobs.append({
            'id':       _job_id(url),
            'title':    title,
            'company':  company,
            'location': loc,
            'url':      url,
            'category': category,
            'source':   'LinkedIn',
            'summary':  '',
        })

    return jobs


def scrape_linkedin_category(category: str) -> list:
    """Scrape todas las keywords de una categoría en LinkedIn."""
    keywords = LINKEDIN_KEYWORDS.get(category, [])
    jobs = []

    for kw in keywords[:2]:   # máx 2 keywords por categoría para no saturar
        html = _fetch_page(kw)
        if html:
            jobs += _parse_jobs(html, category)
        time.sleep(2)          # pausa respetuosa entre requests

    return jobs


def scrape_all_linkedin() -> list:
    """Scrape todas las categorías en LinkedIn."""
    all_jobs = []

    for category in LINKEDIN_KEYWORDS:
        all_jobs += scrape_linkedin_category(category)
        time.sleep(2)

    # Deduplicar por ID
    seen = set()
    unique = []
    for job in all_jobs:
        if job['id'] not in seen:
            seen.add(job['id'])
            unique.append(job)

    print(f'[LinkedIn] {len(unique)} ofertas únicas encontradas.')
    return unique
