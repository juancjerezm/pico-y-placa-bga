"""Tests for the Pico y Placa scraper module.

Strict TDD: tests written BEFORE implementation (RED phase).
Uses HTML fixtures for parsing tests, pure functions for logic tests.
"""

from datetime import date

# ── RED phase: these imports will fail until scraper.py is created ──────────
from scraper.scraper import (  # type: ignore[import-untyped]
    RotationData,
    extract_date_range,
    extract_rotation_digits,
    extract_saturday_calendar,
    filter_article,
    has_current_rotation,
    needs_upsert,
    parse_articles_from_html,
)

# ═══════════════════════════════════════════════════════════════════════════════
# HTML Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

VALID_ROTATION_HTML = """<!DOCTYPE html>
<html><head><title>Noticias — Alcaldía de Bucaramanga</title></head>
<body>
<main class="search-results">
  <article class="news-item">
    <h2 class="title"><a href="/noticias/pico-y-placa-segundo-semestre-2026/">
      Pico y Placa para el segundo semestre de 2026 en Bucaramanga
    </a></h2>
    <div class="meta">
      <time datetime="2026-03-15">15 de marzo de 2026</time>
    </div>
    <div class="content">
      <p>La Alcaldía de Bucaramanga informa que el Pico y Placa para el
      segundo semestre de 2026 regirá a partir del <strong>1 de julio de 2026</strong>
      hasta el <strong>31 de diciembre de 2026</strong>.</p>
      <p>Los dígitos por día son: lunes 5 y 6, martes 7 y 8,
      miércoles 9 y 0, jueves 1 y 2, viernes 3 y 4.</p>
      <p>Para los sábados, el calendario semanal es: primera semana 1 y 2,
      segunda semana 3 y 4, tercera semana 5 y 6, cuarta semana 7 y 8.</p>
    </div>
  </article>
</main>
</body></html>"""

AMBIENTAL_ARTICLE_HTML = """<!DOCTYPE html>
<html><head><title>Noticias — Alcaldía de Bucaramanga</title></head>
<body>
<main class="search-results">
  <article class="news-item">
    <h2 class="title"><a href="/noticias/pico-y-placa-ambiental-2023/">
      Pico y Placa ambiental para mejorar la calidad del aire
    </a></h2>
    <div class="meta">
      <time datetime="2023-02-10">10 de febrero de 2023</time>
    </div>
    <div class="content">
      <p>La Alcaldía anuncia el Pico y Placa ambiental que regirá
      durante la temporada seca. Los dígitos son: lunes 1 y 2,
      martes 3 y 4, miércoles 5 y 6, jueves 7 y 8, viernes 9 y 0.</p>
    </div>
  </article>
</main>
</body></html>"""

OLD_ARTICLE_2020_HTML = """<!DOCTYPE html>
<html><head><title>Noticias — Alcaldía de Bucaramanga</title></head>
<body>
<main class="search-results">
  <article class="news-item">
    <h2 class="title"><a href="/noticias/pico-y-placa-2020/">
      Pico y Placa para el primer semestre de 2020
    </a></h2>
    <div class="meta">
      <time datetime="2020-01-10">10 de enero de 2020</time>
    </div>
    <div class="content">
      <p>Los dígitos del Pico y Placa para 2020 son: lunes 1 y 2,
      martes 3 y 4, miércoles 5 y 6, jueves 7 y 8, viernes 9 y 0.</p>
    </div>
  </article>
</main>
</body></html>"""

MIXED_PAGE_HTML = f"""<!DOCTYPE html>
<html><head><title>Noticias — Resultados de búsqueda</title></head>
<body>
<main class="search-results">
  {OLD_ARTICLE_2020_HTML.split('<body>')[1].split('</body>')[0]}
  {AMBIENTAL_ARTICLE_HTML.split('<body>')[1].split('</body>')[0]}
  {VALID_ROTATION_HTML.split('<body>')[1].split('</body>')[0]}
</main>
</body></html>"""

NO_DIGITS_HTML = """<!DOCTYPE html>
<html><head><title>Noticias</title></head>
<body>
<main class="search-results">
  <article class="news-item">
    <h2 class="title"><a href="/noticias/evento-cultural/">
      Evento cultural en el Parque Santander
    </a></h2>
    <div class="meta">
      <time datetime="2026-05-01">1 de mayo de 2026</time>
    </div>
    <div class="content">
      <p>La Alcaldía invita a todos los ciudadanos al evento cultural
      del fin de semana. No tiene relación con Pico y Placa.</p>
    </div>
  </article>
</main>
</body></html>"""

SATURDAY_CALENDAR_HTML = """<!DOCTYPE html>
<html><body>
<article>
  <h2>Pico y Placa sábados — Calendario</h2>
  <div class="content">
    <p>Calendario de Pico y Placa para sábados del segundo semestre 2026:</p>
    <table>
      <tr><th>Semana</th><th>Dígitos</th></tr>
      <tr><td>Semana 1</td><td>1 y 2</td></tr>
      <tr><td>Semana 2</td><td>3 y 4</td></tr>
      <tr><td>Semana 3</td><td>5 y 6</td></tr>
      <tr><td>Semana 4</td><td>7 y 8</td></tr>
    </table>
  </div>
</article>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# filter_article — REQ-RD-004 date filter + negative keyword
# ═══════════════════════════════════════════════════════════════════════════════


class TestFilterArticle:
    """Article-level filtering: date >= 2022, negative keyword rejection."""

    def test_rejects_article_before_2022(self) -> None:
        """GIVEN an article dated 2020-03-15
        WHEN filter_article is called
        THEN the article is rejected."""
        article = {
            "title": "Pico y Placa 2020",
            "body": "Dígitos del Pico y Placa para 2020: lunes 1 y 2...",
            "date": date(2020, 3, 15),
            "url": "/noticias/2020/",
        }
        assert filter_article(article) is False

    def test_accepts_article_from_2022_boundary(self) -> None:
        """GIVEN an article dated 2022-01-01
        WHEN filter_article is called
        THEN the article is accepted (boundary included)."""
        article = {
            "title": "Pico y Placa 2022",
            "body": "Rotación vigente desde enero 2022.",
            "date": date(2022, 1, 1),
            "url": "/noticias/2022/",
        }
        assert filter_article(article) is True

    def test_accepts_article_from_2026(self) -> None:
        """GIVEN an article dated in 2026
        WHEN filter_article is called
        THEN the article is accepted."""
        article = {
            "title": "Pico y Placa segundo semestre 2026",
            "body": "Dígitos: lunes 5 y 6, martes 7 y 8...",
            "date": date(2026, 3, 15),
            "url": "/noticias/2026/",
        }
        assert filter_article(article) is True

    def test_rejects_pico_y_placa_ambiental_keyword(self) -> None:
        """GIVEN a 2023 article body contains 'Pico y Placa ambiental'
        WHEN filter_article is called
        THEN the article is rejected."""
        article = {
            "title": "Medidas ambientales",
            "body": "El Pico y Placa ambiental regirá durante febrero...",
            "date": date(2023, 2, 1),
            "url": "/noticias/ambiental/",
        }
        assert filter_article(article) is False

    def test_rejects_pico_y_placa_ambiental_in_title(self) -> None:
        """GIVEN the article title contains 'Pico y Placa ambiental'
        WHEN filter_article is called
        THEN the article is rejected (searched in both title and body)."""
        article = {
            "title": "Pico y Placa ambiental entra en vigor",
            "body": "Rotación para mejorar calidad del aire.",
            "date": date(2023, 2, 1),
            "url": "/noticias/ambiental-titulo/",
        }
        assert filter_article(article) is False

    def test_rejects_both_date_and_keyword_fail(self) -> None:
        """GIVEN a 2020 article about Pico y Placa ambiental
        WHEN filter_article is called
        THEN the article is rejected (either filter is sufficient)."""
        article = {
            "title": "Pico y Placa ambiental 2020",
            "body": "Medida ambiental para el área metropolitana.",
            "date": date(2020, 6, 1),
            "url": "/noticias/ambiental-2020/",
        }
        assert filter_article(article) is False

    def test_accepts_article_with_pico_y_placa_but_not_ambiental(self) -> None:
        """GIVEN a 2024 article body mentions 'pico y placa' but NOT 'ambiental'
        WHEN filter_article is called
        THEN the article is accepted."""
        article = {
            "title": "Nuevo Pico y Placa para 2024",
            "body": "Se establece el nuevo esquema de Pico y Placa...",
            "date": date(2024, 1, 15),
            "url": "/noticias/2024/",
        }
        assert filter_article(article) is True


# ═══════════════════════════════════════════════════════════════════════════════
# extract_rotation_digits — REQ-RD-004 digit pair extraction
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractRotationDigits:
    """Extract weekday → digit-pairs from article text."""

    WEEKDAY_TEXT = (
        "lunes 5 y 6, martes 7 y 8, miércoles 9 y 0, "
        "jueves 1 y 2, viernes 3 y 4"
    )

    def test_extracts_all_five_weekdays(self) -> None:
        """GIVEN text with 5 weekday digit pairs
        WHEN extract_rotation_digits is called
        THEN returns dict with 5 entries, correct mappings."""
        result = extract_rotation_digits(self.WEEKDAY_TEXT)
        assert result is not None
        assert len(result) == 5
        assert result["lunes"] == [5, 6]
        assert result["martes"] == [7, 8]
        assert result["miércoles"] == [9, 0]
        assert result["jueves"] == [1, 2]
        assert result["viernes"] == [3, 4]

    def test_extracts_with_e_conjunction(self) -> None:
        """GIVEN text uses 'e' conjunction ('1 e 2') with all 5 weekdays
        WHEN extract_rotation_digits is called
        THEN digits are correctly extracted."""
        text = (
            "lunes 1 e 2, martes 3 e 4, miércoles 5 e 6, "
            "jueves 7 e 8, viernes 9 e 0"
        )
        result = extract_rotation_digits(text)
        assert result is not None
        assert result["lunes"] == [1, 2]
        assert result["miércoles"] == [5, 6]

    def test_extracts_with_comma_separator(self) -> None:
        """GIVEN digits separated by comma ('9, 0') with all 5 weekdays
        WHEN extract_rotation_digits is called
        THEN digits are correctly extracted."""
        text = (
            "lunes 1, 2, martes 3, 4, miércoles 5, 6, "
            "jueves 7, 8, viernes 9, 0"
        )
        result = extract_rotation_digits(text)
        assert result is not None
        assert result["miércoles"] == [5, 6]

    def test_returns_none_when_fewer_than_5_pairs(self) -> None:
        """GIVEN text with only 2 weekday pairs
        WHEN extract_rotation_digits is called
        THEN returns None (insufficient data)."""
        text = "lunes 5 y 6, martes 7 y 8"
        result = extract_rotation_digits(text)
        assert result is None

    def test_handles_uppercase_weekdays(self) -> None:
        """GIVEN text with uppercase weekdays
        WHEN extract_rotation_digits is called
        THEN weekdays are normalized and digits extracted."""
        text = "LUNES 5 Y 6, MARTES 7 Y 8, MIÉRCOLES 9 Y 0, JUEVES 1 Y 2, VIERNES 3 Y 4"
        result = extract_rotation_digits(text)
        assert result is not None
        assert result["lunes"] == [5, 6]

    def test_handles_weekday_variants(self) -> None:
        """GIVEN text uses 'miercoles' without accent and 'sabado'
        WHEN extract_rotation_digits is called
        THEN accented and unaccented forms are matched."""
        text = (
            "lunes 1 y 2, martes 3 y 4, miercoles 5 y 6, "
            "jueves 7 y 8, viernes 9 y 0"
        )
        result = extract_rotation_digits(text)
        assert result is not None
        assert result["miércoles"] == [5, 6]


# ═══════════════════════════════════════════════════════════════════════════════
# extract_date_range — REQ-RD-004
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractDateRange:
    """Extract valid_from / valid_to from article text."""

    def test_extracts_iso_like_range(self) -> None:
        """GIVEN text with '2026-07-01' to '2026-12-31' range
        WHEN extract_date_range is called
        THEN returns correct date tuple."""
        text = "vigencia: 2026-07-01 al 2026-12-31"
        result = extract_date_range(text)
        assert result is not None
        assert result == (date(2026, 7, 1), date(2026, 12, 31))

    def test_extracts_spanish_date_range(self) -> None:
        """GIVEN text with Spanish date format
        WHEN extract_date_range is called
        THEN dates are correctly parsed."""
        text = "del 1 de julio de 2026 hasta el 31 de diciembre de 2026"
        result = extract_date_range(text)
        assert result is not None
        assert result == (date(2026, 7, 1), date(2026, 12, 31))

    def test_returns_none_when_no_dates_found(self) -> None:
        """GIVEN text with no recognizable date range
        WHEN extract_date_range is called
        THEN returns None."""
        text = "El Pico y Placa sigue vigente hasta nuevo aviso."
        result = extract_date_range(text)
        assert result is None

    def test_extracts_single_month_range(self) -> None:
        """GIVEN text with 'enero a marzo de 2026'
        WHEN extract_date_range is called
        THEN dates are correctly derived."""
        text = "vigente de enero a marzo de 2026"
        result = extract_date_range(text)
        assert result is not None
        assert result[0] == date(2026, 1, 1)
        assert result[1] == date(2026, 3, 31)


# ═══════════════════════════════════════════════════════════════════════════════
# extract_saturday_calendar — REQ-RD-006
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractSaturdayCalendar:
    """Per-week Saturday calendar extraction."""

    def test_extracts_four_week_calendar(self) -> None:
        """GIVEN text with 4-week Saturday calendar
        WHEN extract_saturday_calendar is called
        THEN returns dict mapping week number to digit pair."""
        text = (
            "primera semana 1 y 2, segunda semana 3 y 4, "
            "tercera semana 5 y 6, cuarta semana 7 y 8"
        )
        result = extract_saturday_calendar(text)
        assert result is not None
        assert result == {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8]}

    def test_extracts_from_table_html(self) -> None:
        """GIVEN HTML text with Saturday calendar in a table
        WHEN extract_saturday_calendar is called
        THEN digits are extracted from table rows."""
        result = extract_saturday_calendar(SATURDAY_CALENDAR_HTML)
        assert result is not None
        assert len(result) == 4
        assert result[1] == [1, 2]
        assert result[4] == [7, 8]

    def test_returns_none_when_no_calendar_found(self) -> None:
        """GIVEN text with no Saturday calendar
        WHEN extract_saturday_calendar is called
        THEN returns None."""
        text = "Pico y Placa de lunes a viernes únicamente."
        result = extract_saturday_calendar(text)
        assert result is None

    def test_extracts_numeric_week_numbers(self) -> None:
        """GIVEN text with numeric week indicators ('semana 1', 'semana 2')
        WHEN extract_saturday_calendar is called
        THEN week numbers are parsed correctly."""
        text = "semana 1: 5 y 6 | semana 2: 7 y 8 | semana 3: 9 y 0 | semana 4: 1 y 2"
        result = extract_saturday_calendar(text)
        assert result is not None
        assert result == {1: [5, 6], 2: [7, 8], 3: [9, 0], 4: [1, 2]}


# ═══════════════════════════════════════════════════════════════════════════════
# needs_upsert — Idempotency check
# ═══════════════════════════════════════════════════════════════════════════════


class TestNeedsUpsert:
    """Idempotency: compare raw_payload to avoid duplicate writes."""

    EXISTING_PAYLOAD = {
        "weekdays": {"lunes": [5, 6], "martes": [7, 8]},
        "saturday_calendar": {1: [1, 2], 2: [3, 4]},
    }

    def test_needs_upsert_when_no_existing_payload(self) -> None:
        """GIVEN no existing payload
        WHEN needs_upsert is called
        THEN returns True (always write on first run)."""
        assert needs_upsert(None, {"weekdays": {"lunes": [1, 2]}}) is True

    def test_needs_upsert_when_payload_differs(self) -> None:
        """GIVEN existing and new payloads have different weekdays
        WHEN needs_upsert is called
        THEN returns True (data changed)."""
        new_payload = {
            "weekdays": {"lunes": [9, 0], "martes": [7, 8]},
            "saturday_calendar": {1: [1, 2], 2: [3, 4]},
        }
        assert needs_upsert(self.EXISTING_PAYLOAD, new_payload) is True

    def test_skips_upsert_when_payload_identical(self) -> None:
        """GIVEN existing and new payloads are identical
        WHEN needs_upsert is called
        THEN returns False (skip write)."""
        assert needs_upsert(self.EXISTING_PAYLOAD, self.EXISTING_PAYLOAD) is False

    def test_needs_upsert_when_saturday_calendar_differs(self) -> None:
        """GIVEN existing and new Saturday calendars differ
        WHEN needs_upsert is called
        THEN returns True."""
        new_payload = {
            "weekdays": {"lunes": [5, 6], "martes": [7, 8]},
            "saturday_calendar": {1: [5, 6], 2: [7, 8]},
        }
        assert needs_upsert(self.EXISTING_PAYLOAD, new_payload) is True

    def test_needs_upsert_when_new_has_extra_keys(self) -> None:
        """GIVEN new payload has an additional key not in existing
        WHEN needs_upsert is called
        THEN returns True (structure changed)."""
        new_payload = {
            "weekdays": {"lunes": [5, 6], "martes": [7, 8]},
            "saturday_calendar": {1: [1, 2], 2: [3, 4]},
            "notes": "Actualización Q3 2026",
        }
        assert needs_upsert(self.EXISTING_PAYLOAD, new_payload) is True


# ═══════════════════════════════════════════════════════════════════════════════
# has_current_rotation — REQ-RD-007 fail-safe
# ═══════════════════════════════════════════════════════════════════════════════


class TestHasCurrentRotation:
    """Fail-safe: verify at least one rotation covers today's date."""

    TODAY = date(2026, 6, 10)

    def test_returns_true_when_rotation_covers_today(self) -> None:
        """GIVEN a rotation from 2026-01-01 to 2026-12-31
        WHEN has_current_rotation is called for today
        THEN returns True."""
        rotations = [
            {
                "municipality": "bucaramanga",
                "valid_from": date(2026, 1, 1),
                "valid_to": date(2026, 12, 31),
                "raw_payload": {},
            }
        ]
        assert has_current_rotation(rotations, self.TODAY) is True

    def test_returns_false_when_rotation_expired(self) -> None:
        """GIVEN a rotation that ended before today
        WHEN has_current_rotation is called
        THEN returns False."""
        rotations = [
            {
                "municipality": "bucaramanga",
                "valid_from": date(2025, 1, 1),
                "valid_to": date(2025, 6, 30),
                "raw_payload": {},
            }
        ]
        assert has_current_rotation(rotations, self.TODAY) is False

    def test_returns_false_when_no_rotations(self) -> None:
        """GIVEN an empty rotation list
        WHEN has_current_rotation is called
        THEN returns False."""
        assert has_current_rotation([], self.TODAY) is False

    def test_today_on_valid_from_boundary_is_covered(self) -> None:
        """GIVEN a rotation starting exactly today
        WHEN has_current_rotation is called
        THEN returns True (inclusive boundary)."""
        rotations = [
            {
                "municipality": "bucaramanga",
                "valid_from": self.TODAY,
                "valid_to": date(2026, 12, 31),
                "raw_payload": {},
            }
        ]
        assert has_current_rotation(rotations, self.TODAY) is True

    def test_today_on_valid_to_boundary_is_covered(self) -> None:
        """GIVEN a rotation ending exactly today
        WHEN has_current_rotation is called
        THEN returns True (inclusive boundary per REQ-RD-001)."""
        rotations = [
            {
                "municipality": "bucaramanga",
                "valid_from": date(2026, 1, 1),
                "valid_to": self.TODAY,
                "raw_payload": {},
            }
        ]
        assert has_current_rotation(rotations, self.TODAY) is True


# ═══════════════════════════════════════════════════════════════════════════════
# parse_articles_from_html — HTML parsing integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseArticlesFromHtml:
    """Parse HTML into structured article dicts."""

    SOURCE_URL = "https://bucaramanga.gov.co/noticias/?s=pico+y+placa"

    def test_extracts_article_from_valid_html(self) -> None:
        """GIVEN HTML with a valid rotation article
        WHEN parse_articles_from_html is called
        THEN returns a list with one article dict containing title, body, date, url."""
        articles = parse_articles_from_html(VALID_ROTATION_HTML, self.SOURCE_URL)
        assert len(articles) >= 1
        article = articles[0]
        assert "Pico y Placa" in article["title"]
        assert "5 y 6" in article["body"]
        assert article["source_url"] == self.SOURCE_URL

    def test_article_date_is_parsed(self) -> None:
        """GIVEN HTML with a <time datetime='2026-03-15'> element
        WHEN parse_articles_from_html is called
        THEN the article date is correctly extracted."""
        articles = parse_articles_from_html(VALID_ROTATION_HTML, self.SOURCE_URL)
        assert len(articles) >= 1
        assert articles[0]["date"] == date(2026, 3, 15)

    def test_extracts_multiple_articles_from_mixed_page(self) -> None:
        """GIVEN HTML with 3 articles (2020, ambiental 2023, valid 2026)
        WHEN parse_articles_from_html is called
        THEN all 3 are extracted as raw article dicts (filtering happens separately)."""
        articles = parse_articles_from_html(MIXED_PAGE_HTML, self.SOURCE_URL)
        assert len(articles) == 3

    def test_no_articles_in_empty_page(self) -> None:
        """GIVEN HTML with no article elements
        WHEN parse_articles_from_html is called
        THEN returns empty list."""
        articles = parse_articles_from_html(
            "<html><body><p>No news today.</p></body></html>", self.SOURCE_URL
        )
        assert articles == []


# ═══════════════════════════════════════════════════════════════════════════════
# RotationData — data class
# ═══════════════════════════════════════════════════════════════════════════════


class TestRotationData:
    """RotationData dataclass holds one rotation row."""

    def test_creates_rotation_data_instance(self) -> None:
        """GIVEN all required fields
        WHEN RotationData is constructed
        THEN the instance has all fields accessible."""
        rd = RotationData(
            municipality="bucaramanga",
            valid_from=date(2026, 7, 1),
            valid_to=date(2026, 12, 31),
            raw_payload={"weekdays": {"lunes": [5, 6]}},
            source_url="https://bucaramanga.gov.co/noticias/rotacion-2026/",
        )
        assert rd.municipality == "bucaramanga"
        assert rd.valid_from == date(2026, 7, 1)
        assert rd.valid_to == date(2026, 12, 31)
        assert rd.raw_payload["weekdays"]["lunes"] == [5, 6]


# ═══════════════════════════════════════════════════════════════════════════════
# TRIANGULATE: Additional edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestFilterArticleEdgeCases:
    """Edge cases for article filtering."""

    def test_rejects_article_with_none_date(self) -> None:
        """GIVEN an article with date=None
        WHEN filter_article is called
        THEN the article is rejected (no date = cannot verify recency)."""
        article = {
            "title": "Pico y Placa",
            "body": "Rotación vigente.",
            "date": None,
            "url": "/noticias/",
        }
        assert filter_article(article) is False

    def test_rejects_article_with_string_date(self) -> None:
        """GIVEN an article with date as string instead of date object
        WHEN filter_article is called
        THEN the article is rejected (wrong type)."""
        article = {
            "title": "Pico y Placa",
            "body": "Rotación 2026.",
            "date": "2026-01-01",
            "url": "/noticias/",
        }
        assert filter_article(article) is False

    def test_ambiental_keyword_case_insensitive(self) -> None:
        """GIVEN article contains 'PICO Y PLACA AMBIENTAL' (uppercase)
        WHEN filter_article is called
        THEN rejected (case-insensitive match)."""
        article = {
            "title": "Noticias",
            "body": "Se establece el PICO Y PLACA AMBIENTAL para 2024.",
            "date": date(2024, 3, 1),
            "url": "/noticias/",
        }
        assert filter_article(article) is False


class TestExtractSaturdayCalendarEdgeCases:
    """Edge cases for Saturday calendar extraction."""

    def test_three_week_calendar_returns_partial(self) -> None:
        """GIVEN text with only 3 weeks of Saturday calendar
        WHEN extract_saturday_calendar is called
        THEN returns the 3 weeks (partial is better than nothing)."""
        text = "semana 1: 1 y 2 | semana 2: 3 y 4 | semana 3: 5 y 6"
        result = extract_saturday_calendar(text)
        assert result is not None
        assert len(result) == 3
        assert result[1] == [1, 2]

    def test_five_week_calendar(self) -> None:
        """GIVEN text with 5 weeks of Saturday calendar
        WHEN extract_saturday_calendar is called
        THEN returns all 5 weeks."""
        text = (
            "semana 1: 1 y 2, semana 2: 3 y 4, semana 3: 5 y 6, "
            "semana 4: 7 y 8, semana 5: 9 y 0"
        )
        result = extract_saturday_calendar(text)
        assert result is not None
        assert len(result) == 5

    def test_duplicate_week_keeps_last(self) -> None:
        """GIVEN text has duplicate week number entries
        WHEN extract_saturday_calendar is called
        THEN the last entry for a week number wins (overwrite)."""
        text = "semana 1: 1 y 2, semana 1: 9 y 0"
        result = extract_saturday_calendar(text)
        assert result is not None
        # Second entry for semana 1 overwrites the first
        assert result[1] == [9, 0]


class TestExtractDateRangeEdgeCases:
    """Edge cases for date range extraction."""

    def test_handles_hasta_keyword(self) -> None:
        """GIVEN text uses 'hasta' instead of 'al'
        WHEN extract_date_range is called
        THEN dates are correctly parsed."""
        text = "2026-01-01 hasta 2026-06-30"
        result = extract_date_range(text)
        assert result is not None
        assert result[0] == date(2026, 1, 1)
        assert result[1] == date(2026, 6, 30)

    def test_single_date_returns_none(self) -> None:
        """GIVEN text with single date but no range
        WHEN extract_date_range is called
        THEN returns None (need a range)."""
        text = "vigencia desde 2026-01-01"
        result = extract_date_range(text)
        assert result is None


class TestParseArticlesEdgeCases:
    """Edge cases for HTML article parsing."""

    def test_article_without_date_field(self) -> None:
        """GIVEN HTML article without <time> or .date elements
        WHEN parse_articles_from_html is called
        THEN article is still extracted with date=None."""
        html = """<html><body>
        <article>
            <h2><a href="/news/1">Título sin fecha</a></h2>
            <div class="content"><p>Texto del artículo.</p></div>
        </article>
        </body></html>"""
        articles = parse_articles_from_html(html, "https://example.com")
        assert len(articles) == 1
        assert articles[0]["date"] is None

    def test_article_without_title_but_has_body(self) -> None:
        """GIVEN HTML article with no heading elements
        WHEN parse_articles_from_html is called
        THEN article is still extracted (heuristic extraction)."""
        html = """<html><body>
        <article>
            <div class="content"><p>Pico y Placa: lunes 5 y 6.</p></div>
        </article>
        </body></html>"""
        articles = parse_articles_from_html(html, "https://example.com")
        assert len(articles) == 1
        assert "Pico y Placa" in articles[0]["body"]


class TestNeedsUpsertEdgeCases:
    """Edge cases for idempotency."""

    def test_empty_dicts_are_identical(self) -> None:
        """GIVEN both existing and new payloads are empty dicts
        WHEN needs_upsert is called
        THEN returns False."""
        assert needs_upsert({}, {}) is False

    def test_nested_diff_detected(self) -> None:
        """GIVEN payloads differ in a nested key
        WHEN needs_upsert is called
        THEN returns True."""
        existing = {"weekdays": {"lunes": [5, 6], "martes": [7, 8]}}
        new_payload = {"weekdays": {"lunes": [5, 6], "martes": [9, 0]}}
        assert needs_upsert(existing, new_payload) is True


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: full pipeline from HTML fixture to rotation data
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullPipelineIntegration:
    """End-to-end: HTML → articles → filtered → digits extracted."""

    def test_full_pipeline_yields_rotation(self) -> None:
        """GIVEN a valid HTML fixture with a current rotation article
        WHEN the full pipeline runs (parse → filter → extract)
        THEN a complete rotation can be assembled."""
        source = "https://bucaramanga.gov.co/noticias/?s=pico+y+placa"
        articles = parse_articles_from_html(VALID_ROTATION_HTML, source)
        assert len(articles) >= 1

        valid = [a for a in articles if filter_article(a)]
        assert len(valid) >= 1

        digits = extract_rotation_digits(valid[0]["body"])
        assert digits is not None
        assert len(digits) == 5

        date_range = extract_date_range(valid[0]["body"])
        assert date_range is not None

        saturday = extract_saturday_calendar(valid[0]["body"])
        assert saturday is not None
