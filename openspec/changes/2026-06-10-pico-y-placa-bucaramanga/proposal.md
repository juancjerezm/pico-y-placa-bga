# Proposal: Pico y Placa Bucaramanga

**Change**: `2026-06-10-pico-y-placa-bucaramanga`
**Status**: Draft for user review
**Date**: 2026-06-10

## Summary

A consumer webapp that tells residents of the AMB (Bucaramanga, Floridablanca, Girón, Piedecuesta) whether their car can circulate on a given day, based on the official Pico y Placa rotation. Internal-only API, no auth, no payments. The defining trait is a distinctive ("rompedor") single-screen experience — not a generic-looking page.

## Why

The Pico y Placa rule rotates quarterly and is published only in scattered news articles and Resoluciones. Today, residents have to find the right page to know the current digits. We centralize that signal into one tap, defaulting to Bucaramanga and letting the user switch municipalities. Per exploration 797: the rule structure is HIGH-confidence, the current Q2 2026 rotation is MEDIUM-confidence (new mayor's administration), and the plate-parser algorithm is the highest-leverage decision in the system.

## Goals

- Reliable quarterly rotation ingestion from canonical sources, re-verified on every run.
- Fail-safe API: HTTP 404 `rotation_unknown` when stale data is the only data available.
- All 4 AMB municipalities as first-class rows; UI default = Bucaramanga.
- Strict TDD on the plate parser (target: 100% line + branch coverage).
- Distinctive frontend anchored on a typographic digit-hero, micro-interactions on state change.

## Non-Goals

- **No auth, no payments, no public API** in v1.
- No vehicle-type-aware restrictions surfaced in user copy. The parser classifies the format and the API exposes it as a `formato_detectado` field (informational only, never affects the rule), but the UI does not display it.
- No push notifications, history endpoint, native mobile app.
- No multi-city beyond AMB.
- No Pico y Placa ambiental — scraper filters it out.

## Scope

| Component | Tech | Concern |
|---|---|---|
| Scraper | Python (uv/pip) | Pull quarterly rotations from HTML news article (primary) + AMB norm search (fallback). |
| Database | Supabase Postgres | `rotations`, `exception_overrides`, `holidays` tables. |
| API | Cloudflare Worker (TypeScript) | Read-only queries, public cache, fail-safe 404. |
| Frontend | Static HTML/CSS/JS, pnpm for tooling | Single hero screen, vanilla JS, motion library chosen at design. |
| Cron | GitHub Actions | Weekly schedule, writes to Supabase. |

`openspec/config.yaml` declares Python-first with strict TDD; `pnpm` preference applies only to any JS tooling added.

## Approach

### Data model (Supabase)

- `rotations(id uuid pk, municipality text not null, valid_from date not null, valid_to date not null, source_url text not null, scraped_at timestamptz not null default now(), raw_payload jsonb not null)`. Index on `(municipality, valid_from, valid_to)`. **Why**: a rotation row is the unit of truth; the API looks up by `(municipality, fecha)`. Modeling `municipality` per row (even when digits are identical) future-proofs divergence (Q5 in 798).
- `exception_overrides(id, municipality, date, reason, source_url, scraped_at)`. **Why**: ad-hoc suspensions (e.g. Semana Santa 2024) do not fit the rotation cadence; this is the extension point for the incomplete exemption list (Q3 in 798).
- `holidays(date pk, name)`. **Why**: Sundays + festivos are excluded by construction; the table is needed to mark festivos and short-circuit the API.

### Scraper strategy

- **Primary**: Alcaldía news search HTML page (`/noticias/?s=pico+y+placa`). Reason: structured HTML, digits are always spelled out, low parse complexity, single-host.
- **Fallback**: AMB norm search system (`sistemadebusqueda.bucaramanga.gov.co`). Reason: canonical repository of Resoluciones; more authoritative but HTML shape less stable.
- **Excluded**: Resolución PDF parsing — high complexity, only needed if both primary and fallback fail.
- **Filters**: date ≥ 2022; `Pico y Placa ambiental` as a negative keyword (Q3 in 798); reject if no current-quarter rotation is parsed (fail-safe trigger for the API).
- **Cadence**: weekly cron is more than enough (quarterly rule, per exploration 798).

### Plate parser

- **Input contract**: any string ≤ 16 chars after whitespace normalization; no required prefix; letters, digits, spaces, dots, dashes, middle-dots (`·`) accepted.
- **Algorithm**: scan RIGHT to LEFT, return first char where `0-9`. If none, return `None` (validation error).
- **Test cases**:

  | Input | Expected | Notes |
  |---|---|---|
  | `ABC123` | 3 | standard |
  | `ABC12D` | 2 | motorcycle (current) |
  | `ABC12` | 2 | motorcycle (older) |
  | `R 12345` | 5 | trailer (whitespace) |
  | `ABC-123` | 3 | dash form |
  | `ABC·123` | 3 | middle-dot form |
  | `D AB 123` | 3 | diplomatic |
  | `OAB 123` | 3 | official |
  | `M AB 123` | 3 | mission |
  | `T 1234` | 4 | temp import |
  | `` (empty) | `None` | invalid |
  | `ABC` | `None` | no digit |

- **Strict TDD**: red → green → refactor. Module: `python/plate_parser/`. Runner: `pytest` + `pytest-cov`. The table above is encoded as parameterized cases.

### API contract (refined from user's OpenAPI)

- `GET /v1/restriccion?municipio={slug}&fecha={YYYY-MM-DD}&placa={string}`
  - 200: `{ municipio, fecha, placa_normalized, restricted: bool, last_digit: 0-9, formato_detectado: "particular"|"moto"|"oficial"|"diplomatico"|"remolque"|"temporal"|"fuerza_publica"|"desconocido", rule: "weekday"|"saturday"|"festivo", source: "rotation"|"override", generated_at }`
    - `formato_detectado` is **informational only** — it never affects the rule. Surfaced for analytics (Worker logs) and for clients that want to display a confirmation chip. The frontend in v1 does NOT show it.
    - `placa_normalized` is the input with whitespace/case normalized (e.g., `abc 123` → `ABC123`).
  - 404: `{ error: "rotation_unknown", municipio, requested_date }` (Q3 fail-safe)
  - 400: `{ error: "bad_plate"|"bad_date"|"bad_municipio" }`
  - Headers on 200: `Cache-Control: public, max-age=3600` (Q1 decision)
- `GET /v1/schedule?municipio={slug}` — returns the active rotation's window. If no active rotation, returns 200 with `{ current: null, next: null, message: "rotation_unknown" }` (Q4).
- Authentication: **none**. CORS: not enabled. Rate limit: deferred to Cloudflare Turnstile on the frontend (Q1).

### Frontend shape

Single-screen SPA. Three components:
- **Hero**: the digit restricted TODAY (or "no restriction") rendered as a typographic centerpiece.
- **Input**: a plate field that animates as the user types, reveals the last detected digit live, validates on submit.
- **Result**: state-transition micro-interaction (color, motion) showing restriction status.

State: last query in `localStorage` so the page re-hydrates to the same plate + municipality. No framework lock-in; vanilla JS + a small motion library (Framer Motion / GSAP / Motion One) is acceptable — chosen at design time. Pnpm for tooling.

## Capabilities

### New Capabilities

- `plate-parser`: extract the last numeric digit of a Colombian vehicle plate (right-to-left scan).
- `rotation-data`: Supabase schema, scraper, and GitHub Actions cron for quarterly rotation ingestion.
- `restriccion-api`: Cloudflare Worker endpoint serving restriction queries and schedule lookup with fail-safe 404.
- `pico-placa-frontend`: static frontend with hero / input / result components and `localStorage`-backed state.

### Modified Capabilities

- None (no existing capabilities in `openspec/specs/`).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `openspec/specs/{plate-parser,rotation-data,restriccion-api,pico-placa-frontend}/spec.md` | New | One spec per new capability. |
| `python/plate_parser/` | New | Strict TDD parser module. |
| `python/scraper/` | New | HTML scraper + cron entry point. |
| `supabase/migrations/` | New | SQL migrations for the 3 tables (additive only, with `down.sql`). |
| `worker/` | New | Cloudflare Worker (TypeScript). |
| `frontend/` | New | Static site. |
| `.github/workflows/scraper.yml` | New | Weekly cron. |
| `openspec/config.yaml` | Modified (later) | Add JS testing config if needed. |

## Acceptance Criteria

- [ ] Parser unit tests pass with 100% line + branch coverage on the rule; the test table above is encoded as parameterized cases.
- [ ] Scraper completes a weekly scheduled run ≥ 95% over a 4-week window and writes at least one `rotations` row per municipality.
- [ ] API returns HTTP 404 `rotation_unknown` when the requested date falls outside every row in `rotations` for the given municipality — verified by a contract test with an empty DB.
- [ ] All API 200 responses carry `Cache-Control: public, max-age=3600` — verified by a contract test.
- [ ] `GET /v1/restriccion?municipio=floridablanca&fecha=YYYY-MM-DD` works and returns the same digits as Bucaramanga when the rotation is unified.
- [ ] API accepts `fecha` for today and any future date up to the end of the last known rotation; out-of-range returns 404 `rotation_unknown` (Q4).
- [ ] `pnpm` is used wherever JS tooling is added; `pip`/uv is used for Python.

## Risks & open questions

| # | Risk | Blocking? | Mitigation |
|---|---|---|---|
| 1 | Q2 2026 rotation not verified online (new mayor Portilla) | **Blocking for design** — must inspect live HTML in sdd-design before spec freeze | Scraper re-verifies on every run; fail-safe returns 404 if not confirmed. Re-verification is the **design**, not a one-time check. |
| 2 | Complete exemption list not public (only taxis confirmed) | Non-blocking | v1 applies the rule to all formats; `exception_overrides` is the extension point. |
| 3 | 2020 Pico y Placa ambiental contamination | Non-blocking | Date filter ≥ 2022 + negative keyword. |
| 4 | Right-to-left scan is an interpretation, not textual in the decree | Non-blocking | Document in the spec; cover both interpretations with parameterized tests. |
| 5 | 4-municipality divergence (future) | Non-blocking | `municipality` is a column, not a constant; AMB canonical, Alcaldía backup. |
| 6 | RUNT national registry auth-gated | Non-blocking | Out of scope; mention only. |
| 7 | HTML shape of AMB norm search is unknown until inspected | **Blocking for design** — selectors must be locked in sdd-design | Inspect live HTML in sdd-design; lock selectors there. |

New risks added by this proposal:

- **8 (Low)**: Saturday "varies weekly" calendar is a separate artifact the scraper must ingest; not just the weekday table. Defer to sdd-design.
- **9 (Low)**: Mixed-tooling project (Python + JS) means two ecosystems coexist. Document the boundary in `openspec/config.yaml` once JS tooling is added.
- **10 (Low)**: User-facing copy must be generic ("tienes restricción" / "no tienes restricción") per hard rule #3; UX writers must not introduce vehicle-type copy during sdd-design.

## Rollback Plan

- Frontend: redeploy previous static build (Vercel/Netlify/Cloudflare Pages) — instant.
- Worker: revert Worker version on Cloudflare dashboard — instant.
- Scraper cron: disable the GitHub Actions workflow — instant.
- Database: migrations are additive only; each has a `down.sql` checked in. No data-destroying migrations in v1.
- Worst case: point DNS back to a static "we are offline" page hosted on GitHub Pages.

## Dependencies

- Supabase project (free tier is sufficient for v1).
- Cloudflare account with Workers (free tier covers v1).
- GitHub Actions (free for public repos).
- A static host (Vercel/Netlify/Cloudflare Pages) — choice deferred to sdd-design.
- No paid third-party services for v1.

## Out of scope / future

- Multi-city beyond AMB.
- Push notifications or browser alerts.
- Historical "what was the rotation on date X" endpoint.
- Native mobile app.
- Vehicle-type-aware restrictions surfaced to the user.
- Pico y Placa ambiental.
- Plate validation against RUNT.
- OCR-based plate input from a photo.
- User accounts, history of past queries, sharing.

## Chained PR strategy (proposal; user decides at sdd-tasks)

Four components, 400-line review budget, `chained_pr_strategy: ask-always`. Natural slicing (all stacked to `main`):

- **PR 1 — Plate parser + tests** (~80 lines). Pure logic, fastest review, sets the TDD pattern. Stacked on `main`.
- **PR 2 — DB schema + scraper** (~200 lines, may need split). Migrations, scraper module, GitHub Actions cron. Stacked on PR 1.
- **PR 3 — Worker API** (~150 lines). Reads from Supabase, exposes the contract. Stacked on PR 2.
- **PR 4 — Frontend** (~200 lines). Static site with hero / input / result. Stacked on PR 3.

Open questions for sdd-tasks:
- If PR 2 exceeds 400 lines, split into "schema-only" + "scraper-only".
- The frontend could be split into "shell + copy" and "motion + micro-interactions" if the motion library adds bulk.
- Alternative: a single PR per component, but with the chained-PR skill applied if any single PR exceeds 400 lines.

The user decides the final strategy at sdd-tasks time; this proposal does not commit to it.
