from __future__ import annotations

import re
import time
import unicodedata

import requests

USER_AGENT = "erasmusgravity/0.1 (Erasmus mobility study; contact: leo.palanca01@gmail.com)"
CITY_SITEMAP = "https://erasmusu.com/sitemaps/en/city-sitemap-1.xml"
BASE = "https://erasmusu.com/en/"

_RATING = re.compile(r"Rating:\s*([\d.]+)\s*of\s*10")
_COUNT = re.compile(r'ratingCount">(\d+)')
_FLAG = re.compile(r"flag-([a-z]{2})")


def norm_city(name: str | None) -> str | None:
    """Lowercase, strip accents, drop 'cedex' -- shared key with the flow cities."""
    if not name:
        return None
    s = str(name).lower().strip().replace("ß", "ss")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\bcedex\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _get(url: str, pause: float = 0.6, retries: int = 4) -> str | None:
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(retries):
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            time.sleep(pause)
            return r.text
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5.0 * (attempt + 1))
            continue
        return None
    return None


def city_slugs() -> list[str]:
    """Top-level city page slugs from the sitemap (skips sub-paths like /erasmus-universities)."""
    xml = _get(CITY_SITEMAP, pause=0)
    if not xml:
        return []
    slugs = re.findall(r"https://erasmusu\.com/en/(erasmus-[^<]+)", xml)
    out = []
    for s in slugs:
        m = re.fullmatch(r"erasmus-([^/]+)", s)  # exclude slugs with a sub-path
        if m:
            out.append(m.group(1))
    return out


def fetch_city_rating(slug: str, pause: float = 0.6) -> dict | None:
    """Return rating_10, n_opinions, country_code for a city slug, or None if no rating."""
    html = _get(BASE + "erasmus-" + slug, pause=pause)
    if not html:
        return None
    rating = _RATING.search(html)
    if not rating:
        return None
    count = _COUNT.search(html)
    flag = _FLAG.search(html)
    return {
        "slug": slug,
        "rating_10": float(rating.group(1)),
        "n_opinions": int(count.group(1)) if count else None,
        "country_code": flag.group(1).upper() if flag else None,
    }
