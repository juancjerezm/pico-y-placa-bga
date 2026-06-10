# Pico y Placa Frontend — Delta Spec

**Capability**: `pico-placa-frontend`
**Change**: `2026-06-10-pico-y-placa-bucaramanga`
**Status**: ADDED
**Date**: 2026-06-10

## Purpose

A single-page, mobile-first static site that lets AMB residents (Bucaramanga, Floridablanca, Girón, Piedecuesta) check whether their car can circulate on a given day. The page is anchored on a typographic digit-hero (the digit restricted today), a plate input that reveals the last detected digit live, and a result state-transition. State persists in `localStorage` so the page re-hydrates to the last query on reload. User-facing copy is generic — vehicle type is never surfaced.

## ADDED Requirements

### REQ-FE-001: Three components

The system MUST render exactly three top-level components: **Hero**, **Input**, **Result**. The Hero occupies the upper viewport and is always visible. The Input sits below the Hero. The Result is hidden until the first successful query, then persists for the session. No additional views, modals, or routes are exposed in v1.

#### Scenario: Hero is rendered on first load
- GIVEN a user opens the page for the first time
- WHEN the page finishes loading
- THEN the Hero component is visible
- AND the Input component is visible below it
- AND the Result component is hidden

#### Scenario: Result appears after first successful query
- GIVEN the Input has been filled with a valid plate and submitted
- WHEN the API responds with HTTP 200
- THEN the Result component animates in
- AND the Hero remains visible above it

### REQ-FE-002: Hero behavior

The Hero MUST display, for the default municipality (Bucaramanga), the digit restricted TODAY as a typographic centerpiece. If today is a festivo, Sunday, or no rotation is active, the Hero MUST show a calm "no restriction" state instead of a digit. The Hero MUST re-fetch when the user changes the municipality.

#### Scenario: Hero shows today's restricted digit
- GIVEN today is a Monday and the current rotation restricts digits 5, 6 in Bucaramanga
- WHEN the page loads
- THEN the Hero displays "5" (or "5, 6") as a typographic centerpiece
- AND the Hero is labeled with the weekday and the city

#### Scenario: Hero shows calm "no restriction" on a festivo
- GIVEN today is a festivo (or Sunday, or no active rotation)
- WHEN the page loads
- THEN the Hero shows a calm "no restriction" state
- AND no digit is shown as a centerpiece

#### Scenario: Hero re-fetches on municipality change
- GIVEN the Hero is showing today's digit for Bucaramanga
- WHEN the user changes the municipality selector to Floridablanca
- THEN the Hero re-fetches
- AND the new value reflects Floridablanca's rotation

### REQ-FE-003: Input — plate field with live last-digit reveal

The Input MUST include a plate text field. As the user types, the system MUST display the last detected digit live (computed by the same algorithm as the plate parser, but in-browser). The Input MUST include a municipality selector (default Bucaramanga, values: Bucaramanga, Floridablanca, Girón, Piedecuesta). The Input MUST include a date input (default today, accepts any future date).

#### Scenario: Live digit reveal while typing
- GIVEN the user types "ABC1" into the plate field
- WHEN each character is entered
- THEN the live digit indicator updates to "1"
- WHEN the user appends "2" making it "ABC12"
- THEN the indicator updates to "2"

#### Scenario: User types an invalid plate
- GIVEN the user types "XXX" into the plate field
- WHEN the field is blurred or the form is submitted
- THEN the Input shows a friendly inline validation message
- AND the Result component stays hidden
- AND no API call is made

#### Scenario: Municipality selector defaults to Bucaramanga
- GIVEN a fresh page load (no localStorage state)
- WHEN the page renders
- THEN the municipality selector shows "Bucaramanga" as the default

#### Scenario: Date input defaults to today
- GIVEN a fresh page load
- WHEN the page renders
- THEN the date input shows today's date in the user's local timezone

### REQ-FE-004: Result state-transition

The Result MUST animate in (state-transition micro-interaction) when the API returns 200. The animation reflects the restriction status: a distinct visual state for restricted vs unrestricted. Copy is generic.

#### Scenario: Result animates in for a valid query
- GIVEN the user submits a valid plate + today's date + Bucaramanga
- WHEN the API returns HTTP 200
- THEN the Result component animates in
- AND the visual state reflects `restricted` (e.g., one color/state for restricted, another for unrestricted)
- AND the copy is generic ("tienes restricción" / "no tienes restricción")

#### Scenario: Result re-renders on parameter change
- GIVEN a result is visible
- WHEN the user changes the plate, municipality, or date and resubmits
- THEN the Result re-renders with the new outcome
- AND the state-transition animation plays again

### REQ-FE-005: localStorage persistence

The system MUST persist the last query (plate, municipality, date) in `localStorage`. On page load, the system MUST re-hydrate the last query and re-run it. If no prior state exists, the page loads with no prefill.

#### Scenario: Last query is restored on reload
- GIVEN the user previously submitted `ABC123` + Bucaramanga + 2026-06-15
- AND the result is visible
- WHEN the user reloads the page
- THEN the plate field shows "ABC123"
- AND the municipality selector shows "Bucaramanga"
- AND the date input shows 2026-06-15
- AND the result is restored (re-fetched on load)

#### Scenario: First-time visit has no prefill
- GIVEN a user opens the page for the first time (no localStorage entry)
- WHEN the page loads
- THEN the plate field is empty
- AND the municipality selector is Bucaramanga (default)
- AND the date input is today (default)

### REQ-FE-006: Error rendering

The system MUST render 4xx and 404 API responses as friendly inline messages. No technical error text is shown. The system MUST NOT show `formato_detectado` in the DOM under any circumstance.

#### Scenario: 404 rotation_unknown is shown as a friendly hint
- GIVEN the API returns HTTP 404 with `error: "rotation_unknown"`
- WHEN the response is rendered
- THEN the Result area shows "no tenemos datos de la rotación vigente" with a hint to check back later
- AND no false-negative restriction message is shown

#### Scenario: 400 bad_plate is shown as an inline validation message
- GIVEN the API returns HTTP 400 with `error: "bad_plate"`
- WHEN the response is rendered
- THEN the Input shows a friendly inline validation message
- AND no false-restriction is shown

#### Scenario: formato_detectado is never in the DOM
- GIVEN any page state (initial load, after a query, on error, on festivo)
- WHEN the DOM is inspected (e.g., `document.body.innerText`)
- THEN the string "formato_detectado" does not appear
- AND the string "oficial" / "diplomatico" / "fuerza_publica" never appears as a user-facing label

### REQ-FE-007: Responsive layout

The system MUST be mobile-first and MUST be usable on a 360px-wide viewport. All three components (Hero, Input, Result) MUST be reachable and operable at 360px width. No horizontal scrolling.

#### Scenario: Page is usable at 360px width
- GIVEN the viewport is 360px wide
- WHEN the page is rendered
- THEN no horizontal scrollbar appears
- AND the Hero, Input, and Result components are fully visible and operable
- AND all controls (text field, selectors, buttons) meet a minimum touch target of 44×44 px

### REQ-FE-008: Tooling — pnpm only

The system MUST use `pnpm` for any JS tooling (package manager, scripts, lockfile). The repository MUST NOT contain a `package-lock.json` (npm lockfile) or a `yarn.lock`. Tooling scripts in `package.json` MUST reference `pnpm` (e.g., `"dev": "pnpm ..."` is unnecessary because `pnpm` is the runner; but any script that runs npm commands is forbidden).

#### Scenario: Lockfile is pnpm
- GIVEN the repository has a JS project
- WHEN the lockfile directory is inspected
- THEN `pnpm-lock.yaml` exists
- AND `package-lock.json` does NOT exist
- AND `yarn.lock` does NOT exist

#### Scenario: Scripts do not invoke npm directly
- GIVEN the `package.json` is inspected
- WHEN scripts are listed
- THEN no script contains the substring "npm " (npm as a command)
