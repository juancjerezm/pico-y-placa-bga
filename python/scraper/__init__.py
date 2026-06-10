"""Scraper package — Pico y Placa data ingestion."""

from scraper.scraper import (
    RotationData,
    extract_date_range,
    extract_rotation_digits,
    extract_saturday_calendar,
    filter_article,
    has_current_rotation,
    needs_upsert,
    parse_articles_from_html,
)

__all__ = [
    "RotationData",
    "extract_date_range",
    "extract_rotation_digits",
    "extract_saturday_calendar",
    "filter_article",
    "has_current_rotation",
    "needs_upsert",
    "parse_articles_from_html",
]
