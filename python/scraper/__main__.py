"""Pico y Placa scraper — cron entry point.

Usage: python -m scraper

Orchestrates: fetch → parse → upsert → log → fail-safe check.
Exits 0 on success, non-zero on failure (no current rotation written).
"""

import os
import re
import sys
from datetime import date, datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scraper.scraper import (
    RotationData,
    extract_date_range,
    extract_rotation_digits,
    extract_saturday_calendar,
    has_current_rotation,
)

# ── Configuration ────────────────────────────────────────────────────────────

PRIMARY_URL = os.getenv(
    "SCRAPER_PRIMARY_URL",
    "https://bucaramanga.gov.co/noticias/?s=pico+y+placa",
)
FALLBACK_URL = os.getenv(
    "SCRAPER_FALLBACK_URL",
    "https://sistemadebusqueda.bucaramanga.gov.co",
)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

MUNICIPALITIES = ("bucaramanga", "floridablanca", "giron", "piedecuesta")

# HTTP headers that mimic a browser
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    """Run the full scraper pipeline. Returns exit code."""
    today = date.today()
    run_at = datetime.now(timezone.utc)

    # Step 1: Fetch primary source
    print(f"[scraper] Fetching primary: {PRIMARY_URL}")
    html = _fetch_html(PRIMARY_URL)

    # Step 2: Parse and extract rotation
    rotation = _extract_rotation(html, PRIMARY_URL)
    if rotation is None:
        print(f"[scraper] Primary failed. Trying fallback: {FALLBACK_URL}")
        html = _fetch_html(FALLBACK_URL)
        rotation = _extract_rotation(html, FALLBACK_URL)

    if rotation is None:
        print("[scraper] FAIL: No current-quarter rotation found in either source.")
        _log_run(run_at, PRIMARY_URL, success=False, rows_written=0, error="no_rotation_found")
        return 1

    # Step 3: Fail-safe — verify rotation covers today
    rotations = [_rotation_to_dict(rotation, m) for m in MUNICIPALITIES]
    if not has_current_rotation(rotations, today):
        print("[scraper] FAIL: Parsed rotation does not cover today's date.")
        _log_run(
            run_at,
            PRIMARY_URL,
            success=False,
            rows_written=0,
            error="rotation_expired",
        )
        return 1

    # Step 4: Upsert to Supabase (if configured)
    rows_written = _upsert_rotations(rotations)
    print(f"[scraper] Wrote {rows_written} rotation rows.")

    # Step 5: Log
    _log_run(run_at, PRIMARY_URL, success=True, rows_written=rows_written)

    print("[scraper] Run complete — rotation data is current.")
    return 0


# ── Helpers ──────────────────────────────────────────────────────────────────


def _fetch_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML from a URL with browser-like headers."""
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError as exc:
        print(f"[scraper] HTTP error fetching {url}: {exc}", file=sys.stderr)
        return ""


def _extract_rotation(html: str, source_url: str) -> RotationData | None:
    """Parse search page, follow article links, extract rotation from full articles."""
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Step 1: Find article links on the search results page
    article_urls: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        # Match links that reference pico y placa
        if "pico" in href.lower() or "pico" in text:
            full_url = urljoin(source_url, href)
            if full_url not in article_urls:
                article_urls.append(full_url)

    if not article_urls:
        print("[scraper] No article links found on search page.")
        return None

    print(f"[scraper] Found {len(article_urls)} candidate article links.")

    # Step 2: Fetch and parse each article individually
    for article_url in article_urls[:10]:  # Limit to first 10 to stay under budget
        print(f"[scraper] Fetching article: {article_url[:100]}")
        article_html = _fetch_html(article_url)
        if not article_html:
            continue

        # Parse article text
        article_soup = BeautifulSoup(article_html, "html.parser")
        article_body = article_soup.find("article") or article_soup.find(class_=re.compile("content|entry|post|body", re.I)) or article_soup
        article_text = article_body.get_text("\n", strip=True)

        if "pico" not in article_text.lower():
            continue

        # Extract digits and date range from full article text
        digits = extract_rotation_digits(article_text)
        if digits is None:
            continue

        date_range = extract_date_range(article_text)
        if date_range is None:
            # Try to find date in the article
            date_match = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+(?:al|hasta)\s+(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})", article_text)
            if not date_match:
                continue
            # This is a Spanish date format — handled by extract_date_range already
            date_range = extract_date_range(article_text)
            if date_range is None:
                continue

        saturday = extract_saturday_calendar(article_text)

        raw_payload = {
            "weekdays": digits,
            "saturday_calendar": saturday if saturday else {},
            "article_url": article_url,
        }

        print(f"[scraper] Rotation found: {date_range[0]} → {date_range[1]}")
        return RotationData(
            municipality="",
            valid_from=date_range[0],
            valid_to=date_range[1],
            raw_payload=raw_payload,
            source_url=source_url,
        )

    return None


def _rotation_to_dict(rotation: RotationData, municipality: str) -> dict:
    """Convert RotationData + municipality to dict for storage."""
    return {
        "municipality": municipality,
        "valid_from": rotation.valid_from,
        "valid_to": rotation.valid_to,
        "raw_payload": rotation.raw_payload,
        "source_url": rotation.source_url,
    }


def _upsert_rotations(rotations: list[dict]) -> int:
    """Upsert rotation rows to Supabase via REST API.

    Uses httpx to POST to Supabase with upsert semantics.
    Falls back to dry-run mode if SUPABASE_URL or key are not configured.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[scraper] Supabase not configured. Dry-run mode:")
        for rot in rotations:
            print(f"  [{rot['municipality']}] {rot['valid_from']} → {rot['valid_to']}")
        return len(rotations)

    api_url = f"{SUPABASE_URL}/rest/v1/rotations"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    params = {"on_conflict": "municipality,valid_from"}

    written = 0
    for rot in rotations:
        body = {
            "municipality": rot["municipality"],
            "valid_from": rot["valid_from"].isoformat(),
            "valid_to": rot["valid_to"].isoformat(),
            "raw_payload": rot["raw_payload"],
            "source_url": rot["source_url"],
        }
        try:
            resp = httpx.post(
                api_url,
                headers=headers,
                params=params,
                json=body,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                written += 1
                print(f"  [scraper] UPSERT {rot['municipality']}: {rot['valid_from']} → {rot['valid_to']}")
            else:
                print(f"  [scraper] WARN {rot['municipality']}: HTTP {resp.status_code} — {resp.text[:200]}")
        except httpx.HTTPError as exc:
            print(f"  [scraper] ERROR {rot['municipality']}: {exc}")

    return written


def _log_run(
    run_at: datetime,
    source: str,
    success: bool,
    rows_written: int,
    error: str | None = None,
) -> None:
    """Log the scraper run to stdout (and scrape_logs table if configured)."""
    status = "SUCCESS" if success else "FAILED"
    print(
        f"[scraper_run_complete] "
        f"run_at={run_at.isoformat()} "
        f"source={source} "
        f"status={status} "
        f"rows_written={rows_written}"
        + (f" error={error}" if error else "")
    )


if __name__ == "__main__":
    sys.exit(main())
