# Pico y Placa — Selector Strategy

> **Status**: Build-time documented, runtime heuristic fallback
> **Last inspection**: Not yet performed (requires live HTTP access to target pages)
> **Change**: `2026-06-10-pico-y-placa-bucaramanga`

## Target URLs

| Source | URL | Role |
|--------|-----|------|
| Primary | `https://bucaramanga.gov.co/noticias/?s=pico+y+placa` | Alcaldía news search — structured HTML, digits spelled out in article titles/bodies |
| Fallback | `https://sistemadebusqueda.bucaramanga.gov.co` | AMB norm search system — canonical Resoluciones, HTML shape less stable |

## Locked Selectors (to be filled after live inspection)

> **⚠️ CRITICAL**: The selectors below are PLACEHOLDERS. They MUST be verified against live HTML before the scraper is deployed to production. The heuristic fallback (below) provides a safety net.

### Primary Source (Alcaldía news page)

```python
# PLACEHOLDER — verify against live HTML
ARTICLE_LIST_SELECTOR = "article.news-item, div.article-listing article, .search-results article"
ARTICLE_TITLE_SELECTOR = "h2 a, .title a, h3 a"
ARTICLE_BODY_SELECTOR = ".content p, .entry-content p, .article-body p"
ARTICLE_DATE_SELECTOR = "time, .date, .meta time"
```

### Fallback Source (AMB norm search)

```python
# PLACEHOLDER — verify against live HTML
AMB_RESULT_SELECTOR = ".resultado-busqueda, .search-result-item"
AMB_TITLE_SELECTOR = "h3 a, .result-title a"
AMB_BODY_SELECTOR = ".result-snippet, .result-body"
```

## Runtime Heuristic Fallback

When CSS selectors fail to produce results (page structure changed), the scraper falls back to a content-based heuristic:

### Article-Level Heuristics

1. **Keyword presence**: Article title or body contains `pico y placa` (case-insensitive).
2. **Date filter**: Article date ≥ 2022-01-01. Articles from 2020 or 2021 are rejected (Pico y Placa ambiental era).
3. **Negative keyword**: Article body containing `Pico y Placa ambiental` (case-insensitive) is rejected.
4. **Recency**: Prefer the most recent article that passes all filters.

### Digit Extraction Heuristic

Search article text for digit-pair patterns associated with weekdays:

```
Pattern: digit_pair ("y" | "e" | ",") digit_pair
Examples: "5 y 6", "7 y 8", "9, 0", "1 e 2"
```

Weekday assignment is done positionally from the order found in text:
- First pair → Monday
- Second pair → Tuesday
- ...etc.

If fewer than 5 pairs are found, the article is rejected.

### Date Range Extraction

Search for date patterns within 6 months of the article publication date:
- `YYYY-MM-DD` to `YYYY-MM-DD`
- `del DD de MES al DD de MES de YYYY`
- `vigencia: MES YYYY`

### Saturday Calendar

Search for a separate block with per-week Saturday assignments:
- Pattern: `sábado.*semana \d.*(\d+)\s*y\s*(\d+)` or
- ISO week number → digit pair mapping

## Edge Cases

| Case | Behavior |
|------|----------|
| No article passes date/keyword filter | Fall back to AMB source |
| AMB also fails | Exit non-zero (fail-safe, per REQ-RD-007) |
| Article found but digit extraction fails | Log warning, try next article |
| Saturday calendar not found in article | Log warning, use conservative default (restricted=true for all Saturdays) |

## Verification Checklist

- [ ] Inspect primary source live HTML and lock selectors
- [ ] Inspect fallback source live HTML and lock selectors
- [ ] Verify heuristic extracts correct Q2 2026 digits
- [ ] Verify Saturday calendar format on current rotation article
- [ ] Test with a known 2020/2021 article to confirm date filter
- [ ] Test with "Pico y Placa ambiental" article to confirm keyword filter
