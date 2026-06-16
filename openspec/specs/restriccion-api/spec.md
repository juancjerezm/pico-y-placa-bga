# Restriccion API — Delta Spec

**Capability**: `restriccion-api`
**Change**: `2026-06-10-pico-y-placa-bucaramanga`
**Status**: ADDED
**Date**: 2026-06-10

## Purpose

The Cloudflare Worker (TypeScript) that exposes the Pico y Placa lookup. It answers two questions: "is THIS plate restricted on THIS date in THIS municipality?" and "what is the current rotation?". It is internal-only: no auth, no open CORS, public-cacheable on 200. When the DB has no row covering the requested date, the API fails safe with HTTP 404 — never returns unverified digits.

## ADDED Requirements

### REQ-API-001: `GET /v1/restriccion` happy path (200)

The system MUST return HTTP 200 with JSON body:
```json
{
  "municipio": "bucaramanga",
  "fecha": "2026-06-15",
  "placa_normalized": "ABC123",
  "restricted": true,
  "last_digit": 3,
  "formato_detectado": "particular",
  "rule": "weekday",
  "source": "rotation",
  "generated_at": "2026-06-10T10:00:00Z"
}
```
The response MUST also carry the header `Cache-Control: public, max-age=3600`. The system MUST default `municipio` to `bucaramanga` when the query parameter is omitted. `last_digit` MUST be the integer 0–9 produced by the plate parser. `formato_detectado` MUST be one of the 8 locked values (informational only). `rule` is one of `weekday | saturday | festivo`. `source` is one of `rotation | override`.

#### Scenario: Restricted plate on a weekday
- GIVEN a known rotation says Monday restricts digits 5, 6
- WHEN the API is called with `?municipio=bucaramanga&fecha=2026-06-15&placa=ABC005` (Monday)
- THEN HTTP 200 is returned
- AND `restricted == true`
- AND `last_digit == 5`
- AND `rule == "weekday"`
- AND `source == "rotation"`
- AND the response includes `Cache-Control: public, max-age=3600`

#### Scenario: Unrestricted plate on a weekday
- GIVEN the same Monday-only-5,6 rotation
- WHEN the API is called with `?municipio=bucaramanga&fecha=2026-06-15&placa=ABC003` (last digit 3)
- THEN HTTP 200 is returned
- AND `restricted == false`
- AND `last_digit == 3`

#### Scenario: Plate with letter-then-digit extracts the right digit
- GIVEN Tuesday restricts digits 1, 2
- WHEN the API is called with `placa=ABC12D`
- THEN `last_digit == 2`
- AND `restricted == true`
- AND `placa_normalized == "ABC12D"`

#### Scenario: formato_detectado is present on 200
- GIVEN the input plate "OAB 123"
- WHEN the API is called
- THEN HTTP 200 is returned
- AND `formato_detectado == "oficial"`
- AND `placa_normalized == "OAB 123"`

#### Scenario: placa_normalized strips whitespace and separators
- GIVEN the input plate "abc-123"
- WHEN the API is called
- THEN `placa_normalized == "ABC123"`

#### Scenario: Default municipality is Bucaramanga
- GIVEN the `municipio` query parameter is omitted
- WHEN the API is called
- THEN the lookup uses `municipio = "bucaramanga"`
- AND the response echoes `municipio: "bucaramanga"`

### REQ-API-002: `GET /v1/restriccion` fail-safe (404)

The system MUST return HTTP 404 with body `{ "error": "rotation_unknown", "municipio": "<slug>", "requested_date": "YYYY-MM-DD" }` when no row in `rotations` covers the requested `(municipio, fecha)`. This is the explicit fail-safe behavior: the API never returns unverified digits.

#### Scenario: Future date inside a known rotation
- GIVEN a rotation covers `2026-07-01` to `2026-09-30`
- WHEN the API is called with `fecha=2026-08-15`
- THEN HTTP 200 is returned (the date is in range)

#### Scenario: Future date outside any known rotation
- GIVEN the latest `rotations` row ends on `2026-09-30`
- WHEN the API is called with `fecha=2026-12-01`
- THEN HTTP 404 is returned
- AND the body is `{"error":"rotation_unknown","municipio":"...","requested_date":"2026-12-01"}`

#### Scenario: Empty database returns 404
- GIVEN the `rotations` table is empty
- WHEN the API is called for any date
- THEN HTTP 404 is returned with `error: "rotation_unknown"`

### REQ-API-003: `GET /v1/restriccion` validation errors (400)

The system MUST return HTTP 400 with body `{ "error": "bad_plate" | "bad_date" | "bad_municipio" }` for invalid inputs. The error type is exhaustive: any validation failure on `placa`, `fecha`, or `municipio` produces one of these three values.

#### Scenario: Malformed fecha
- GIVEN the `fecha` query parameter is "not-a-date"
- WHEN the API is called
- THEN HTTP 400 is returned
- AND the body is `{"error":"bad_date"}`

#### Scenario: Unknown municipality slug
- GIVEN the `municipio` query parameter is "medellin"
- WHEN the API is called
- THEN HTTP 400 is returned
- AND the body is `{"error":"bad_municipio"}`

#### Scenario: Empty placa
- GIVEN the `placa` query parameter is ""
- WHEN the API is called
- THEN HTTP 400 is returned
- AND the body is `{"error":"bad_plate"}`

#### Scenario: Placa with no digit
- GIVEN the `placa` query parameter is "ABC"
- WHEN the API is called
- THEN HTTP 400 is returned
- AND the body is `{"error":"bad_plate"}`

#### Scenario: Placa over the length cap
- GIVEN the normalized `placa` exceeds 32 characters
- WHEN the API is called
- THEN HTTP 400 is returned
- AND the body is `{"error":"bad_plate"}`

### REQ-API-004: Festivo behavior

When the requested date is a festivo (date present in `holidays` OR a Sunday), the system MUST return HTTP 200 with `restricted: false` and `rule: "festivo"`. The weekday digits are ignored.

#### Scenario: Festivo short-circuits the rule
- GIVEN a `holidays` row exists for `2026-07-20` (Colombian independence day, a Monday)
- AND the Monday rotation restricts digits 5, 6
- WHEN the API is called with `placa=ABC005` for 2026-07-20
- THEN HTTP 200 is returned
- AND `restricted == false`
- AND `rule == "festivo"`

#### Scenario: Sunday is treated as festivo
- GIVEN the requested date is a Sunday with no `holidays` row
- WHEN the API is called
- THEN HTTP 200 is returned
- AND `restricted == false`
- AND `rule == "festivo"`

### REQ-API-005: Saturday behavior

When the requested date is a Saturday, the system MUST consult the per-week Saturday calendar embedded in `raw_payload`. If a calendar entry exists for the requested ISO week, the system MUST evaluate the rule against those digits. If no calendar entry exists, the system MUST apply the conservative default: `restricted: false` (A13).

#### Scenario: Saturday WITH a known calendar entry
- GIVEN the rotation's Saturday calendar lists digits 1, 2 for ISO week 27 of 2026
- WHEN the API is called for any Saturday in that ISO week with `placa=ABC001`
- THEN HTTP 200 is returned
- AND `restricted == true`
- AND `rule == "saturday"`

#### Scenario: Saturday WITHOUT a known calendar entry
- GIVEN no Saturday calendar entry exists for the requested date's ISO week
- WHEN the API is called
- THEN HTTP 200 is returned
- AND `restricted == false`
- AND `rule == "saturday"` (rule value reflects the day, restricted reflects the conservative default)

### REQ-API-006: `GET /v1/schedule` (200 always)

The system MUST return HTTP 200 for any valid `municipio` (default `bucaramanga`). If a current rotation exists, the body is `{ "current": {...}, "next": null | {...}, "message": null }`. If no current rotation exists, the body is `{ "current": null, "next": null, "message": "rotation_unknown" }` (NOT a 404 — schedule is a metadata endpoint, not a lookup).

#### Scenario: Schedule with active rotation
- GIVEN a current-quarter rotation exists for Bucaramanga
- WHEN `GET /v1/schedule?municipio=bucaramanga` is called
- THEN HTTP 200 is returned
- AND `current` is populated with `valid_from`, `valid_to`, and `raw_payload` (without festivos)
- AND the response includes `Cache-Control: public, max-age=3600`

#### Scenario: Schedule with no active rotation
- GIVEN the `rotations` table has no row covering today's date
- WHEN `GET /v1/schedule?municipio=bucaramanga` is called
- THEN HTTP 200 is returned
- AND the body is `{"current": null, "next": null, "message": "rotation_unknown"}`

### REQ-API-007: Authentication, CORS, and rate limiting

The system MUST NOT require authentication. The system MUST enable CORS for all origins (`Access-Control-Allow-Origin: *`) and handle OPTIONS preflight requests. The system MUST implement rate limiting at 100 requests per minute per IP (Nivel 1 MVP).

#### Scenario: CORS headers present on all responses
- GIVEN any request (200, 400, 404)
- WHEN the response is observed
- THEN `Access-Control-Allow-Origin: *` is present
- AND `Access-Control-Allow-Methods: GET, OPTIONS` is present

#### Scenario: OPTIONS preflight is handled
- GIVEN an OPTIONS request to any endpoint
- WHEN the request is processed
- THEN HTTP 204 is returned with CORS headers

#### Scenario: No auth required
- GIVEN a request with no `Authorization` header
- WHEN the API is called
- THEN the request succeeds (subject to the normal validation rules)

#### Scenario: Rate limiting enforced at 100 req/min
- GIVEN a single IP sends more than 100 requests in a 60-second window
- WHEN the 101st request arrives
- THEN HTTP 429 is returned

### REQ-API-008: Municipality slug enum

The valid `municipio` slug values are: `bucaramanga | floridablanca | giron | piedecuesta`. The system MUST reject any other value with HTTP 400 `bad_municipio`.

#### Scenario: All four AMB municipalities are accepted
- GIVEN the slug is one of `bucaramanga`, `floridablanca`, `giron`, `piedecuesta`
- WHEN the API is called
- THEN the request is accepted (subject to other validations)

#### Scenario: Slug outside the enum is rejected
- GIVEN the slug is "bogota"
- WHEN the API is called
- THEN HTTP 400 is returned with `error: "bad_municipio"`

### REQ-API-009: `fecha` validation

`fecha` MUST be an ISO-8601 date (`YYYY-MM-DD`) with no time component and no timezone offset. Any other format yields HTTP 400 `bad_date`. The system MUST accept any date ≥ 2022-01-01 (the scraper's minimum) and any future date; the fail-safe 404 handles the case where the date falls outside any known rotation.

#### Scenario: ISO date is accepted
- GIVEN `fecha=2026-06-15`
- WHEN the API is called
- THEN the request is accepted (subject to other validations)

#### Scenario: ISO datetime is rejected
- GIVEN `fecha=2026-06-15T10:00:00Z`
- WHEN the API is called
- THEN HTTP 400 is returned with `error: "bad_date"`
