# Plate Parser — Delta Spec

**Capability**: `plate-parser`
**Change**: `2026-06-10-pico-y-placa-bucaramanga`
**Status**: ADDED
**Date**: 2026-06-10

## Purpose

A pure, side-effect-free module that classifies a Colombian vehicle plate string and extracts the last numeric digit using a deterministic right-to-left scan. The output drives the restriction lookup (`last_digit`) and analytics (`formato_detectado`); `formato_detectado` is informational and never affects the rule. The module is the highest-leverage piece of the system: every API call and every UI render depends on it. It is built strict-TDD with 100% line + branch coverage on the rule.

## ADDED Requirements

### REQ-PP-001: Input normalization

The system MUST accept any string whose normalized form is ≤ 32 characters. Normalization MUST: (a) collapse internal ASCII whitespace runs to a single space, (b) remove the separator characters ASCII dot (`.`), ASCII dash (`-`), and middle-dot (`·`), (c) uppercase all ASCII letters. The original input is not preserved.

#### Scenario: Mixed case is uppercased
- GIVEN the input "AbC123"
- WHEN parse_placa is called
- THEN placa_normalized == "ABC123"

#### Scenario: ASCII dot is stripped
- GIVEN the input "abc.123"
- WHEN parse_placa is called
- THEN placa_normalized == "ABC123"

#### Scenario: ASCII dash is stripped
- GIVEN the input "abc-123"
- WHEN parse_placa is called
- THEN placa_normalized == "ABC123"

#### Scenario: Middle-dot is stripped
- GIVEN the input "abc·123"
- WHEN parse_placa is called
- THEN placa_normalized == "ABC123"

#### Scenario: Internal whitespace is collapsed
- GIVEN the input "D  AB  123"
- WHEN parse_placa is called
- THEN placa_normalized == "D AB 123"

#### Scenario: Length cap is enforced
- GIVEN a 33-character input after normalization
- WHEN parse_placa is called
- THEN a validation error of type "too_long" is raised

### REQ-PP-002: Last-digit extraction (right-to-left scan)

The system MUST extract `last_digit` by scanning the normalized string from RIGHT to LEFT and returning the first character where `c.isdigit()`. The result is an integer in `0..9`. If no digit exists, the system MUST raise a validation error.

#### Scenario: Standard particular plate
- GIVEN the input "ABC123"
- WHEN parse_placa is called
- THEN last_digit == 3

#### Scenario: Motorcycle with trailing letter
- GIVEN the input "ABC12D"
- WHEN parse_placa is called
- THEN last_digit == 2

#### Scenario: Older motorcycle (no trailing letter)
- GIVEN the input "ABC12"
- WHEN parse_placa is called
- THEN last_digit == 2

#### Scenario: Trailer with internal whitespace
- GIVEN the input "R 12345"
- WHEN parse_placa is called
- THEN last_digit == 5

#### Scenario: Diplomatic plate
- GIVEN the input "D AB 123"
- WHEN parse_placa is called
- THEN last_digit == 3

#### Scenario: Official plate
- GIVEN the input "OAB 123"
- WHEN parse_placa is called
- THEN last_digit == 3

#### Scenario: Mission plate
- GIVEN the input "M AB 123"
- WHEN parse_placa is called
- THEN last_digit == 3

#### Scenario: Temporary import plate
- GIVEN the input "T 1234"
- WHEN parse_placa is called
- THEN last_digit == 4

#### Scenario: No digit present raises "no_digit"
- GIVEN the input "ABC"
- WHEN parse_placa is called
- THEN a validation error of type "no_digit" is raised

#### Scenario: Empty string raises "empty"
- GIVEN the input ""
- WHEN parse_placa is called
- THEN a validation error of type "empty" is raised

#### Scenario: Whitespace + separators only raises "empty"
- GIVEN the input "  -  ·  "
- WHEN parse_placa is called
- THEN a validation error of type "empty" is raised

### REQ-PP-003: Formato classification (8 categories, deterministic order)

The system MUST classify every accepted input into exactly one of 8 categories: `particular | moto | oficial | diplomatico | remolque | temporal | fuerza_publica | desconocido`. The classifier MUST apply rules in this fixed order; the first rule that matches wins. Rules are evaluated against the normalized string.

| # | Rule (applied in order) | Category |
|---|---|---|
| 1 | Normalized starts with `R` followed by a digit (e.g., `R 12345`) | `remolque` |
| 2 | Normalized starts with `T` followed by a digit (e.g., `T 1234`) | `temporal` |
| 3 | Normalized starts with `FAC` | `fuerza_publica` |
| 4 | First 4 chars are digits, then ASCII dash, then 4 digits (e.g., `12-3456`) | `fuerza_publica` |
| 5 | First char ∈ {`D`,`C`,`M`} and matches `[DCM] [A-Z]{2} [0-9]{1,4}` shape | `diplomatico` |
| 6 | First 3 chars are letters and the 3rd char is the only letter before digits (e.g., `OAB 123`) | `oficial` |
| 7 | Matches `[A-Z]{3}[0-9]{2}[A-Z]?` with no whitespace (e.g., `ABC12D`, `ABC12`) | `moto` |
| 8 | Matches `[A-Z]{3}[0-9]{3}` with no whitespace (e.g., `ABC123`) | `particular` |
| 9 | Fallback | `desconocido` |

`formato_detectado` MUST NOT influence `last_digit`. The parser MUST accept diplomatic, official, consular, mission, and temporary-import plates (they are subject to the rule per the 2024 metropolitan decree).

#### Scenario: Particular classification
- GIVEN the input "ABC123"
- WHEN parse_placa is called
- THEN formato_detectado == "particular"

#### Scenario: Moto with trailing letter
- GIVEN the input "ABC12D"
- WHEN parse_placa is called
- THEN formato_detectado == "moto"

#### Scenario: Moto without trailing letter
- GIVEN the input "ABC12"
- WHEN parse_placa is called
- THEN formato_detectado == "moto"

#### Scenario: Oficial classification
- GIVEN the input "OAB 123"
- WHEN parse_placa is called
- THEN formato_detectado == "oficial"

#### Scenario: Diplomatico D-prefix
- GIVEN the input "D AB 123"
- WHEN parse_placa is called
- THEN formato_detectado == "diplomatico"

#### Scenario: Diplomatico C-prefix
- GIVEN the input "C AB 123"
- WHEN parse_placa is called
- THEN formato_detectado == "diplomatico"

#### Scenario: Diplomatico M-mission
- GIVEN the input "M AB 123"
- WHEN parse_placa is called
- THEN formato_detectado == "diplomatico"

#### Scenario: Remolque classification
- GIVEN the input "R 12345"
- WHEN parse_placa is called
- THEN formato_detectado == "remolque"

#### Scenario: Temporal classification
- GIVEN the input "T 1234"
- WHEN parse_placa is called
- THEN formato_detectado == "temporal"

#### Scenario: Fuerza publica FAC prefix
- GIVEN the input "FAC 123456"
- WHEN parse_placa is called
- THEN formato_detectado == "fuerza_publica"

#### Scenario: Fuerza publica national-police shape
- GIVEN the input "12-3456"
- WHEN parse_placa is called
- THEN formato_detectado == "fuerza_publica"

#### Scenario: Desconocido fallback
- GIVEN the input "ZZ 9999"
- WHEN parse_placa is called
- THEN formato_detectado == "desconocido"

### REQ-PP-004: Output contract

The system SHALL return a named tuple `(last_digit: int, formato_detectado: str, placa_normalized: str)`. `placa_normalized` is the canonical form per REQ-PP-001. `formato_detectado` is one of the 8 locked values per REQ-PP-003. The function is pure: no I/O, no exceptions beyond the listed validation errors, deterministic for any given input.

#### Scenario: Standard return tuple
- GIVEN the input "abc 123"
- WHEN parse_placa is called
- THEN the return value is `(3, "particular", "ABC123")`

#### Scenario: Classification never alters last_digit
- GIVEN the input "OAB 123" (oficial)
- WHEN parse_placa is called
- THEN last_digit == 3
- AND formato_detectado == "oficial"
- AND placa_normalized == "OAB 123"
