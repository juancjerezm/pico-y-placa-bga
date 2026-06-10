# Exploration — Pico y Placa Bucaramanga

> Phase: `sdd/explore` (research only, no code).
> Date: 2026-06-10.
> Companion Engram observation: `sdd/pruebaminimax/explore` (id 797) holds the full Spanish-language research notes; this file is the English review-facing summary.

## Why this exploration

The Pico y Placa system for Bucaramanga cannot be designed without knowing the canonical source of the rule, the current rotation, the full set of plate formats in circulation, and the cadence at which the rule changes. This document captures what is known with confidence, what is assumed, and what is unresolved.

## 1. Source authority

| Role | Entity | URL |
| --- | --- | --- |
| Primary issuer (decree) | Dirección de Tránsito de Bucaramanga (DTB), under the Alcaldía de Bucaramanga | https://www.bucaramanga.gov.co/ |
| Canonical news feed (rotations announced here) | Alcaldía — news search | https://www.bucaramanga.gov.co/noticias/?s=pico+y+placa |
| Searchable norms repository | Sistema de búsqueda propio de la entidad | https://sistemadebusqueda.bucaramanga.gov.co/ |
| Transparency portal (decrees + resolutions) | Alcaldía — transparency | https://www.bucaramanga.gov.co/transparencia/sistema-de-busquedas-de-normas-propio-de-la-entidad/ |
| Metropolitan coordinator | Área Metropolitana de Bucaramanga (AMB) | https://www.amb.gov.co/ |
| Metropolitan resolutions | AMB Subdirección de Transporte | https://www.amb.gov.co/resoluciones-transporte-metropolitano/ |

There is no public open-data API. The scraper must read HTML news pages or PDF resolutions. No CSV/JSON feed is offered.

## 2. Current rule (verified Q3 2025)

Source: https://www.bucaramanga.gov.co/noticias/nuevas-disposiciones-del-pico-y-placa-en-bucaramanga-rigen-desde-el-1-de-julio/ (28 Jun 2025).

| Day | Restricted digits (last numeric digit) |
| --- | --- |
| Monday | 5, 6 |
| Tuesday | 7, 8 |
| Wednesday | 9, 0 |
| Thursday | 1, 2 |
| Friday | 3, 4 |
| Saturday | Varies weekly (a per-week calendar is published) |
| Sunday + festivos | No Pico y Placa |

**Hours:**
- Monday to Friday: 06:00 to 20:00 (single continuous 14-hour window)
- Saturday: 09:00 to 13:00
- Sunday + holidays: free circulation

**Fine for infringement:** 15 SMDLV + vehicle immobilization (per the 29 Feb 2024 metropolitan article).

**Cadence:** Quarterly. Each rotation is a Resolución of the DTB; the AMB metropolitan unification follows the same cycle. A scraper cron every 2–4 weeks is sufficient.

## 3. Validity scope (geographic)

Since 1 March 2024, the rule applies to the metropolitan corridors of:
- Bucaramanga (city)
- Floridablanca
- Girón
- Piedecuesta

Specifically: the autopista Piedecuesta → Bucaramanga through Floridablanca, plus the anillo vial externo between Girón and Bucaramanga's eastern ring. Coordination is via the AMB Consejo Metropolitano de Movilidad.

As of the latest verified rotation (Q3 2025) the rule and digits are identical across the four municipalities. The scraper should treat them as one canonical rule, reading both AMB (canonical) and Alcaldía (backup).

## 4. Plate formats (verified)

Source: https://es.wikipedia.org/wiki/Anexo:Matr%C3%ADculas_automovil%C3%ADsticas_de_Colombia (last edited 11 May 2026).

| Format | Vehicle type | Subject to Pico y Placa? |
| --- | --- | --- |
| `ABC·123` | Particular (car) | YES |
| `ABC·123` | Commercial (car) | YES |
| `OAB·123` | Official | YES (per 2024 metropolitan rule — see correction below) |
| `ABC·12D` (current) or `ABC·12` (older, still in use) | Motorcycle | YES |
| `123·ABC` | Mototaxi (private or commercial) | TBD — not explicitly mentioned in news; conservatively subject |
| `R·12345` | Trailer | TBD |
| `T·1234` | Temporary import | YES (per 2024 metropolitan rule) |
| `M AB 123` | Special diplomatic mission | YES (per 2024 metropolitan rule) |
| `D AB 123` | Diplomatic | YES (per 2024 metropolitan rule) |
| `C AB 123` | Consular | YES (per 2024 metropolitan rule) |
| `A AB 123` | Administrative / technical staff | TBD |
| `O AB 123` | International organizations | TBD |
| `D CO 123` | Missions in accreditation | TBD |
| `FAC 123456` | Colombian Air Force | TBD (likely exempt by category) |
| `12-3456` | National Police | TBD (likely exempt by category) |
| `AB 1234` (pre-1990) | Older particular design | YES (still in circulation) |
| `OA 1234` (pre-1990) | Older official design | YES |

**Correction to a preflight assumption:** the user preflight stated that diplomatic and official plates are "typically excluded". This is **wrong for Bucaramanga**. The 2024 metropolitan decree explicitly INCLUDES official, diplomatic, consular, and temporary-import vehicles. The plate parser must therefore accept these formats and not exclude them by prefix.

## 5. Parser rule (already decided, restated here for review)

To extract the last numeric digit of a plate, scan the plate string from RIGHT to LEFT and take the first character that is a digit (0–9).

Examples:
- `ABC12D` → 'D' (skip) → '2' (found) → 2
- `ABC123` → '3' (found) → 3
- `ABC12` → '2' (found) → 2
- `R·12345` → '5' → 5
- `D AB 123` → '3' → 3

This rule covers all formats in the table above correctly. The "right-to-left scan" interpretation is sensible but is **not** literally written in the decree (the decree says "placas terminadas en X", which is unambiguous for `ABC123` and `ABC12` but could be read differently for `ABC12D`).

## 6. Exceptions (per public news articles)

| Category | Subject to the rule? | Source |
| --- | --- | --- |
| Taxis | EXEMPT | 29 Feb 2024 article, confirmed in Q3 2025 article |
| Ambulances, fire trucks, electric vehicles, persons with disabilities, press, school transport, public-force vehicles | TBD — not mentioned in public news; must be extracted from the underlying Resolución PDF | — |

**Implication for v1:** the system should apply the rule to all parsed formats (including official/diplomatic) and treat the full exception list as a future enrichment that the scraper ingests from the Resolución PDF.

## 7. Holiday / festivos handling

- Sundays and festivos are excluded by construction.
- Semana Santa 2024 was explicitly suspended by DTB (ad-hoc, not a standing rule). The system should treat holiday suspensions as ad-hoc overrides the scraper must catch.
- A separate **Pico y Placa ambiental** (Resolución 094 de 2020, tied to air-quality emergencies) is a distinct regime with different digits (typically 7–8 on specific days). The scraper must filter out 2020 articles to avoid contaminating historical data.

## 8. Cadence and history

Quarterly rotations since at least 2020. Verified historical start dates include: 1 Jul 2020, 3 Apr 2021, 1 Oct 2021, 1 Apr 2022, 13 Jan 2023, Apr 2023, 2 Oct 2023, 1 Mar 2024, 1 Apr 2024, 1 Jul 2025. A scraper cron every 2–4 weeks is more than enough.

## 9. Open questions (carry to sdd-propose)

See Engram observation `sdd/pruebaminimax/explore/open-questions` (id 798) for the full set. Highlights:

1. **HIGH — Q2 2026 rotation not verified online.** The new mayor (Cristian Fernando Portilla, since early 2026) may have changed the rule. The scraper must re-verify the current rotation on every run; the system cannot trust cached Q3 2025 data.
2. **MED — Full exception list not public.** Only taxis are confirmed exempt. Everything else lives in the Resolución PDF.
3. **MED — 2020 Pico y Placa ambiental contamination risk.** Filter by date (≥ 2022) and treat "Pico y Placa ambiental" as a negative keyword.
4. **LOW — Right-to-left scan rule is an interpretation, not a textual decree clause.** Documented assumption, defensible, but worth a test that covers both interpretations.
5. **LOW — 4-municipality synchronization could diverge in the future.** Read AMB as canonical, Alcaldía as backup.

## 10. Confidence levels

- **HIGH** (2+ independent official sources): source authority, hours, cadence, metropolitan scope, Q3 2025 rotation, plate formats.
- **MEDIUM** (single source): Q4 2025 rotation, whether motorcycles and mototaxis are treated identically, exemption list beyond taxis.
- **LOW / unverifiable**: Q2 2026 rotation, whether the Portilla administration has changed the rule, full exemption list.
