"""Pico y Placa scraper — parse rotation data from HTML sources.

Pure-function module with no I/O side effects. HTML parsing via BeautifulSoup.
Supabase writes are handled by the orchestration layer (main entry point).
"""

import json
import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup, Tag

# ═══════════════════════════════════════════════════════════════════════════════
# Data model
# ═══════════════════════════════════════════════════════════════════════════════

_MUNICIPALITIES = ("bucaramanga", "floridablanca", "giron", "piedecuesta")

_WEEKDAY_NAMES = {
    "lunes",
    "martes",
    "miércoles",
    "miercoles",
    "jueves",
    "viernes",
    "sábado",
    "sabado",
}

# Normalized (unaccented) weekday map
_WEEKDAY_NORMALIZED = {
    "lunes": "lunes",
    "martes": "martes",
    "miércoles": "miércoles",
    "miercoles": "miércoles",
    "jueves": "jueves",
    "viernes": "viernes",
    "sábado": "sábado",
    "sabado": "sábado",
}

# Spanish month names → number
_MONTHS_ES: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# Last day per month (non-leap)
_MONTH_LAST_DAY: dict[int, int] = {
    1: 31,
    2: 28,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31,
}

_CUTOFF_DATE = date(2022, 1, 1)
_NEGATIVE_KEYWORD = "pico y placa ambiental"

# Regex patterns
_RE_DIGIT_PAIR_Y = re.compile(r"(\d+)\s*y\s*(\d+)")
_RE_DIGIT_PAIR_E = re.compile(r"(\d+)\s*e\s*(\d+)")
_RE_DIGIT_PAIR_COMMA = re.compile(r"(\d+)\s*,\s*(\d+)")
_RE_ISO_DATE_RANGE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+(?:al|a|hasta)\s+(\d{4}-\d{2}-\d{2})"
)
_RE_SPANISH_DATE_RANGE = re.compile(
    r"(?:a\s+partir\s+)?del\s+(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})\s+(?:al|a|hasta)\s+(?:el\s+)?"
    r"(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})",
    re.IGNORECASE,
)
_RE_SPANISH_MONTH_RANGE = re.compile(
    r"(?:vigente\s+)?(?:de\s+)?(\w+)\s+(?:a|hasta)\s+(\w+)\s+(?:de\s+)?(\d{4})",
    re.IGNORECASE,
)
_RE_WEEKDAY_DIGITS = re.compile(
    r"(?:"
    r"lunes\s+(\d+)\s*(?:y|e|,)\s*(\d+)"
    r"|martes\s+(\d+)\s*(?:y|e|,)\s*(\d+)"
    r"|mi[eé]rcoles\s+(\d+)\s*(?:y|e|,)\s*(\d+)"
    r"|jueves\s+(\d+)\s*(?:y|e|,)\s*(\d+)"
    r"|viernes\s+(\d+)\s*(?:y|e|,)\s*(\d+)"
    r")",
    re.IGNORECASE,
)

# Saturday calendar patterns
# Pattern 1: "semana N: D1 y D2" or "semana N D1 y D2"
_RE_SAT_WEEK_NUM = re.compile(
    r"semana\s*(\d+)\s*:?\s*(\d+)\s*(?:y|e|,)\s*(\d+)",
    re.IGNORECASE,
)
# Pattern 2: "primera semana D1 y D2" — ordinal word + "semana"
_RE_SAT_WEEK_WORD = re.compile(
    r"(primera|segunda|tercera|cuarta)\s+semana\s+(\d+)\s*(?:y|e|,)\s*(\d+)",
    re.IGNORECASE,
)
# Pattern 3: "primera semana: D1 y D2" — ordinal word + "semana" + colon + digits
_RE_SAT_WEEK_WORD_COLON = re.compile(
    r"(primera|segunda|tercera|cuarta)\s+semana\s*:?\s*(\d+)\s*(?:y|e|,)\s*(\d+)",
    re.IGNORECASE,
)

_WEEK_NUMBER_WORDS: dict[str, int] = {
    "primera": 1,
    "segunda": 2,
    "tercera": 3,
    "cuarta": 4,
}


@dataclass
class RotationData:
    """One rotation row per municipality."""

    municipality: str
    valid_from: date
    valid_to: date
    raw_payload: dict
    source_url: str


# ═══════════════════════════════════════════════════════════════════════════════
# Article filtering — REQ-RD-004 date & negative keyword
# ═══════════════════════════════════════════════════════════════════════════════


def filter_article(article: dict) -> bool:
    """Return True if the article passes all filters.

    Filters:
    1. Date >= 2022-01-01 (rejects pre-2022 articles)
    2. No 'Pico y Placa ambiental' in title or body
    """
    article_date = article.get("date")
    if article_date is None or not isinstance(article_date, date):
        return False
    if article_date < _CUTOFF_DATE:
        return False

    # Negative keyword: check both title and body
    search_text = f"{article.get('title', '')} {article.get('body', '')}".lower()
    if _NEGATIVE_KEYWORD in search_text:
        return False

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Digit extraction — REQ-RD-004
# ═══════════════════════════════════════════════════════════════════════════════


def extract_rotation_digits(text: str) -> dict[str, list[int]] | None:
    """Extract weekday→digit-pairs map from article text.

    Returns a dict with at least 5 entries (lunes..viernes), or None
    if insufficient pairs are found.
    """
    text_lower = text.lower()
    result: dict[str, list[int]] = {}

    matches = list(_RE_WEEKDAY_DIGITS.finditer(text_lower))
    for match in matches:
        groups = match.groups()
        # Each match has 10 groups (2 per weekday in order)
        for i, wd in enumerate(["lunes", "martes", "miércoles", "jueves", "viernes"]):
            d1_idx = i * 2
            d2_idx = i * 2 + 1
            if groups[d1_idx] is not None:
                result[wd] = [int(groups[d1_idx]), int(groups[d2_idx])]

    # Fallback: try line-by-line pair extraction
    if len(result) < 5:
        result = _extract_digits_line_by_line(text_lower)

    if len(result) < 5:
        return None

    return result


def _extract_digits_line_by_line(text: str) -> dict[str, list[int]]:
    """Extract weekday-digit pairs by scanning each line."""
    result: dict[str, list[int]] = {}
    weekday_order = ["lunes", "martes", "miércoles", "jueves", "viernes"]

    for wd in weekday_order:
        # Find the line/segment mentioning this weekday
        pattern = re.compile(
            rf"{wd}\s+(\d+)\s*(?:y|e|,)\s*(\d+)", re.IGNORECASE
        )
        m = pattern.search(text)
        if m:
            result[wd] = [int(m.group(1)), int(m.group(2))]

    return result


def _parse_digit_pair(text: str) -> list[int] | None:
    """Parse one digit pair from 'X y Y' or 'X e Y' or 'X, Y' form."""
    for pattern in (_RE_DIGIT_PAIR_Y, _RE_DIGIT_PAIR_E, _RE_DIGIT_PAIR_COMMA):
        m = pattern.search(text)
        if m:
            return [int(m.group(1)), int(m.group(2))]
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Date range extraction — REQ-RD-004
# ═══════════════════════════════════════════════════════════════════════════════


def extract_date_range(text: str) -> tuple[date, date] | None:
    """Extract (valid_from, valid_to) from article text.

    Supports:
    - ISO-like: '2026-07-01 al 2026-12-31'
    - Spanish long form: 'del 1 de julio de 2026 hasta el 31 de diciembre de 2026'
    - Month range: 'enero a marzo de 2026'
    """
    # Try ISO range first
    m = _RE_ISO_DATE_RANGE.search(text)
    if m:
        return (date.fromisoformat(m.group(1)), date.fromisoformat(m.group(2)))

    # Try Spanish long form
    m = _RE_SPANISH_DATE_RANGE.search(text)
    if m:
        d1, mes1, y1, d2, mes2, y2 = m.groups()
        m1 = _MONTHS_ES.get(mes1.lower())
        m2 = _MONTHS_ES.get(mes2.lower())
        if m1 and m2:
            return (date(int(y1), m1, int(d1)), date(int(y2), m2, int(d2)))

    # Try month range
    m = _RE_SPANISH_MONTH_RANGE.search(text)
    if m:
        from_month_str, to_month_str, year_str = m.groups()
        fm = _MONTHS_ES.get(from_month_str.lower())
        tm = _MONTHS_ES.get(to_month_str.lower())
        if fm and tm and year_str.isdigit():
            year = int(year_str)
            last_day = _MONTH_LAST_DAY.get(tm, 30)
            return (date(year, fm, 1), date(year, tm, last_day))

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Saturday calendar — REQ-RD-006
# ═══════════════════════════════════════════════════════════════════════════════


def extract_saturday_calendar(text: str) -> dict[int, list[int]] | None:
    """Extract per-week Saturday calendar from article text.

    Returns a dict mapping week number (1-4 or 1-5) to digit pair,
    or None if no calendar pattern is found.
    """
    result: dict[int, list[int]] = {}
    text_lower = text.lower()

    # Pattern 1: "semana N: D1 y D2" or "semana N D1 y D2"
    for m in _RE_SAT_WEEK_NUM.finditer(text_lower):
        week_num = int(m.group(1))
        d1, d2 = int(m.group(2)), int(m.group(3))
        result[week_num] = [d1, d2]

    # Pattern 2: "primera/segunda/tercera/cuarta semana D1 y D2"
    for m in _RE_SAT_WEEK_WORD.finditer(text_lower):
        week_num = _WEEK_NUMBER_WORDS.get(m.group(1).lower(), 0)
        d1, d2 = int(m.group(2)), int(m.group(3))
        if week_num:
            result[week_num] = [d1, d2]

    # Pattern 3: ordinal + "semana" + optional colon + digits
    for m in _RE_SAT_WEEK_WORD_COLON.finditer(text_lower):
        week_num = _WEEK_NUMBER_WORDS.get(m.group(1).lower(), 0)
        d1, d2 = int(m.group(2)), int(m.group(3))
        if week_num and week_num not in result:
            result[week_num] = [d1, d2]

    if len(result) >= 4:
        return dict(sorted(result.items()))

    # Fallback: scan for all "semana N" mentions independently
    table_result = _extract_saturday_from_table(text_lower)
    if table_result:
        result.update(table_result)

    if len(result) >= 4:
        return dict(sorted(result.items()))

    return None if not result else dict(sorted(result.items()))


def _resolve_week_number(token: str) -> int | None:
    """Convert 'primera', 'segunda', '1', etc. to integer week number."""
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return _WEEK_NUMBER_WORDS.get(token)


def _extract_saturday_from_table(text: str) -> dict[int, list[int]]:
    """Extract Saturday calendar from HTML table rows."""
    result: dict[int, list[int]] = {}
    # Pattern: semana N ... D1 y D2 (across any text structure)
    pattern = re.compile(
        r"(?:semana|primera|segunda|tercera|cuarta)\s*(\d+|[a-záéíóú]+)"
        r".*?"
        r"(\d+)\s*(?:y|e|,)\s*(\d+)",
        re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        week_token, d1, d2 = m.group(1), m.group(2), m.group(3)
        wn = _resolve_week_number(week_token)
        if wn is not None:
            result[wn] = [int(d1), int(d2)]
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Idempotency — compare raw_payload byte-equivalent
# ═══════════════════════════════════════════════════════════════════════════════


def needs_upsert(existing_payload: dict | None, new_payload: dict) -> bool:
    """Return True if the new payload differs from the existing one.

    Comparison is done via canonical JSON serialization (sorted keys).
    """
    if existing_payload is None:
        return True

    existing_json = _canonical_json(existing_payload)
    new_json = _canonical_json(new_payload)

    return existing_json != new_json


def _canonical_json(data: dict) -> str:
    """Serialize dict to canonical JSON string (sorted keys, no spaces)."""
    return json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


# ═══════════════════════════════════════════════════════════════════════════════
# Fail-safe — REQ-RD-007
# ═══════════════════════════════════════════════════════════════════════════════


def has_current_rotation(rotations: list[dict], today: date) -> bool:
    """Return True if at least one rotation covers today's date (inclusive)."""
    for rot in rotations:
        vf = rot.get("valid_from")
        vt = rot.get("valid_to")
        if isinstance(vf, date) and isinstance(vt, date):
            if vf <= today <= vt:
                return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# HTML parsing — BeautifulSoup
# ═══════════════════════════════════════════════════════════════════════════════

_ARTICLE_SELECTORS = [
    "article.news-item",
    "article",
    "div.article-listing article",
    ".search-results article",
    ".news-listing article",
]


def parse_articles_from_html(html: str, source_url: str) -> list[dict]:
    """Parse HTML page into a list of article dicts.

    Each article dict has: title, body, date, url, source_url.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles: list[dict] = []

    # Try CSS selector first, then fall back to direct tag scan
    article_tags = _find_article_tags(soup)
    for tag in article_tags:
        article = _parse_article_element(tag, source_url)
        if article:
            articles.append(article)

    return articles


def _find_article_tags(soup: BeautifulSoup) -> list[Tag]:
    """Find article elements using a cascade of selectors."""
    for selector in _ARTICLE_SELECTORS:
        tags = soup.select(selector)
        if tags:
            return tags  # type: ignore[return-value]
    return []


def _parse_article_element(tag: Tag, source_url: str) -> dict | None:
    """Extract title, body, date, and url from an article tag."""
    # Title: try h2 a, h3 a, then direct h2/h3 text
    title = ""
    title_link = tag.select_one("h2 a, h3 a, .title a")
    if title_link:
        title = title_link.get_text(" ", strip=True)
        url = title_link.get("href", "")
    else:
        heading = tag.select_one("h2, h3, .title")
        title = heading.get_text(" ", strip=True) if heading else ""
        url = ""

    # Body: collect all <p> text. Using get_text(separator=" ", strip=True)
    # ensures inline tags like <strong> don't merge adjacent text nodes
    # (e.g., "del<strong>1</strong>" → "del 1" instead of "del1").
    body_parts: list[str] = []
    for p in tag.select(".content p, .entry-content p, p"):
        body_parts.append(p.get_text(" ", strip=True))
    body = " ".join(body_parts)

    # Date: try <time datetime="">, then text patterns
    article_date = _extract_article_date(tag)

    if not title and not body:
        return None

    return {
        "title": title,
        "body": body,
        "date": article_date,
        "url": str(url) if url else "",
        "source_url": source_url,
    }


def _extract_article_date(tag: Tag) -> date | None:
    """Extract article date from HTML element.

    Tries:
    1. <time datetime="YYYY-MM-DD">
    2. <time> text content
    3. .date / .meta text content
    """
    time_tag = tag.select_one("time[datetime], time")
    if time_tag:
        dt_str = time_tag.get("datetime", "")
        if isinstance(dt_str, str) and dt_str:
            try:
                return date.fromisoformat(dt_str[:10])
            except ValueError:
                pass

    # Fallback: text-based date in meta divs
    for meta_sel in (".meta", ".date"):
        meta = tag.select_one(meta_sel)
        if meta:
            text = meta.get_text(strip=True)
            parsed = _parse_spanish_date_text(text)
            if parsed:
                return parsed

    return None


def _parse_spanish_date_text(text: str) -> date | None:
    """Try to parse a Spanish date from free text like '15 de marzo de 2026'."""
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})", text, re.IGNORECASE)
    if m:
        day_str, month_str, year_str = m.groups()
        month = _MONTHS_ES.get(month_str.lower())
        if month and year_str.isdigit():
            return date(int(year_str), month, int(day_str))
    return None
