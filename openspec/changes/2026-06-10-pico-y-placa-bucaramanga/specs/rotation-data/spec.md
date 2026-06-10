# Rotation Data — Delta Spec

**Capability**: `rotation-data`
**Change**: `2026-06-10-pico-y-placa-bucaramanga`
**Status**: ADDED
**Date**: 2026-06-10

## Purpose

The data pipeline that ingests the quarterly Pico y Placa rotation from canonical sources and persists it in Supabase Postgres, plus the weekly GitHub Actions cron that drives it. The data layer is the system of record: the API never trusts the cache, only the DB. A scheduled run that finds no current-quarter rotation is a hard failure that the API surfaces as 404.

## ADDED Requirements

### REQ-RD-001: `rotations` table

The system MUST persist every Pico y Placa rotation as one row per municipality, even when the four AMB municipalities share the same digits. Schema: `rotations(id uuid pk, municipality text not null check (municipality in ('bucaramanga','floridablanca','giron','piedecuesta')), valid_from date not null, valid_to date not null, source_url text not null, scraped_at timestamptz not null default now(), raw_payload jsonb not null)`. The system MUST create an index on `(municipality, valid_from, valid_to)`. `valid_to` is inclusive (the last day the rotation applies).

#### Scenario: Rotation row is written for each of the 4 municipalities
- GIVEN the scraper parsed a current-quarter rotation with digits {Mon:5,6; Tue:7,8; ...}
- WHEN the run completes
- THEN exactly 4 rows exist in `rotations`, one per municipality, all sharing the same `valid_from`, `valid_to`, and `raw_payload` shape
- AND `raw_payload` includes the weekday→digits map and the per-Saturday weekly calendar

#### Scenario: Identical digits are still written 4 times
- GIVEN the AMB has unified Bucaramanga, Floridablanca, Girón, and Piedecuesta on the same digits
- WHEN the scraper writes the rotation
- THEN 4 rows are created with identical `raw_payload` (one per `municipality`)

### REQ-RD-002: `exception_overrides` table

The system MUST persist ad-hoc suspensions (e.g., Semana Santa 2024) in a separate table. Schema: `exception_overrides(id uuid pk, municipality text not null, date date not null, reason text not null, source_url text not null, scraped_at timestamptz not null default now())`. Each row nullifies the rule for one `(municipality, date)`. The API MUST check this table before the rotation table.

#### Scenario: Override row short-circuits the rule
- GIVEN an `exception_overrides` row exists for `(bucaramanga, 2026-04-15)` with reason "Semana Santa"
- WHEN the API is asked whether plate `ABC005` is restricted on 2026-04-15
- THEN the response is `restricted: false` with `source: "override"`

### REQ-RD-003: `holidays` table

The system MUST persist Colombian festivos in `holidays(date date pk, name text not null)`. The API MUST treat any date present in `holidays` OR any Sunday as `restricted: false, rule: "festivo"`.

#### Scenario: Festivo overrides the weekday rule
- GIVEN a `holidays` row exists for `2026-07-20` (Colombian independence day)
- WHEN the API is asked whether plate `ABC005` is restricted on 2026-07-20 (a Monday)
- THEN `restricted == false`
- AND `rule == "festivo"`

#### Scenario: Sunday is treated as festivo
- GIVEN the requested date is a Sunday with no rotation entry
- WHEN the API is asked
- THEN `restricted == false`
- AND `rule == "festivo"`

### REQ-RD-004: Scraper primary source

The scraper MUST attempt the Alcaldía news search HTML page (`/noticias/?s=pico+y+placa`) as its primary source. The page is structured HTML; digits and effective dates are spelled out in article text. The scraper MUST locate the most recent article that announces a rotation effective on or after 2022-01-01 and parse it.

#### Scenario: Primary source writes 4 rotation rows
- GIVEN the most recent article announces the current-quarter rotation with weekdays {Mon:5,6; Tue:7,8; Wed:9,0; Thu:1,2; Fri:3,4} and Saturday calendar {week1:1,2; week2:3,4; ...}
- WHEN the scraper runs against the primary source
- THEN 4 rows are inserted into `rotations` (one per municipality)
- AND each row's `raw_payload` contains the weekday→digits map and the Saturday calendar

#### Scenario: 2020 article is rejected by the date filter
- GIVEN a 2020 article exists on the page
- WHEN the scraper evaluates it
- THEN the article is rejected (date < 2022-01-01)
- AND no row is written for that article

#### Scenario: "Pico y Placa ambiental" article is rejected by the negative keyword
- GIVEN a 2023 article body contains the phrase "Pico y Placa ambiental"
- WHEN the scraper evaluates it
- THEN the article is rejected
- AND no row is written for that article

### REQ-RD-005: Scraper fallback source

If the primary source yields no current-quarter rotation, the scraper MUST fall back to the AMB norm search system (`sistemadebusqueda.bucaramanga.gov.co`). The fallback parser uses the same shape (one row per municipality, same `raw_payload`).

#### Scenario: Fallback is used when primary fails
- GIVEN the primary source returned no current-quarter rotation
- WHEN the scraper falls back to AMB
- THEN the AMB article is parsed
- AND 4 rows are written to `rotations`

### REQ-RD-006: Saturday weekly calendar ingestion

The scraper MUST ingest the per-week Saturday calendar (which varies by week) as a separate artifact within `raw_payload`. The Saturday calendar is part of the rotation's `valid_from`/`valid_to` window.

#### Scenario: Saturday calendar is captured
- GIVEN a rotation includes a 4-week Saturday calendar {week1:1,2; week2:3,4; week3:5,6; week4:7,8}
- WHEN the scraper writes the row
- THEN `raw_payload.saturday_calendar` contains the 4 entries
- AND the API can look up a Saturday by ISO week number

### REQ-RD-007: Fail-safe on no current-quarter rotation

If neither primary nor fallback yields a rotation whose `valid_from <= today <= valid_to`, the scraper MUST refuse to write any row for that run and MUST exit non-zero so the cron surfaces a failure.

#### Scenario: Scraper aborts when no current rotation exists
- GIVEN the primary source returns no rotation covering today's date
- AND the fallback also returns no rotation covering today's date
- WHEN the scraper run completes
- THEN 0 rows are inserted into `rotations`
- AND the run exits with a non-zero status
- AND the API subsequently returns HTTP 404 `rotation_unknown` for queries on today's date

### REQ-RD-008: GitHub Actions weekly cron

A GitHub Actions workflow MUST run the scraper on a weekly schedule (weekday and hour chosen at design time). The workflow MUST use Python (pip/uv). Each run MUST publish its result to the `rotations` table.

#### Scenario: Weekly cron runs the scraper
- GIVEN the schedule is configured for every Monday 06:00 UTC
- WHEN the cron trigger fires
- THEN the scraper module runs
- AND the run result is written to the `rotations` table
- AND the run status is captured in the GitHub Actions run log

### REQ-RD-009: Migrations are additive and reversible

All database schema changes MUST be applied as additive migrations with a paired `down.sql`. Migrations MUST NOT drop columns, rename columns, or destroy data. A `down.sql` MUST be sufficient to return the schema to its prior state without manual intervention.

#### Scenario: Applying a migration then its down returns to prior schema
- GIVEN migration `0002_add_exception_overrides.sql` adds the `exception_overrides` table
- WHEN the migration is applied
- THEN the new table exists in the schema
- WHEN the matching `0002_add_exception_overrides.down.sql` is applied
- THEN the `exception_overrides` table no longer exists
- AND the schema is byte-equivalent to its pre-migration state (modulo generated `down` audit rows)

### REQ-RD-010: PDF parsing is out of scope for v1

The scraper MUST NOT attempt to parse Resolución PDFs in v1. Both the primary and fallback parsers read HTML only. If neither HTML source yields a current-quarter rotation, the run fails (per REQ-RD-007).

#### Scenario: HTML-only ingestion
- GIVEN both HTML sources yield no current-quarter rotation
- WHEN the scraper completes
- THEN no PDF is fetched or parsed
- AND the run fails per REQ-RD-007
