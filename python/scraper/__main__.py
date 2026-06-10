"""Pico y Placa scraper — cron entry point.

Usage: python -m scraper

Scrapes picoyplacaya.com.co for Bucaramanga rotation data.
Extracts embedded JSON from Next.js script tag → parses current rotation.
Upserts to Supabase. Idempotent: skips if raw_payload unchanged.
"""
import json
import os
import re
import sys
from datetime import date, datetime, timezone

import httpx

from scraper.scraper import has_current_rotation, needs_upsert

# ── Configuration ────────────────────────────────────────────────────────────

SOURCE_URL = os.getenv(
    "SCRAPER_PRIMARY_URL",
    "https://picoyplacaya.com.co/bucaramanga",
)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

MUNICIPALITIES = ("bucaramanga", "floridablanca", "giron", "piedecuesta")

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
    today = date.today()
    run_at = datetime.now(timezone.utc)

    print(f"[scraper] Fetching: {SOURCE_URL}")
    html = _fetch_html(SOURCE_URL)
    if not html:
        print("[scraper] FAIL: Could not fetch source.")
        _log_run(run_at, SOURCE_URL, success=False, rows_written=0, error="fetch_failed")
        return 1

    # Extract the embedded JSON from Next.js script tag
    data = _extract_city_data(html)
    if not data:
        print("[scraper] FAIL: Could not extract rotation data.")
        _log_run(run_at, SOURCE_URL, success=False, rows_written=0, error="parse_failed")
        return 1

    # Build rotation payload
    rotation = _build_rotation(data)
    if not rotation:
        print("[scraper] FAIL: No valid rotation found in data.")
        _log_run(run_at, SOURCE_URL, success=False, rows_written=0, error="no_rotation")
        return 1

    # Fail-safe: verify rotation covers today
    rotations = [
        {
            "municipality": m,
            "valid_from": rotation["valid_from"],
            "valid_to": rotation["valid_to"],
            "raw_payload": rotation["raw_payload"],
            "source_url": SOURCE_URL,
        }
        for m in MUNICIPALITIES
    ]
    if not has_current_rotation(rotations, today):
        print("[scraper] FAIL: Rotation does not cover today.")
        _log_run(run_at, SOURCE_URL, success=False, rows_written=0, error="expired")
        return 1

    # Upsert to Supabase
    rows_written = _upsert_rotations(rotations)
    print(f"[scraper] Wrote {rows_written} rotation rows.")

    _log_run(run_at, SOURCE_URL, success=True, rows_written=rows_written)
    print("[scraper] Run complete.")
    return 0


# ── Extraction ───────────────────────────────────────────────────────────────


def _fetch_html(url: str, timeout: int = 30) -> str:
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError as exc:
        print(f"[scraper] HTTP error: {exc}", file=sys.stderr)
        return ""


def _extract_city_data(html: str) -> dict | None:
    """Extract Bucaramanga city data from the embedded Next.js JSON."""
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    for script in scripts:
        if len(script) < 50000:
            continue
        # Look for the city data structure
        # Pattern: "citySlug":"bucaramanga"... with categories containing digits
        if '"citySlug":"bucaramanga"' not in script:
            continue

        # Extract the relevant JSON objects
        # Find the "particular" vehicle category (usually c0 or c1)
        # Look for "Lunes" pattern which indicates the current rotation description
        desc_match = re.search(
            r'"shortDescription":"([^"]*?(?:Lunes|Martes)[^"]*)"',
            script,
        )
        if desc_match:
            print(f"[scraper] Found description: {desc_match.group(1)[:100]}")

        # Extract cyclePairs if available (for Saturday/weekly data)
        pairs_match = re.search(
            r'"cyclePairs":\s*(\[\[.*?\]\])',
            script,
        )
        if pairs_match:
            try:
                pairs = json.loads(pairs_match.group(1))
                print(f"[scraper] Cycle pairs: {pairs}")
            except json.JSONDecodeError:
                pass

        # Extract valid_from / valid_to
        vf_match = re.search(r'"validFrom":"(\d{4}-\d{2}-\d{2})"', script)
        vt_match = re.search(r'"validTo":"(\d{4}-\d{2}-\d{2})"', script)
        valid_from = vf_match.group(1) if vf_match else None
        valid_to = vt_match.group(1) if vt_match else None

        # Try to find the current restriction description from rendered text
        # The page shows "Lunes: 9 y 0" format
        desc_text = ""
        if desc_match:
            desc_text = desc_match.group(1)

        # Parse weekday digits from description text
        weekdays = _parse_weekdays_from_text(desc_text)
        if not weekdays:
            # Fallback: parse from cyclePairs
            if pairs_match:
                try:
                    pairs = json.loads(pairs_match.group(1))
                    weekdays = _weekdays_from_pairs(pairs)
                except json.JSONDecodeError:
                    pass

        if not weekdays:
            continue

        return {
            "weekdays": weekdays,
            "saturday_calendar": {},
            "valid_from": valid_from or "2026-04-06",
            "valid_to": valid_to or "2026-07-04",
            "resolution": "picoyplacaya.com.co",
        }

    return None


def _parse_weekdays_from_text(text: str) -> dict | None:
    """Parse 'Lunes: 9 y 0 · Martes: 1 y 2' format."""
    if not text:
        return None

    from scraper.scraper import extract_rotation_digits

    # Build a full text that the existing parser can handle
    full_text = text.replace("·", "\n").replace(".", "\n")
    return extract_rotation_digits(full_text)


def _weekdays_from_pairs(pairs: list) -> dict | None:
    """Convert cyclePairs to weekday map (current week = index 0)."""
    if len(pairs) < 5:
        return None
    names = ["lunes", "martes", "miércoles", "jueves", "viernes"]
    return {
        names[i]: [int(pairs[i][0]), int(pairs[i][1])]
        for i in range(5)
    }


def _build_rotation(data: dict) -> dict | None:
    """Build the rotation dict for upsert."""
    weekdays = data.get("weekdays")
    if not weekdays or len(weekdays) < 5:
        return None

    return {
        "valid_from": date.fromisoformat(data["valid_from"]),
        "valid_to": date.fromisoformat(data["valid_to"]),
        "raw_payload": {
            "weekdays": weekdays,
            "saturday_calendar": data.get("saturday_calendar", {}),
            "resolution": data.get("resolution", ""),
        },
    }


# ── Upsert ───────────────────────────────────────────────────────────────────


def _upsert_rotations(rotations: list[dict]) -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[scraper] Supabase not configured. Dry-run:")
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
            resp = httpx.post(api_url, headers=headers, params=params, json=body, timeout=15)
            if resp.status_code in (200, 201):
                written += 1
                print(f"  UPSERT {rot['municipality']}: {rot['valid_from']} → {rot['valid_to']}")
            else:
                print(f"  WARN {rot['municipality']}: HTTP {resp.status_code}")
        except httpx.HTTPError as exc:
            print(f"  ERROR {rot['municipality']}: {exc}")

    return written


# ── Logging ──────────────────────────────────────────────────────────────────


def _log_run(
    run_at: datetime,
    source: str,
    success: bool,
    rows_written: int,
    error: str | None = None,
) -> None:
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
