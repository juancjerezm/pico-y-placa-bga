# Design: Pico y Placa Bucaramanga

**Approach**: Four chained PRs — plate parser (strict TDD), Supabase schema + scraper (HTML ingestion, re-verification on every cron run), Cloudflare Worker API (read-only, fail-safe 404), static frontend (Vite + vanilla JS + Motion One). All free-tier.

## Architecture Decisions

### Decision: Static Host

| Option | Free-tier constraint | Decision |
|--------|---------------------|----------|
| Vercel | 100 GB bandwidth, unlimited hobby builds | **Selected** |
| Netlify | 100 GB bandwidth, 300 build-min/month cap | Rejected |

Vercel wins on unlimited builds — no anxiety on frequent deploys. Edge caching integrates with the Worker backend without conflict.

### Decision: Motion Library

| Option | Bundle + license | Decision |
|--------|------------------|----------|
| Motion One | 3.8 KB gzipped, MIT | **Selected** |
| GSAP | 10 KB gzipped, premium plugins behind paywall | Rejected |
| anime.js | 8 KB, unmaintained since 2019 | Rejected |
| CSS-only | 0 KB, no state-transition orchestration | Rejected |

Motion One is smallest, tree-shakable, and covers the Hero digit-flip + Result slide-in required by REQ-FE-004.

### Decision: Cloudflare Worker Tooling

| Area | Choice | Rationale |
|------|--------|-----------|
| CLI | wrangler | Standard Worker tooling, free-tier |
| Language | TypeScript | Type safety at the API contract boundary |
| Postgres client | postgres.js | Smallest bundle; Supabase JS client includes realtime/auth — dead weight for read-only queries |

### Decision: Python Stack

| Area | Choice | Non-standard? Why justified |
|------|--------|---------------------------|
| Package manager | uv | Yes — lockfile reproducibility, CI caching speed, `uv run` replaces venv scripts. Faster than pip. |
| Formatter + Linter | ruff | ruff format + ruff check replaces black + flake8 + isort in one tool. |
| Type checker | mypy | Most mature, strict mode by default. |
| Test runner | pytest + pytest-cov | Per `openspec/config.yaml`. |

### Decision: Frontend Bundler

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Vite + vanilla JS | Dev server, HMR, vitest integration | **Selected** |
| Plain ES modules | Zero build, fragile test integration | Rejected |

Vitest is already declared in `config.yaml`; Vite provides seamless vitest integration and first-class `pnpm` support (REQ-FE-008).

## Data Flow

```
GitHub Actions (weekly cron, Mon 06:00 UTC)
  └─ scraper (uv + pytest)
       ├─ bucaramanga.gov.co/noticias/?s=pico+y+placa (primary)
       └─ sistemadebusqueda.bucaramanga.gov.co (fallback)
            │ ▼
      Supabase Postgres (rotations, exception_overrides, holidays, scrape_logs)
            │ ▼
      Cloudflare Worker (TypeScript + postgres.js)
       ├─ GET /v1/restriccion → 200 | 404 | 400
       └─ GET /v1/schedule → 200
            │ ▼
      Vercel static frontend (Vite + vanilla JS + Motion One)
       ├─ Hero (today's digit) → Input (live reveal) → Result (state-transition)
```

## Scraping Selector Strategy

Live selectors cannot be locked without HTML inspection (proposal risk #7). Strategy:

1. **Build-time**: Run `curl` + `beautifulsoup4` against the Alcaldía news page. Document actual `h2` + `p` selectors in `scraper/selectors.md`.
2. **Runtime heuristic fallback**: Search for "pico y placa" + digit pairs (`5 y 6`, `7 y 8`) + date pattern < 6 months old. If page structure changes, the heuristic still works; the run fails only if NO article parses.

## Re-verification & Cron Strategy (Deliverable #5)

- **Frequency**: Weekly (Monday 06:00 UTC). Rotation is quarterly, but the new mayor (Portilla) may issue mid-quarter resolutions.
- **Idempotency**: Before writing, query latest `rotations` row per municipality. If `raw_payload` is byte-equivalent to the live parse, skip. If different → UPSERT with new `valid_from`/`valid_to`.
- **Stale-data alert**: GitHub Actions workflow step queries `MAX(scraped_at)` from Supabase. If older than 8 days, the job emits a warning annotation.

## Supabase Schema Sketch

| Table | Key Columns (type) | Purpose |
|-------|-------------------|---------|
| `rotations` | `id uuid pk`, `municipality text` (check: 4 slugs), `valid_from date`, `valid_to date`, `raw_payload jsonb`, `source_url text`, `scraped_at timestamptz` | Quarterly rule per municipality. Index: `(municipality, valid_from, valid_to)`. |
| `exception_overrides` | `id uuid pk`, `municipality text`, `date date`, `reason text`, `source_url text`, `scraped_at timestamptz` | Ad-hoc suspensions. Checked before `rotations` lookup. |
| `holidays` | `date date pk`, `name text` | Colombian festivos. Seeded from manual CSV (law changes rarely). |
| `scrape_logs` | `id uuid pk`, `run_at timestamptz default now()`, `source text`, `success boolean`, `rows_written integer`, `error text` | Audit trail. Written on every scraper run. |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `python/plate_parser/` | Create | Pure-function module (parser.py, test_parser.py). Strict TDD. |
| `python/scraper/` | Create | BeautifulSoup scraper + selectors.md + test_scraper.py |
| `supabase/migrations/0001_` through `0003_` | Create | Additive SQL + paired `down.sql` |
| `worker/src/index.ts` + `worker/wrangler.toml` | Create | CF Worker entry point + config |
| `frontend/` | Create | Vite project (index.html, main.js, style.css, 3 components) |
| `.github/workflows/scraper.yml` | Create | Weekly cron + stale-data check |

## Testing Strategy

| Layer | What | Tool |
|-------|------|------|
| Plate parser unit | Right-to-left scan, classification, edge cases | pytest + pytest-cov (100% target) |
| Scraper integration | HTML parse with fixtures, idempotency, fail-safe | pytest + responses |
| Worker contract | API responses, headers, Cache-Control | vitest + miniflare |
| Frontend unit | Component render, live digit, localStorage | vitest + jsdom |

## Open Questions

- [ ] Exact CSS selectors for Alcaldía/AMB pages — must inspect live HTML at build time, documented in `scraper/selectors.md`
- [ ] Saturday calendar format: ISO-week map or date-range list? Defer to scraper implementation; spec says ISO week
