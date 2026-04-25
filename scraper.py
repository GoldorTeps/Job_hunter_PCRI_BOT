import time
import hashlib

import feedparser
import requests
from bs4 import BeautifulSoup

from config import BLACKLIST, LOCATION, RADIUS_KM, PROVINCE, SEARCHES

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'es-ES,es;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

def _job_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:20]

def _is_blacklisted(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BLACKLIST)

def _clean(text: str) -> str:
    return ' '.join(text.split()) if text else ''


# ── Indeed (RSS) ───────────────────────────────────────────────────────────
def scrape_indeed(keyword: str, category: str) -> list:
    jobs = []
    url = (
        f'https://es.indeed.com/rss'
        f'?q={keyword.replace(" ", "+")}'
        f'&l={LOCATION.replace(" ", "+")}'
        f'&radius={RADIUS_KM}'
        f'&sort=date'
    )
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title   = _clean(entry.get('title', ''))
            company = _clean(entry.get('author', 'Empresa'))
            link    = entry.get('link', '')
            summary = _clean(entry.get('summary', ''))
            loc     = _clean(entry.get('indeed_city', LOCATION))

            if not title or not link:
                continue
            if _is_blacklisted(title + ' ' + summary):
                continue

            jobs.append({
                'id':       _job_id(link),
                'title':    title,
                'company':  company,
                'location': loc,
                'url':      link,
                'category': category,
                'source':   'Indeed',
                'summary':  summary[:220],
            })
    except Exception as e:
        print(f'[Indeed] Error "{keyword}": {e}')
    return jobs


# ── InfoJobs ───────────────────────────────────────────────────────────────
def scrape_infojobs(keyword: str, category: str) -> list:
    jobs = []
    url = (
        f'https://www.infojobs.net/jobsearch/search-results/list.xhtml'
        f'?keyword={keyword.replace(" ", "+")}'
        f'&province={PROVINCE}'
        f'&sortBy=PUBLICATION_DATE'
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')

        for item in soup.select('li[data-jobad-id], .ij-OfferList-item')[:12]:
            title_el   = item.select_one('h2 a, .ij-OfferList-item-title a, h3 a')
            company_el = item.select_one('.ij-OfferList-item-company, .company-name')
            loc_el     = item.select_one('.ij-OfferList-item-location, .location')

            if not title_el:
                continue

            title   = _clean(title_el.get_text())
            company = _clean(company_el.get_text()) if company_el else 'Empresa'
            loc     = _clean(loc_el.get_text()) if loc_el else 'Málaga'
            href    = title_el.get('href', '')
            link    = href if href.startswith('http') else f'https://www.infojobs.net{href}'

            if not title or _is_blacklisted(title):
                continue

            jobs.append({
                'id':       _job_id(link),
                'title':    title,
                'company':  company,
                'location': loc,
                'url':      link,
                'category': category,
                'source':   'InfoJobs',
                'summary':  '',
            })
    except Exception as e:
        print(f'[InfoJobs] Error "{keyword}": {e}')
    return jobs


# ── Turijobs ───────────────────────────────────────────────────────────────
def scrape_turijobs(keyword: str, category: str) -> list:
    jobs = []
    url = (
        f'https://www.turijobs.com/ofertas-trabajo/malaga'
        f'?keywords={keyword.replace(" ", "+")}'
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')

        selectors = [
            'article.job-item', '.offer-card', 'li.js-offer',
            'div[data-offer-id]', '.job-list-item',
        ]
        items = []
        for sel in selectors:
            items = soup.select(sel)
            if items:
                break

        for item in items[:12]:
            title_el   = item.select_one('h2, h3, .job-title, .offer-title')
            company_el = item.select_one('.company, .company-name, .employer-name')
            loc_el     = item.select_one('.location, .job-location, .city')
            link_el    = item.select_one('a[href]')

            if not title_el or not link_el:
                continue

            title   = _clean(title_el.get_text())
            company = _clean(company_el.get_text()) if company_el else 'Empresa'
            loc     = _clean(loc_el.get_text()) if loc_el else 'Málaga'
            href    = link_el.get('href', '')
            link    = href if href.startswith('http') else f'https://www.turijobs.com{href}'

            if not title or _is_blacklisted(title):
                continue

            jobs.append({
                'id':       _job_id(link),
                'title':    title,
                'company':  company,
                'location': loc,
                'url':      link,
                'category': category,
                'source':   'Turijobs',
                'summary':  '',
            })
    except Exception as e:
        print(f'[Turijobs] Error "{keyword}": {e}')
    return jobs


# ── Orquestador ────────────────────────────────────────────────────────────
def run_all_searches() -> list:
    from scraper_linkedin import scrape_all_linkedin

    all_jobs = []

    for search in SEARCHES:
        cat = search['category']

        for kw in search['indeed'][:2]:
            all_jobs += scrape_indeed(kw, cat)
            time.sleep(1.2)

        for kw in search['infojobs'][:1]:
            all_jobs += scrape_infojobs(kw, cat)
            time.sleep(1.5)

        for kw in search['turijobs'][:2]:
            all_jobs += scrape_turijobs(kw, cat)
            time.sleep(1.2)

    # LinkedIn (endpoint público, sin login)
    all_jobs += scrape_all_linkedin()

    # Eliminar duplicados por ID
    seen_ids = set()
    unique = []
    for job in all_jobs:
        if job['id'] not in seen_ids:
            seen_ids.add(job['id'])
            unique.append(job)

    print(f'[Scraper] {len(unique)} ofertas únicas encontradas.')
    return unique
