# Tasks: Pico y Placa Bucaramanga

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~630 total (PR 1: 80, PR 2: 200, PR 3: 150, PR 4: 200) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | ask-always |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Plate parser + 100% coverage tests | PR 1 | Stacked on main; pure Python TDD |
| 2 | Supabase schema + scraper + cron | PR 2 | Stacked on PR 1; split if >400 lines |
| 3 | Cloudflare Worker API + contract tests | PR 3 | Stacked on PR 2 |
| 4 | Vite frontend + Motion One micro-interactions | PR 4 | Stacked on PR 3 |

## Phase 1: Foundation

- [x] 1.1 Create `python/pyproject.toml` with uv, pytest, pytest-cov, ruff, mypy
- [x] 1.2 Create `python/.python-version` and generate uv lockfile

## Phase 2: Plate Parser — PR 1 (strict TDD)

- [x] 2.1 RED: Create `python/plate_parser/test_parser.py` with parameterized cases for REQ-PP-001/002/003
- [x] 2.2 GREEN: Create `python/plate_parser/parser.py` with `parse_placa()` implementing normalization, right-to-left scan, and 8-rule formato classifier
- [x] 2.3 REFACTOR: Add `python/plate_parser/__init__.py`, run `pytest --cov=plate_parser` until 100% line + branch coverage

## Phase 3: Schema + Scraper — PR 2

- [x] 3.1 Create `supabase/migrations/0001_create_rotations.sql` + `0001_create_rotations.down.sql` (REQ-RD-001)
- [x] 3.2 Create `supabase/migrations/0002_create_exception_overrides.sql` + down.sql (REQ-RD-002)
- [x] 3.3 Create `supabase/migrations/0003_create_holidays.sql` + down.sql (REQ-RD-003)
- [x] 3.4 Create `python/scraper/selectors.md` with locked Alcaldía/AMB selectors (design deliverable)
- [x] 3.5 Create `python/scraper/scraper.py` with primary/fallback parse, idempotent UPSERT, Saturday calendar ingestion, fail-safe exit (REQ-RD-004/005/006/007)
- [x] 3.6 Create `python/scraper/test_scraper.py` with HTML fixture tests for idempotency and fail-safe
- [x] 3.7 Create `.github/workflows/scraper.yml` with weekly cron (Mon 06:00 UTC), stale-data check, uv setup (REQ-RD-008)

## Phase 4: Worker API — PR 3

- [x] 4.1 Create `worker/wrangler.toml` with TypeScript, postgres.js bindings
- [x] 4.2 Create `worker/src/index.ts` with `GET /v1/restriccion` (200/404/400) and `GET /v1/schedule` (REQ-API-001/002/006)
- [x] 4.3 Add `Cache-Control: public, max-age=3600` to all 200 responses (REQ-API-001)
- [x] 4.4 Write `worker/test/index.test.ts` with vitest + miniflare contract tests for REQ-API-001/002/004/006

## Phase 5: Frontend — PR 4

- [x] 5.1 Create `frontend/package.json` with Vite, Motion One, vitest; generate `pnpm-lock.yaml` (REQ-FE-008)
- [x] 5.2 Create `frontend/index.html` with single-screen layout (Hero, Input, Result)
- [x] 5.3 Create `frontend/src/main.js` with Hero (today's digit fetch), Input (live digit reveal + validation), Result (state transition animation)
- [x] 5.4 Implement `localStorage` persistence and re-hydration per REQ-FE-005
- [x] 5.5 Add `frontend/src/style.css` responsive for 360px viewport, 44×44 touch targets (REQ-FE-007)

## Phase 6: Verification

- [x] 6.1 Run `pytest --cov=plate_parser` and confirm 100% line + branch coverage
- [x] 6.2 Run scraper contract test against empty DB to confirm 404 fail-safe path
- [x] 6.3 Run worker vitest suite and confirm all API scenario assertions pass
- [x] 6.4 Run frontend vitest (assumed until package.json confirms) and verify component render + localStorage round-trip
