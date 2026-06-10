"""Plate parser — extract last digit and classify Colombian vehicle plates.

Pure-function module. No I/O, no side effects.
"""

import re
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Output contract (REQ-PP-004)
# ---------------------------------------------------------------------------

_VALID_FORMATS = frozenset({
    "particular",
    "moto",
    "oficial",
    "diplomatico",
    "remolque",
    "temporal",
    "fuerza_publica",
    "desconocido",
})


class ParseResult(NamedTuple):
    """Return value from parse_placa()."""

    last_digit: int
    formato_detectado: str
    placa_normalized: str


class PlateValidationError(ValueError):
    """Raised when a plate string fails validation.

    Attributes:
        error_type: One of 'empty', 'too_long', 'no_digit'.
    """

    def __init__(self, error_type: str) -> None:
        self.error_type = error_type
        super().__init__(f"Plate validation error: {error_type}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_placa(raw: str) -> ParseResult:
    """Parse a Colombian vehicle plate string.

    Returns a ParseResult with last_digit, formato_detectado,
    and placa_normalized. Raises PlateValidationError on invalid input.
    """
    # --- normalization (REQ-PP-001) ------------------------------------------
    normalized = _normalize(raw)

    # Check empty (after normalization)
    if not normalized:
        raise PlateValidationError("empty")

    # Check length cap
    if len(normalized) > 32:
        raise PlateValidationError("too_long")

    # --- last-digit extraction (REQ-PP-002) ----------------------------------
    last_digit = _extract_last_digit(normalized)
    if last_digit is None:
        raise PlateValidationError("no_digit")

    # --- formato classification (REQ-PP-003) ---------------------------------
    # Classification uses a form that preserves dashes for fuerza_publica
    # police-shape matching (rule 4), but strips spaces for other rules.
    classified_form = _classify_form(raw)
    formato = _classify(classified_form, normalized)

    return ParseResult(last_digit, formato, normalized)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Characters removed during normalization (REQ-PP-001-b).
_SEPARATORS = str.maketrans("", "", ".-·")


def _normalize(s: str) -> str:
    """Apply REQ-PP-001 normalization: uppercase, strip separators,
    collapse whitespace, then produce a compact form (no spaces).

    The compact form is needed for classification rules 7-8
    and for the placa_normalized output field.
    """
    s = s.upper()
    # Remove separators: dot, dash, middle-dot
    s = s.translate(_SEPARATORS)
    # Collapse whitespace runs to single space, then strip
    s = re.sub(r"\s+", " ", s).strip()
    # Remove all spaces for compact form
    s = s.replace(" ", "")
    return s


def _classify_form(s: str) -> str:
    """Build the form used for classification matching.

    Unlike _normalize(), this KEEPS ASCII dashes so rule 4
    (national-police shape ``12-3456``) still matches.
    """
    s = s.upper()
    # Remove dots and middle-dots, but KEEP dashes
    s = s.translate(str.maketrans("", "", ".·"))
    # Collapse whitespace, strip
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_last_digit(s: str) -> int | None:
    """Scan RIGHT to LEFT, return first digit as int, or None."""
    for ch in reversed(s):
        if ch.isdigit():
            return int(ch)
    return None


# ---------------------------------------------------------------------------
# Formato classifier — 8 categories, deterministic order (REQ-PP-003)
# ---------------------------------------------------------------------------

def _classify(classified_form: str, compact: str) -> str:
    """Apply the 8-rule classifier in fixed priority order.

    Args:
        classified_form: Uppercase with whitespace collapsed, dashes kept.
        compact: Fully-compact form (no separators, no spaces).
    """

    # Rule 1: Remolque — starts with 'R' followed by a digit
    #         (whitespace between R and digit is allowed, already
    #          collapsed in classified_form)
    if _match_r_t_digit(compact):
        return "remolque"

    # Rule 2: Temporal — starts with 'T' followed by a digit
    if _match_r_t_digit(compact, prefix="T"):
        return "temporal"

    # Rule 3: Fuerza Pública — FAC prefix
    if compact.startswith("FAC"):
        return "fuerza_publica"

    # Rule 4: Fuerza Pública — national-police shape (digits, dash, digits)
    #         Checked against classified_form because dashes are kept there.
    #         The spec says "4 digits, dash, 4 digits" but the example is
    #         "12-3456" (2+4). Use 2-4 digits + dash + 4 digits as a safe
    #         middle ground that covers both.
    #         TODO: Verify actual fuerza_publica plate format with DTB/AMB.
    if re.fullmatch(r"\d{2,4}-\d{4}", classified_form):
        return "fuerza_publica"

    # Rule 5: Diplomático — [DCM] [A-Z]{2} [0-9]{1,4} shape
    if _match_diplomatico(compact):
        return "diplomatico"

    # Rule 6: Oficial — first 3 chars are letters, 3rd is last letter before digits,
    #         and there is whitespace between the letter block and digit block
    #         in the classified form (distinguishes from particular).
    if _match_oficial(classified_form, compact):
        return "oficial"

    # Rule 7: Moto — [A-Z]{3}[0-9]{2}[A-Z]?  (no whitespace)
    if re.fullmatch(r"[A-Z]{3}\d{2}[A-Z]?", compact):
        return "moto"

    # Rule 8: Particular — [A-Z]{3}[0-9]{3}  (no whitespace)
    if re.fullmatch(r"[A-Z]{3}\d{3}", compact):
        return "particular"

    # Rule 9: Fallback
    return "desconocido"


# --- Rule-specific helpers --------------------------------------------------


def _match_r_t_digit(compact: str, prefix: str = "R") -> bool:
    """Check if compact form starts with *prefix* immediately followed by a digit.

    Covers rules 1 (remolque, prefix='R') and 2 (temporal, prefix='T').

    Precondition: ``compact`` always contains at least one digit, so if it
    starts with *prefix* the length is always ≥ 2.
    """
    return compact.startswith(prefix) and compact[1].isdigit()


def _match_diplomatico(compact: str) -> bool:
    """Rule 5: compact matches ``[DCM][A-Z]{2}[0-9]{1,4}``."""
    return bool(re.fullmatch(r"[DCM][A-Z]{2}\d{1,4}", compact))


def _match_oficial(classified_form: str, compact: str) -> bool:
    """Rule 6: First 3 chars are letters and the 3rd char is the ONLY letter
    before digits. Additionally, the classified_form must show whitespace
    between the letter and digit groups (distinguishes from particular).

    Colombian official plates start with 'O' (Oficial).
    Example: ``OAB 123`` → classified ``OAB 123``, compact ``OAB123``.
    """
    # Must have at least 3 letters followed by digits in compact form,
    # AND the plate must start with 'O' (oficial prefix).
    if not re.fullmatch(r"O[A-Z]{2}\d+", compact):
        return False

    # The classified form must contain a space between the 3-letter prefix
    # and the digit group, confirming it is NOT a compact particular plate.
    return bool(re.fullmatch(r"O[A-Z]{2}\s+\d+", classified_form))
