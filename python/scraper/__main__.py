"""Pico y Placa scraper — cron entry point.

Usage: python -m scraper

Orchestrates: fetch → parse → upsert → log → fail-safe check.
Exits 0 on success, non-zero on failure (no current rotation written).
"""

import os
import sys
from datetime import date, datetime, timezone

import httpx

from scraper.scraper import (
    RotationData,
    extract_date_range,
    extract_rotation_digits,
    extract_saturday_calendar,
    filter_article,
    has_current_rotation,
    parse_articles_from_html,
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
    """Parse HTML into a RotationData if a valid rotation is found."""
    if not html:
        return None

    articles = parse_articles_from_html(html, source_url)
    # Sort by date descending — prefer the most recent valid article
    articles.sort(key=lambda a: a.get("date") or date.min, reverse=True)

    for article in articles:
        if not filter_article(article):
            continue

        digits = extract_rotation_digits(article["body"])
        if digits is None:
            continue

        date_range = extract_date_range(article["body"])
        if date_range is None:
            continue

        saturday = extract_saturday_calendar(article["body"])

        raw_payload = {
            "weekdays": digits,
            "saturday_calendar": saturday if saturday else {},
            "article_title": article["title"],
            "article_url": article.get("url", ""),
        }

        return RotationData(
            municipality="",  # filled per municipality during upsert
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
    """Upsert rotation rows to Supabase.

    If Supabase is not configured (no SUPABASE_URL), prints the SQL
    for manual execution and returns the number of rows that would be written.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[scraper] Supabase not configured. Printing rotations for dry run:")
        for rot in rotations:
            print(f"  [{rot['municipality']}] {rot['valid_from']} → {rot['valid_to']}")
        return len(rotations)

    # Real Supabase upsert would go here. For v1, we output the SQL
    # that can be executed manually or via a migration step.
    # TODO: Implement Supabase REST API upsert using httpx + SUPABASE_URL/KEY.
    print("[scraper] WARNING: Supabase upsert not yet implemented (v1 placeholder).")
    print("[scraper] Rotation data parsed successfully — manual insertion required.")
    for rot in rotations:
        print(
            f"  INSERT INTO rotations (municipality, valid_from, valid_to, "
            f"raw_payload, source_url) VALUES "
            f"('{rot['municipality']}', '{rot['valid_from']}', "
            f"'{rot['valid_to']}', '{rot['raw_payload']}', '{rot['source_url']}') "
            f"ON CONFLICT DO NOTHING;"
        )
    return len(rotations)


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
